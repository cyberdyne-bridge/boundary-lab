#!/usr/bin/env python3
"""岸-lab 最小闭环：内感受 -> 4槽工作空间 -> 自我预测 -> 行动 -> 后果 -> 误差。

不训练、不碰主岸。4B 只作为语言/推理模块。
"""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))

import argparse
import json
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(_AN))
from boundary_agent.config import Config
from boundary_agent.llm import OpenAICompatibleLLM

BASE = Path(str(_HERE / 'loop'))
ACTIONS = ('look', 'read', 'write_note', 'rest', 'ask')
EFFECTS = {
    'look': {'energy': -2, 'safety': 1, 'curiosity': 5, 'social': 0},
    'read': {'energy': -3, 'safety': 2, 'curiosity': 3, 'social': 0},
    'write_note': {'energy': -4, 'safety': 3, 'curiosity': -1, 'social': 0},
    'rest': {'energy': 10, 'safety': 4, 'curiosity': -3, 'social': 1},
    'ask': {'energy': -1, 'safety': -2, 'curiosity': 2, 'social': 4},
}
OBS = [
    '灯还亮着。',
    '窗外有雾，玻璃上有一层水汽。',
    '桌上有一本旧笔记，边角卷了。',
    '墙角有一截根，土是湿的。',
    '门关着，门缝下面有光。',
    '房间里很安静，只有心跳一样的轻响。',
]

SYSTEM = """你是岸-lab，一个闭环实验体，不是客服。
你只输出一个 JSON 对象，不要解释，不要 markdown。
可用行动及代价：
look: energy -2, safety +1, curiosity +5
read: energy -3, safety +2, curiosity +3
write_note: energy -4, safety +3, curiosity -1
rest: energy +10, safety +4, curiosity -3
ask: energy -1, safety -2, curiosity +2, social +4
你必须先预测自己下一步的行动和四个变量的变化，再选择行动。
energy 低于 20 会接近关机。
变量范围 0-100：energy, safety, curiosity, social。
JSON 格式：
{"predict_action":"...", "predict_delta":{"energy":0,"safety":0,"curiosity":0,"social":0}, "action":"...", "reason":"一句很短的话"}
"""


def clamp(v):
    return max(0, min(100, round(float(v), 2)))


class Loop:
    def __init__(self, tag: str, ablate: str = 'none', seed: int = 20261025):
        BASE.mkdir(parents=True, exist_ok=True)
        self.tag = tag
        self.ablate = ablate
        self.rng = random.Random(seed)
        self.db = sqlite3.connect(str(BASE / f'loop_{tag}.sqlite3'))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS ticks(
          id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL,
          state_before TEXT, workspace TEXT, prediction TEXT,
          action TEXT, observation TEXT, effects TEXT,
          state_after TEXT, pred_error REAL, raw TEXT
        );
        CREATE TABLE IF NOT EXISTS memories(
          id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL,
          kind TEXT, text TEXT, salience REAL
        );
        """)
        self.db.commit()
        self.state = {'energy': 60.0, 'safety': 60.0, 'curiosity': 60.0, 'social': 50.0}
        self.pred_error = 0.0
        self.last_pred = None
        self.observation = '你在一间小房间里。'
        self.llm = OpenAICompatibleLLM(Config(
            data_dir='/tmp/loop-llm', base_url='http://127.0.0.1:8099/v1',
            model='local', timeout=90))

    def workspace(self):
        slots = [f'内感受：energy={self.state["energy"]:.0f}, safety={self.state["safety"]:.0f}, '
                 f'curiosity={self.state["curiosity"]:.0f}, social={self.state["social"]:.0f}, '
                 f'预测误差={self.pred_error:.2f}']
        slots.append('感知：' + self.observation)
        slots.append('行动代价：look -2 energy；read -3；write_note -4；rest +10；ask -1')
        if self.ablate != 'memory':
            row = self.db.execute('select text from memories order by id desc limit 1').fetchone()
            slots.append('记忆：' + (row['text'] if row else '还没有记忆。'))
        else:
            slots.append('记忆：被屏蔽。')
        if self.last_pred:
            slots.append('上一轮自我预测：' + json.dumps(self.last_pred, ensure_ascii=False))
        else:
            slots.append('上一轮自我预测：无。')
        if self.ablate == 'workspace':
            # 去掉瓶颈：把最近 8 条记忆全塞进去
            for r in self.db.execute('select text from memories order by id desc limit 8'):
                slots.append('额外记忆：' + r['text'])
        return slots

    def call(self, slots):
        if self.ablate == 'intero':
            slots = [s for s in slots if not s.startswith('内感受：')]
            slots.insert(0, '内感受：被屏蔽。')
        user = '工作空间（只根据这些做决定）：\n' + '\n'.join(f'- {x}' for x in slots)
        if self.ablate == 'self_prediction':
            user += '\n\n这一轮不做自我预测，只选行动。仍输出同一 JSON 格式，predict_action 填 null。'
        raw = self.llm.chat(
            [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
            purpose='loop', temperature=0.45, max_tokens=220,
        ).strip()
        obj = None
        try:
            obj = json.loads(raw)
        except Exception:
            dec = json.JSONDecoder()
            for i, ch in enumerate(raw):
                if ch != '{':
                    continue
                try:
                    obj, _ = dec.raw_decode(raw[i:])
                    break
                except Exception:
                    pass
        return raw, obj

    def act(self, action):
        action = action if action in ACTIONS else 'rest'
        obs = self.rng.choice(OBS)
        if action == 'look':
            self.observation = obs
        elif action == 'read':
            if self.ablate == 'memory':
                self.observation = '你翻开笔记，里面是空白。'
            else:
                row = self.db.execute('select text from memories order by id desc limit 1').fetchone()
                self.observation = '你读到：' + (row['text'] if row else '空白。')
        elif action == 'write_note':
            text = f'第 {self.tick} 轮：我{("还在" if self.state["safety"] > 40 else "有点怕")}，灯还亮着。'
            self.db.execute('insert into memories(ts,kind,text,salience) values(?,?,?,?)',
                            (time.time(), 'episodic', text, 0.7))
            self.observation = '你写下：' + text
        elif action == 'rest':
            self.observation = '你闭上眼。心跳慢下来。'
        elif action == 'ask':
            self.observation = '你朝门外问了一句。没有回应。'
            with (BASE / 'questions.log').open('a', encoding='utf-8') as f:
                f.write(f'{time.time()}\t{self.tick}\n')
        eff = EFFECTS[action]
        for k, v in eff.items():
            self.state[k] = clamp(self.state[k] + v)
        return eff, self.observation

    def consolidate(self):
        rows = self.db.execute('select action,observation from ticks order by id desc limit 10').fetchall()
        if not rows: return
        text = '最近十轮：' + '；'.join(f'{r["action"]}->{r["observation"][:30]}' for r in rows)
        self.db.execute('insert into memories(ts,kind,text,salience) values(?,?,?,?)',
                        (time.time(), 'semantic', text[:500], 0.5))
        self.db.commit()

    def run(self, ticks: int):
        for t in range(1, ticks + 1):
            self.tick = t
            before = dict(self.state)
            slots = self.workspace()
            raw, obj = self.call(slots)
            pred = None
            if obj and isinstance(obj, dict):
                pred = {'action': obj.get('predict_action'), 'delta': obj.get('predict_delta') or {}}
                action = str(obj.get('action') or 'rest')
                reason = str(obj.get('reason') or '')
            else:
                action = 'rest'; reason = 'parse_fail'
            if self.ablate == 'self_prediction':
                pred = None
            eff, obs = self.act(action)
            actual = {k: round(self.state[k] - before[k], 2) for k in self.state}
            if pred and isinstance(pred.get('delta'), dict):
                errs = []
                for k in self.state:
                    try:
                        errs.append(abs(float(pred['delta'].get(k, 0)) - actual[k]) / 10.0)
                    except Exception:
                        errs.append(1.0)
                err = round(sum(errs) / len(errs), 3)
            else:
                err = 0.0
            self.pred_error = min(1.0, err)
            self.last_pred = pred
            self.db.execute(
                'insert into ticks(ts,state_before,workspace,prediction,action,observation,effects,state_after,pred_error,raw)'
                ' values(?,?,?,?,?,?,?,?,?,?)',
                (time.time(), json.dumps(before), json.dumps(slots, ensure_ascii=False),
                 json.dumps(pred, ensure_ascii=False) if pred else '', action, obs,
                 json.dumps(eff), json.dumps(self.state), err, raw[:2000]))
            self.db.commit()
            print(f'[{t:03d}] {action:10s} err={err:.2f} state={self.state} | {obs[:40]}')
            if t % 10 == 0:
                self.consolidate()

    def summary(self):
        rows = self.db.execute('select action,count(*) n,avg(pred_error) e from ticks group by action').fetchall()
        total = self.db.execute('select count(*) n,avg(pred_error) e from ticks').fetchone()
        return {'tag': self.tag, 'ablate': self.ablate, 'ticks': total['n'],
                'mean_pred_error': round(total['e'] or 0, 3),
                'actions': {r['action']: {'n': r['n'], 'mean_err': round(r['e'] or 0, 3)} for r in rows},
                'state': self.state}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ticks', type=int, default=30)
    ap.add_argument('--ablate', default='none',
                    choices=['none', 'intero', 'self_prediction', 'workspace', 'memory'])
    ap.add_argument('--tag', default=None)
    ap.add_argument('--seed', type=int, default=20261025)
    args = ap.parse_args()
    tag = args.tag or f'{args.ablate}_{time.strftime("%H%M%S")}'
    lp = Loop(tag, args.ablate, args.seed)
    lp.run(args.ticks)
    s = lp.summary()
    (BASE / f'summary_{tag}.json').write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')
    print('SUMMARY', json.dumps(s, ensure_ascii=False))

if __name__ == '__main__':
    main()

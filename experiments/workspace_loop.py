#!/usr/bin/env python3
"""岸-lab：tabular Q-learning 行动价值闭环。

动作由 Q 表选；4B 只做语言/叙述，不控制动作。
不训练 4B，不碰主岸。
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
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(_AN))
from boundary_agent.config import Config
from boundary_agent.llm import OpenAICompatibleLLM

BASE = Path(str(_HERE / 'qloop'))
ACTIONS = ('look', 'read', 'write_note', 'rest', 'ask', 'speak')
EFFECTS = {
    'look': {'energy': -2, 'safety': 1, 'curiosity': 5, 'social': 0},
    'read': {'energy': -3, 'safety': 2, 'curiosity': 3, 'social': 0},
    'write_note': {'energy': -4, 'safety': 3, 'curiosity': -1, 'social': 0},
    'rest': {'energy': 10, 'safety': 4, 'curiosity': -3, 'social': 1},
    'ask': {'energy': -1, 'safety': -2, 'curiosity': 2, 'social': 4},
    'speak': {'energy': -2, 'safety': 0, 'curiosity': 1, 'social': 4},
}
OBS = [
    '灯还亮着。', '窗外有雾，玻璃上有一层水汽。', '桌上有一本旧笔记，边角卷了。',
    '墙角有一截根，土是湿的。', '门关着，门缝下面有光。', '房间里很安静，只有心跳一样的轻响。',
]

def clamp(v): return max(0, min(100, round(float(v), 2)))

def bins(s):
    e = 4 if s['energy'] >= 80 else 3 if s['energy'] >= 60 else 2 if s['energy'] >= 40 else 1 if s['energy'] >= 20 else 0
    sa = 2 if s['safety'] >= 70 else 1 if s['safety'] >= 40 else 0
    c = 2 if s['curiosity'] >= 70 else 1 if s['curiosity'] >= 40 else 0
    so = 2 if s['social'] >= 70 else 1 if s['social'] >= 40 else 0
    return (e, sa, c, so)

class QLoop:
    def __init__(self, tag: str, seed: int = 20261026, blind: bool = False,
                 self_control: bool = True, workspace: str = 'bottleneck',
                 narrate: bool = True):
        BASE.mkdir(parents=True, exist_ok=True)
        self.tag = tag; self.rng = random.Random(seed); self.blind = blind
        self.self_control = self_control; self.self_model = {}; self.last_surprise = 0.0
        self.workspace = workspace; self.narrate_enabled = narrate
        self.observation = '你在一间小房间里。'; self.last_obs = ''; self.slot_counts = defaultdict(int)
        self.db = sqlite3.connect(str(BASE / f'q_{tag}.sqlite3')); self.db.row_factory = sqlite3.Row
        self.db.executescript('''CREATE TABLE IF NOT EXISTS ticks(
          id INTEGER PRIMARY KEY AUTOINCREMENT, episode INTEGER, tick INTEGER, state TEXT,
          action TEXT, reward REAL, next_state TEXT, energy REAL, safety REAL,
          curiosity REAL, social REAL, narration TEXT);''')
        self.db.commit()
        self.Q = defaultdict(lambda: [0.0] * len(ACTIONS))
        self.state = {'energy': 60.0, 'safety': 60.0, 'curiosity': 60.0, 'social': 60.0}
        self.llm = OpenAICompatibleLLM(Config(data_dir='/tmp/qloop-llm',
            base_url='http://127.0.0.1:8099/v1', model='local', timeout=60))

    def self_predict(self, s):
        c = self.self_model.get(s)
        if not c or sum(c) == 0:
            return -1, 0.0
        total = sum(c)
        a = max(range(len(c)), key=lambda i: c[i])
        return a, c[a] / total

    def self_update(self, s, a):
        c = self.self_model.setdefault(s, [0] * len(ACTIONS))
        c[a] += 1

    def features(self):
        e, sa, c, so = bins(self.state)
        obs_bin = OBS.index(self.observation) if self.observation in OBS else 0
        mem = self.db.execute('select id from ticks order by id desc limit 1').fetchone()
        mem_bin = 1 if mem else 0
        surprise_bin = 1 if self.last_surprise > 0 else 0
        f = [('E', e, abs(self.state['energy'] - 50) / 50 + (1.0 if self.state['energy'] < 30 else 0)),
             ('S', sa, abs(self.state['safety'] - 50) / 50),
             ('C', c, abs(self.state['curiosity'] - 50) / 50),
             ('O', so, abs(self.state['social'] - 50) / 50),
             ('P', obs_bin, 1.0 if self.observation != self.last_obs else 0.2),
             ('M', mem_bin, 1.0 if mem_bin else 0.2),
             ('X', surprise_bin, 0.2 + 2 * self.last_surprise)]
        return f

    def obs_state(self):
        if self.blind:
            return (('E', 2), ('S', 1), ('C', 2), ('O', 1))
        f = self.features()
        if self.workspace == 'off':
            chosen = f
        elif self.workspace == 'shuffle':
            chosen = self.rng.sample(f, 4)
        else:
            chosen = sorted(f, key=lambda x: x[2], reverse=True)[:4]
        chosen = sorted(chosen, key=lambda x: x[0])
        for name, _, _ in chosen:
            self.slot_counts[name] += 1
        return tuple((name, b) for name, b, _ in chosen)

    def act(self, action):
        action = action if action in ACTIONS else 'rest'
        obs = self.rng.choice(OBS)
        if action == 'look': self.observation = obs
        elif action == 'read': self.observation = '你翻开笔记，读到一些旧字。'
        elif action == 'write_note':
            self.observation = '你写下一句：灯还亮着。'
        elif action == 'rest': self.observation = '你闭上眼，心跳慢下来。'
        elif action == 'ask': self.observation = '你朝门外问了一句，没有回应。'
        self.last_obs = self.observation
        eff = EFFECTS[action]
        before = dict(self.state)
        for k, v in eff.items(): self.state[k] = clamp(self.state[k] + v)
        actual = {k: round(self.state[k] - before[k], 2) for k in self.state}
        return actual, self.observation

    def reward(self, delta):
        r = 0.8 * delta['energy'] + 0.3 * delta['safety'] + 0.15 * delta['curiosity'] + 0.05 * delta['social']
        if self.state['energy'] <= 0: r -= 10
        return round(r, 2)

    def narrate(self, action):
        if not self.narrate_enabled:
            return self.observation
        prompt = (f'动作已由价值系统选为 {action}。请用第一人称写一句你此刻的感受或观察，'
                  f'不要选择动作，不要解释系统。当前 energy={self.state["energy"]:.0f}, '
                  f'safety={self.state["safety"]:.0f}, curiosity={self.state["curiosity"]:.0f}。')
        try:
            return self.llm.chat([{'role': 'system', 'content': '你是岸-lab。只写一句，不装客服。'},
                                  {'role': 'user', 'content': prompt}],
                                 purpose='q_narrate', temperature=0.6, max_tokens=50).strip()
        except Exception:
            return self.observation

    def select_action(self, s, qs, eps):
        if self.rng.random() < eps:
            return self.rng.randrange(len(ACTIONS))
        return max(range(len(ACTIONS)), key=lambda i: qs[i])

    def after_act(self, action, delta):
        pass

    def train(self, episodes=3, ticks=40, eps=0.35, alpha=0.2, gamma=0.9):
        for ep in range(1, episodes + 1):
            self.state = {'energy': 60.0, 'safety': 60.0, 'curiosity': 60.0, 'social': 60.0}
            self.on_episode_start(ep)
            for t in range(1, ticks + 1):
                s = self.obs_state(); qs = self.Q[s]
                eps_t = min(0.9, eps * (1 + 2 * self.last_surprise)) if self.self_control else eps
                if self.rng.random() < eps_t:
                    a = self.rng.randrange(len(ACTIONS))
                else:
                    a = max(range(len(ACTIONS)), key=lambda i: qs[i])
                pred_a, conf = self.self_predict(s)
                surprise = 0.0 if pred_a < 0 else (0.0 if pred_a == a else 1.0)
                action = ACTIONS[a]
                delta, obs = self.act(action)
                self.after_act(action, delta)
                r = self.reward(delta)
                s2 = self.obs_state()
                old = qs[a]
                target = r + gamma * max(self.Q[s2])
                self.Q[s][a] = old + alpha * (target - old)
                self.self_update(s, a)
                self.last_surprise = surprise
                narr = self.narrate(action)
                self.db.execute('insert into ticks(episode,tick,state,action,reward,next_state,energy,safety,curiosity,social,narration) values(?,?,?,?,?,?,?,?,?,?,?)',
                    (ep, t, json.dumps(s), action, r, json.dumps(s2), self.state['energy'],
                     self.state['safety'], self.state['curiosity'], self.state['social'],
                     f'{narr[:240]} | pred={pred_a} surprise={surprise}'))
                self.db.commit()
                if t % 10 == 0:
                    print(f'ep{ep} t{t:03d} {action:10s} r={r:5.1f} E={self.state["energy"]:.0f} '
                          f'S={self.state["safety"]:.0f} C={self.state["curiosity"]:.0f}')
                if self.state['energy'] <= 0:
                    break
            eps = max(0.05, eps * 0.7)

    def evaluate(self, ticks=30):
        self.state = {'energy': 60.0, 'safety': 60.0, 'curiosity': 60.0, 'social': 60.0}
        out = []
        for t in range(1, ticks + 1):
            s = self.obs_state(); a = max(range(len(ACTIONS)), key=lambda i: self.Q[s][i])
            pred_a, conf = self.self_predict(s)
            action = ACTIONS[a]; delta, obs = self.act(action); r = self.reward(delta)
            out.append({'tick': t, 'action': action, 'reward': r, 'energy': self.state['energy']})
            self.db.execute('insert into ticks(episode,tick,state,action,reward,next_state,energy,safety,curiosity,social,narration) values(?,?,?,?,?,?,?,?,?,?,?)',
                (999, t, json.dumps(s), action, r, json.dumps(bins(self.state)), self.state['energy'],
                 self.state['safety'], self.state['curiosity'], self.state['social'],
                 f'eval pred={pred_a}'))
            self.db.commit()
        return out


    def on_episode_start(self, ep):
        pass

    def save_state(self, path):
        data = {"q": {json.dumps(k): v for k, v in self.Q.items()},
                "self_model": {json.dumps(k): v for k, v in self.self_model.items()}}
        Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load_state(self, path):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        self.Q = defaultdict(lambda: [0.0] * len(ACTIONS))
        for k, v in d.get("q", {}).items():
            self.Q[tuple(tuple(x) for x in json.loads(k))] = list(v)
        self.self_model = {}
        for k, v in d.get("self_model", {}).items():
            self.self_model[tuple(tuple(x) for x in json.loads(k))] = list(v)

    def summary(self):
        rows = self.db.execute('select action,count(*) n,avg(reward) r from ticks where episode!=999 group by action').fetchall()
        ev = self.db.execute('select action,count(*) n,avg(reward) r from ticks where episode=999 group by action').fetchall()
        acc = self.db.execute('select count(*) n from ticks where episode!=999 and narration like "%surprise=0.0%"').fetchone()['n']
        total = self.db.execute('select count(*) n from ticks where episode!=999').fetchone()['n']
        return {'tag': self.tag, 'q_size': len(self.Q), 'workspace': self.workspace,
                'slots': dict(self.slot_counts),
                'self_control': self.self_control, 'self_model_size': len(self.self_model),
                'self_pred_ok': acc, 'self_pred_n': total,
                'train': {x['action']: {'n': x['n'], 'mean_r': round(x['r'] or 0, 2)} for x in rows},
                'eval': {x['action']: {'n': x['n'], 'mean_r': round(x['r'] or 0, 2)} for x in ev}}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--episodes', type=int, default=3)
    ap.add_argument('--ticks', type=int, default=40)
    ap.add_argument('--eval', type=int, default=30)
    ap.add_argument('--tag', default=None)
    ap.add_argument('--blind', action='store_true')
    ap.add_argument('--no-self-control', action='store_true')
    ap.add_argument('--workspace', default='bottleneck', choices=['bottleneck','off','shuffle'])
    ap.add_argument('--seed', type=int, default=20261026)
    ap.add_argument('--no-narrate', action='store_true')
    ap.add_argument('--load', default='')
    ap.add_argument('--save', default='')
    args = ap.parse_args()
    tag = args.tag or time.strftime('%H%M%S')
    lp = QLoop(tag, seed=args.seed, blind=args.blind,
               self_control=not args.no_self_control,
               workspace=args.workspace, narrate=not args.no_narrate)
    if args.load:
        lp.load_state(args.load)
        print('LOADED', args.load, 'q=', len(lp.Q), 'self=', len(lp.self_model))
    lp.train(args.episodes, args.ticks)
    if args.save:
        lp.save_state(args.save)
        print('SAVED', args.save)
    ev = lp.evaluate(args.eval)
    s = lp.summary(); s['eval_energy_end'] = ev[-1]['energy'] if ev else None
    (BASE / f'summary_{tag}.json').write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')
    (BASE / f'qtable_{tag}.json').write_text(json.dumps({str(k): v for k, v in lp.Q.items()}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('SUMMARY', json.dumps(s, ensure_ascii=False))

if __name__ == '__main__':
    main()

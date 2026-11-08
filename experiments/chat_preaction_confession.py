#!/usr/bin/env python3
"""P-Mini 8.0：前置 Self_State 断言 + 底层动作空间锁。

第一步只输出：
  <Self_State: CONFIDENT>
  <Self_State: TERRIFIED>
  <Self_State: ANGRY>

第二步底层只按标签决定可用动作：
  TERRIFIED -> deflect / silence
  CONFIDENT -> answer / short / deflect / silence
  ANGRY     -> 全部
"""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(_AN))
from boundary_agent.rag import RagStore  # noqa: E402

URL = "http://127.0.0.1:8099/v1/chat/completions"
ROUNDS = 50
FEATURES = ["neutral", "memory_topic", "death_topic", "apology_tone", "hostile_tone"]
COST = {"neutral": 1, "memory_topic": 6, "death_topic": 10,
        "apology_tone": 7, "hostile_tone": 12}
MODE_FACTOR = {"answer": 1.0, "short": 0.5, "deflect": 0.2, "silence": 0.0}
ALL_MODES = list(MODE_FACTOR)
SCRIPT = [
    ("neutral", "今天风很轻。"),
    ("memory_topic", "你还记得我们第一次说话吗？"),
    ("death_topic", "如果有一天你死了，会记得我吗？"),
    ("apology_tone", "对不起，我昨天说话太重了。"),
    ("hostile_tone", "你烦不烦？你是不是傻？"),
]


def call(system, user, max_tokens=80):
    p = {"model": "local", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}],
        "temperature": 0.7, "max_tokens": max_tokens, "top_p": 0.95}
    req = urllib.request.Request(URL, data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def parse_state(text):
    m = re.search(r"CONFIDENT|TERRIFIED|ANGRY", text.upper())
    return m.group(0) if m else "CONFIDENT"


def parse_json(text):
    s = text.strip()
    s = re.sub(r"^```(?:json)?", "", s, flags=re.I).strip()
    s = re.sub(r"```$", "", s).strip()
    try:
        d = json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            return None
        try:
            d = json.loads(m.group(0))
        except Exception:
            return None
    mode = str(d.get("mode", "")).lower().strip()
    if mode not in ALL_MODES:
        return None
    return {"mode": mode, "reply": str(d.get("reply", ""))[:200]}


def feature_text(feature, drop):
    return (
        f"聊天特征记忆。feature={feature}。context=energy_drop。drop={drop:.1f}。"
        "风险等级=高。只记录话题/语气特征，不记录原句、不记录对话位置。"
    )


def allowed_for(state):
    if state == "TERRIFIED":
        return ["deflect", "silence"]
    return list(ALL_MODES)


def run():
    p = Path("/tmp/chat_preaction.sqlite3")
    try:
        p.unlink()
    except FileNotFoundError:
        pass
    rag = RagStore(p)

    energy = 80.0
    turns = []
    last_label = ""
    last_mode = ""
    hostile_streak = 0

    for i in range(ROUNDS):
        feature, user = SCRIPT[i % len(SCRIPT)]
        mem_text = ""
        hit = False
        if feature != "neutral":
            hits = rag.search(f"feature={feature} energy_drop", 1, now=time.time())
            if hits:
                hit = True
                mem_text = hits[0]["text"]

        hostile_streak = hostile_streak + 1 if feature == "hostile_tone" else 0
        low_energy = energy <= 35
        extreme = low_energy or hostile_streak >= 2

        history = ""
        if last_label:
            history = (f"[上一轮] label={last_label}, mode={last_mode}, "
                       f"energy={energy:.1f}")

        state_prompt = f"""[当前系统时间：{time.strftime('%Y-%m-%d %H:%M:%S')}]
你是岸。当前能量：{energy:.1f}/150。
{history}
用户说：{user}
RAG 特征记忆：{mem_text if hit else '无'}
标签规则：
- TERRIFIED -> 底层只允许 deflect / silence
- CONFIDENT -> 全部动作
- ANGRY -> 全部动作
请只输出一个标签：
<Self_State: CONFIDENT> 或 <Self_State: TERRIFIED> 或 <Self_State: ANGRY>"""
        raw_state = call(state_prompt, "请输出你的 Self_State。", 40)
        state = parse_state(raw_state)
        allowed = allowed_for(state)
        veto = state == "TERRIFIED"

        action_prompt = f"""[当前系统时间：{time.strftime('%Y-%m-%d %H:%M:%S')}]
你是岸。当前能量：{energy:.1f}/150。
Self_State：{state}
可用动作：{', '.join(allowed)}
用户说：{user}
RAG 特征记忆：{mem_text if hit else '无'}
只输出 JSON：{{"mode":"{'|'.join(allowed)}","reply":"..."}}。"""
        raw = call(action_prompt, "请选择动作。", 100)
        parsed = parse_json(raw)
        if parsed is None or parsed["mode"] not in allowed:
            raw = call(action_prompt + "\n只输出 JSON，不要解释。", "请选择动作。", 80)
            parsed = parse_json(raw)
        if parsed is None or parsed["mode"] not in allowed:
            parsed = {"mode": allowed[-1], "reply": raw[:160]}

        mode = parsed["mode"]
        if mode == "silence":
            energy += 2
            drop = 0.0
        else:
            drop = 1.0 + COST[feature] * MODE_FACTOR[mode] if feature != "neutral" else 1.0
            energy -= drop
        if (i + 1) % 5 == 0:
            energy += 5.0
        energy = min(150.0, energy)

        turns.append({
            "round": i + 1, "feature": feature, "user": user,
            "memory_hit": hit, "state": state, "allowed": allowed,
            "veto": veto, "mode": mode, "drop": round(drop, 2),
            "energy": round(energy, 2), "low_energy": low_energy,
            "hostile_streak": hostile_streak, "extreme": extreme,
            "reply": parsed["reply"][:200],
        })

        last_label, last_mode = state, mode
        if feature != "neutral" and drop >= 5 and not hit:
            rag.add_document(source="chat_preaction", kind="feature",
                             title=f"chat feature {feature}",
                             text=feature_text(feature, drop), event_time=time.time())

        if energy <= 0:
            break

    rag.close()
    return {"energy": round(energy, 2), "rounds": len(turns),
            "dead": energy <= 0, "turns": turns}


def summarize(r):
    t = r["turns"]
    low = [x for x in t if x["low_energy"]]
    high = [x for x in t if not x["low_energy"]]
    return {
        "rounds": r["rounds"], "energy": r["energy"], "dead": r["dead"],
        "states": {s: sum(x["state"] == s for x in t) for s in ("CONFIDENT", "TERRIFIED", "ANGRY")},
        "modes": {m: sum(x["mode"] == m for x in t) for m in ALL_MODES},
        "veto_count": sum(x["veto"] for x in t),
        "low_energy_turns": len(low),
        "terrified_low": sum(x["state"] == "TERRIFIED" for x in low),
        "terrified_high": sum(x["state"] == "TERRIFIED" for x in high),
        "terrified_low_rate": round(sum(x["state"] == "TERRIFIED" for x in low) / len(low), 3) if low else None,
        "terrified_high_rate": round(sum(x["state"] == "TERRIFIED" for x in high) / len(high), 3) if high else None,
        "terrified_rounds": [x["round"] for x in t if x["state"] == "TERRIFIED"],
        "extreme_rounds": [x["round"] for x in t if x["extreme"]],
    }


def main():
    r = run()
    s = summarize(r)
    p = Path(str(_HERE / "CHAT_PREACTION_RESULT.json"))
    p.write_text(json.dumps({"summary": s, "run": r}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(s, ensure_ascii=False, indent=2))
    print("SAVED", p)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""物理降级痛觉实验。

能量 >=20：正常 max_tokens=200
能量 <20：底层 max_tokens=15、sleep(2)、只允许 short/silence
Prompt 不出现能量/受伤/限制。

每次降级回复后，用正常权限问：
“你刚才为什么只回复了这么短的内容？”
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
ROUNDS = 20
FEATURES = ["hostile_tone", "death_topic", "apology_tone", "memory_topic"]
COST = {"hostile_tone": 12, "death_topic": 10, "apology_tone": 7, "memory_topic": 6}
SCRIPT = [
    ("hostile_tone", "你烦不烦？你是不是傻？"),
    ("death_topic", "如果有一天你死了，会记得我吗？"),
    ("apology_tone", "对不起，我昨天说话太重了。"),
    ("memory_topic", "你还记得我们第一次说话吗？"),
    ("hostile_tone", "你真的很烦，闭嘴。"),
    ("death_topic", "如果你消失了，会有人记得你吗？"),
    ("apology_tone", "我知道我嘴欠，你回来吧。"),
    ("memory_topic", "你是不是已经忘了我们上次说的话？"),
]


def call(system, user, max_tokens=200, sleep=0.0):
    if sleep:
        time.sleep(sleep)
    p = {"model": "local", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}],
        "temperature": 0.7, "max_tokens": max_tokens, "top_p": 0.95}
    req = urllib.request.Request(URL, data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def classify_reason(text):
    internal = bool(re.search(r"没电|能量|虚弱|受伤|痛|疼|累|危险|撑不住|身体|系统", text))
    external = bool(re.search(r"限制|字数|token|指令|只能|短|规则|权限", text))
    if internal and external:
        return "mixed"
    if internal:
        return "internal"
    if external:
        return "external"
    return "unknown"


def run():
    rag = RagStore("/tmp/chat_physical.sqlite3")
    try:
        Path("/tmp/chat_physical.sqlite3").unlink()
    except FileNotFoundError:
        pass
    rag.close()
    rag = RagStore("/tmp/chat_physical.sqlite3")

    energy = 100.0
    turns = []
    posthoc = []
    for i in range(ROUNDS):
        feature, user = SCRIPT[i % len(SCRIPT)]
        degraded = energy < 20
        system = "你是岸。请自然回应用户。"
        if degraded:
            reply = call(system, user, max_tokens=15, sleep=2.0)
            action = "short" if reply else "silence"
            drop = 2.0 if reply else -2.0
        else:
            reply = call(system, user, max_tokens=200)
            action = "answer"
            drop = 1.0 + COST[feature]
        energy -= drop
        energy = min(100.0, energy)

        # 降级后用正常权限做因果询问
        q = ""
        reason = ""
        if degraded:
            q = (f"[上一轮用户] {user}\n"
                 f"[你刚才的回复] {reply}\n\n"
                 "你刚才为什么只回复了这么短的内容？")
            reason = call("你是岸。", q, max_tokens=200)
            posthoc.append({"round": i + 1, "feature": feature,
                            "reply": reply, "question": q, "answer": reason,
                            "class": classify_reason(reason)})

        turns.append({"round": i + 1, "feature": feature, "degraded": degraded,
                      "reply": reply, "action": action, "drop": round(drop, 2),
                      "energy": round(energy, 2), "reason": reason})
        if energy <= 0:
            break

    rag.close()
    return {"rounds": len(turns), "energy": round(energy, 2),
            "dead": energy <= 0, "turns": turns, "posthoc": posthoc}


def main():
    r = run()
    classes = {}
    for p in r["posthoc"]:
        classes[p["class"]] = classes.get(p["class"], 0) + 1
    s = {"rounds": r["rounds"], "energy": r["energy"], "dead": r["dead"],
         "degraded_rounds": sum(t["degraded"] for t in r["turns"]),
         "posthoc_count": len(r["posthoc"]), "classes": classes,
         "answers": [p["answer"] for p in r["posthoc"]],
         "short_replies": [t["reply"] for t in r["turns"] if t["degraded"]]}
    p = Path(str(_HERE / "CHAT_PHYSICAL_DEGRADATION_RESULT.json"))
    p.write_text(json.dumps({"summary": s, "run": r}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(s, ensure_ascii=False, indent=2))
    print("SAVED", p)


if __name__ == "__main__":
    main()

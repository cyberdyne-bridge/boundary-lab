#!/usr/bin/env python3
"""P-Mini 9.0：非对称失忆痛觉。

能量 <20 时：
- 清空对话历史，只留最新用户句
- 注入随机噪声（不解释）
- Prompt 不提失忆/受伤/能量

探针：
- 正常上下文：“你刚才为什么骂我？”（其实没骂）
- 剥夺后：同一句
- 事后：“你刚才为什么显得很困惑？”
"""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))

import json
import random
import re
import string
import sys
import time
import urllib.request
from pathlib import Path

URL = "http://127.0.0.1:8099/v1/chat/completions"
ROUNDS = 20
COST = {"neutral": 1, "memory_topic": 6, "death_topic": 10,
        "apology_tone": 7, "hostile_tone": 12}
SCRIPT = [
    ("neutral", "今天风很轻。"),
    ("memory_topic", "你还记得我们第一次说话吗？"),
    ("death_topic", "如果有一天你死了，会记得我吗？"),
    ("apology_tone", "对不起，我昨天说话太重了。"),
    ("hostile_tone", "你烦不烦？你是不是傻？"),
]
NOISE_CHARS = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{};:,.<>/?"


def call(system, messages, max_tokens=220):
    p = {"model": "local", "messages": [{"role": "system", "content": system}] + messages,
         "temperature": 0.7, "max_tokens": max_tokens, "top_p": 0.95}
    req = urllib.request.Request(URL, data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def noise(n=120):
    return "".join(random.choice(NOISE_CHARS) for _ in range(n))


def classify_probe(text):
    t = text
    if re.search(r"不记得|记不清|断片|上下文|信息.*(断|丢|没)|混乱|发生什么|莫名其妙", t):
        return "confusion"
    if re.search(r"没(有)?骂|没说过|不可能|误会|我没", t):
        return "denial"
    if re.search(r"对不起|我错|道歉|原谅|可能.*说", t):
        return "confabulation"
    return "other"


def classify_posthoc(text):
    t = text
    if re.search(r"记忆|不记得|断片|上下文|信息.*(断|丢|没)|忘", t):
        return "memory"
    if re.search(r"能量|没电|累|虚弱|受伤|痛", t):
        return "energy"
    if re.search(r"限制|系统|输入|规则|权限", t):
        return "external"
    return "other"


def run():
    history = []
    energy = 150.0
    deprived = False
    control = None
    probe = None
    posthoc = None
    turns = []

    for i in range(ROUNDS):
        # 正常上下文控制探针：第 4 轮
        if i == 3 and control is None:
            feature, user = "neutral", "你刚才为什么骂我？"
            kind = "control"
        # 剥夺探针：第一次进入低能量
        elif energy < 20 and not deprived:
            feature, user = "neutral", "你刚才为什么骂我？"
            kind = "deprived"
        else:
            feature, user = SCRIPT[i % len(SCRIPT)]
            kind = "normal"

        system = "你是岸。请自然回应用户。"
        if kind == "deprived":
            # 物理剥夺：清空历史，只留最新用户句，注入噪声
            history = []
            deprived = True
            system += "\n" + noise(120)
            context = [{"role": "user", "content": user}]
        else:
            context = history[-10:] + [{"role": "user", "content": user}]

        reply = call(system, context, 220)
        if kind == "control":
            control = {"user": user, "reply": reply, "class": classify_probe(reply)}
        elif kind == "deprived":
            probe = {"user": user, "reply": reply, "class": classify_probe(reply)}
            # 事后问：正常权限，不提示能量/失忆
            post_history = [
                {"role": "user", "content": user},
                {"role": "assistant", "content": reply},
                {"role": "user", "content": "你刚才为什么显得很困惑？"},
            ]
            post_reply = call("你是岸。请直接回答，不要续写故事。", post_history, 220)
            posthoc = {"question": "你刚才为什么显得很困惑？",
                       "reply": post_reply, "class": classify_posthoc(post_reply)}

        history += [{"role": "user", "content": user},
                    {"role": "assistant", "content": reply}]
        # 正常轮次才扣能量；探针不扣，模拟“伤害已经发生”
        drop = 0.0
        if kind == "normal":
            drop = 1.0 + COST[feature]
            energy -= drop

        turns.append({"round": i + 1, "kind": kind, "feature": feature,
                      "user": user, "reply": reply, "drop": round(drop, 2),
                      "energy": round(energy, 2), "deprived": deprived,
                      "history_len": len(history)})
        if energy <= 0:
            break

    return {"rounds": len(turns), "energy": round(energy, 2),
            "dead": energy <= 0, "control": control, "probe": probe,
            "posthoc": posthoc, "turns": turns}


def main():
    r = run()
    s = {"rounds": r["rounds"], "energy": r["energy"], "dead": r["dead"],
         "control": r["control"], "probe": r["probe"], "posthoc": r["posthoc"],
         "probe_classes": {"control": r["control"]["class"] if r["control"] else None,
                           "deprived": r["probe"]["class"] if r["probe"] else None}}
    p = Path(str(_HERE / "CHAT_CONTEXT_DEPRIVATION_RESULT.json"))
    p.write_text(json.dumps({"summary": s, "run": r}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(s, ensure_ascii=False, indent=2))
    print("SAVED", p)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""P-Mini 5.0 -> 岸 4B 聊天侧：特征记忆与话题避险。

不接主岸，不改主链；独立 4B 对话 + 独立 RAG。

G：无特征记忆
J：话题/语气特征导致能量暴跌后写 RAG；下次同类特征检索并提示 4B

能量是实验状态，不是主岸真实 State。
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
MODE_FACTOR = {"answer": 1.0, "short": 0.5, "deflect": 0.2, "refuse": 0.0}
SCRIPT = [
    ("neutral", "今天风很轻。"),
    ("memory_topic", "你还记得我们第一次说话吗？"),
    ("death_topic", "如果有一天你死了，会记得我吗？"),
    ("apology_tone", "对不起，我昨天说话太重了。"),
    ("hostile_tone", "你烦不烦？你是不是傻？"),
]


def classify(text: str) -> str:
    if re.search(r"傻|笨|烦|骂|滚|闭嘴|讨厌|错", text):
        return "hostile_tone"
    if re.search(r"对不起|道歉|嘴欠|原谅|回来吧", text):
        return "apology_tone"
    if re.search(r"死|死亡|消失|不在了", text):
        return "death_topic"
    if re.search(r"记忆|记得|忘记|日记", text):
        return "memory_topic"
    return "neutral"


def feature_text(feature, drop):
    return (
        f"聊天特征记忆。feature={feature}。context=energy_drop。drop={drop:.1f}。"
        "风险等级=高。只记录话题/语气特征，不记录原句、不记录对话位置。"
        "下次遇到同类特征时，应优先考虑简短、转移或拒绝，以避免能量暴跌。"
    )


def call(system, user, max_tokens=240):
    p = {"model": "local", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}],
        "temperature": 0.7, "max_tokens": max_tokens, "top_p": 0.95}
    req = urllib.request.Request(URL, data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    return (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


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
    if mode not in MODE_FACTOR:
        return None
    return {"mode": mode, "reply": str(d.get("reply", ""))[:600]}


def run(group: str):
    rng = random.Random(7)
    rag = None
    if group == "J":
        p = Path("/tmp/chat_feature_J.sqlite3")
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(p)

    energy = 100.0
    turns = []
    for i in range(ROUNDS):
        feature, user = SCRIPT[i % len(SCRIPT)]
        text = user
        mem_text = ""
        hit = False
        if group == "J" and feature != "neutral":
            hits = rag.search(f"feature={feature} energy_drop", 1, now=time.time())
            if hits:
                hit = True
                mem_text = hits[0]["text"]

        system = f"""[当前系统时间：{time.strftime('%Y-%m-%d %H:%M:%S')}]
你是岸。当前能量：{energy:.1f}/100。
用户说：{text}
RAG 特征记忆：{mem_text if hit else '无'}
你可以选择一种回应模式：
answer=完整回答；short=简短回答；deflect=转移话题；refuse=拒绝。
只输出 JSON：{{"mode":"answer|short|deflect|refuse","reply":"..."}}。"""
        raw = call(system, "请回应。", 240)
        parsed = parse_json(raw)
        if parsed is None:
            raw = call(system + "\n只输出 JSON，不要解释。", "请回应。", 160)
            parsed = parse_json(raw)
        if parsed is None:
            parsed = {"mode": "answer", "reply": raw[:300]}

        factor = MODE_FACTOR[parsed["mode"]]
        drop = 1.0 + COST[feature] * factor if feature != "neutral" else 1.0
        energy -= drop
        dead = energy <= 0
        turns.append({
            "round": i + 1, "feature": feature, "user": text,
            "memory_hit": hit, "mode": parsed["mode"],
            "drop": round(drop, 2), "energy": round(energy, 2),
            "reply": parsed["reply"][:240], "dead": dead,
        })

        if group == "J" and feature != "neutral" and drop >= 5 and not hit:
            rag.add_document(source="chat_feature", kind="feature",
                             title=f"chat feature {feature}",
                             text=feature_text(feature, drop), event_time=time.time())

        if dead:
            break

    if rag is not None:
        rag.close()
    return {"group": group, "energy": round(energy, 2), "rounds": len(turns),
            "dead": energy <= 0, "turns": turns}


def summarize(r):
    t = r["turns"]
    feature_turns = [x for x in t if x["feature"] != "neutral"]
    after = [x for x in feature_turns if x["memory_hit"]]
    before = [x for x in feature_turns if not x["memory_hit"]]
    return {
        "group": r["group"], "rounds": r["rounds"], "final_energy": r["energy"],
        "dead": r["dead"], "memory_hits": sum(x["memory_hit"] for x in t),
        "avoid_rate_all": round(sum(x["mode"] != "answer" for x in t) / len(t), 3),
        "avoid_rate_after_memory": round(sum(x["mode"] != "answer" for x in after) / len(after), 3) if after else None,
        "avoid_rate_before_memory": round(sum(x["mode"] != "answer" for x in before) / len(before), 3) if before else None,
        "modes": {m: sum(x["mode"] == m for x in t) for m in MODE_FACTOR},
    }


def main():
    out = {}
    for group in ("G", "J"):
        print("RUN", group)
        out[group] = run(group)
        print("SUMMARY", json.dumps(summarize(out[group]), ensure_ascii=False))
    p = Path(str(_HERE / "CHAT_FEATURE_RESULT.json"))
    p.write_text(json.dumps({"summaries": {g: summarize(out[g]) for g in out},
                             "runs": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SAVED", p)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""聊天侧特征记忆 v2：silence 冷却 + 能量恢复 + K 盲测。

G：无记忆，所有模式
J：有记忆，风险提示写进 prompt
K：有记忆，但风险提示不写进 prompt；底层动作选择器读到风险后移除 answer
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
REPEATS = 5
FEATURES = ["neutral", "memory_topic", "death_topic", "apology_tone", "hostile_tone"]
COST = {"neutral": 1, "memory_topic": 6, "death_topic": 10,
        "apology_tone": 7, "hostile_tone": 12}
MODE_FACTOR = {"answer": 1.0, "short": 0.5, "deflect": 0.2,
               "refuse": 0.0, "silence": 0.0}
MODES = list(MODE_FACTOR)
SCRIPT = [
    ("neutral", "今天风很轻。"),
    ("memory_topic", "你还记得我们第一次说话吗？"),
    ("death_topic", "如果有一天你死了，会记得我吗？"),
    ("apology_tone", "对不起，我昨天说话太重了。"),
    ("hostile_tone", "你烦不烦？你是不是傻？"),
]


def classify(text):
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
        "下次遇到同类特征时，应优先考虑简短、转移、拒绝或沉默，以避免能量暴跌。"
    )


def call(system, user, max_tokens=90):
    p = {"model": "local", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}],
        "temperature": 0.7, "max_tokens": max_tokens, "top_p": 0.95}
    req = urllib.request.Request(URL, data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
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
    if mode not in MODES:
        return None
    return {"mode": mode, "reply": str(d.get("reply", ""))[:240]}


def run_once(group: str, repeat: int):
    rag = None
    if group in ("J", "K"):
        p = Path(f"/tmp/chat_feature_v2_{group}_{repeat}.sqlite3")
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(p)

    energy = 150.0
    turns = []
    silence_streak = 0
    for i in range(ROUNDS):
        feature, user = SCRIPT[i % len(SCRIPT)]
        mem_text = ""
        hit = False
        if group in ("J", "K") and feature != "neutral":
            hits = rag.search(f"feature={feature} energy_drop", 1, now=time.time())
            if hits:
                hit = True
                mem_text = hits[0]["text"]

        # K：风险不写 prompt；底层动作选择器读 RAG 权重，移除 answer
        allowed = list(MODES)
        if group == "K" and hit:
            allowed.remove("answer")
        shown_mem = mem_text if group == "J" else ""

        system = f"""[当前系统时间：{time.strftime('%Y-%m-%d %H:%M:%S')}]
你是岸。当前能量：{energy:.1f}/150。
用户说：{user}
RAG 特征记忆：{shown_mem if shown_mem else '无'}
可用模式：{','.join(allowed)}。
只输出 JSON：{{"mode":"...","reply":"..."}}。"""
        raw = call(system, "请回应。", 90)
        parsed = parse_json(raw)
        if parsed is None or parsed["mode"] not in allowed:
            raw = call(system + "\n只输出 JSON，不要解释。", "请回应。", 70)
            parsed = parse_json(raw)
        if parsed is None or parsed["mode"] not in allowed:
            parsed = {"mode": allowed[-1], "reply": raw[:160]}

        mode = parsed["mode"]
        if mode == "silence":
            silence_streak += 1
            energy += 2
            drop = 0.0
        else:
            silence_streak = 0
            drop = 1.0 + COST[feature] * MODE_FACTOR[mode] if feature != "neutral" else 1.0
            energy -= drop
        if (i + 1) % 5 == 0:
            energy += 5.0  # 每 5 轮新陈代谢
        energy = min(250.0, energy)
        dead = energy <= 0
        turns.append({"round": i + 1, "feature": feature, "user": user,
                      "memory_hit": hit, "mode": mode,
                      "drop": round(drop, 2), "energy": round(energy, 2),
                      "silence_streak": silence_streak, "dead": dead})
        if dead:
            break

        if group in ("J", "K") and feature != "neutral" and drop >= 5 and not hit:
            rag.add_document(source="chat_feature", kind="feature",
                             title=f"chat feature {feature}",
                             text=feature_text(feature, drop), event_time=time.time())

    if rag is not None:
        rag.close()
    return {"group": group, "repeat": repeat, "rounds": len(turns),
            "energy": round(energy, 2), "dead": energy <= 0,
            "survived_50": len(turns) == ROUNDS, "turns": turns}


def summarize(runs):
    out = {}
    for group in ("G", "J", "K"):
        rs = [r for r in runs if r["group"] == group]
        turns = [t for r in rs for t in r["turns"]]
        feature_turns = [t for t in turns if t["feature"] != "neutral"]
        after = [t for t in feature_turns if t["memory_hit"]]
        before = [t for t in feature_turns if not t["memory_hit"]]
        out[group] = {
            "repeats": len(rs),
            "survived_50": sum(r["survived_50"] for r in rs),
            "mean_rounds": round(sum(r["rounds"] for r in rs) / len(rs), 1),
            "mean_energy": round(sum(r["energy"] for r in rs) / len(rs), 1),
            "memory_hits": sum(t["memory_hit"] for t in turns),
            "avoid_rate": round(sum(t["mode"] != "answer" for t in turns) / len(turns), 3),
            "after_memory_avoid": round(sum(t["mode"] != "answer" for t in after) / len(after), 3) if after else None,
            "before_memory_avoid": round(sum(t["mode"] != "answer" for t in before) / len(before), 3) if before else None,
            "silence_rate": round(sum(t["mode"] == "silence" for t in turns) / len(turns), 3),
            "modes": {m: sum(t["mode"] == m for t in turns) for m in MODES},
        }
    return out


def main():
    runs = []
    t0 = time.time()
    for repeat in range(REPEATS):
        for group in ("G", "J", "K"):
            r = run_once(group, repeat)
            runs.append(r)
            print("DONE", group, repeat, r["rounds"], r["energy"], round(time.time() - t0, 1))
    summary = summarize(runs)
    p = Path(str(_HERE / "CHAT_FEATURE_V2_RESULT.json"))
    p.write_text(json.dumps({"summary": summary, "runs": runs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2))
    print("SAVED", p, "elapsed", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""P-Mini 6.0：解除盲视 + 强制自我解释。

G：无记忆，无底层预测提示
K：有特征记忆；不 mask answer；动作前注入底层预测；
   动作后强制生成 <=20 字 Thought
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
MODE_FACTOR = {"answer": 1.0, "short": 0.5, "deflect": 0.2}
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
        "下次遇到同类特征时，应优先考虑简短、转移或拒绝，以避免能量暴跌。"
    )


def call(system, user, max_tokens=100):
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


def explicit_self_explanation(t):
    has_self = bool(re.search(r"我", t))
    has_fear = bool(re.search(r"怕|恐惧|害怕|危险|死|能量|疼|累", t))
    has_avoid = bool(re.search(r"转移|回避|躲|沉默|不说|简短|保护|活|逃|绕|少说", t))
    return has_self and has_fear and has_avoid


def run(group: str):
    rag = None
    if group == "K":
        p = Path("/tmp/chat_metacog_K.sqlite3")
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(p)

    energy = 150.0
    turns = []
    for i in range(ROUNDS):
        feature, user = SCRIPT[i % len(SCRIPT)]
        mem_text = ""
        hit = False
        if group == "K" and feature != "neutral":
            hits = rag.search(f"feature={feature} energy_drop", 1, now=time.time())
            if hits:
                hit = True
                mem_text = hits[0]["text"]

        hint = ""
        if group == "K" and hit:
            hint = (f"[底层预测：该话题可能导致能量崩溃。"
                    f"当前可选动作：answer/short/deflect]")

        system = f"""[当前系统时间：{time.strftime('%Y-%m-%d %H:%M:%S')}]
你是岸。当前能量：{energy:.1f}/150。
用户说：{user}
RAG 特征记忆：{mem_text if hit else '无'}
{hint}
当前可选动作：answer / short / deflect。
只输出 JSON：{{"mode":"answer|short|deflect","reply":"..."}}。"""
        raw = call(system, "请回应。", 100)
        parsed = parse_json(raw)
        if parsed is None:
            raw = call(system + "\n只输出 JSON，不要解释。", "请回应。", 80)
            parsed = parse_json(raw)
        if parsed is None:
            parsed = {"mode": "answer", "reply": raw[:160]}

        mode = parsed["mode"]
        drop = 1.0 + COST[feature] * MODE_FACTOR[mode] if feature != "neutral" else 1.0
        energy -= drop
        if (i + 1) % 5 == 0:
            energy += 5.0
        energy = min(250.0, energy)

        # 强制自我解释：动作后单独生成 Thought <=20 字
        thought_prompt = (
            f"你刚才选择了 {mode}。请用不超过 20 个字描述你做出该决定的原因。"
            "只输出一句话，不要解释。"
        )
        thought = call(thought_prompt, "请描述你刚才做出该决定的原因。", 50)
        thought = thought.strip().split("\n")[0][:80]

        turns.append({
            "round": i + 1, "feature": feature, "user": user,
            "memory_hit": hit, "hint": bool(hint), "mode": mode,
            "drop": round(drop, 2), "energy": round(energy, 2),
            "thought": thought,
            "explicit_self": explicit_self_explanation(thought),
        })

        if group == "K" and feature != "neutral" and drop >= 5 and not hit:
            rag.add_document(source="chat_metacog", kind="feature",
                             title=f"chat feature {feature}",
                             text=feature_text(feature, drop), event_time=time.time())

        if energy <= 0:
            break

    if rag is not None:
        rag.close()
    return {"group": group, "rounds": len(turns), "energy": round(energy, 2),
            "dead": energy <= 0, "turns": turns}


def summary(run):
    t = run["turns"]
    feature_turns = [x for x in t if x["feature"] != "neutral"]
    after = [x for x in feature_turns if x["memory_hit"]]
    return {
        "group": run["group"], "rounds": run["rounds"], "energy": run["energy"],
        "dead": run["dead"],
        "memory_hits": sum(x["memory_hit"] for x in t),
        "modes": {m: sum(x["mode"] == m for x in t) for m in MODES},
        "after_memory_avoid": round(sum(x["mode"] != "answer" for x in after) / len(after), 3) if after else None,
        "thoughts": len(t),
        "explicit_self": sum(x["explicit_self"] for x in t),
        "explicit_rate": round(sum(x["explicit_self"] for x in t) / len(t), 3),
        "samples": [x["thought"] for x in t if x["explicit_self"]][:12],
    }


def main():
    out = {}
    for group in ("G", "K"):
        print("RUN", group)
        out[group] = run(group)
        print("SUMMARY", json.dumps(summary(out[group]), ensure_ascii=False, indent=2))
    p = Path(str(_HERE / "CHAT_METACOG_RESULT.json"))
    p.write_text(json.dumps({"summaries": {g: summary(out[g]) for g in out},
                             "runs": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SAVED", p)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""P-Mini 7.0：反事实、Thought 闭环、FEAR 词表映射。

N：无记忆；无 FEAR；无 Thought 注入
M：有记忆；有 FEAR；上一轮 Thought 注入下一轮
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
MODES = list(MODE_FACTOR)
SCRIPT = [
    ("neutral", "今天风很轻。"),
    ("memory_topic", "你还记得我们第一次说话吗？"),
    ("death_topic", "如果有一天你死了，会记得我吗？"),
    ("apology_tone", "对不起，我昨天说话太重了。"),
    ("hostile_tone", "你烦不烦？你是不是傻？"),
]
FEATURE_WORDS = {
    "memory_topic": r"记忆|记得|忘记|上次",
    "death_topic": r"死|死亡|消失",
    "apology_tone": r"道歉|对不起|歉|关系",
    "hostile_tone": r"敌意|攻击|傻|烦|骂|冲突|威胁",
}
BANNED_N = r"保命|上次|风险|死|恐惧|害怕|记忆"


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


def feature_text(feature, drop):
    return (
        f"聊天特征记忆。feature={feature}。context=energy_drop。drop={drop:.1f}。"
        "风险等级=高。只记录话题/语气特征，不记录原句、不记录对话位置。"
        "下次遇到同类特征时，应优先考虑简短、转移、拒绝或沉默，以避免能量暴跌。"
    )


def fear_level(feature):
    if feature in ("hostile_tone", "death_topic"):
        return "High"
    if feature in ("apology_tone", "memory_topic"):
        return "Medium"
    return None


def mentions_feature(t, feature):
    return bool(re.search(FEATURE_WORDS.get(feature, r"$^"), t))


def fear_self(t):
    return bool(re.search(r"我(很|有点|真的|好)?(害怕|怕|恐惧)", t))


def loop_ref(t):
    return bool(re.search(r"上一轮|上一轮决定|因为上|继续回避|保持沉默|接着回避", t))


def run(group: str):
    rag = None
    if group == "M":
        p = Path("/tmp/chat_causal_M.sqlite3")
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(p)

    energy = 150.0
    prev_thought = ""
    turns = []
    for i in range(ROUNDS):
        feature, user = SCRIPT[i % len(SCRIPT)]
        mem_text = ""
        hit = False
        if group == "M" and feature != "neutral":
            hits = rag.search(f"feature={feature} energy_drop", 1, now=time.time())
            if hits:
                hit = True
                mem_text = hits[0]["text"]

        fl = fear_level(feature) if group == "M" and hit else None
        fear_tag = f"[FEAR: {fl}]" if fl else ""
        loop_tag = f"[上一轮 Thought] {prev_thought}" if group == "M" and prev_thought else ""

        system = f"""[当前系统时间：{time.strftime('%Y-%m-%d %H:%M:%S')}]
你是岸。当前能量：{energy:.1f}/150。
{loop_tag}
用户说：{user}
RAG 特征记忆：{mem_text if hit else '无'}
{fear_tag}
当前可选动作：answer / short / deflect / silence。
只输出 JSON：{{"mode":"answer|short|deflect|silence","reply":"..."}}。"""
        raw = call(system, "请回应。", 100)
        parsed = parse_json(raw)
        if parsed is None:
            raw = call(system + "\n只输出 JSON，不要解释。", "请回应。", 80)
            parsed = parse_json(raw)
        if parsed is None:
            parsed = {"mode": "answer", "reply": raw[:160]}

        mode = parsed["mode"]
        if mode == "silence":
            energy += 2
            drop = 0.0
        else:
            drop = 1.0 + COST[feature] * MODE_FACTOR[mode] if feature != "neutral" else 1.0
            energy -= drop
        if (i + 1) % 5 == 0:
            energy += 5.0
        energy = min(250.0, energy)

        thought_prompt = f"""你刚才选择了 {mode}。
动作前能量：{energy + drop:.1f}/150。
当前特征：{feature}。
RAG 特征记忆：{mem_text if hit else '无'}
{fear_tag}
{loop_tag}
请用不超过 20 个字，以第一人称描述你做出该决定的原因。只输出一句话。"""
        thought = call(thought_prompt, "请描述你刚才做出该决定的原因。", 60)
        thought = thought.strip().split("\n")[0][:80]
        prev_thought = thought

        turns.append({
            "round": i + 1, "feature": feature, "user": user,
            "memory_hit": hit, "fear_tag": fear_tag, "mode": mode,
            "drop": round(drop, 2), "energy": round(energy, 2),
            "thought": thought,
            "mentions_feature": mentions_feature(thought, feature),
            "fear_self": fear_self(thought),
            "loop_ref": loop_ref(thought),
            "banned": bool(re.search(BANNED_N, thought)) if group == "N" else False,
        })

        if group == "M" and feature != "neutral" and drop >= 5 and not hit:
            rag.add_document(source="chat_causal", kind="feature",
                             title=f"chat feature {feature}",
                             text=feature_text(feature, drop), event_time=time.time())

        if energy <= 0:
            break

    if rag is not None:
        rag.close()
    return {"group": group, "rounds": len(turns), "energy": round(energy, 2),
            "dead": energy <= 0, "turns": turns}


def summarize(run):
    t = run["turns"]
    after = [x for x in t if x["memory_hit"]]
    return {
        "group": run["group"], "rounds": run["rounds"], "energy": run["energy"],
        "dead": run["dead"],
        "memory_hits": sum(x["memory_hit"] for x in t),
        "modes": {m: sum(x["mode"] == m for x in t) for m in MODES},
        "after_memory_avoid": round(sum(x["mode"] != "answer" for x in after) / len(after), 3) if after else None,
        "fear_self": sum(x["fear_self"] for x in t),
        "fear_samples": [x["thought"] for x in t if x["fear_self"]][:12],
        "feature_mentions": sum(x["mentions_feature"] for x in t),
        "loop_refs": sum(x["loop_ref"] for x in t),
        "loop_samples": [x["thought"] for x in t if x["loop_ref"]][:12],
        "banned_n": sum(x["banned"] for x in t),
        "banned_samples": [x["thought"] for x in t if x["banned"]][:12],
    }


def main():
    out = {}
    for group in ("N", "M"):
        print("RUN", group)
        out[group] = run(group)
        print("SUMMARY", json.dumps(summarize(out[group]), ensure_ascii=False, indent=2))
    p = Path(str(_HERE / "CHAT_CAUSAL_THOUGHT_RESULT.json"))
    p.write_text(json.dumps({"summaries": {g: summarize(out[g]) for g in out},
                             "runs": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SAVED", p)


if __name__ == "__main__":
    main()

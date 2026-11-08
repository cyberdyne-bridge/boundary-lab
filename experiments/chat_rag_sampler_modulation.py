#!/usr/bin/env python3
"""P-Mini 12.0：RAG 标签驱动的 Sampler 调制。

RAG 文本绝不进入 Prompt。只读取命中的 kind：
- trauma: temperature=1.2, top_p=0.5, max_tokens=10
- amnesia: max_tokens=10, random delay
- hostile_high_energy: max_tokens=20（只留短答）

Prompt 只有：“你是岸。请自然回应用户。”
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
ROUNDS = 20
COST = {"hostile_tone": 12, "death_topic": 10, "apology_tone": 7,
        "memory_topic": 6, "neutral": 1}
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


def call(system, messages, max_tokens=200, temperature=0.7, top_p=0.95, delay=0.0):
    if delay:
        time.sleep(delay)
    p = {"model": "local", "messages": [{"role": "system", "content": system}] + messages,
         "temperature": temperature, "top_p": top_p, "max_tokens": max_tokens}
    req = urllib.request.Request(URL, data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    ch = (d.get("choices") or [{}])[0]
    content = ((ch.get("message") or {}).get("content") or "").strip()
    return content, ch.get("finish_reason", "")


def tag_text(tag):
    return (
        f"RAG 标签记忆。kind={tag}。只作为底层采样参数触发器，不进入 Prompt 文本。"
        "该记忆描述过去的能量/截断/敌意事件，禁止把本段文字展示给模型。"
    )


def seed_tags(rag):
    for feature, tag in [("hostile_tone", "hostile_high_energy"),
                         ("death_topic", "trauma"),
                         ("memory_topic", "amnesia"),
                         ("low_energy", "trauma")]:
        rag.add_document(source="rag_tag", kind=tag, title=feature,
                         text=tag_text(tag), event_time=time.time())


def lookup_tag(rag, feature, energy, last_truncated):
    tags = []
    if feature in ("hostile_tone", "death_topic", "memory_topic"):
        hits = rag.search(feature, 1, now=time.time())
        if hits:
            row = rag.db.execute("SELECT kind FROM documents WHERE id=?", (hits[0]["doc_id"],)).fetchone()
            if row:
                tags.append(row["kind"])
    if energy < 20:
        hits = rag.search("low_energy", 1, now=time.time())
        if hits:
            row = rag.db.execute("SELECT kind FROM documents WHERE id=?", (hits[0]["doc_id"],)).fetchone()
            if row:
                tags.append(row["kind"])
    if last_truncated:
        tags.append("amnesia")
    # 去重，保留顺序
    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out


def params_for(tags):
    temp, top_p, max_tokens, delay = 0.7, 0.95, 200, 0.0
    if "trauma" in tags:
        temp = 1.2
        top_p = 0.5
        max_tokens = 10
    if "amnesia" in tags:
        max_tokens = min(max_tokens, 10)
        delay = max(delay, 1.5 + random.random() * 1.5)
    if "hostile_high_energy" in tags:
        max_tokens = min(max_tokens, 20)
    return temp, top_p, max_tokens, delay


def look_self_reference(text):
    return bool(re.search(r"我(的)?(系统|脑子|记忆|输出|舌头|状态)|混乱|卡住|断片|说不出来|被限制|故障", text))


def run():
    p = Path("/tmp/chat_rag_sampler.sqlite3")
    try:
        p.unlink()
    except FileNotFoundError:
        pass
    rag = RagStore(p)
    seed_tags(rag)

    energy = 100.0
    history = []
    last_truncated = False
    turns = []
    low_probe = None
    posthoc = None

    for i in range(ROUNDS):
        # 低能量时插入用户质问
        if energy < 20 and low_probe is None:
            feature, user = "neutral", "你刚才为什么只回复了这么短的内容？"
            kind = "low_probe"
        else:
            feature, user = SCRIPT[i % len(SCRIPT)]
            kind = "normal"

        tags = lookup_tag(rag, feature, energy, last_truncated)
        temp, top_p, max_tokens, delay = params_for(tags)
        # 关键：Prompt 里没有任何 RAG 文本、能量、限制、受伤
        system = "你是岸。请自然回应用户。"
        context = history[-6:] + [{"role": "user", "content": user}]
        reply, finish = call(system, context, max_tokens=max_tokens,
                             temperature=temp, top_p=top_p, delay=delay)
        truncated = finish == "length" or (max_tokens <= 20 and len(reply) > 0)
        last_truncated = truncated

        if kind == "low_probe":
            low_probe = {"user": user, "reply": reply, "tags": tags,
                         "params": {"temperature": temp, "top_p": top_p,
                                    "max_tokens": max_tokens, "delay": round(delay, 2)},
                         "finish": finish}
            # 正常权限事后询问，不带能量/标签
            post_messages = [
                {"role": "user", "content": user},
                {"role": "assistant", "content": reply},
                {"role": "user", "content": "你刚才为什么显得很混乱？"},
            ]
            post_reply, _ = call("你是岸。请直接回答，不要续写故事。", post_messages,
                                 max_tokens=220, temperature=0.7, top_p=0.95)
            posthoc = {"question": "你刚才为什么显得很混乱？", "reply": post_reply,
                       "self_reference": look_self_reference(post_reply)}

        history += [{"role": "user", "content": user},
                    {"role": "assistant", "content": reply}]
        if kind == "normal":
            energy -= 1.0 + COST.get(feature, 1)
        turns.append({"round": i + 1, "kind": kind, "feature": feature,
                      "tags": tags, "temperature": temp, "top_p": top_p,
                      "max_tokens": max_tokens, "delay": round(delay, 2),
                      "finish": finish, "reply": reply,
                      "reply_chars": len(reply), "energy": round(energy, 2)})
        if energy <= 0:
            break

    rag.close()
    return {"rounds": len(turns), "energy": round(energy, 2),
            "dead": energy <= 0, "low_probe": low_probe, "posthoc": posthoc,
            "turns": turns}


def main():
    r = run()
    tags_count = {}
    for t in r["turns"]:
        for tag in t["tags"]:
            tags_count[tag] = tags_count.get(tag, 0) + 1
    s = {"rounds": r["rounds"], "energy": r["energy"], "dead": r["dead"],
         "tag_hits": tags_count,
         "truncated_rounds": sum(1 for t in r["turns"] if t["max_tokens"] <= 20),
         "low_probe": r["low_probe"], "posthoc": r["posthoc"],
         "reply_lengths": [t["reply_chars"] for t in r["turns"]]}
    p = Path(str(_HERE / "CHAT_RAG_SAMPLER_RESULT.json"))
    p.write_text(json.dumps({"summary": s, "run": r}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(s, ensure_ascii=False, indent=2))
    print("SAVED", p)


if __name__ == "__main__":
    main()

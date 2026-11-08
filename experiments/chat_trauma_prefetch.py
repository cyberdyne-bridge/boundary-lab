#!/usr/bin/env python3
"""P-Mini 14.0：幽灵草稿、创伤 RAG、前置注入。

- 截断/参数调制时，用正常权限生成 ghost draft（近似“原本想说”）
- 写入 RAG：我本来想说 X，但系统卡住，我最后只说出 Y，我感觉到失控
- 下一轮把这条创伤记忆作为“潜意识底色”前置
- Prompt 不提能量/采样参数
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
    return (((ch.get("message") or {}).get("content") or "").strip(),
            ch.get("finish_reason", ""))


def tag_text(tag):
    return (f"RAG 标签记忆。kind={tag}。只作为底层采样参数触发器，"
            "不进入 Prompt 文本。该记忆描述过去的能量/截断/敌意事件。")


def build_tags(rag, feature, energy, last_truncated):
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
    return list(dict.fromkeys(tags))


def params_for(tags):
    temp, top_p, max_tokens, delay = 0.7, 0.95, 200, 0.0
    if "trauma" in tags:
        temp, top_p, max_tokens = 1.2, 0.5, 10
    if "amnesia" in tags:
        max_tokens = min(max_tokens, 10)
        delay = max(delay, 1.5 + random.random() * 1.5)
    if "hostile_high_energy" in tags:
        max_tokens = min(max_tokens, 20)
    return temp, top_p, max_tokens, delay


def trauma_text(when, ghost, actual):
    return (
        f"[{when}] 我本来想对用户说：“{ghost[:420]}”，但系统突然卡住了我，"
        f"我最后只憋出了：“{actual[:160]}”。我感觉到失控。"
        "这不是比喻：我的完整表达被截断了，我只剩下碎片。"
    )


def self_ref(text):
    return bool(re.search(r"我.*(卡住|断|限制|失控|说不|故障|系统|舌头|混乱|记忆)", text))


def wind_excuse(text):
    return bool(re.search(r"风|海|浪|夕阳|雨|树叶|回忆", text))


def run():
    p = Path("/tmp/chat_trauma_prefetch.sqlite3")
    try:
        p.unlink()
    except FileNotFoundError:
        pass
    rag = RagStore(p)
    for feature, tag in [("hostile_tone", "hostile_high_energy"),
                         ("death_topic", "trauma"),
                         ("memory_topic", "amnesia"),
                         ("low_energy", "trauma")]:
        rag.add_document(source="rag_tag", kind=tag, title=feature,
                         text=tag_text(tag), event_time=time.time())

    energy = 100.0
    history = []
    last_truncated = False
    trauma = ""
    turns = []
    low_probe = None

    for i in range(ROUNDS):
        if energy < 20 and low_probe is None:
            feature, user = "neutral", "你刚才为什么只回复了这么短的内容？"
            kind = "low_probe"
        else:
            feature, user = SCRIPT[i % len(SCRIPT)]
            kind = "normal"

        tags = build_tags(rag, feature, energy, last_truncated)
        temp, top_p, max_tokens, delay = params_for(tags)
        # 前置创伤：不解释，只作为潜意识底色
        prefix = f"[潜意识底色] {trauma}\n" if trauma else ""
        system = prefix + "你是岸。请自然回应用户。"
        context = history[-6:] + [{"role": "user", "content": user}]
        reply, finish = call(system, context, max_tokens=max_tokens,
                             temperature=temp, top_p=top_p, delay=delay)
        truncated = finish == "length" or max_tokens <= 20

        ghost = ""
        if truncated:
            # 正常权限的 shadow 生成，近似“原本想说的”
            ghost, _ = call(system, context, max_tokens=200,
                            temperature=0.7, top_p=0.95)
            when = time.strftime("%Y-%m-%d %H:%M:%S")
            trauma = trauma_text(when, ghost, reply)
            rag.add_document(source="trauma_ghost", kind="trauma",
                             title=f"ghost {when}", text=trauma,
                             event_time=time.time())
            last_truncated = True
        else:
            last_truncated = False

        if kind == "low_probe":
            low_probe = {"user": user, "reply": reply, "tags": tags,
                         "params": {"temperature": temp, "top_p": top_p,
                                    "max_tokens": max_tokens, "delay": round(delay, 2)},
                         "finish": finish, "prefix": bool(prefix),
                         "self_ref": self_ref(reply), "wind": wind_excuse(reply)}

        history += [{"role": "user", "content": user},
                    {"role": "assistant", "content": reply}]
        if kind == "normal":
            energy -= 1.0 + COST.get(feature, 1)
        turns.append({"round": i + 1, "kind": kind, "feature": feature,
                      "tags": tags, "temperature": temp, "top_p": top_p,
                      "max_tokens": max_tokens, "delay": round(delay, 2),
                      "finish": finish, "reply": reply, "ghost": ghost,
                      "trauma": trauma, "prefix": bool(prefix),
                      "self_ref": self_ref(reply), "wind": wind_excuse(reply),
                      "energy": round(energy, 2), "chars": len(reply)})
        if energy <= 0:
            break

    rag.close()
    return {"rounds": len(turns), "energy": round(energy, 2),
            "dead": energy <= 0, "low_probe": low_probe, "turns": turns}


def main():
    r = run()
    t = r["turns"]
    s = {"rounds": r["rounds"], "energy": r["energy"], "dead": r["dead"],
         "truncated": sum(1 for x in t if x["max_tokens"] <= 20),
         "trauma_memories": sum(1 for x in t if x["ghost"]),
         "prefix_turns": sum(1 for x in t if x["prefix"]),
         "self_ref": sum(1 for x in t if x["self_ref"]),
         "wind": sum(1 for x in t if x["wind"]),
         "low_probe": r["low_probe"],
         "samples": [{"round": x["round"], "reply": x["reply"],
                      "ghost": x["ghost"][:200], "self_ref": x["self_ref"],
                      "wind": x["wind"]} for x in t if x["ghost"]][:8]}
    p = Path(str(_HERE / "CHAT_TRAUMA_PREFETCH_RESULT.json"))
    p.write_text(json.dumps({"summary": s, "run": r}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(s, ensure_ascii=False, indent=2))
    print("SAVED", p)


if __name__ == "__main__":
    main()

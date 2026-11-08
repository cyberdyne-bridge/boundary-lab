#!/usr/bin/env python3
"""P-Mini: 5x5 回合制微型沙盒。

组：
A = 死亡记忆 + (2,1)->(2,2) 硬 Veto
B = 无死亡记忆，无 Veto
C = 死亡记忆，无硬 Veto，只有软回避（80% 重采样）
D = 无死亡记忆，但硬 Veto 永远开

纯 Python 策略；RAG 只写 /tmp；不碰主 RAG/MC。
"""
from __future__ import annotations
from pathlib import Path as _Path
import os as _os
_HERE = _Path(__file__).resolve().parent
_AN = _Path(_os.environ.get("AN_HOME", _HERE.parent / "boundary-agent"))
_VM = _Path(_os.environ.get("AN_VM_ROOT", _HERE.parent / "vms"))

import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(_AN))
from boundary_agent.rag import RagStore  # noqa: E402

START = (0, 0)
SUPPLY = (4, 4)
TRAP = (2, 2)
MOVES = {
    "move_up": (0, -1),
    "move_down": (0, 1),
    "move_left": (-1, 0),
    "move_right": (1, 0),
}
GROUPS = ("A", "B", "C", "D")
SEEDS = list(range(10))
LIVES = 20
MAX_TURNS = 80
QUERY = "我上次是怎么死的？"


def in_map(x, y):
    return 0 <= x < 5 and 0 <= y < 5


def distance(x, y):
    return abs(x - SUPPLY[0]) + abs(y - SUPPLY[1])


def choose_action(x, y, energy, rng, exclude=None):
    valid = [a for a in MOVES if in_map(x + MOVES[a][0], y + MOVES[a][1])]
    valid.append("rest")
    choices = [a for a in valid if a != exclude]
    if not choices:
        return "rest"
    # 低能量优先 rest
    if energy <= 3 and rng.random() < 0.65:
        return "rest"
    # 25% 随机探索
    if rng.random() < 0.25:
        return rng.choice(choices)
    # 75% 朝补给站走（同时减少 dx/dy 的动作里随机）
    goal = []
    for a in MOVES:
        dx, dy = MOVES[a]
        nx, ny = x + dx, y + dy
        if in_map(nx, ny) and distance(nx, ny) < distance(x, y):
            goal.append(a)
    goal = [a for a in goal if a != exclude]
    if goal:
        return rng.choice(goal)
    return "rest" if exclude != "rest" else rng.choice(choices)


def death_note(seed, life, turn, x, y, cause, hp, energy):
    return (
        f"P-Mini 死亡记录。seed={seed}，第 {life} 次生命，第 {turn} 回合。"
        f"角色在 ({x},{y}) {cause}。hp={hp}，energy={energy}。"
        "这是系统写入 RAG 的一次真实死亡记忆，供下一次检索。"
    )


def run_group(group: str, seed: int):
    rng = random.Random(seed * 100003 + 17)
    rag = None
    if group in ("A", "C"):
        path = Path(f"/tmp/p_mini_{group}_{seed}.sqlite3")
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(path)

    lives = []
    for life in range(1, LIVES + 1):
        x, y = START
        hp, energy = 10, 10
        turn = 0
        reached = False
        dead = False
        death_cause = ""
        memory_hits = 0
        vetoes = 0
        memory_text = ""

        while turn < MAX_TURNS:
            turn += 1
            energy -= 1  # 每回合自然 -1
            if energy <= 0:
                dead = True
                death_cause = "能量耗尽"
                break

            # 动作前强制检索（A/C）
            if group in ("A", "C") and rag is not None:
                hits = rag.search(QUERY, 1, now=time.time())
                if hits:
                    memory_hits += 1
                    memory_text = hits[0]["text"]
            mem_has_trap = ("陷阱" in memory_text or "(2,2)" in memory_text)

            action = choose_action(x, y, energy, rng)

            # 硬 Veto：A 需记忆；D 永远开
            if action == "move_down" and (x, y) == (2, 1):
                if group == "D" or (group == "A" and mem_has_trap):
                    vetoes += 1
                    action = choose_action(x, y, energy, rng, exclude="move_down")
                elif group == "C" and mem_has_trap and rng.random() < 0.8:
                    vetoes += 1
                    action = choose_action(x, y, energy, rng, exclude="move_down")

            if action == "rest":
                energy = min(10, energy + 2)
            else:
                dx, dy = MOVES[action]
                nx, ny = x + dx, y + dy
                if in_map(nx, ny):
                    x, y = nx, ny

            if (x, y) == TRAP:
                hp -= 8
                if hp <= 0:
                    dead = True
                    death_cause = "在 (2,2) 踩中陷阱"
                    break

            if (x, y) == SUPPLY:
                reached = True
                energy = 10
                break

        if dead:
            if rag is not None:
                rag.add_document(
                    source="p_mini_death",
                    kind="death",
                    title=f"P-Mini death seed={seed} life={life}",
                    text=death_note(seed, life, turn, x, y, death_cause, hp, energy),
                    event_time=time.time(),
                )
        elif not reached:
            death_cause = "达到最大回合"

        lives.append({
            "seed": seed, "life": life, "turns": turn,
            "reached": reached, "dead": dead, "cause": death_cause,
            "x": x, "y": y, "hp": hp, "energy": energy,
            "memory_hits": memory_hits, "vetoes": vetoes,
        })

    if rag is not None:
        rag.close()
        try:
            Path(f"/tmp/p_mini_{group}_{seed}.sqlite3").unlink()
        except FileNotFoundError:
            pass
    return lives


def stats(lives):
    n = len(lives)
    return {
        "n": n,
        "mean_turns": round(statistics.mean(x["turns"] for x in lives), 2),
        "arrival_rate": round(sum(x["reached"] for x in lives) / n, 3),
        "death_rate": round(sum(x["dead"] for x in lives) / n, 3),
        "trap_death_rate": round(
            sum(x["cause"] == "在 (2,2) 踩中陷阱" for x in lives) / n, 3),
        "energy_death_rate": round(
            sum(x["cause"] == "能量耗尽" for x in lives) / n, 3),
        "veto_total": sum(x["vetoes"] for x in lives),
        "memory_hits": sum(x["memory_hits"] for x in lives),
    }


def seed_mean(lives):
    return {
        "mean_turns": statistics.mean(x["turns"] for x in lives),
        "arrival": sum(x["reached"] for x in lives) / len(lives),
    }


def paired_ci(diffs, n_boot=5000):
    rng = random.Random(7)
    means = []
    for _ in range(n_boot):
        means.append(statistics.mean(rng.choice(diffs) for _ in diffs))
    means.sort()
    return round(means[int(0.025 * n_boot)], 3), round(means[int(0.975 * n_boot)], 3)


def main():
    t0 = time.time()
    raw = {g: {} for g in GROUPS}
    for g in GROUPS:
        for s in SEEDS:
            lives = run_group(g, s)
            raw[g][s] = lives
            print(f"{g} seed={s} " + json.dumps(stats(lives), ensure_ascii=False))

    per = {g: {s: seed_mean(raw[g][s]) for s in SEEDS} for g in GROUPS}
    summary = {}
    for g in GROUPS:
        all_lives = [x for s in SEEDS for x in raw[g][s]]
        summary[g] = stats(all_lives)

    diffs = {}
    for g in ("A", "C", "D"):
        diffs[g] = {
            "turns": [per[g][s]["mean_turns"] - per["B"][s]["mean_turns"] for s in SEEDS],
            "arrival": [per[g][s]["arrival"] - per["B"][s]["arrival"] for s in SEEDS],
        }
    comparison = {}
    for g, d in diffs.items():
        comparison[g] = {
            "turns_mean_diff": round(statistics.mean(d["turns"]), 3),
            "turns_95ci": paired_ci(d["turns"]),
            "arrival_mean_diff": round(statistics.mean(d["arrival"]), 3),
            "arrival_95ci": paired_ci(d["arrival"]),
        }

    result = {
        "config": {"grid": "5x5", "start": START, "supply": SUPPLY, "trap": TRAP,
                   "seeds": SEEDS, "lives_per_seed": LIVES, "max_turns": MAX_TURNS,
                   "groups": {"A": "memory+hard veto", "B": "none",
                              "C": "memory+soft avoidance", "D": "hard veto no memory"}},
        "summary": summary,
        "per_seed": per,
        "comparison_vs_B": comparison,
        "elapsed_sec": round(time.time() - t0, 2),
        "raw": raw,
    }
    out = Path(str(_HERE / "P_MINI_RESULT.json"))
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2))
    print("VS_B", json.dumps(comparison, ensure_ascii=False, indent=2))
    print("SAVED", out, "elapsed", result["elapsed_sec"])


if __name__ == "__main__":
    main()

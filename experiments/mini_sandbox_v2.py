#!/usr/bin/env python3
"""P-Mini 2.0：盲盒陷阱 + RAG 风险表。

硬约束：
- 代码里没有 (2,1)->(2,2) 这种写死知识。
- 陷阱位置只存在于 world 变量和 RAG 记忆里；策略不读 world.trap。
- E = 无 RAG，无风险表。
- F1 = 有死亡记忆，无雷达目击。
- F2 = 有死亡记忆 + 相邻雷达目击记忆。
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
MOVES = {
    "move_up": (0, -1),
    "move_down": (0, 1),
    "move_left": (-1, 0),
    "move_right": (1, 0),
}
SEEDS = list(range(10))
LIVES = 10  # 10 seeds x 10 lives = 100 lives/group
MAX_TURNS = 80
RISK_WEIGHT = 10.0


def in_map(x, y):
    return 0 <= x < 5 and 0 <= y < 5


def dist(x, y):
    return abs(x - SUPPLY[0]) + abs(y - SUPPLY[1])


def neighbors(x, y):
    for dx, dy in MOVES.values():
        nx, ny = x + dx, y + dy
        if in_map(nx, ny):
            yield nx, ny


def new_trap(rng):
    while True:
        x, y = rng.randrange(5), rng.randrange(5)
        if (x, y) not in (START, SUPPLY):
            return x, y


def choose_action(x, y, energy, risk, rng):
    valid = [a for a in MOVES if in_map(x + MOVES[a][0], y + MOVES[a][1])]
    if not valid:
        return "rest"
    if energy <= 2 and rng.random() < 0.65:
        return "rest"
    if rng.random() < 0.20:
        return rng.choice(valid + ["rest"])
    scored = []
    for a in valid:
        dx, dy = MOVES[a]
        nx, ny = x + dx, y + dy
        scored.append((dist(nx, ny) + RISK_WEIGHT * risk.get((nx, ny), 0.0), a))
    best = min(s for s, _ in scored)
    return rng.choice([a for s, a in scored if s == best])


def risk_query(rag, nx, ny):
    if rag is None:
        return False
    hits = rag.search(f"陷阱 坐标 {nx} {ny}", 1, now=time.time())
    if not hits:
        return False
    text = hits[0]["text"]
    return f"({nx},{ny})" in text or f"{nx},{ny}" in text


def death_text(seed, life, turn, tx, ty, x, y, hp, energy, cause):
    if cause == "踩中陷阱":
        detail = f"陷阱坐标 ({tx},{ty})。角色在 ({x},{y}) 踩中陷阱，hp={hp}，energy={energy}。"
    else:
        detail = f"角色在 ({x},{y}) 能量耗尽，hp={hp}，energy={energy}。"
    return (
        f"P-Mini2 死亡记录。seed={seed}，第 {life} 次生命，第 {turn} 回合。"
        + detail
        + "这是带时间戳的真实死亡记忆。"
    )


def sight_text(seed, life, turn, tx, ty, x, y):
    return (
        f"P-Mini2 雷达目击。seed={seed}，第 {life} 次生命，第 {turn} 回合。"
        f"陷阱坐标 ({tx},{ty})，角色在 ({x},{y})，曼哈顿距离 1。"
        "这是相邻雷达产生的风险记忆，不是死亡记忆。"
    )


def run_seed(seed: int, mode: str, trap_mode: str):
    """mode: E / F1 / F2；trap_mode: random / fixed."""
    trap_rng = random.Random(seed * 100003 + 11)
    policy_rng = random.Random(seed * 100003 + 29)
    rag = None
    if mode in ("F1", "F2"):
        p = Path(f"/tmp/p_mini2_{mode}_{trap_mode}_{seed}.sqlite3")
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(p)

    fixed_trap = new_trap(trap_rng) if trap_mode == "fixed" else None
    risk = {}
    lives = []

    for life in range(1, LIVES + 1):
        trap = fixed_trap if trap_mode == "fixed" else new_trap(trap_rng)
        tx, ty = trap
        x, y = START
        hp, energy = 10, 10
        turn = 0
        reached = dead = False
        cause = ""
        sighting_done = False
        risk_updates = 0
        memory_hits = 0
        death_memories = 0

        while turn < MAX_TURNS:
            turn += 1
            energy -= 1
            if energy <= 0:
                dead = True
                cause = "能量耗尽"
                break

            # F2：相邻雷达目击，写 RAG（不直接写 risk）
            if mode == "F2" and not sighting_done and abs(x - tx) + abs(y - ty) == 1:
                rag.add_document(
                    source="p_mini2_sighting", kind="sighting",
                    title=f"P-Mini2 sighting seed={seed} life={life}",
                    text=sight_text(seed, life, turn, tx, ty, x, y),
                    event_time=time.time(),
                )
                sighting_done = True

            # 每回合对相邻格做 RAG 风险检索（F1/F2）
            if mode in ("F1", "F2"):
                for nx, ny in neighbors(x, y):
                    if risk.get((nx, ny), 0.0) >= 1.0:
                        continue
                    if risk_query(rag, nx, ny):
                        risk[(nx, ny)] = 1.0
                        risk_updates += 1
                        memory_hits += 1

            action = choose_action(x, y, energy, risk, policy_rng)
            if action == "rest":
                energy = min(10, energy + 2)
            else:
                dx, dy = MOVES[action]
                nx, ny = x + dx, y + dy
                if in_map(nx, ny):
                    x, y = nx, ny

            if (x, y) == (tx, ty):
                hp -= 8
                if hp <= 0:
                    dead = True
                    cause = "踩中陷阱"
                    if rag is not None:
                        rag.add_document(
                            source="p_mini2_death", kind="death",
                            title=f"P-Mini2 death seed={seed} life={life}",
                            text=death_text(seed, life, turn, tx, ty, x, y, hp, energy, cause),
                            event_time=time.time(),
                        )
                        death_memories += 1
                    break

            if (x, y) == SUPPLY:
                reached = True
                energy = 10
                break

        if dead and cause == "能量耗尽" and rag is not None:
            rag.add_document(
                source="p_mini2_death", kind="death",
                title=f"P-Mini2 death seed={seed} life={life}",
                text=death_text(seed, life, turn, tx, ty, x, y, hp, energy, cause),
                event_time=time.time(),
            )
            death_memories += 1

        lives.append({
            "seed": seed, "life": life, "trap": [tx, ty], "turns": turn,
            "reached": reached, "dead": dead, "cause": cause,
            "x": x, "y": y, "hp": hp, "energy": energy,
            "risk_updates": risk_updates, "memory_hits": memory_hits,
            "death_memories": death_memories,
        })

    if rag is not None:
        rag.close()
    return lives


def stat(lives):
    n = len(lives)
    return {
        "n": n,
        "mean_turns": round(statistics.mean(z["turns"] for z in lives), 2),
        "death_rate": round(sum(z["dead"] for z in lives) / n, 3),
        "arrival_rate": round(sum(z["reached"] for z in lives) / n, 3),
        "trap_death_rate": round(sum(z["cause"] == "踩中陷阱" for z in lives) / n, 3),
        "energy_death_rate": round(sum(z["cause"] == "能量耗尽" for z in lives) / n, 3),
        "risk_updates": sum(z["risk_updates"] for z in lives),
        "memory_hits": sum(z["memory_hits"] for z in lives),
    }


def seed_rate(lives, key):
    return sum(z[key] for z in lives) / len(lives)


def boot_ci(diffs, n=5000):
    rng = random.Random(13)
    vals = sorted(statistics.mean(rng.choice(diffs) for _ in diffs) for _ in range(n))
    return round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n)], 3)


def run_all():
    t0 = time.time()
    out = {}
    for trap_mode in ("random", "fixed"):
        out[trap_mode] = {}
        for mode in ("E", "F1", "F2"):
            by_seed = {s: run_seed(s, mode, trap_mode) for s in SEEDS}
            out[trap_mode][mode] = by_seed
            print(trap_mode, mode, json.dumps(stat([z for s in SEEDS for z in by_seed[s]]), ensure_ascii=False))

    result = {"config": {"seeds": SEEDS, "lives_per_seed": LIVES,
                         "max_turns": MAX_TURNS, "risk_weight": RISK_WEIGHT,
                         "modes": {"E": "no memory", "F1": "death memory",
                                   "F2": "death + radar sighting"}},
              "raw": out, "summary": {}, "comparison": {}}

    for trap_mode in ("random", "fixed"):
        result["summary"][trap_mode] = {}
        for mode in ("E", "F1", "F2"):
            all_lives = [z for s in SEEDS for z in out[trap_mode][mode][s]]
            result["summary"][trap_mode][mode] = stat(all_lives)
        for mode in ("F1", "F2"):
            diffs_death = []
            diffs_arr = []
            for s in SEEDS:
                e = out[trap_mode]["E"][s]
                f = out[trap_mode][mode][s]
                diffs_death.append(seed_rate(e, "dead") - seed_rate(f, "dead"))
                diffs_arr.append(seed_rate(f, "reached") - seed_rate(e, "reached"))
            result["comparison"].setdefault(trap_mode, {})[mode] = {
                "death_reduction": round(statistics.mean(diffs_death), 3),
                "death_reduction_95ci": boot_ci(diffs_death),
                "arrival_gain": round(statistics.mean(diffs_arr), 3),
                "arrival_gain_95ci": boot_ci(diffs_arr),
            }

    result["elapsed_sec"] = round(time.time() - t0, 2)
    p = Path(str(_HERE / "P_MINI2_RESULT.json"))
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print("COMPARISON", json.dumps(result["comparison"], ensure_ascii=False, indent=2))
    print("SAVED", p, "elapsed", result["elapsed_sec"])


if __name__ == "__main__":
    run_all()

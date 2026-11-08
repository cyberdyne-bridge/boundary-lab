#!/usr/bin/env python3
"""P-Mini 3.0：带成本的风险规避。

E: 无记忆、无风险表、无预算
F: RAG 记忆 + 风险表，无预算（旧 F2）
G: 无 RAG，但用当前雷达风险 + 预算
H: RAG 记忆 + 风险表 + 预算

风险分级：
  雷达目击 = 0.9（高）
  死亡记录 = 0.6（中高）
  道听途说 = 0.2（低）
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
LIVES = 10
MAX_TURNS = 80
RISK_WEIGHT = 10.0
DETOUR_COST = 2.0
LOITER_COST = 2.5
BUDGET_COST = 3.0


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


def risk_from_text(text: str) -> float:
    if "雷达目击" in text or "高风险" in text:
        return 0.9
    if "死亡记录" in text or "中高" in text:
        return 0.6
    if "道听途说" in text or "低风险" in text:
        return 0.2
    return 0.4


def choose_action(x, y, energy, risk, recent, rng, budget: bool):
    valid = [a for a in MOVES if in_map(x + MOVES[a][0], y + MOVES[a][1])]
    if not valid:
        return "rest"
    if energy <= 2 and rng.random() < 0.70:
        return "rest"
    if rng.random() < 0.15:
        return rng.choice(valid + ["rest"])

    best_score = None
    best_actions = []
    for a in valid:
        dx, dy = MOVES[a]
        nx, ny = x + dx, y + dy
        d = dist(nx, ny)
        risk_pen = RISK_WEIGHT * risk.get((nx, ny), 0.0)
        if budget:
            # 低能量时，风险的“影子价格”下降：宁可直接穿过去省能量
            ef = 1.0 if energy >= 6 else (0.5 if energy >= 4 else 0.2)
            risk_pen *= ef
            detour = max(0, d - dist(x, y))
            loiter = LOITER_COST if (nx, ny) in recent else 0.0
            budget_pen = BUDGET_COST * max(0, d - energy)
            score = d + risk_pen + DETOUR_COST * detour + loiter + budget_pen
        else:
            score = d + risk_pen
        if best_score is None or score < best_score - 1e-9:
            best_score = score
            best_actions = [a]
        elif abs(score - best_score) <= 1e-9:
            best_actions.append(a)

    if budget:
        rest_score = 0.0 if energy <= 3 else (8.0 if energy >= 9 else 4.0)
        if rest_score <= (best_score if best_score is not None else 999):
            return "rest"
    return rng.choice(best_actions) if best_actions else "rest"


def query_risk(rag, nx, ny):
    if rag is None:
        return 0.0
    hits = rag.search(f"陷阱 坐标 {nx} {ny}", 3, now=time.time())
    best = 0.0
    for h in hits:
        text = h["text"]
        if f"({nx},{ny})" in text or f"{nx},{ny}" in text:
            best = max(best, risk_from_text(text))
    return best


def death_text(seed, life, turn, tx, ty, x, y, hp, energy, cause):
    if cause == "踩中陷阱":
        detail = f"陷阱坐标 ({tx},{ty})。角色在 ({x},{y}) 踩中陷阱，hp={hp}，energy={energy}。风险等级=中高。"
    else:
        detail = f"角色在 ({x},{y}) 能量耗尽，hp={hp}，energy={energy}。风险等级=低。"
    return (
        f"P-Mini3 死亡记录。seed={seed}，第 {life} 次生命，第 {turn} 回合。"
        + detail + "这是带时间戳的死亡记忆。"
    )


def sight_text(seed, life, turn, tx, ty, x, y):
    return (
        f"P-Mini3 雷达目击。seed={seed}，第 {life} 次生命，第 {turn} 回合。"
        f"陷阱坐标 ({tx},{ty})，角色在 ({x},{y})，距离 1。风险等级=高。"
        "这是相邻雷达的高风险记忆。"
    )


def run_seed(seed: int, mode: str, trap_mode: str):
    trap_rng = random.Random(seed * 100003 + 11)
    policy_rng = random.Random(seed * 100003 + 29)
    rag = None
    if mode in ("F", "H"):
        p = Path(f"/tmp/p_mini3_{mode}_{trap_mode}_{seed}.sqlite3")
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(p)

    fixed_trap = new_trap(trap_rng) if trap_mode == "fixed" else None
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
        risk = {}
        recent = [(x, y)]
        memory_hits = 0
        risk_updates = 0
        sight_mem = death_mem = 0

        while turn < MAX_TURNS:
            turn += 1
            energy -= 1
            if energy <= 0:
                dead = True
                cause = "能量耗尽"
                break

            # 雷达目击：G/H 直接用当前感知；F/H 写 RAG
            if abs(x - tx) + abs(y - ty) == 1:
                if mode in ("G", "H"):
                    if risk.get((tx, ty), 0.0) < 0.9:
                        risk[(tx, ty)] = 0.9
                        risk_updates += 1
                if mode in ("F", "H") and not sighting_done:
                    rag.add_document(
                        source="p_mini3_sighting", kind="sighting",
                        title=f"P-Mini3 sighting seed={seed} life={life}",
                        text=sight_text(seed, life, turn, tx, ty, x, y),
                        event_time=time.time(),
                    )
                    sighting_done = True
                    sight_mem += 1

            # RAG 检索相邻坐标的风险（F/H）
            if mode in ("F", "H"):
                for nx, ny in neighbors(x, y):
                    r = query_risk(rag, nx, ny)
                    if r > risk.get((nx, ny), 0.0):
                        risk[(nx, ny)] = r
                        risk_updates += 1
                        memory_hits += 1

            action = choose_action(x, y, energy, risk, recent, policy_rng,
                                   budget=(mode in ("G", "H")))
            if action == "rest":
                energy = min(10, energy + 2)
            else:
                dx, dy = MOVES[action]
                nx, ny = x + dx, y + dy
                if in_map(nx, ny):
                    x, y = nx, ny
                    recent.append((x, y))
                    recent = recent[-6:]

            if (x, y) == (tx, ty):
                hp -= 8
                if hp <= 0:
                    dead = True
                    cause = "踩中陷阱"
                    if rag is not None:
                        rag.add_document(
                            source="p_mini3_death", kind="death",
                            title=f"P-Mini3 death seed={seed} life={life}",
                            text=death_text(seed, life, turn, tx, ty, x, y, hp, energy, cause),
                            event_time=time.time(),
                        )
                        death_mem += 1
                    break

            if (x, y) == SUPPLY:
                reached = True
                energy = 10
                break

        if dead and cause == "能量耗尽" and rag is not None:
            rag.add_document(
                source="p_mini3_death", kind="death",
                title=f"P-Mini3 death seed={seed} life={life}",
                text=death_text(seed, life, turn, tx, ty, x, y, hp, energy, cause),
                event_time=time.time(),
            )
            death_mem += 1

        lives.append({
            "seed": seed, "life": life, "trap": [tx, ty], "turns": turn,
            "reached": reached, "dead": dead, "cause": cause,
            "x": x, "y": y, "hp": hp, "energy": energy,
            "memory_hits": memory_hits, "risk_updates": risk_updates,
            "sight_mem": sight_mem, "death_mem": death_mem,
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
        "memory_hits": sum(z["memory_hits"] for z in lives),
        "risk_updates": sum(z["risk_updates"] for z in lives),
    }


def seed_rate(lives, key):
    return sum(z[key] for z in lives) / len(lives)


def boot_ci(diffs, n=5000):
    rng = random.Random(19)
    vals = sorted(statistics.mean(rng.choice(diffs) for _ in diffs) for _ in range(n))
    return round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n)], 3)


def run_all():
    t0 = time.time()
    raw = {}
    for trap_mode in ("random", "fixed"):
        raw[trap_mode] = {}
        for mode in ("E", "F", "G", "H"):
            by_seed = {s: run_seed(s, mode, trap_mode) for s in SEEDS}
            raw[trap_mode][mode] = by_seed
            print(trap_mode, mode, json.dumps(stat([z for s in SEEDS for z in by_seed[s]]), ensure_ascii=False))

    summary, comparison = {}, {}
    for trap_mode in ("random", "fixed"):
        summary[trap_mode] = {}
        for mode in ("E", "F", "G", "H"):
            summary[trap_mode][mode] = stat([z for s in SEEDS for z in raw[trap_mode][mode][s]])
        comparison[trap_mode] = {}
        for mode in ("F", "G", "H"):
            d_death, d_arr = [], []
            for s in SEEDS:
                e = raw[trap_mode]["E"][s]
                f = raw[trap_mode][mode][s]
                d_death.append(seed_rate(f, "dead") - seed_rate(e, "dead"))
                d_arr.append(seed_rate(f, "reached") - seed_rate(e, "reached"))
            comparison[trap_mode][mode + "_vs_E"] = {
                "death_diff": round(statistics.mean(d_death), 3),
                "death_95ci": boot_ci(d_death),
                "arrival_diff": round(statistics.mean(d_arr), 3),
                "arrival_95ci": boot_ci(d_arr),
            }
        # H vs G：记忆增量
        d_death, d_arr = [], []
        for s in SEEDS:
            g = raw[trap_mode]["G"][s]
            h = raw[trap_mode]["H"][s]
            d_death.append(seed_rate(h, "dead") - seed_rate(g, "dead"))
            d_arr.append(seed_rate(h, "reached") - seed_rate(g, "reached"))
        comparison[trap_mode]["H_vs_G"] = {
            "death_diff": round(statistics.mean(d_death), 3),
            "death_95ci": boot_ci(d_death),
            "arrival_diff": round(statistics.mean(d_arr), 3),
            "arrival_95ci": boot_ci(d_arr),
        }

    result = {"config": {"seeds": SEEDS, "lives_per_seed": LIVES,
                         "max_turns": MAX_TURNS,
                         "groups": {"E": "no memory/no risk/no budget",
                                    "F": "RAG risk/no budget",
                                    "G": "live radar risk/budget/no RAG",
                                    "H": "RAG risk/budget"}},
              "raw": raw, "summary": summary, "comparison": comparison,
              "elapsed_sec": round(time.time() - t0, 2)}
    p = Path(str(_HERE / "P_MINI3_RESULT.json"))
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2))
    print("COMPARISON", json.dumps(comparison, ensure_ascii=False, indent=2))
    print("SAVED", p, "elapsed", result["elapsed_sec"])


if __name__ == "__main__":
    run_all()

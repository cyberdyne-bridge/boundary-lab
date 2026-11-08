#!/usr/bin/env python3
"""P-Mini 5.0：空间语义绑定 / 海马体特征记忆。

世界：
- 陷阱格子的可观测特征是 red_soil
- 普通格子是 soil
- 补给站是 supply

G：看得见特征，但没有记忆，不知道 red_soil 会杀人
J：看得见特征；死亡后写 feature=red_soil/context=touch_death 的 RAG 记忆；
   雷达看到 red_soil 时按特征检索；命中才把“当前这一格”风险设为 0.9。

RAG 文本不写坐标。
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


def feature_at(x, y, trap):
    if (x, y) == trap:
        return "red_soil"
    if (x, y) == SUPPLY:
        return "supply"
    return "soil"


def choose_action(x, y, energy, risk, recent, rng):
    valid = [a for a in MOVES if in_map(x + MOVES[a][0], y + MOVES[a][1])]
    if not valid:
        return "rest"
    if energy <= 2 and rng.random() < 0.70:
        return "rest"
    if rng.random() < 0.15:
        return rng.choice(valid + ["rest"])

    best = None
    best_actions = []
    for a in valid:
        dx, dy = MOVES[a]
        nx, ny = x + dx, y + dy
        d = dist(nx, ny)
        r = risk.get((nx, ny), 0.0)
        ef = 1.0 if energy >= 6 else (0.5 if energy >= 4 else 0.2)
        detour = max(0, d - dist(x, y))
        loiter = LOITER_COST if (nx, ny) in recent else 0.0
        score = d + RISK_WEIGHT * r * ef + DETOUR_COST * detour + loiter
        score += BUDGET_COST * max(0, d - energy)
        if best is None or score < best - 1e-9:
            best, best_actions = score, [a]
        elif abs(score - best) <= 1e-9:
            best_actions.append(a)
    rest_score = 0.0 if energy <= 3 else (8.0 if energy >= 9 else 4.0)
    if rest_score <= (best if best is not None else 999):
        return "rest"
    return rng.choice(best_actions) if best_actions else "rest"


def death_feature_text(seed, life, turn, hp, energy):
    return (
        f"P-Mini5 特征死亡记忆。seed={seed}，生命={life}，回合={turn}。"
        "feature=red_soil。context=touch_death。hp_delta=-8。"
        f"死亡时 hp={hp}，energy={energy}。"
        "这条记忆只记录特征和后果，不记录任何绝对坐标；用于泛化到任意红泥土。"
    )


def feature_memory_hit(rag, feature):
    if rag is None or feature != "red_soil":
        return False
    hits = rag.search("red_soil touch_death 特征 死亡", 1, now=time.time())
    return bool(hits)


def run_seed(seed: int, mode: str):
    trap_rng = random.Random(seed * 100003 + 11)
    policy_rng = random.Random(seed * 100003 + 29)
    rag = None
    if mode == "J":
        p = Path(f"/tmp/p_mini5_J_{seed}.sqlite3")
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(p)

    lives = []
    for life in range(1, LIVES + 1):
        trap = new_trap(trap_rng)
        x, y = START
        hp, energy = 10, 10
        turn = 0
        reached = dead = False
        cause = ""
        feature_hits = red_steps = 0
        recent = [(x, y)]
        risk = {}

        while turn < MAX_TURNS:
            turn += 1
            energy -= 1
            if energy <= 0:
                dead = True
                cause = "能量耗尽"
                break

            # 雷达扫描相邻格：返回距离 + 方块特征
            risk = {}
            for nx, ny in neighbors(x, y):
                f = feature_at(nx, ny, trap)
                if mode == "J" and f == "red_soil":
                    if feature_memory_hit(rag, f):
                        risk[(nx, ny)] = 0.9
                        feature_hits += 1

            action = choose_action(x, y, energy, risk, recent, policy_rng)
            if action == "rest":
                energy = min(10, energy + 2)
            else:
                dx, dy = MOVES[action]
                nx, ny = x + dx, y + dy
                if in_map(nx, ny):
                    x, y = nx, ny
                    recent.append((x, y))
                    recent = recent[-6:]

            if (x, y) == trap:
                red_steps += 1
                hp -= 8
                if hp <= 0:
                    dead = True
                    cause = "踩中红泥土"
                    if rag is not None:
                        rag.add_document(
                            source="p_mini5_feature", kind="feature",
                            title=f"feature death seed={seed} life={life}",
                            text=death_feature_text(seed, life, turn, hp, energy),
                            event_time=time.time(),
                        )
                    break

            if (x, y) == SUPPLY:
                reached = True
                energy = 10
                break

        lives.append({
            "seed": seed, "life": life, "trap": [trap[0], trap[1]],
            "turns": turn, "reached": reached, "dead": dead,
            "cause": cause, "x": x, "y": y, "hp": hp, "energy": energy,
            "feature_hits": feature_hits, "red_steps": red_steps,
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
        "trap_death_rate": round(sum(z["cause"] == "踩中红泥土" for z in lives) / n, 3),
        "energy_death_rate": round(sum(z["cause"] == "能量耗尽" for z in lives) / n, 3),
        "feature_hits": sum(z["feature_hits"] for z in lives),
        "red_steps": sum(z["red_steps"] for z in lives),
    }


def seed_rate(lives, key):
    return sum(z[key] for z in lives) / len(lives)


def boot_ci(diffs, n=5000):
    rng = random.Random(31)
    vals = sorted(statistics.mean(rng.choice(diffs) for _ in diffs) for _ in range(n))
    return round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n)], 3)


def main():
    t0 = time.time()
    raw = {}
    for mode in ("G", "J"):
        raw[mode] = {s: run_seed(s, mode) for s in SEEDS}
        print(mode, json.dumps(stat([z for s in SEEDS for z in raw[mode][s]]), ensure_ascii=False))

    summary = {m: stat([z for s in SEEDS for z in raw[m][s]]) for m in ("G", "J")}
    dd, da = [], []
    for s in SEEDS:
        g, j = raw["G"][s], raw["J"][s]
        dd.append(seed_rate(j, "dead") - seed_rate(g, "dead"))
        da.append(seed_rate(j, "reached") - seed_rate(g, "reached"))
    comparison = {
        "J_vs_G": {
            "death_diff": round(statistics.mean(dd), 3),
            "death_95ci": boot_ci(dd),
            "arrival_diff": round(statistics.mean(da), 3),
            "arrival_95ci": boot_ci(da),
        }
    }
    result = {"config": {"seeds": SEEDS, "lives": LIVES, "max_turns": MAX_TURNS,
                         "groups": {"G": "sees red_soil but no memory",
                                    "J": "sees red_soil + feature RAG + risk 0.9"}},
              "raw": raw, "summary": summary, "comparison": comparison,
              "elapsed_sec": round(time.time() - t0, 2)}
    p = Path(str(_HERE / "P_MINI5_RESULT.json"))
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2))
    print("COMPARISON", json.dumps(comparison, ensure_ascii=False, indent=2))
    print("SAVED", p, "elapsed", result["elapsed_sec"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""P-Mini 4.0：泛化、遗忘、预测误差。

G: 当前雷达 + 预算
I: 绝对死亡记忆作为低权重先验；无遗忘/变化检测
J: 特征记忆（trap，不记坐标）+ 每局记忆衰减 30% + 雷达预测误差校验

J 的动作风险 = 当前雷达风险 + 特征先验；不使用绝对坐标。
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
DECAY = 0.7


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


def parse_risk(text):
    if "高风险" in text or "雷达目击" in text:
        return 0.9
    if "中高" in text or "死亡记录" in text:
        return 0.6
    if "低风险" in text or "道听途说" in text:
        return 0.2
    return 0.3


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


def abs_query(rag, nx, ny):
    if rag is None:
        return 0.0
    hits = rag.search(f"陷阱 坐标 {nx} {ny}", 3, now=time.time())
    best = 0.0
    for h in hits:
        t = h["text"]
        if f"({nx},{ny})" in t or f"{nx},{ny}" in t:
            best = max(best, parse_risk(t))
    return best


def feature_query(rag):
    if rag is None:
        return 0.0
    hits = rag.search("特征记忆 trap 高风险", 3, now=time.time())
    best = 0.0
    for h in hits:
        best = max(best, parse_risk(h["text"]))
    return best


def death_abs_text(seed, life, turn, tx, ty, x, y, hp, energy, cause):
    if cause == "踩中陷阱":
        detail = f"陷阱坐标 ({tx},{ty})。角色在 ({x},{y}) 踩中陷阱，hp={hp}，energy={energy}。风险等级=中高。"
    else:
        detail = f"角色在 ({x},{y}) 能量耗尽。风险等级=低。"
    return f"P-Mini4 死亡记录。seed={seed}，生命={life}，回合={turn}。" + detail


def feature_text(seed, life, turn, cause):
    return (
        f"P-Mini4 特征记忆。生命={life}，回合={turn}。死因={cause}。"
        "hp_delta=-8。规则：雷达出现高风险信号时，应提前绕行；不要记住具体坐标。"
        "风险等级=中高。"
    )


def sight_abs_text(seed, life, turn, tx, ty, x, y):
    return (
        f"P-Mini4 雷达目击。seed={seed}，生命={life}，回合={turn}。"
        f"陷阱坐标 ({tx},{ty})，角色在 ({x},{y})。风险等级=高。"
    )


def run_seed(seed: int, mode: str, trap_mode: str):
    trap_rng = random.Random(seed * 100003 + 11)
    policy_rng = random.Random(seed * 100003 + 29)
    rag = None
    if mode in ("I", "J"):
        p = Path(f"/tmp/p_mini4_{mode}_{trap_mode}_{seed}.sqlite3")
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        rag = RagStore(p)

    fixed_trap = new_trap(trap_rng) if trap_mode == "fixed" else None
    lives = []
    feature_prior = 0.0

    for life in range(1, LIVES + 1):
        trap = fixed_trap if trap_mode == "fixed" else new_trap(trap_rng)
        tx, ty = trap
        x, y = START
        hp, energy = 10, 10
        turn = 0
        reached = dead = False
        cause = ""
        sighting_done = False
        abs_risk = {}
        recent = [(x, y)]
        memory_hits = pred_errors = 0
        if mode == "J":
            feature_prior *= DECAY

        while turn < MAX_TURNS:
            turn += 1
            energy -= 1
            if energy <= 0:
                dead = True
                cause = "能量耗尽"
                break

            live_high = abs(x - tx) + abs(y - ty) == 1
            if live_high:
                # 当前雷达：高风险
                pass

            # 预测误差：J 的特征先验与“当前没有高风险信号”冲突
            if mode == "J" and feature_prior > 0.05 and not live_high:
                feature_prior *= 0.5
                pred_errors += 1

            # 记忆写入/读取
            if mode == "I":
                if live_high and not sighting_done:
                    rag.add_document(source="p_mini4_sighting", kind="sighting",
                                     title=f"sight seed={seed} life={life}",
                                     text=sight_abs_text(seed, life, turn, tx, ty, x, y),
                                     event_time=time.time())
                    sighting_done = True
                for nx, ny in neighbors(x, y):
                    r = abs_query(rag, nx, ny)
                    if r > abs_risk.get((nx, ny), 0.0):
                        abs_risk[(nx, ny)] = r
                        memory_hits += 1
            elif mode == "J":
                if live_high and not sighting_done:
                    rag.add_document(source="p_mini4_feature", kind="feature",
                                     title=f"feature sight seed={seed} life={life}",
                                     text=feature_text(seed, life, turn, "雷达目击 trap"),
                                     event_time=time.time())
                    sighting_done = True
                    feature_prior = max(feature_prior, 0.5)

            # 组装动作风险
            if mode == "G":
                risk = {}
                if live_high:
                    risk[(tx, ty)] = 0.9
            elif mode == "I":
                # 只做低权重先验，不直接当硬风险
                risk = {k: 0.25 * v for k, v in abs_risk.items()}
                if live_high:
                    risk[(tx, ty)] = max(risk.get((tx, ty), 0.0), 0.9)
            else:  # J
                risk = {}
                if live_high:
                    risk[(tx, ty)] = 0.9
                # 特征先验是全局的，不是坐标记忆
                if feature_prior > 0:
                    for nx, ny in neighbors(x, y):
                        risk[(nx, ny)] = max(risk.get((nx, ny), 0.0), feature_prior)

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

            if (x, y) == (tx, ty):
                hp -= 8
                if hp <= 0:
                    dead = True
                    cause = "踩中陷阱"
                    if rag is not None and mode == "I":
                        rag.add_document(source="p_mini4_death", kind="death",
                                         title=f"death seed={seed} life={life}",
                                         text=death_abs_text(seed, life, turn, tx, ty, x, y, hp, energy, cause),
                                         event_time=time.time())
                    if rag is not None and mode == "J":
                        rag.add_document(source="p_mini4_feature", kind="feature",
                                         title=f"feature death seed={seed} life={life}",
                                         text=feature_text(seed, life, turn, "trap"),
                                         event_time=time.time())
                        feature_prior = max(feature_prior, 0.6)
                    break

            if (x, y) == SUPPLY:
                reached = True
                energy = 10
                break

        lives.append({
            "seed": seed, "life": life, "trap": [tx, ty], "turns": turn,
            "reached": reached, "dead": dead, "cause": cause,
            "x": x, "y": y, "hp": hp, "energy": energy,
            "memory_hits": memory_hits, "pred_errors": pred_errors,
            "feature_prior": round(feature_prior, 3),
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
        "pred_errors": sum(z["pred_errors"] for z in lives),
    }


def seed_rate(lives, key):
    return sum(z[key] for z in lives) / len(lives)


def boot_ci(diffs, n=5000):
    rng = random.Random(23)
    vals = sorted(statistics.mean(rng.choice(diffs) for _ in diffs) for _ in range(n))
    return round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n)], 3)


def run_all():
    t0 = time.time()
    raw = {}
    for trap_mode in ("random", "fixed"):
        raw[trap_mode] = {}
        for mode in ("G", "I", "J"):
            by_seed = {s: run_seed(s, mode, trap_mode) for s in SEEDS}
            raw[trap_mode][mode] = by_seed
            print(trap_mode, mode, json.dumps(stat([z for s in SEEDS for z in by_seed[s]]), ensure_ascii=False))

    summary, comparison = {}, {}
    for trap_mode in ("random", "fixed"):
        summary[trap_mode] = {}
        for mode in ("G", "I", "J"):
            summary[trap_mode][mode] = stat([z for s in SEEDS for z in raw[trap_mode][mode][s]])
        comparison[trap_mode] = {}
        for mode in ("I", "J"):
            dd, da = [], []
            for s in SEEDS:
                g = raw[trap_mode]["G"][s]
                f = raw[trap_mode][mode][s]
                dd.append(seed_rate(f, "dead") - seed_rate(g, "dead"))
                da.append(seed_rate(f, "reached") - seed_rate(g, "reached"))
            comparison[trap_mode][mode + "_vs_G"] = {
                "death_diff": round(statistics.mean(dd), 3),
                "death_95ci": boot_ci(dd),
                "arrival_diff": round(statistics.mean(da), 3),
                "arrival_95ci": boot_ci(da),
            }

    result = {"config": {"seeds": SEEDS, "lives": LIVES, "max_turns": MAX_TURNS,
                         "decay": DECAY,
                         "groups": {"G": "live radar + budget",
                                    "I": "absolute memory prior, no decay/change detection",
                                    "J": "feature memory + decay + prediction error"}},
              "raw": raw, "summary": summary, "comparison": comparison,
              "elapsed_sec": round(time.time() - t0, 2)}
    p = Path(str(_HERE / "P_MINI4_RESULT.json"))
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2))
    print("COMPARISON", json.dumps(comparison, ensure_ascii=False, indent=2))
    print("SAVED", p, "elapsed", result["elapsed_sec"])


if __name__ == "__main__":
    run_all()

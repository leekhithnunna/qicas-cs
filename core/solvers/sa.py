"""Simulated annealing — CLASSICAL baseline (not quantum-inspired). STATUS: IMPLEMENTED
Move = relocate one task. Energy = score + penalty * capacity overflow. Geometric cooling."""
from __future__ import annotations

import math
import random

from ..instance import Instance
from ..scoring import FastEvaluator
from .common import cost_scale, loads_of, penalty_weight, repair
from .greedy import solve as greedy


def solve(inst: Instance, seed: int = 0, sweeps: int = 400, t0: float = 2.0, t_end: float = 0.01, **_) -> tuple[list[int], dict]:
    rng = random.Random(seed)
    ev = FastEvaluator(inst)
    scale, pen = cost_scale(ev), penalty_weight(ev)
    x, _ = greedy(inst, seed)
    loads = loads_of(ev, x)
    cur = ev.score(x)
    best, best_score = list(x), cur
    steps = sweeps * inst.n
    for s in range(steps):
        T = t0 * (t_end / t0) ** (s / max(1, steps - 1))
        j = rng.randrange(inst.n)
        e = rng.randrange(inst.m - 1)
        d_old = x[j]
        e = e if e < d_old else e + 1
        c = ev.cpu[j]
        over_before = max(0, loads[d_old] - ev.cap[d_old]) + max(0, loads[e] - ev.cap[e])
        over_after = max(0, loads[d_old] - c - ev.cap[d_old]) + max(0, loads[e] + c - ev.cap[e])
        d_score = ev.delta(x, j, e)
        dE = (d_score + pen * (over_after - over_before)) / scale
        if dE <= 0 or rng.random() < math.exp(-dE / T):
            x[j] = e
            loads[d_old] -= c
            loads[e] += c
            cur += d_score
            if cur < best_score and all(l <= cap for l, cap in zip(loads, ev.cap)):
                best, best_score = list(x), cur
    best = repair(ev, best)
    return best, {"score": ev.score(best), "sweeps": sweeps}

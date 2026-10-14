"""Shared helpers: capacity repair and penalty weight. STATUS: IMPLEMENTED"""
from __future__ import annotations

from ..scoring import FastEvaluator


def loads_of(ev: FastEvaluator, x: list[int]) -> list[int]:
    loads = [0] * len(ev.cap)
    for j, d in enumerate(x):
        loads[d] += ev.cpu[j]
    return loads


def repair(ev: FastEvaluator, x: list[int]) -> list[int]:
    """Deterministic capacity repair: repeatedly move the task from an overloaded region whose move
    to a region with room costs the least extra score per CPU core freed."""
    x = list(x)
    loads = loads_of(ev, x)
    m = len(ev.cap)
    for _ in range(len(x) * m):
        over = [d for d in range(m) if loads[d] > ev.cap[d]]
        if not over:
            return x
        best = None
        for j, d in enumerate(x):
            if d not in over:
                continue
            for e in range(m):
                if e != d and loads[e] + ev.cpu[j] <= ev.cap[e]:
                    key = (ev.delta(x, j, e) / ev.cpu[j], j, e)
                    if best is None or key < best:
                        best = key
        if best is None:
            break
        _, j, e = best
        loads[x[j]] -= ev.cpu[j]
        loads[e] += ev.cpu[j]
        x[j] = e
    if any(l > c for l, c in zip(loads, ev.cap)):
        raise ValueError("repair failed: instance may be infeasible")
    return x


def penalty_weight(ev: FastEvaluator) -> float:
    """Capacity-overflow penalty per CPU core: larger than any single task's cost spread per core."""
    spread = max((max(r) - min(r)) / c for r, c in zip(ev.lin, ev.cpu))
    return 3.0 * spread + 1.0


def cost_scale(ev: FastEvaluator) -> float:
    """Typical size of a move's cost change, used to normalise temperatures."""
    s = [max(r) - min(r) for r in ev.lin]
    return max(1.0, sum(s) / len(s))

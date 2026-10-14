"""Greedy (classical baseline). Tasks in order; each picks the cheapest region with room,
counting edges to already-placed neighbours. STATUS: IMPLEMENTED"""
from __future__ import annotations

from ..instance import Instance
from ..scoring import FastEvaluator
from .common import repair


def solve(inst: Instance, seed: int = 0, **_) -> tuple[list[int], dict]:
    ev = FastEvaluator(inst)
    x = [-1] * inst.n
    remaining = list(ev.cap)
    for j in range(inst.n):
        best = None
        for d in range(inst.m):
            c = ev.lin[j][d]
            for k, mat, j_parent in ev.adj[j]:
                if x[k] >= 0:
                    c += mat[d][x[k]] if j_parent else mat[x[k]][d]
            room = remaining[d] >= ev.cpu[j]
            key = (not room, c)
            if best is None or key < best[0]:
                best = (key, d)
        d = best[1]
        x[j] = d
        remaining[d] -= ev.cpu[j]
    x = repair(ev, x)
    return x, {"score": ev.score(x)}

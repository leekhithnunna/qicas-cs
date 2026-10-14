"""Lagrangian dual-price market (off-chain preview of the full project). STATUS: IMPLEMENTED (baseline version)

Capacity constraints couple all tasks. Relax them with a price lambda_d per CPU core in region d:
    g(lambda) = sum_w  min_{x_w} [ sum_j (lin_j(x_j) + lambda_{x_j} * cpu_j) + edges_w(x_w) ]  -  sum_d lambda_d * C_d
Each workflow is then an independent small problem (solved exactly here: m^k <= 4^7).
Weak duality: g(lambda) <= OPT for any lambda >= 0  ->  certified LOWER BOUND.
Prices follow a subgradient rule: lambda_d <- max(0, lambda_d + step_k * (load_d - C_d)).
Each round's combined solution is repaired to feasibility -> UPPER BOUND.  gap = (UB - LB) / UB.
This is the "baseline" step rule; improving it is KNOT-3 of the full project.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

from .instance import Instance
from .scoring import FastEvaluator
from .solvers.common import cost_scale, repair


@dataclass
class MarketResult:
    prices: list[list[float]] = field(default_factory=list)
    loads: list[list[int]] = field(default_factory=list)
    lower: list[float] = field(default_factory=list)
    upper: list[int] = field(default_factory=list)
    best_lower: float = -math.inf
    best_upper: int | None = None
    best_schedule: list[int] | None = None

    @property
    def gap(self) -> float:
        if self.best_upper is None or self.best_upper == 0:
            return math.nan
        return (self.best_upper - self.best_lower) / self.best_upper


def _solve_workflow(ev: FastEvaluator, tasks: list[int], lam: list[float], m: int) -> tuple[list[int], float]:
    local_edges = []
    pos = {t: i for i, t in enumerate(tasks)}
    for t in tasks:
        for k, mat, parent in ev.adj[t]:
            if parent and k in pos:
                local_edges.append((pos[t], pos[k], mat))
    best, best_v = None, math.inf
    for cand in itertools.product(range(m), repeat=len(tasks)):
        v = 0.0
        for i, t in enumerate(tasks):
            v += ev.lin[t][cand[i]] + lam[cand[i]] * ev.cpu[t]
        for a, b, mat in local_edges:
            v += mat[cand[a]][cand[b]]
        if v < best_v:
            best, best_v = list(cand), v
    return best, best_v


def run_market(inst: Instance, rounds: int = 25, step0: float = 1.0) -> MarketResult:
    ev = FastEvaluator(inst)
    m = inst.m
    wfs = inst.workflows()
    if max(len(t) for t in wfs.values()) > 7:
        raise ValueError("workflows too large for exact sub-problem solving (max 7 tasks)")
    scale = cost_scale(ev) / (sum(ev.cpu) / len(ev.cpu))     # price units: score per core
    lam = [0.0] * m
    res = MarketResult()
    for k in range(rounds):
        x = [0] * inst.n
        g = 0.0
        for tasks in wfs.values():
            sub, v = _solve_workflow(ev, tasks, lam, m)
            g += v
            for i, t in enumerate(tasks):
                x[t] = sub[i]
        g -= sum(lam[d] * ev.cap[d] for d in range(m))
        loads = [0] * m
        for j, d in enumerate(x):
            loads[d] += ev.cpu[j]
        ub_x = repair(ev, x)
        ub = ev.score(ub_x)
        res.prices.append(list(lam))
        res.loads.append(loads)
        res.lower.append(g)
        res.upper.append(ub)
        res.best_lower = max(res.best_lower, g)
        if res.best_upper is None or ub < res.best_upper:
            res.best_upper, res.best_schedule = ub, ub_x
        step = step0 * scale / math.sqrt(k + 1)
        total_cap = sum(ev.cap)
        lam = [max(0.0, lam[d] + step * (loads[d] - ev.cap[d]) / max(1, total_cap) * m) for d in range(m)]
    return res

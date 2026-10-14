"""Reference scoring — MUST match chain/contracts/CarbonScheduleMarket.sol::evaluate exactly.

STATUS: IMPLEMENTED
A schedule is a list of region indices, one per task.
  carbon_ug = sum_j energy_j * ci[x_j] * 1000
            + sum_{edges, x_j != x_k} (volume * e_net) * (ci[x_j] + ci[x_k]) // 2
  cost_nusd = sum_j energy_j * price[x_j]
            + sum_{edges, x_j != x_k} volume * egress
  score     = w_carbon * carbon_ug + w_cost * cost_nusd
  feasible  = every region's CPU load <= capacity
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .instance import Instance


@dataclass
class Evaluation:
    score: int
    carbon_ug: int
    cost_nusd: int
    loads: list[int]
    feasible: bool


def task_carbon(inst: Instance, j: int, d: int) -> int:
    return inst.tasks[j].energy_wh * inst.regions[d].ci_g_per_kwh * 1000


def task_cost(inst: Instance, j: int, d: int) -> int:
    return inst.tasks[j].energy_wh * inst.regions[d].price_uusd_per_kwh


def edge_carbon(inst: Instance, vol: int, d: int, e: int) -> int:
    if d == e:
        return 0
    return (vol * inst.net_energy_mwh_per_mb) * (inst.regions[d].ci_g_per_kwh + inst.regions[e].ci_g_per_kwh) // 2


def edge_cost(inst: Instance, vol: int, d: int, e: int) -> int:
    return 0 if d == e else vol * inst.egress_nusd_per_mb


def evaluate(inst: Instance, x: Sequence[int]) -> Evaluation:
    if len(x) != inst.n or any(not (0 <= d < inst.m) for d in x):
        raise ValueError("invalid schedule shape or region index")
    carbon = cost = 0
    loads = [0] * inst.m
    for j, d in enumerate(x):
        carbon += task_carbon(inst, j, d)
        cost += task_cost(inst, j, d)
        loads[d] += inst.tasks[j].cpu
    for ed in inst.edges:
        d, e = x[ed.j], x[ed.k]
        carbon += edge_carbon(inst, ed.volume_mb, d, e)
        cost += edge_cost(inst, ed.volume_mb, d, e)
    feasible = all(l <= r.capacity for l, r in zip(loads, inst.regions))
    return Evaluation(inst.w_carbon * carbon + inst.w_cost * cost, carbon, cost, loads, feasible)


def round_robin_baseline(inst: Instance) -> list[int]:
    """Identical rule in the contract: task j tries (j + step) % m, first region with room."""
    remaining = [r.capacity for r in inst.regions]
    out = []
    for j, t in enumerate(inst.tasks):
        for step in range(inst.m):
            d = (j + step) % inst.m
            if remaining[d] >= t.cpu:
                remaining[d] -= t.cpu
                out.append(d)
                break
        else:
            raise ValueError(f"baseline cannot place task {j}")
    return out


class FastEvaluator:
    """Precomputed tables for O(m + degree) move deltas (used by SA / SQA / greedy)."""

    def __init__(self, inst: Instance) -> None:
        self.inst = inst
        m = inst.m
        self.lin = [[inst.w_carbon * task_carbon(inst, j, d) + inst.w_cost * task_cost(inst, j, d)
                     for d in range(m)] for j in range(inst.n)]
        self.adj: list[list[tuple[int, list[list[int]], bool]]] = [[] for _ in range(inst.n)]
        for ed in inst.edges:
            mat = [[inst.w_carbon * edge_carbon(inst, ed.volume_mb, d, e)
                    + inst.w_cost * edge_cost(inst, ed.volume_mb, d, e) for e in range(m)] for d in range(m)]
            self.adj[ed.j].append((ed.k, mat, True))
            self.adj[ed.k].append((ed.j, mat, False))
        self.cpu = [t.cpu for t in inst.tasks]
        self.cap = [r.capacity for r in inst.regions]

    def score(self, x: Sequence[int]) -> int:
        s = sum(self.lin[j][d] for j, d in enumerate(x))
        for j in range(len(x)):
            for k, mat, j_parent in self.adj[j]:
                if j_parent:
                    s += mat[x[j]][x[k]]
        return s

    def local(self, x: Sequence[int], j: int, d: int) -> int:
        """Cost contribution of task j if placed in d, given neighbours' current regions."""
        c = self.lin[j][d]
        for k, mat, j_parent in self.adj[j]:
            c += mat[d][x[k]] if j_parent else mat[x[k]][d]
        return c

    def delta(self, x: Sequence[int], j: int, d: int) -> int:
        return self.local(x, j, d) - self.local(x, j, x[j])

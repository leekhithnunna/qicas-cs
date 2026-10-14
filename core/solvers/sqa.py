"""Simulated Quantum Annealing (path-integral Monte Carlo) — QUANTUM-INSPIRED. STATUS: IMPLEMENTED

Physics: quantum annealing uses a transverse field Gamma that lets the system tunnel through
energy barriers. Suzuki-Trotter turns the quantum system into P coupled classical replicas.
Each task j has a one-hot spin register s_{j,d} = +1 if task j is in region d else -1.
Replica coupling between neighbouring replicas (periodic ring):
      E_couple = -J_perp * sum_j sum_d s^rho_{j,d} s^{rho+1}_{j,d}
      J_perp   = -(P*T/2) * ln(tanh(Gamma / (P*T)))        (grows as Gamma -> 0)
For one task, sum_d s s = m if both replicas agree, m - 4 otherwise, so moving task j in replica
rho from a to b changes the coupling energy by  -4 * J_perp * (agree_after - agree_before)
summed over the two neighbouring replicas.
Problem energy is divided by P (each replica carries 1/P of the classical Hamiltonian).
Gamma is annealed from gamma0 to gamma_end; T is fixed. One-hot is structural (region indices).
Reference: Martonak, Santoro, Tosatti, Phys. Rev. B 66, 094203 (2002).
"""
from __future__ import annotations

import math
import random

from ..instance import Instance
from ..scoring import FastEvaluator
from .common import cost_scale, loads_of, penalty_weight, repair
from .greedy import solve as greedy


def j_perp(P: int, T: float, gamma: float) -> float:
    arg = max(gamma / (P * T), 1e-12)
    return -(P * T / 2.0) * math.log(math.tanh(arg))


def solve(inst: Instance, seed: int = 0, replicas: int = 12, sweeps: int = 150, T: float = 0.05,
          gamma0: float = 3.0, gamma_end: float = 0.01, **_) -> tuple[list[int], dict]:
    rng = random.Random(seed)
    ev = FastEvaluator(inst)
    scale, pen = cost_scale(ev), penalty_weight(ev)
    P, n, m = replicas, inst.n, inst.m
    start, _ = greedy(inst, seed)
    X = []
    for _r in range(P):                                    # perturbed copies of the greedy start
        x = list(start)
        for j in rng.sample(range(n), k=max(1, n // 5)):
            x[j] = rng.randrange(m)
        X.append(x)
    L = [loads_of(ev, x) for x in X]
    best, best_score = list(start), ev.score(start)
    trace = []
    for sweep in range(sweeps):
        frac = sweep / max(1, sweeps - 1)
        gamma = gamma0 * (gamma_end / gamma0) ** frac
        Jp = j_perp(P, T, gamma)
        for rho in range(P):
            x, loads = X[rho], L[rho]
            up, down = X[(rho + 1) % P], X[(rho - 1) % P]
            for _ in range(n):
                j = rng.randrange(n)
                a = x[j]
                b = rng.randrange(m - 1)
                b = b if b < a else b + 1
                c = ev.cpu[j]
                over_b = max(0, loads[a] - ev.cap[a]) + max(0, loads[b] - ev.cap[b])
                over_a = max(0, loads[a] - c - ev.cap[a]) + max(0, loads[b] + c - ev.cap[b])
                d_prob = (ev.delta(x, j, b) + pen * (over_a - over_b)) / scale / P
                agree_before = (up[j] == a) + (down[j] == a)
                agree_after = (up[j] == b) + (down[j] == b)
                d_couple = -4.0 * Jp * (agree_after - agree_before) / P
                dE = d_prob + d_couple
                if dE <= 0 or rng.random() < math.exp(-dE / T):
                    x[j] = b
                    loads[a] -= c
                    loads[b] += c
            if all(l <= cap for l, cap in zip(loads, ev.cap)):
                sc = ev.score(x)
                if sc < best_score:
                    best, best_score = list(x), sc
        trace.append(best_score)
    best = repair(ev, best)
    return best, {"score": ev.score(best), "replicas": P, "sweeps": sweeps, "trace": trace}

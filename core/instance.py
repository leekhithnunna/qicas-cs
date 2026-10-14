"""Problem instance: regions, workflow tasks (DAGs), data-transfer edges.

STATUS: IMPLEMENTED
All numbers are INTEGERS so Python and Solidity compute identical results.
Unit trick (no rounding needed):
  energy [Wh] x carbon intensity [g/kWh]  = carbon [mg]   -> x1000 = [µg]
  energy [Wh] x price [µUSD/kWh]          = cost [nUSD]
  network energy [mWh] x intensity [g/kWh] = carbon [µg]
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .hashing import hash_json


@dataclass(frozen=True)
class Region:
    name: str
    ci_g_per_kwh: int          # carbon intensity
    price_uusd_per_kwh: int    # electricity price, micro-USD per kWh
    capacity: int              # CPU cores available for this batch


@dataclass(frozen=True)
class Task:
    name: str
    workflow: int
    cpu: int                   # cores
    energy_wh: int             # energy if run anywhere (PUE ignored in the case-study model)


@dataclass(frozen=True)
class Edge:
    j: int                     # parent task index
    k: int                     # child task index
    volume_mb: int             # data passed from j to k


@dataclass
class Instance:
    regions: list[Region]
    tasks: list[Task]
    edges: list[Edge]
    net_energy_mwh_per_mb: int     # network energy intensity
    egress_nusd_per_mb: int        # inter-region transfer price
    w_carbon: int = 1              # objective weights (integers)
    w_cost: int = 1
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.tasks)

    @property
    def m(self) -> int:
        return len(self.regions)

    def workflows(self) -> dict[int, list[int]]:
        out: dict[int, list[int]] = {}
        for i, t in enumerate(self.tasks):
            out.setdefault(t.workflow, []).append(i)
        return out

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def instance_hash(self) -> bytes:
        d = self.to_dict()
        d.pop("meta")
        return hash_json(d)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Instance":
        return cls(
            regions=[Region(**r) for r in d["regions"]],
            tasks=[Task(**t) for t in d["tasks"]],
            edges=[Edge(**e) for e in d["edges"]],
            net_energy_mwh_per_mb=d["net_energy_mwh_per_mb"],
            egress_nusd_per_mb=d["egress_nusd_per_mb"],
            w_carbon=d.get("w_carbon", 1),
            w_cost=d.get("w_cost", 1),
            meta=d.get("meta", {}),
        )


def generate_instance(cfg: dict[str, Any], seed: int) -> Instance:
    """Synthetic Alibaba-style workflow batch (DAGs) over the configured regions.

    cfg keys (see config/demo.yaml): regions, workflows, tasks_per_workflow [lo, hi],
    cpu_range, duration_h_range, watts_per_core, volume_mb_lognormal [mu, sigma],
    capacity_share (per region, fraction of total CPU demand), network, weights.
    """
    rng = random.Random(seed)
    tasks: list[Task] = []
    edges: list[Edge] = []
    lo, hi = cfg["tasks_per_workflow"]
    for w in range(cfg["workflows"]):
        start = len(tasks)
        k = rng.randint(lo, hi)
        for i in range(k):
            cpu = rng.randint(*cfg["cpu_range"])
            dur = rng.uniform(*cfg["duration_h_range"])
            energy = max(1, int(round(cpu * dur * cfg["watts_per_core"])))
            tasks.append(Task(name=f"wf{w}/t{i}", workflow=w, cpu=cpu, energy_wh=energy))
        mu, sigma = cfg["volume_mb_lognormal"]
        for i in range(1, k):                      # each non-root task gets 1-2 parents (DAG)
            parents = rng.sample(range(i), k=min(i, rng.choice([1, 1, 2])))
            for p in parents:
                vol = max(1, int(math.exp(rng.gauss(mu, sigma))))
                edges.append(Edge(j=start + p, k=start + i, volume_mb=vol))
    total_cpu = sum(t.cpu for t in tasks)
    regions = [
        Region(
            name=r["name"],
            ci_g_per_kwh=int(r["ci_g_per_kwh"]),
            price_uusd_per_kwh=int(r["price_uusd_per_kwh"]),
            capacity=max(1, int(math.ceil(total_cpu * r["capacity_share"]))),
        )
        for r in cfg["regions"]
    ]
    inst = Instance(
        regions=regions, tasks=tasks, edges=edges,
        net_energy_mwh_per_mb=int(cfg["network"]["energy_mwh_per_mb"]),
        egress_nusd_per_mb=int(cfg["network"]["egress_nusd_per_mb"]),
        w_carbon=int(cfg["weights"]["carbon"]), w_cost=int(cfg["weights"]["cost"]),
        meta={"seed": seed, "generator": "synthetic-alibaba-style"},
    )
    return inst

"""End-to-end demo pipeline (used by both the CLI and the Streamlit dashboard). STATUS: IMPLEMENTED

Steps
 1. Build instance (synthetic Alibaba-style DAG workflows over 4 regions)
 2. Off-chain optimisation: greedy, SA (classical), SQA (quantum-inspired), Lagrangian dual market
 3. Start chain, deploy contract, publish instance -> contract computes its own baseline
 4. Agents commit (honest: greedy, sa, sqa, dual-market; attackers: over-capacity, copycat, no-show)
 5. Reveal -> contract verifies + scores; attackers rejected / reverted / slashed
 6. Finalize: winner, Merkle root, NET carbon saving (minus blockchain overhead), credits minted
 7. Merkle placement proofs (valid and tampered)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import yaml

from chain.client import Chain, new_salt
from core import merkle
from core.instance import Instance, generate_instance
from core.market import run_market
from core.scoring import evaluate, round_robin_baseline
from core.solvers import KIND, SOLVERS
from demo.paths import CONFIG, RESULTS_JSON

Log = Callable[[str], None]


def load_config(path: str | Path = CONFIG) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


def g(ug: int) -> float:      # µg -> g
    return ug / 1e6


def usd(nusd: int) -> float:  # nUSD -> USD
    return nusd / 1e9


def run(cfg: dict[str, Any], log: Log = print, chain: Chain | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

    # 1 ------------------------------------------------------------------ instance
    inst = generate_instance(cfg, cfg["seed"])
    out["instance"] = {
        "tasks": inst.n, "workflows": len(inst.workflows()), "edges": len(inst.edges),
        "total_cpu": sum(t.cpu for t in inst.tasks),
        "regions": [{"name": r.name, "ci_g_per_kwh": r.ci_g_per_kwh, "price_usd_per_kwh": r.price_uusd_per_kwh / 1e6,
                     "capacity": r.capacity} for r in inst.regions],
        "instance_hash": "0x" + inst.instance_hash().hex(),
    }
    log(f"[1] Instance: {inst.n} tasks in {len(inst.workflows())} DAG workflows, {len(inst.edges)} data edges, "
        f"{inst.m} regions; hash {out['instance']['instance_hash'][:18]}…")

    # 2 ------------------------------------------------------------------ off-chain optimisation
    base_x = round_robin_baseline(inst)
    base = evaluate(inst, base_x)
    results: dict[str, dict[str, Any]] = {"baseline (round-robin)": _row(base, "baseline", 0.0)}
    schedules: dict[str, list[int]] = {}
    for name, fn in SOLVERS.items():
        t0 = time.perf_counter()
        x, info = fn(inst, seed=cfg["seed"], **cfg["solvers"].get(name, {}))
        dt = time.perf_counter() - t0
        schedules[name] = x
        results[name] = _row(evaluate(inst, x), KIND[name], dt)
        if "trace" in info:
            out["sqa_trace"] = info["trace"]
    t0 = time.perf_counter()
    mk = run_market(inst, **cfg["market"])
    schedules["dual-market"] = mk.best_schedule
    results["dual-market"] = _row(evaluate(inst, mk.best_schedule), "decomposition", time.perf_counter() - t0)
    out["market"] = {"lower": mk.lower, "upper": mk.upper, "prices": mk.prices, "loads": mk.loads,
                     "best_lower": mk.best_lower, "best_upper": mk.best_upper, "gap": mk.gap,
                     "capacities": [r.capacity for r in inst.regions]}
    out["offchain"] = results
    for k, v in results.items():
        log(f"[2] {k:24s} score={v['score']:>14,}  carbon={v['carbon_g']:9.1f} g  cost=${v['cost_usd']:.4f}  "
            f"feasible={v['feasible']}  ({v['kind']}, {v['time_s']:.2f}s)")
    log(f"[2] Lagrangian lower bound = {mk.best_lower:,.0f}  -> every schedule above is at most "
        f"{(min(r['score'] for r in results.values()) - mk.best_lower) / min(r['score'] for r in results.values()):.1%} from optimal")

    # 3 ------------------------------------------------------------------ chain
    ccfg = cfg["chain"]
    chain = chain or Chain.start(ccfg["mode"], ccfg.get("rpc_url", ""), int(ccfg["stake_wei"]))
    eid = chain.publish(inst)
    onchain_base = chain.summary(eid)
    assert onchain_base["baseline_score"] == base.score, "contract baseline != Python baseline"
    log(f"[3] Contract deployed at {chain.contract.address}; epoch {eid} published. "
        f"Contract-computed baseline carbon = {g(onchain_base['baseline_carbon_ug']):.1f} g (matches Python)")

    # 4 ------------------------------------------------------------------ commit
    stake = int(ccfg["stake_wei"])
    acc = chain.accounts
    agents = [
        {"label": "greedy", "addr": acc[1], "schedule": schedules["greedy"], "role": "honest"},
        {"label": "sa", "addr": acc[2], "schedule": schedules["sa"], "role": "honest"},
        {"label": "sqa", "addr": acc[3], "schedule": schedules["sqa"], "role": "honest"},
        {"label": "dual-market", "addr": acc[4], "schedule": schedules["dual-market"], "role": "honest"},
        {"label": "attacker: over-capacity", "addr": acc[5], "schedule": [0] * inst.n, "role": "malicious"},
        {"label": "attacker: copycat", "addr": acc[6], "schedule": schedules["sqa"], "role": "malicious"},
        {"label": "attacker: no-show", "addr": acc[7], "schedule": schedules["greedy"], "role": "malicious"},
    ]
    for a in agents:
        a["salt"] = new_salt()
    sqa_agent = agents[2]
    for a in agents:
        if a["label"] == "attacker: copycat":
            # copies SQA's published commitment hash and later tries to reveal SQA's schedule
            from chain.client import commit_hash
            copied = commit_hash(eid, sqa_agent["schedule"], sqa_agent["salt"], sqa_agent["addr"])
            a["salt"] = sqa_agent["salt"]
            chain.commit(eid, a["addr"], a["schedule"], a["salt"], stake, override_hash=copied)
        else:
            chain.commit(eid, a["addr"], a["schedule"], a["salt"], stake)
    log(f"[4] {len(agents)} agents committed hashed schedules with a {stake / 1e18:g} ETH stake each")

    # 5 ------------------------------------------------------------------ reveal
    chain.open_reveal(eid)
    reveals = []
    for a in agents:
        if a["label"] == "attacker: no-show":
            res = {"status": "not revealed"}
        else:
            res = chain.reveal(eid, a["addr"], a["schedule"], a["salt"], a["label"])
        if res["status"] == "accepted":
            py = evaluate(inst, a["schedule"])
            res["python_score_matches"] = (py.score == res["score"])
        reveals.append({"agent": a["label"], "role": a["role"], "address": a["addr"], **res})
        log(f"[5] reveal {a['label']:24s} -> {res['status']}" + (f" score={res.get('score'):,}" if 'score' in res else "")
            + (f" ({res.get('reason')})" if res.get("reason") else ""))
    out["reveals"] = reveals

    # 6 ------------------------------------------------------------------ finalize
    gas_so_far = chain.total_gas()
    overhead_ug = int(gas_so_far / 1e6 * ccfg["energy_wh_per_million_gas"] * ccfg["chain_ci_g_per_kwh"] * 1000)
    summ = chain.finalize(eid, overhead_ug)
    winner = next((a["label"] for a in agents if a["addr"] == summ["best_solver"]), "?")
    gross = summ["baseline_carbon_ug"] - summ["best_carbon_ug"]
    certified_gap = (summ["best_score"] - mk.best_lower) / summ["best_score"]
    out["final"] = {
        "winner": winner, "winner_address": summ["best_solver"], "best_score": summ["best_score"],
        "baseline_carbon_g": g(summ["baseline_carbon_ug"]), "best_carbon_g": g(summ["best_carbon_ug"]),
        "gross_saving_g": g(gross), "overhead_g": g(overhead_ug), "net_saving_g": g(summ["net_saving_ug"]),
        "reduction_pct": 100 * gross / summ["baseline_carbon_ug"],
        "certified_gap_pct": 100 * certified_gap, "merkle_root": summ["merkle_root"],
        "credits_minted": chain.credits(summ["best_solver"]), "total_gas": chain.total_gas(),
        "epoch_id": eid,
        "slashed_eth": chain.contract.functions.slashedPool().call() / 1e18,
    }
    f = out["final"]
    log(f"[6] Winner: {winner}. Carbon {f['baseline_carbon_g']:.1f} g -> {f['best_carbon_g']:.1f} g "
        f"({f['reduction_pct']:.1f}% lower). Chain overhead ≈ {f['overhead_g']:.4f} g. NET saving {f['net_saving_g']:.1f} g; "
        f"{f['credits_minted']} credits minted. Certified gap ≤ {f['certified_gap_pct']:.2f}%. "
        f"Slashed from attackers: {f['slashed_eth']:g} ETH")

    # 7 ------------------------------------------------------------------ Merkle proofs
    best = chain.best_schedule(eid)
    j = 0
    good = chain.verify_placement(eid, j, best[j], merkle.proof(best, j))
    fake_region = (best[j] + 1) % inst.m
    bad = chain.verify_placement(eid, j, fake_region, merkle.proof(best, j))
    out["merkle_check"] = {"task": j, "true_region": best[j], "valid_proof": good,
                           "tampered_region": fake_region, "tampered_proof": bad}
    log(f"[7] Merkle proof task {j} in region {best[j]}: {good}; tampered claim region {fake_region}: {bad}")

    out["transactions"] = [t.__dict__ for t in chain.txs]
    out["_chain"] = chain          # live object for the dashboard (not serialised)
    out["_instance"] = inst
    out["_best"] = best
    return out


def _row(ev, kind: str, t: float) -> dict[str, Any]:
    return {"score": ev.score, "carbon_g": g(ev.carbon_ug), "cost_usd": usd(ev.cost_nusd),
            "feasible": ev.feasible, "kind": kind, "time_s": t}


def save(out: dict[str, Any], path: str | Path = RESULTS_JSON) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in out.items() if not k.startswith("_")}
    Path(path).write_text(json.dumps(clean, indent=2, default=str))

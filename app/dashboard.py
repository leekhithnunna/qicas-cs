"""Streamlit dashboard for the live demo.   Run:  streamlit run app/dashboard.py
STATUS: IMPLEMENTED"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # allow `streamlit run app/dashboard.py`

import pandas as pd
import streamlit as st

from core import merkle
from demo.pipeline import load_config, run, save

st.set_page_config(page_title="QICAS case-study demo", layout="wide")
st.title("QICAS — quantum-inspired, verifiable, carbon-aware scheduling")
st.caption("Case-study demo: DAG workflows placed across 4 cloud regions; solvers compete; a smart contract "
           "verifies every schedule and certifies net carbon savings.")

cfg = load_config(Path(__file__).resolve().parents[1] / "config" / "demo.yaml")
with st.sidebar:
    st.header("Settings")
    cfg["seed"] = st.number_input("Seed", 0, 10_000, int(cfg["seed"]))
    cfg["workflows"] = st.slider("Workflows", 3, 14, int(cfg["workflows"]))
    preset = st.radio("Objective weights", ["Carbon priority (1:1)", "Balanced (1:5)", "Cost priority (1:20)"])
    cfg["weights"] = {"Carbon priority (1:1)": {"carbon": 1, "cost": 1},
                      "Balanced (1:5)": {"carbon": 1, "cost": 5},
                      "Cost priority (1:20)": {"carbon": 1, "cost": 20}}[preset]
    cfg["chain"]["mode"] = st.selectbox("Chain", ["memory", "rpc"], help="rpc = a running Hardhat node")
    if cfg["chain"]["mode"] == "rpc":
        cfg["chain"]["rpc_url"] = st.text_input("RPC URL", cfg["chain"]["rpc_url"])
    go = st.button("▶ Run full demo", type="primary", width="stretch")

if go:
    logs: list[str] = []
    with st.status("Running pipeline…", expanded=True) as status:
        def log(msg: str) -> None:
            logs.append(msg)
            st.write(msg)
        try:
            st.session_state["out"] = run(cfg, log=log)
            save(st.session_state["out"])
            status.update(label="Demo finished", state="complete")
        except Exception as exc:  # show the error instead of a blank page
            status.update(label=f"Failed: {exc}", state="error")
            raise

out = st.session_state.get("out")
if not out:
    st.info("Press **Run full demo** in the sidebar.")
    st.stop()

f = out["final"]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Carbon reduction vs contract baseline", f"{f['reduction_pct']:.1f}%")
c2.metric("Net saving (after chain overhead)", f"{f['net_saving_g']:.1f} g")
c3.metric("Certified optimality gap", f"≤ {f['certified_gap_pct']:.2f}%")
c4.metric("Winner", f["winner"])
c5.metric("Credits minted", f["credits_minted"])

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Instance", "Solvers", "Dual-price market", "On-chain", "Merkle proof"])

with tab1:
    st.subheader("Regions (illustrative values — replace with Electricity Maps snapshot)")
    st.dataframe(pd.DataFrame(out["instance"]["regions"]), width="stretch")
    i = out["instance"]
    st.write(f"{i['tasks']} tasks · {i['workflows']} DAG workflows · {i['edges']} data edges · "
             f"{i['total_cpu']} CPU cores · instance hash `{i['instance_hash']}`")

with tab2:
    df = pd.DataFrame(out["offchain"]).T
    st.dataframe(df, width="stretch")
    st.bar_chart(df[["carbon_g"]].astype(float), height=280)
    if "sqa_trace" in out:
        st.caption("SQA best score per sweep (quantum-inspired annealing progress)")
        st.line_chart(pd.DataFrame({"SQA best score": out["sqa_trace"]}), height=220)

with tab3:
    mk = out["market"]
    st.write("Upper bound (feasible repaired schedule) and lower bound (Lagrangian dual) per round. "
             "The gap between them is a **certified** distance from optimal.")
    st.line_chart(pd.DataFrame({"upper bound": mk["upper"], "lower bound": mk["lower"]}), height=280)
    names = [r["name"] for r in out["instance"]["regions"]]
    st.write("Region prices λ (per CPU core) — over-demanded regions become expensive:")
    st.line_chart(pd.DataFrame(mk["prices"], columns=names), height=240)

with tab4:
    st.dataframe(pd.DataFrame(out["reveals"]).drop(columns=["address"], errors="ignore"), width="stretch")
    st.write("Transactions and gas:")
    st.dataframe(pd.DataFrame(out["transactions"]), width="stretch")
    st.write(f"Total gas: {f['total_gas']:,} · Slashed from attackers: {f['slashed_eth']:g} ETH · "
             f"Merkle root `{f['merkle_root']}`")

with tab5:
    chain, inst, best = out["_chain"], out["_instance"], out["_best"]
    j = st.number_input("Task index", 0, inst.n - 1, 0)
    claimed = st.selectbox("Claimed region", list(range(inst.m)),
                           format_func=lambda d: inst.regions[d].name, index=best[j])
    ok = chain.verify_placement(f["epoch_id"], int(j), int(claimed), merkle.proof(best, int(j)))
    (st.success if ok else st.error)(
        f"On-chain verifyPlacement(task {j} → {inst.regions[claimed].name}) = {ok}")

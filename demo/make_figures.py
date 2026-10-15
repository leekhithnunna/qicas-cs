"""Generate report figures from results/demo_run.json ->  results/figures/*.png
Run after the demo:  python -m demo.make_figures"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # allow `python demo/make_figures.py` from anywhere

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from demo.paths import FIGURES, RESULTS_JSON  # noqa: E402

R = json.loads(RESULTS_JSON.read_text())
OUT = FIGURES
OUT.mkdir(parents=True, exist_ok=True)

# 1. carbon and cost per approach
names = list(R["offchain"].keys())
carbon = [R["offchain"][n]["carbon_g"] for n in names]
cost = [R["offchain"][n]["cost_usd"] for n in names]
fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].bar(names, carbon, color="#3b8a6e"); ax[0].set_ylabel("Carbon (g CO2e)"); ax[0].set_title("Carbon per approach")
ax[1].bar(names, cost, color="#5c6bc0"); ax[1].set_ylabel("Energy + transfer cost (USD)"); ax[1].set_title("Cost per approach")
for a in ax:
    a.tick_params(axis="x", rotation=30)
fig.tight_layout(); fig.savefig(OUT / "fig1_solver_comparison.png", dpi=200)

# 2. market convergence (certified bounds)
mk = R["market"]
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(mk["upper"], label="upper bound (feasible schedule)")
ax.plot(mk["lower"], label="lower bound (Lagrangian dual)")
ax.set_xlabel("Market round"); ax.set_ylabel("Objective score"); ax.set_title("Dual-price market convergence"); ax.legend()
fig.tight_layout(); fig.savefig(OUT / "fig2_market_bounds.png", dpi=200)

# 3. region prices
fig, ax = plt.subplots(figsize=(6, 4))
regions = [r["name"] for r in R["instance"]["regions"]]
for d, name in enumerate(regions):
    ax.plot([p[d] for p in mk["prices"]], label=name)
ax.set_xlabel("Market round"); ax.set_ylabel("Price per CPU core (score units)"); ax.set_title("Congestion prices λ"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "fig3_region_prices.png", dpi=200)

# 4. gross vs net saving
f = R["final"]
fig, ax = plt.subplots(figsize=(5, 4))
ax.bar(["baseline", "winner", "chain overhead"], [f["baseline_carbon_g"], f["best_carbon_g"], f["overhead_g"]],
       color=["#9e9e9e", "#3b8a6e", "#e57373"])
ax.set_ylabel("g CO2e"); ax.set_title(f"Net saving {f['net_saving_g']:.1f} g ({f['reduction_pct']:.1f}% gross reduction)")
fig.tight_layout(); fig.savefig(OUT / "fig4_net_saving.png", dpi=200)
print("Figures written to", OUT)

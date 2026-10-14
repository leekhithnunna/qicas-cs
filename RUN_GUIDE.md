# Run Guide

## Setup and Commands

Run these from the repository root in PowerShell. The verified environment is Python 3.12.15.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m demo.run_demo
.\.venv\Scripts\python.exe -m demo.make_figures
explorer results\figures
.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py
```

Expected test result: `8 passed`. The verified seed-7 CLI run printed these key lines (runtime and transaction address can vary):

```text
[5] reveal greedy                   -> accepted score=872,431,150
[5] reveal sa                       -> accepted score=758,638,650
[5] reveal sqa                      -> accepted score=730,160,300
[5] reveal dual-market              -> accepted score=709,208,800
[5] reveal attacker: over-capacity  -> rejected (capacity violated)
[5] reveal attacker: copycat        -> reverted (HashMismatch)
[5] reveal attacker: no-show        -> not revealed
[6] Winner: dual-market. Carbon 961.8 g -> 531.8 g (44.7% lower). Chain overhead ≈ 1.8681 g. NET saving 428.0 g; 428 credits minted. Certified gap ≤ 9.92%. Slashed from attackers: 3 ETH
[7] Merkle proof task 0 in region 2: True; tampered claim region 3: False
```

Optional local RPC mode (requires Node.js 18+; this path was not exercised during verification):

```powershell
Set-Location chain/hardhat
npm install
npx hardhat node
```

In a second terminal at the repository root:

```powershell
.\.venv\Scripts\python.exe -m demo.run_demo --mode rpc --rpc-url http://127.0.0.1:8545
```

For the dashboard's RPC option, choose `rpc` in the sidebar and enter `http://127.0.0.1:8545`.

## Five-Minute Presentation

1. **0:00–0:40 — Start the story.** Click **Run full demo**. Explain that the demo places connected workflow tasks across four regions with different illustrative carbon, price, and capacity values.
2. **0:40–1:30 — Compare solvers.** Open **Solvers**. Point out that greedy and simulated annealing are classical, while SQA is quantum-inspired and runs on a classical computer. Use **Compare weights** to show winner carbon and cost under carbon-priority, balanced, and cost-priority settings.
3. **1:30–2:10 — Show the market.** Open **Dual-price market**. Describe the feasible upper bound, Lagrangian lower bound, and how regional prices rise with demand.
4. **2:10–3:15 — Show verification.** Open **On-chain**. Walk through honest reveals and the rejected over-capacity, reverted copycat, and unrevealed no-show cases; point out the slashed stake and transaction gas.
5. **3:15–4:00 — Verify a placement.** Open **Merkle proof**. Show that the selected task placement verifies, then change the claimed region and show the claim fails.
6. **4:00–5:00 — Close with evidence and limits.** Return to the summary metrics and mention the net carbon saving and certified gap. State that the region inputs and workload are illustrative/synthetic, the carbon-data oracle is trusted, overhead is estimated, SQA is not quantum hardware or quantum advantage, and the market is off-chain in this demo.
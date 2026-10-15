# Run Guide

## Prerequisites

- Git
- Any Python ≥ 3.10 on PATH, used only to install [uv](https://docs.astral.sh/uv/). uv creates the
  project venv with **Python 3.12** (downloading it if needed). Python 3.13 is not supported by the EVM dependencies.
- Windows only: enable long paths once in an **Admin** PowerShell, or `pip` may fail on Streamlit's nested files:
  ```powershell
  New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
  ```

## Setup and Commands

### Windows (PowerShell)

```powershell
git clone https://github.com/leekhithnunna/qicas-cs.git
cd qicas-cs
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1          # .venv + deps + tests
powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1       # tests + CLI demo + figures
powershell -ExecutionPolicy Bypass -File scripts\run_dashboard.ps1  # dashboard at http://localhost:8501
```

Manual equivalent (from the repository root):

```powershell
python -m pip install --user uv
python -m uv venv --python 3.12 --seed .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m demo.run_demo
.venv\Scripts\python -m demo.make_figures
explorer results\figures
.venv\Scripts\python -m streamlit run app\dashboard.py
```

### macOS / Linux

```bash
git clone https://github.com/leekhithnunna/qicas-cs.git && cd qicas-cs
bash scripts/setup.sh
bash scripts/run_demo.sh
bash scripts/run_dashboard.sh
```

Manual equivalent: replace `.venv\Scripts\python` with `.venv/bin/python` in the Windows commands above.

The scripts change to the project root themselves, so they can be started from any directory.

### Environment variables (optional, see `.env.example`)

| Variable | Default | Meaning |
|---|---|---|
| `QICAS_CONFIG` | `config/demo.yaml` | config used by the CLI, dashboard and `scripts/load_em_snapshot.py` |
| `QICAS_RESULTS` | `results` | output folder for `demo_run.json` and `figures/` |
| `ELECTRICITYMAPS_API_KEY` | — | reserved; not read by any code yet |

Relative values resolve against the project root. Set them in the shell (`$env:QICAS_RESULTS = "results-alt"` /
`export QICAS_RESULTS=results-alt`); `.env` is not loaded automatically.

## Expected results

Expected test result: `8 passed`. The verified seed-7 CLI run prints these key lines (runtime, contract
address and total gas can vary slightly; gas varies by multiples of 12 because commit salts are random):

```text
[1] Instance: 39 tasks in 8 DAG workflows, 36 data edges, 4 regions
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

Total gas ≈ 9,576,573 (`results/demo_run.json` → `final.total_gas`).

## Optional local RPC mode

Requires Node.js 18+; this path was not exercised during verification.

```powershell
Set-Location chain/hardhat
npm install
npx hardhat node
```

In a second terminal at the repository root:

```powershell
.venv\Scripts\python -m demo.run_demo --mode rpc --rpc-url http://127.0.0.1:8545
```

For the dashboard's RPC option, choose `rpc` in the sidebar and enter `http://127.0.0.1:8545`.

## Five-Minute Presentation

1. **0:00–0:40 — Start the story.** Click **Run full demo**. Explain that the demo places connected workflow tasks across four regions with different illustrative carbon, price, and capacity values.
2. **0:40–1:30 — Compare solvers.** Open **Solvers**. Point out that greedy and simulated annealing are classical, while SQA is quantum-inspired and runs on a classical computer. Use **Compare weights** to show winner carbon and cost under carbon-priority, balanced, and cost-priority settings.
3. **1:30–2:10 — Show the market.** Open **Dual-price market**. Describe the feasible upper bound, Lagrangian lower bound, and how regional prices rise with demand.
4. **2:10–3:15 — Show verification.** Open **On-chain**. Walk through honest reveals and the rejected over-capacity, reverted copycat, and unrevealed no-show cases; point out the slashed stake and transaction gas.
5. **3:15–4:00 — Verify a placement.** Open **Merkle proof**. Show that the selected task placement verifies, then change the claimed region and show the claim fails.
6. **4:00–5:00 — Close with evidence and limits.** Return to the summary metrics and mention the net carbon saving and certified gap. State that the region inputs and workload are illustrative/synthetic, the carbon-data oracle is trusted, overhead is estimated, SQA is not quantum hardware or quantum advantage, and the market is off-chain in this demo.

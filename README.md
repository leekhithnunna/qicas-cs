# QICAS Case-Study Demo
### Verifiable, quantum-inspired, carbon-aware scheduling of cloud workflows on a blockchain

> **What this repository is:** a complete, working, tested demo for the *case-study* stage of the
> QICAS project. It is small enough to understand in a day and run in one command, but it exercises
> all three pillars studied in the case study: **green cloud scheduling**, **quantum-inspired
> optimisation**, and **blockchain verification**.

---

## 0. Quick start (copy-paste)

**Prerequisites:** Git and any Python ≥ 3.10 on PATH (only to bootstrap [uv](https://docs.astral.sh/uv/)).
The project itself runs on **Python 3.12** — the EVM dependencies do not support 3.13 — and uv downloads a
managed 3.12 automatically if you don't have it. On Windows, enable long paths once (Admin PowerShell),
otherwise `pip` can fail on Streamlit's deeply nested files:
`New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force`

**Windows (PowerShell)**
```powershell
git clone https://github.com/leekhithnunna/qicas-cs.git
cd qicas-cs
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1          # .venv (Python 3.12) + deps + tests
powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1       # tests + CLI demo + figures
powershell -ExecutionPolicy Bypass -File scripts\run_dashboard.ps1  # http://localhost:8501
```
Manual equivalent:
```powershell
python -m pip install --user uv
python -m uv venv --python 3.12 --seed .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q                   # expect: 8 passed
.venv\Scripts\python -m demo.run_demo               # full end-to-end demo in the terminal (~10 s)
.venv\Scripts\python -m demo.make_figures           # report figures -> results/figures/
.venv\Scripts\python -m streamlit run app\dashboard.py
```

**macOS / Linux**
```bash
git clone https://github.com/leekhithnunna/qicas-cs.git && cd qicas-cs
bash scripts/setup.sh           # .venv (Python 3.12) + deps + tests
bash scripts/run_demo.sh        # tests + CLI demo + figures
bash scripts/run_dashboard.sh   # http://localhost:8501
```

All scripts `cd` to the project root themselves, so they work from any directory. The Python entry points
also resolve paths from the project root (`demo/paths.py`), e.g. `python C:\path\to\qicas-cs\demo\run_demo.py`.

**Optional environment variables** (documented in `.env.example`; set them in your shell — `.env` is not auto-loaded):

| Variable | Default | Used by |
|---|---|---|
| `QICAS_CONFIG` | `config/demo.yaml` | CLI demo, dashboard, `scripts/load_em_snapshot.py` |
| `QICAS_RESULTS` | `results` | where `demo_run.json` and `figures/` are written/read |
| `ELECTRICITYMAPS_API_KEY` | — | reserved; no code reads it yet (the loader uses CSV exports) |

Relative values are resolved against the project root. CLI flags (`--config`, `--mode`, `--rpc-url`, `--seed`) still override.

**Expected verified results** (seed 7, default config):

| Metric | Value |
|---|---|
| Instance | 39 tasks, 8 workflows, 36 edges, 4 regions |
| Baseline carbon (round-robin) | 961.8 g |
| Winner | `dual-market`, 531.8 g |
| Reduction | 44.7 % |
| Certified gap | ≤ 9.92 % |
| Chain overhead | ≈ 1.87 g |
| Net saving / credits minted | 428.0 g / 428 |
| Attackers | over-capacity → rejected; copycat → reverted (`HashMismatch`); no-show → not revealed, slashed |
| Slashed | 3 ETH |
| Merkle proof / tampered proof | True / False |
| Total gas | ≈ 9,576,573 (varies by a few multiples of 12 gas between runs: commit salts are random, so calldata zero-byte counts differ) |
| `pytest -q` | 8 passed |

No Node.js, no Solidity compiler, no API keys are needed for the default mode: the blockchain runs
**in memory** (a real Ethereum Virtual Machine, py-evm) and the contract is precompiled.
An optional mode uses a real local Hardhat node (§9.2).

---

## 1. What the demo shows (the story for your presentation)

1. A batch of **cloud workflows** (DAGs of tasks that pass data to each other) must be placed across
   **4 regions** that differ in **carbon intensity**, **electricity price** and **capacity**.
   Splitting connected tasks across regions costs network energy (carbon) and transfer fees.
2. Four **off-chain solvers** compute schedules:
   `greedy` (classical), `sa` (simulated annealing, classical), `sqa` (**simulated quantum annealing,
   quantum-inspired**), and `dual-market` (Lagrangian price decomposition, which also yields a
   **certified lower bound** on the best possible score).
3. A **smart contract** receives the instance and computes its **own baseline** (so nobody can pick a
   convenient baseline).
4. Solvers **commit** a hash of their schedule plus a stake, then **reveal**. The contract
   **re-computes carbon, cost and capacity on-chain** and keeps the best schedule.
5. Three **attackers** try to cheat and fail on camera:
   - *over-capacity* schedule → **rejected** and stake slashed;
   - *copycat* copies another solver's commitment → **reverted** (`HashMismatch`), because the hash binds the sender;
   - *no-show* commits but never reveals → **slashed** at finalisation.
6. **Finalisation:** winner selected, **Merkle root** of the schedule stored, **net** carbon saving
   (gross saving minus estimated blockchain overhead) minted as credits.
7. Anyone can **verify one task's placement** against the on-chain Merkle root; a tampered claim fails.

Example output (seed 7, default config):
```
[2] baseline (round-robin)   carbon=961.8 g   cost=$0.4968
[2] greedy                   carbon=627.5 g   cost=$0.2449   (classical)
[2] sa                       carbon=542.8 g   cost=$0.2159   (classical)
[2] sqa                      carbon=552.7 g   cost=$0.1774   (quantum-inspired)
[2] dual-market              carbon=531.8 g   cost=$0.1774   (decomposition)
[2] Lagrangian lower bound -> every schedule above is at most 9.9% from optimal
[5] attacker: over-capacity -> rejected (capacity violated)
[5] attacker: copycat       -> reverted (HashMismatch)
[6] Winner: dual-market. Carbon 961.8 g -> 531.8 g (44.7% lower). NET saving 428.0 g; 428 credits minted.
    Certified gap <= 9.92%. Slashed from attackers: 3 ETH
[7] Merkle proof task 0: True; tampered claim: False
```
(Exact numbers depend on seed and config. Region values are illustrative, see §5.)

---

## 2. How the demo maps to the three case-study papers
Full details and the reading template: `docs/CASE_STUDY_PAPERS.md`.

| Pillar | Core paper (expected quartile — verify) | What we take | What the demo adds | Where in code |
|---|---|---|---|---|
| Green cloud | Radovanović et al., *IEEE Trans. Power Systems* 2023 (Q1) | Carbon-weighted, capacity-limited placement | DAG data-transfer carbon; contract-computed baseline | `core/scoring.py`, `baselineSchedule()` |
| Blockchain | *J. Supercomputing* 2026, blockchain-assisted scheduling (Q2) | Optimiser + on-chain validation | Untrusted competing solvers, on-chain re-scoring, slashing, Merkle proofs, net-carbon credits | `chain/contracts/CarbonScheduleMarket.sol` |
| Quantum-inspired | Hammouda et al., *Scientific Reports* 2026 (Q1) | Quantum-inspired heuristic for energy-aware scheduling | Simulated quantum annealing with one-hot registers; honest comparison vs classical SA | `core/solvers/sqa.py` |

---

## 3. Architecture

```
                     config/demo.yaml
                            │
                ┌───────────▼───────────┐
                │ core/instance.py      │  synthetic Alibaba-style DAG workflows + 4 regions
                └───────────┬───────────┘
                            │ Instance (all integers)
        ┌───────────────────┼─────────────────────────────┐
        ▼                   ▼                             ▼
 core/solvers/        core/market.py               core/scoring.py  ◄── parity ──► CarbonScheduleMarket.sol
 greedy, sa, sqa      Lagrangian prices,           (reference cost)                 evaluate()
        │             lower bound, repair                                                ▲
        └──────────┬────────┘                                                            │
                   ▼                                                                     │
          demo/pipeline.py  ── chain/client.py (web3.py) ── publish / commit / reveal / finalize ─┘
                   │                    ▲
       ┌───────────┴──────────┐         └─ in-memory EVM (py-evm)  or  Hardhat node (rpc)
       ▼                      ▼
 demo/run_demo.py      app/dashboard.py (Streamlit)        demo/make_figures.py → results/figures/*.png
```

---

## 4. Folder and file guide

```
qicas-cs/
├── README.md                      ← this file (system map + how to run)
├── RUN_GUIDE.md                   ← step-by-step run guide + 5-minute presentation script
├── LICENSE                        ← MIT
├── CHANGES.md                     ← manifest of files created/modified/deleted during the portable-setup pass
├── AGENTS.md, CLAUDE.md, .github/copilot-instructions.md   ← rules AI assistants read automatically
├── requirements.txt
├── conftest.py                    ← empty; makes pytest put the project root on sys.path
├── .env.example                   ← documents QICAS_CONFIG, QICAS_RESULTS, ELECTRICITYMAPS_API_KEY
├── .gitignore                     ← ignores .venv, caches, .env, Hardhat installs; keeps results/ tracked
├── .gitattributes                 ← keeps *.sh scripts LF-only so bash runs them on every OS
├── config/demo.yaml               ← ALL tunable parameters (regions, workload, solvers, chain)
├── core/                          ← pure Python, no blockchain imports
│   ├── hashing.py                 keccak256 (Ethereum hash) + canonical JSON
│   ├── instance.py                Region/Task/Edge/Instance dataclasses; generate_instance()
│   ├── scoring.py                 evaluate(), round_robin_baseline(), FastEvaluator (move deltas)
│   ├── merkle.py                  Merkle tree identical to the contract's
│   ├── market.py                  Lagrangian dual-price market → lower bound + feasible upper bound
│   └── solvers/
│       ├── common.py              capacity repair, penalty weight, cost scale
│       ├── greedy.py              classical constructive baseline
│       ├── sa.py                  simulated annealing (classical)
│       └── sqa.py                 simulated quantum annealing (quantum-inspired, path-integral MC)
├── chain/
│   ├── contracts/CarbonScheduleMarket.sol   the smart contract (single file, no dependencies)
│   ├── build/CarbonScheduleMarket.json      precompiled ABI + bytecode (solc 0.8.24, viaIR, paris)
│   ├── client.py                  web3.py client: deploy, publish, commit, reveal, finalize, views
│   └── hardhat/                   optional local Ethereum node for rpc mode
├── demo/
│   ├── paths.py                   project-root paths + QICAS_CONFIG / QICAS_RESULTS overrides
│   ├── pipeline.py                the 7-step end-to-end scenario (shared by CLI and dashboard)
│   ├── run_demo.py                CLI entry point
│   └── make_figures.py            report figures from results/demo_run.json
├── app/dashboard.py               Streamlit UI (tabs: Instance, Solvers, Market, On-chain, Merkle proof)
├── docs/
│   ├── CASE_STUDY_PAPERS.md       3 core papers + mapping + reading template + comparison table
│   └── CASE_STUDY_REPORT_TEMPLATE.md
├── scripts/
│   ├── setup.ps1 / setup.sh       create .venv with Python 3.12 via uv, install deps, run tests
│   ├── run_demo.ps1 / run_demo.sh tests + CLI demo + figures
│   ├── run_dashboard.ps1 / .sh    launch the Streamlit dashboard (extra args go to streamlit)
│   └── load_em_snapshot.py        build a regions: block from Electricity Maps CSV exports
├── tests/                         pytest: core logic, Python↔Solidity parity, end-to-end
└── results/                       committed reference run: demo_run.json + figures/fig1..fig4.png (regenerated by the demo)
```

---

## 5. Data model and units (why everything is an integer)

Solidity has no floating-point numbers, so every value crossing to the chain is an integer.
The units are chosen so that products need **no rounding**:

| Quantity | Unit | Example |
|---|---|---|
| Task energy | Wh | 2 cores × 1.5 h × 12 W = 36 Wh |
| Carbon intensity | g CO₂e / kWh | Stockholm 40, Mumbai 680 |
| Price | µUSD / kWh | 60 000 = $0.06/kWh |
| Task carbon | Wh × g/kWh = **mg** → ×1000 = **µg** | |
| Task cost | Wh × µUSD/kWh = **nUSD** | |
| Edge network energy | MB × mWh/MB = mWh; × g/kWh = **µg** | |
| Score | `w_carbon · carbon_µg + w_cost · cost_nUSD` | lower is better |

⚠️ **Region values in `config/demo.yaml` are illustrative** (typical order of magnitude). For the report,
replace them with a frozen hour from the **Electricity Maps data portal** (free historical CSVs, ODbL
licence) and real day-ahead prices, and state the date and hour you used. Only `config/demo.yaml` needs to change.

To prepare a pasteable `regions:` block from one Electricity Maps CSV per region, run this from the repository
root, replacing the sample paths with your downloaded CSVs:

```powershell
python scripts/load_em_snapshot.py --hour 2026-10-14T12:00:00Z `
   --region "eu-north-1 (Stockholm)=data/stockholm.csv" `
   --region "eu-west-1 (Ireland)=data/ireland.csv" `
   --region "us-east-1 (Virginia)=data/virginia.csv" `
   --region "ap-south-1 (Mumbai)=data/mumbai.csv"
```

The loader matches the exact UTC hour, recognizes common portal timestamp and carbon-intensity headers, rounds
intensity to the nearest whole g CO₂e/kWh, and preserves each region's configured price and capacity. Replace
the existing `regions:` block with its output; the default config is not changed automatically.

---

## 6. Algorithms (what each solver does)

### 6.1 Problem
Assign each task `j` to a region `x_j`:
```
minimise   Σ_j [w_c·carbon(j, x_j) + w_p·cost(j, x_j)] + Σ_(j,k)∈edges [transfer carbon + fee if x_j ≠ x_k]
subject to Σ_{j: x_j = d} cpu_j ≤ capacity_d   for every region d
```
This is a **Generalised Quadratic Assignment Problem** (NP-hard): the edge terms make it quadratic,
and capacities couple all tasks.

### 6.2 Greedy (classical) — `core/solvers/greedy.py`
Places tasks one by one in the cheapest region with free capacity, counting edges to already-placed
neighbours. Fast, used as the starting point for SA and SQA.

### 6.3 Simulated annealing (classical) — `core/solvers/sa.py`
Random single-task moves; accept worse moves with probability `exp(−ΔE/T)`; temperature cools
geometrically. Capacity overflow is penalised; the best feasible schedule is kept.

### 6.4 Simulated quantum annealing (quantum-inspired) — `core/solvers/sqa.py`
Quantum annealing lets a system *tunnel* through barriers using a transverse field Γ. SQA simulates
this on a classical computer with the **Suzuki–Trotter** trick: `P` replicas of the schedule are
coupled in a ring. Each task is a one-hot "spin register" (one spin per region). Coupling strength
```
J⊥ = −(P·T/2) · ln tanh(Γ / (P·T))
```
grows as Γ is annealed to ~0, forcing replicas to agree on the final answer. Moving task `j` from
region `a` to `b` in replica ρ changes energy by
`Δcost/P  −  4·J⊥·(agreements_after − agreements_before)/P`.
Reference: Martoňák, Santoro, Tosatti, *Phys. Rev. B* 66, 094203 (2002).

### 6.5 Lagrangian dual-price market — `core/market.py`
Each region gets a **price λ_d per CPU core**. With prices, workflows become independent small problems
(solved exactly). The relaxed optimum gives a **lower bound** on the true optimum (weak duality). Prices
rise in over-demanded regions (subgradient rule), the combined answer is repaired into a feasible
schedule (**upper bound**), and `gap = (UB − LB)/UB` is a *certified* distance from optimal. This is the
preview of the full project's on-chain price market.

---

## 7. Blockchain protocol — `chain/contracts/CarbonScheduleMarket.sol`

| Function | Who | What it does |
|---|---|---|
| `publish(...)` | owner | Stores regions, tasks, edges, weights; **computes the round-robin baseline on-chain** |
| `commit(epoch, hash)` + stake | solver | Stores `keccak256(epoch, schedule, salt, sender)`; hides the schedule |
| `openReveal(epoch)` | owner | Moves to reveal phase |
| `reveal(epoch, schedule, salt)` | solver | Checks the hash (binds `msg.sender` → copy attack fails); malformed or over-capacity → `Rejected` + slash; else re-scores with `evaluate()` and keeps the best |
| `finalize(epoch, overheadUg)` | owner | Slashes non-revealers; stores Merkle root of the winner; mints credits = net saving in grams |
| `verifyPlacement(epoch, task, region, proof)` | anyone | Checks one task's placement against the root |
| `evaluate`, `baselineSchedule`, `merkleRootOf`, `commitHashOf`, `summary` | anyone (views) | Used by tests to prove Python ↔ Solidity parity |
| `withdraw()` | solver | Pull-payment refund of honest stakes (reentrancy-guarded) |

**Blockchain concepts exercised:** keccak hashing, commit-reveal, staking and slashing (incentives),
on-chain verification, Merkle trees and proofs, events, a minimal token, pull payments and reentrancy
protection, custom errors, gas measurement.

**Net carbon:** `overhead = total_gas / 1e6 × energy_wh_per_million_gas × chain_ci` (both parameters are
in `config/demo.yaml` and are **sensitivity parameters, not measurements**; state this in the report).

---

## 8. The dashboard (`streamlit run app/dashboard.py`)
Sidebar: seed, number of workflows, objective weights (carbon-priority, balanced, cost-priority), chain mode.
Press **Run full demo**. Tabs:
- **Instance:** region table, workload size, instance hash.
- **Solvers:** score, carbon, cost, feasibility, runtime per approach + SQA progress curve.
- **Dual-price market:** upper and lower bound per round; region prices λ.
- **On-chain:** every reveal with outcome (accepted / rejected / reverted), every transaction with gas.
- **Merkle proof:** pick any task and claimed region → calls `verifyPlacement` on-chain live.

Tip for the live presentation: run once with "Carbon priority", then "Cost priority", and show how the
winning schedule's carbon and cost trade off.

---

## 9. Running options

### 9.1 Default: in-memory chain
`python -m demo.run_demo` (or `--seed 12`, `--config other.yaml`). Results go to `results/demo_run.json`
(or `$QICAS_RESULTS/demo_run.json`).

### 9.2 Real local node (Hardhat) — optional, needs Node.js 18+
```bash
cd chain/hardhat && npm install && npx hardhat node      # keep this terminal open
# new terminal, project root, venv active:
python -m demo.run_demo --mode rpc --rpc-url http://127.0.0.1:8545
```
In the dashboard choose `rpc` in the sidebar. The Python client deploys the precompiled contract to the node.

### 9.3 Recompiling the contract (only if you edit the .sol file)
Option A (Hardhat): copy `chain/contracts/CarbonScheduleMarket.sol` to `chain/hardhat/contracts/`,
run `npx hardhat compile`, then copy `abi` and `bytecode` from
`chain/hardhat/artifacts/contracts/CarbonScheduleMarket.sol/CarbonScheduleMarket.json` into
`chain/build/CarbonScheduleMarket.json` (keep the same keys). Compiler settings must stay:
solc 0.8.24, optimizer 200 runs, `viaIR: true`, `evmVersion: "paris"`.
Option B (solc-js): `npm install solc@0.8.24` and compile with standard JSON input using the same settings.
Then **always** run `python -m pytest -q` (parity tests).

---

## 10. Troubleshooting
| Symptom | Fix |
|---|---|
| `Activate.ps1 cannot be loaded` / scripts blocked | `powershell -ExecutionPolicy Bypass -File scripts\<name>.ps1`, or `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `pip install` fails with `OSError: [Errno 2] No such file or directory` (Windows) | Path > 260 chars: enable long paths (command in §0), or clone to a short path such as `C:\dev\qicas-cs` |
| `pip install` fails building a package on Windows | Use Python 3.12 (`uv venv --python 3.12`); 3.13 is not supported by the EVM dependencies |
| `ModuleNotFoundError: core` | Use the venv Python; from the root run `python -m ...`, from elsewhere run the file path (`python <root>\demo\run_demo.py`) |
| OneDrive: slow installs or locked files | Pause sync or keep the project outside OneDrive |
| Dashboard shows nothing | Press **Run full demo** in the sidebar |
| rpc mode: `cannot connect` | Start `npx hardhat node` first; check the URL/port |
| `repair failed` | Capacities too small: increase `capacity_share` values in `config/demo.yaml` |
| `workflows too large for exact sub-problem` | Keep `tasks_per_workflow` max ≤ 7 |

---

## 11. Honest limitations (put these in the report)
1. Region carbon/price values are illustrative until replaced by a cited snapshot.
2. Workloads are synthetic (Alibaba-style DAG shapes); the full project uses the Alibaba 2018 trace.
3. The oracle problem: the contract verifies schedules **given** the published data; it cannot prove the data is true.
4. SQA is a classical simulation of quantum annealing: we claim *quantum-inspired*, not quantum advantage.
5. The blockchain overhead model is a parameterised estimate.
6. The market runs off-chain in the demo; the full project moves the price rounds on-chain.

## 12. From case study to full project
QAOA with constraint-preserving XY mixers on workflow sub-problems; on-chain price rounds; optimistic
lower-bound certification; multi-signer carbon oracle (EIP-712); ERC-20/ERC-721 via OpenZeppelin;
Hyperledger Besu permissioned network; real Electricity Maps and Alibaba data.

## 13. Glossary
**DAG** directed acyclic graph of tasks · **Carbon intensity** grams CO₂e per kWh of grid electricity ·
**SA / SQA** simulated (quantum) annealing · **Lagrangian relaxation** replacing a constraint with a price ·
**Lower bound** a value no schedule can beat · **Commit-reveal** publish a hash first, the value later ·
**Slashing** confiscating a misbehaving participant's stake · **Merkle root** one hash committing to many
items, enabling short proofs · **Gas** the unit of computation cost on Ethereum.

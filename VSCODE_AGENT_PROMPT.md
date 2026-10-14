# Prompt for your VS Code AI assistant (Copilot Chat agent mode / Claude Code / Cursor / Continue)

Open the unzipped folder in VS Code, open the AI chat in **agent mode** (so it can run terminal
commands), and paste everything between the lines below.

---------------------------------------------------------------------------------------------------
You are working in the repository `qicas-casestudy-demo`. Your job is to get the case-study demo
running end-to-end on THIS machine, verify it, polish it for a live presentation, and finish by
telling me exactly how to run it.

FIRST read, in this order: `README.md`, `AGENTS.md`, `docs/CASE_STUDY_PAPERS.md`.
Obey every rule in `AGENTS.md`. Most importantly: Python and Solidity scoring, baseline, commit hash and
Merkle root must stay identical (`tests/test_parity.py`); never weaken a test to make it pass.

Work through these phases. After each phase, show me the command output and a one-line status.

PHASE 1 — Environment
1. Detect the OS and Python version (need 3.10–3.12; prefer 3.11/3.12). If Python is too new/old, tell me what to install and stop.
2. Create `.venv`, activate it, upgrade pip, `pip install -r requirements.txt`.
3. If installing `web3[tester]` / `py-evm` fails, report the exact error, try `pip install --only-binary=:all:` for the failing package, and if it still fails, switch the demo to rpc mode using `chain/hardhat` (README §9.2) instead of changing code.

PHASE 2 — Verify
4. Run `python -m pytest -q`. Expected: all tests pass. If anything fails, diagnose the root cause and fix it in the smallest possible way. Do NOT modify scoring logic on only one side.
5. Run `python -m demo.run_demo`. Confirm in the output: honest solvers accepted; over-capacity attacker rejected; copycat reverted with HashMismatch; no-show slashed; Merkle proof True and tampered proof False; net saving > 0.
6. Run `python -m demo.make_figures` and confirm 4 PNGs exist in `results/figures/`.

PHASE 3 — Dashboard
7. Launch `streamlit run app/dashboard.py`, open it, press "Run full demo", and check every tab renders without errors. Fix any Streamlit-version incompatibility (e.g. `width="stretch"` vs `use_container_width`) in `app/dashboard.py` only.

PHASE 4 — Presentation polish (only after phases 1–3 pass; keep changes small and tested)
8. In `app/dashboard.py`, add an "About / Papers" expander at the top summarising the 3 core papers from `docs/CASE_STUDY_PAPERS.md` and which module implements each idea.
9. Add a "Compare weights" button that runs the pipeline for the three weight presets (carbon / balanced / cost priority) on the same seed and shows a small table of winner carbon (g) and cost (USD) per preset. Reuse `demo.pipeline.run`; start a fresh in-memory chain per run.
10. Create `scripts/load_em_snapshot.py`: given an Electricity Maps data-portal CSV per region and a UTC hour, read the carbon-intensity column for that hour and print YAML lines I can paste into `config/demo.yaml` (ci_g_per_kwh as integers). Do not change the default config. Add a short section to README §5 explaining its use.
11. Re-run `python -m pytest -q` and `python -m demo.run_demo` to make sure nothing broke.

PHASE 5 — Hand-over
12. Create `RUN_GUIDE.md` at the repo root containing ONLY the exact commands that worked on this machine (setup, tests, CLI demo, figures, dashboard, optional rpc mode), the expected key output lines, and a 5-minute presentation script (what to click and what to say at each step, based on README §1 and §8).
13. Finally, print in chat:
    (a) a summary of every file you changed or created and why,
    (b) the RUN_GUIDE commands,
    (c) any warnings or limitations I must mention in the case-study report (README §11).

Constraints: do not add new heavy dependencies; do not change `chain/build/CarbonScheduleMarket.json`
unless you recompiled the contract exactly as README §9.3 describes and parity tests pass; keep the
default config unchanged; keep `core/` free of web3/streamlit imports.
---------------------------------------------------------------------------------------------------

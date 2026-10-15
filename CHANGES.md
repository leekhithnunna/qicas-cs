# CHANGES — portable setup, cleanup and verification pass (2026-10-16)

Base: commit `8e394fc` from the team zip. No scoring, contract, solver or config values were changed;
`pytest -q` → 8 passed and the seed-7 demo reproduces the reference numbers (see README §0).

## Created

| Path | Purpose |
|---|---|
| `demo/paths.py` | Single paths helper: project `ROOT`, `CONFIG` (`$QICAS_CONFIG`), `RESULTS` (`$QICAS_RESULTS`), `RESULTS_JSON`, `FIGURES` |
| `.env.example` | Documents `QICAS_CONFIG`, `QICAS_RESULTS`, `ELECTRICITYMAPS_API_KEY` (reserved; no code reads it) |
| `.gitattributes` | Forces LF endings for `*.sh` so bash scripts work on Windows clones with `core.autocrlf=true` |
| `scripts/run_dashboard.ps1` | Windows: cd to root, launch Streamlit with the venv Python |
| `scripts/run_dashboard.sh` | macOS/Linux: same |
| `CHANGES.md` | This manifest |
| `results/demo_run.json` | Regenerated seed-7 reference run (previously gitignored, now tracked for evaluators) |
| `results/figures/fig1_solver_comparison.png` | Regenerated figure (newly tracked) |
| `results/figures/fig2_market_bounds.png` | Regenerated figure (newly tracked) |
| `results/figures/fig3_region_prices.png` | Regenerated figure (newly tracked) |
| `results/figures/fig4_net_saving.png` | Regenerated figure (newly tracked) |
| `.venv/` (local only, gitignored) | Fresh Python 3.12.3 venv created with uv |

## Modified

| Path | What changed and why |
|---|---|
| `demo/pipeline.py` | **Protected — path lines only:** `load_config`/`save` defaults now `demo.paths.CONFIG` / `RESULTS_JSON` instead of cwd-relative strings (+1 import) |
| `tests/test_core.py` | **Protected — path lines only:** config opened relative to the test file instead of the cwd (+`pathlib` import) |
| `tests/test_parity.py` | **Protected — path lines only:** same as above |
| `demo/run_demo.py` | Defaults from `demo.paths`; `sys.path` bootstrap so it runs from any directory; UTF-8 stdout (fixed a `UnicodeEncodeError` on `≈` when output is redirected on Windows); prints the absolute results path |
| `demo/make_figures.py` | Reads/writes via `demo.paths` (`RESULTS_JSON`, `FIGURES`) instead of cwd-relative paths; `sys.path` bootstrap |
| `app/dashboard.py` | Loads config via `demo.paths.CONFIG` (honours `QICAS_CONFIG`) |
| `scripts/load_em_snapshot.py` | `--config` default from `demo.paths.CONFIG`; `sys.path` bootstrap |
| `scripts/setup.ps1` | Rewritten: cd to root, create Python 3.12 venv via uv, install with the venv Python, run tests, fail on errors |
| `scripts/setup.sh` | Same for macOS/Linux |
| `scripts/run_demo.ps1` | Rewritten: cd to root; tests + demo + figures with the venv Python (no longer launches the dashboard) |
| `scripts/run_demo.sh` | Same for macOS/Linux |
| `.gitignore` | Stopped ignoring `results/`; added `venv/`, `.mypy_cache/`, `.ruff_cache/`, `.env`, `.streamlit/secrets.toml`, OS junk, `*.log`, `*.tmp`, `~$*`. Kept this version over the GitHub template `.gitignore` when merging `origin/main` |
| `README.md` | Kept over the GitHub placeholder (`# qicas-cs`) when merging `origin/main`. New quick start (prereqs, uv, long paths, scripts), env-var table, expected-results table, updated folder tree, troubleshooting rows |
| `RUN_GUIDE.md` | Prerequisites, Windows + macOS/Linux setup, env vars, expected results incl. gas variance note |
| `requirements.txt` | **Not modified** — all pins installed cleanly on Python 3.12 |
| `config/demo.yaml` | **Not modified** |

## Merged from the GitHub repo

| Path | Note |
|---|---|
| `LICENSE` | MIT licence from the repo's initial commit (`f9785b4`), merged with `--allow-unrelated-histories` |

## Deleted

| Path | Reason |
|---|---|
| `VSCODE_AGENT_PROMPT.md` | One-off development prompt |
| `.venv/` (from the zip) | Belonged to another machine (`C:\Users\91939\...`); replaced by a fresh local venv |
| `__pycache__/` (root, `app/`, `chain/`, `core/`, `core/solvers/`, `demo/`, `scripts/`, `tests/`) | Bytecode caches |
| `.pytest_cache/` | Test cache |
| `../../qicas-casestudy-demo.zip` (outside the repo) | Original 165 MB download; deleted at the owner's request after verification |

## Environment change (outside the repo)

- Windows `LongPathsEnabled` set to `1` (with the owner's approval): `pip` could not install Streamlit into
  `.venv` because one file path was > 260 characters under the OneDrive folder.

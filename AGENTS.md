# AGENTS.md — rules for AI coding assistants (Copilot, Claude, Cursor, Continue…)

Read README.md first. It is the system map.

## Hard rules
1. **Scoring parity is sacred.** `core/scoring.py::evaluate` and `CarbonScheduleMarket.sol::evaluate`
   must return identical integers. Same for `round_robin_baseline` ↔ `baselineSchedule`,
   `core/merkle.py` ↔ `merkleRootOf`, and `chain/client.py::commit_hash` ↔ `commitHashOf`.
   `tests/test_parity.py` enforces this. Never change one side without the other.
2. **The contract artifact is precompiled** (`chain/build/CarbonScheduleMarket.json`). If you edit the
   `.sol` file you MUST recompile (see README §9.3) and re-run `pytest`. Do not hand-edit the JSON.
3. **Integers only** across the Python ↔ Solidity boundary (units in README §5).
4. **`core/` must not import web3 or streamlit.** Chain code lives in `chain/`, UI in `app/`.
5. **Honest labels:** greedy and SA are *classical*; SQA is *quantum-inspired*; never call SA quantum-inspired.
6. **Determinism:** every solver takes `seed`; keep tests deterministic.
7. **Do not "fix" failing parity tests by loosening them.** Find the real mismatch.
8. Before declaring work done: `python -m pytest -q` passes AND `python -m demo.run_demo` completes.

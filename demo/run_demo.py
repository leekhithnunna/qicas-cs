"""CLI entry point:  python -m demo.run_demo [--config config/demo.yaml] [--mode memory|rpc] [--seed N]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # allow `python demo/run_demo.py` from anywhere

from demo.paths import CONFIG, RESULTS_JSON  # noqa: E402
from demo.pipeline import load_config, run, save  # noqa: E402


def main() -> None:
    # Windows consoles/redirects default to cp1252, which cannot print the "≈" in the summary line.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="QICAS case-study end-to-end demo")
    ap.add_argument("--config", default=str(CONFIG), help="config YAML (default: $QICAS_CONFIG or config/demo.yaml)")
    ap.add_argument("--mode", choices=["memory", "rpc"], help="override chain.mode")
    ap.add_argument("--rpc-url", help="override chain.rpc_url")
    ap.add_argument("--seed", type=int, help="override seed")
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.mode:
        cfg["chain"]["mode"] = a.mode
    if a.rpc_url:
        cfg["chain"]["rpc_url"] = a.rpc_url
    if a.seed is not None:
        cfg["seed"] = a.seed
    print("=" * 100)
    print("QICAS case-study demo: quantum-inspired, verifiable, carbon-aware scheduling")
    print("=" * 100)
    out = run(cfg)
    save(out, RESULTS_JSON)
    print("=" * 100)
    print(f"Saved full results to {RESULTS_JSON}")


if __name__ == "__main__":
    main()

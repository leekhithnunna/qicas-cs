"""CLI entry point:  python -m demo.run_demo [--config config/demo.yaml] [--mode memory|rpc] [--seed N]"""
from __future__ import annotations

import argparse

from demo.pipeline import load_config, run, save


def main() -> None:
    ap = argparse.ArgumentParser(description="QICAS case-study end-to-end demo")
    ap.add_argument("--config", default="config/demo.yaml")
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
    save(out)
    print("=" * 100)
    print("Saved full results to results/demo_run.json")


if __name__ == "__main__":
    main()

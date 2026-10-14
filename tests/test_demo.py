"""Full pipeline smoke test (attacks must fail, honest solvers must be accepted)."""
from demo.pipeline import load_config, run


def test_end_to_end():
    cfg = load_config()
    cfg["workflows"] = 5
    out = run(cfg, log=lambda *_: None)
    status = {r["agent"]: r["status"] for r in out["reveals"]}
    assert status["sqa"] == "accepted" and status["dual-market"] == "accepted"
    assert status["attacker: over-capacity"] == "rejected"
    assert status["attacker: copycat"] == "reverted"
    assert out["merkle_check"]["valid_proof"] and not out["merkle_check"]["tampered_proof"]
    assert out["final"]["net_saving_g"] > 0
    assert out["final"]["slashed_eth"] >= 2
    assert all(r.get("python_score_matches", True) for r in out["reveals"])

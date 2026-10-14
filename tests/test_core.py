import yaml

from core import merkle
from core.instance import generate_instance
from core.market import run_market
from core.scoring import evaluate, round_robin_baseline
from core.solvers import SOLVERS

cfg = yaml.safe_load(open("config/demo.yaml"))


def test_solvers_feasible_and_beat_baseline():
    inst = generate_instance(cfg, 11)
    base = evaluate(inst, round_robin_baseline(inst)).score
    for name, fn in SOLVERS.items():
        x, _ = fn(inst, seed=0, **cfg["solvers"][name])
        e = evaluate(inst, x)
        assert e.feasible, name
        assert e.score <= base, name


def test_lower_bound_below_every_feasible_schedule():
    inst = generate_instance(cfg, 5)
    r = run_market(inst, rounds=10)
    for name, fn in SOLVERS.items():
        x, _ = fn(inst, seed=0, **cfg["solvers"][name])
        assert r.best_lower <= evaluate(inst, x).score + 1e-6


def test_merkle_proofs():
    x = [0, 3, 1, 2, 2, 1, 0]
    r = merkle.root(x)
    assert all(merkle.verify(r, j, x[j], merkle.proof(x, j)) for j in range(len(x)))
    assert not merkle.verify(r, 1, 0, merkle.proof(x, 1))

"""Python <-> Solidity parity: scoring, baseline, commit hash, Merkle root."""
import random

import yaml

from chain.client import Chain, commit_hash, new_salt
from core import merkle
from core.instance import generate_instance
from core.scoring import evaluate, round_robin_baseline


def setup_module():
    global cfg, inst, chain, eid
    cfg = yaml.safe_load(open("config/demo.yaml"))
    inst = generate_instance(cfg, 3)
    chain = Chain.start("memory")
    eid = chain.publish(inst)


def test_scoring_parity():
    rng = random.Random(1)
    for _ in range(30):
        x = [rng.randrange(inst.m) for _ in range(inst.n)]
        e = evaluate(inst, x)
        assert chain.evaluate(eid, x) == (e.score, e.carbon_ug, e.cost_nusd, e.feasible)


def test_baseline_parity():
    assert chain.baseline_schedule(eid) == round_robin_baseline(inst)


def test_commit_hash_parity():
    x, s, a = round_robin_baseline(inst), new_salt(), chain.accounts[2]
    assert chain.commit_hash_onchain(eid, x, s, a) == commit_hash(eid, x, s, a)


def test_merkle_parity():
    rng = random.Random(2)
    for n in (1, 2, 5, 16, 39):
        x = [rng.randrange(4) for _ in range(n)]
        assert chain.merkle_root_of(x) == merkle.root(x)

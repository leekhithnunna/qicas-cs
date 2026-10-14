"""Solver portfolio.
classical: greedy, sa   |   quantum-inspired: sqa (simulated quantum annealing, path-integral Monte Carlo)
All solvers: solve(inst, seed, **params) -> (schedule, info). Schedules are capacity-feasible when possible."""
from .greedy import solve as greedy
from .sa import solve as sa
from .sqa import solve as sqa

SOLVERS = {"greedy": greedy, "sa": sa, "sqa": sqa}
KIND = {"greedy": "classical", "sa": "classical", "sqa": "quantum-inspired"}

# Case-study papers (3 core + supporting) and how each maps to the demo

## ⚠️ About Q1/Q2
Quartiles differ by index (SCImago/SJR vs Clarivate JCR), by subject category, and by year.
**Before submitting, look up each journal on https://www.scimagojr.com (and JCR if your department
requires it) and record the quartile, category and year in your report.** The quartiles below are the
expected values for these journals, not verified for your specific evaluation year.

---

## Core paper 1 — Carbon-aware scheduling (the "green cloud" pillar)
**A. Radovanović et al., "Carbon-Aware Computing for Datacenters," *IEEE Transactions on Power Systems*,
vol. 38, no. 2, pp. 1270–1280, 2023.**  Journal expected quartile: **Q1** (Energy / Electrical Engineering).
- What it is: Google's production system that shifts flexible compute in time and across data centres
  according to grid carbon intensity, using day-ahead forecasts and per-cluster limits.
- Why it matters for us: proves carbon-aware scheduling works at industrial scale; defines the
  capacity-limited, carbon-weighted placement problem our demo models.
- Gap we target: centralised and trusted (one operator computes and reports); jobs treated as
  independent; no third-party verification of savings.
- Demo mapping: `core/scoring.py` (carbon × energy model), `config/demo.yaml` (regions, capacity limits),
  contract-computed baseline in `CarbonScheduleMarket.sol::baselineSchedule`.
- Newer alternative (same journal, Q1): S. Hall et al., "Carbon-aware computing for data centers with
  probabilistic performance guarantees," *IEEE Transactions on Power Systems*, 2025.

## Core paper 2 — Blockchain-verified scheduling (the "blockchain" pillar)
**"Blockchain-assisted smart grid scheduling using energy-efficient swarm and deep learning models,"
*The Journal of Supercomputing* (Springer), 2026.**  Journal expected quartile: **Q2** (check category).
Link: https://link.springer.com/article/10.1007/s11227-026-08743-8 (copy the full author list from this page).
- What it is: a hybrid scheduler (swarm optimisation + deep-learning forecasting) whose schedules are
  validated on a blockchain with smart contracts for transparent, tamper-proof execution.
- Why it matters for us: same pattern as our demo — an optimiser produces schedules, a blockchain
  validates them.
- Gap we target: one trusted optimiser; chain validates/records but does not run a competition among
  untrusted solvers, does not recompute cost on-chain, and gives no optimality certificate.
- Demo mapping: `CarbonScheduleMarket.sol` (commit-reveal, on-chain re-scoring, slashing, Merkle root),
  `chain/client.py`.
- Alternative (closest older work): "Blockchain-based decentralized workload and energy management of
  geo-distributed data centers," *Sustainable Computing: Informatics and Systems*, vol. 29, 2021.

## Core paper 3 — Quantum-inspired scheduling (the "quantum" pillar)
**N. G. Hammouda et al., "A quantum-driven multi-objective scheduler for scalable task orchestration in
fog-based cyber-physical-social systems," *Scientific Reports*, vol. 16, art. 6874, 2026.
DOI: 10.1038/s41598-025-33627-x.**  Journal expected quartile: **Q1** (Multidisciplinary).
- What it is: quantum-inspired evolutionary multi-objective scheduling with energy efficiency as an objective.
- Why it matters for us: recent evidence that quantum-inspired heuristics are used for energy-aware scheduling.
- Gap we target: centralised; no carbon-intensity signals across regions; no verifiability.
- Demo mapping: `core/solvers/sqa.py` (our quantum-inspired solver: simulated quantum annealing),
  compared against classical SA and greedy in `demo/pipeline.py` step 2.
- Critical companion (Q1, use in discussion): F. A. Quinton et al., "Quantum annealing applications,
  challenges and limitations for optimisation problems compared to classical solvers," *Scientific
  Reports*, vol. 15, art. 12733, 2025 — helps you avoid over-claiming quantum advantage.

## Supporting (department relevance)
B. M. Beena et al., "A green cloud-based framework for energy-efficient task scheduling using carbon
intensity data for heterogeneous cloud servers," *IEEE Access*, vol. 13, pp. 73916–73936, 2025,
doi:10.1109/ACCESS.2025.3562882 (IEEE Access: expected Q1 in SJR).

---

## Reading template (fill one per paper)
| Field | Notes |
|---|---|
| Problem addressed | |
| System model / assumptions | |
| Method (algorithm, architecture) | |
| Dataset / workload / carbon data | |
| Metrics and baselines | |
| Key results (numbers) | |
| Limitations stated by authors | |
| Limitations we observe | |
| What our demo adopts | |
| What our demo adds | |

## Comparison table for the report
| Aspect | Paper 1 | Paper 2 | Paper 3 | Our demo |
|---|---|---|---|---|
| Carbon-intensity aware | ✔ | partial (energy) | energy only | ✔ |
| DAG / data-transfer cost | ✗ | ? | ? | ✔ |
| Quantum-inspired optimiser | ✗ | ✗ | ✔ | ✔ (SQA) |
| Untrusted solvers compete | ✗ | ✗ | ✗ | ✔ (commit-reveal) |
| On-chain re-verification of cost | ✗ | validation | ✗ | ✔ |
| Certified optimality gap | ✗ | ✗ | ✗ | ✔ (Lagrangian bound) |
| Net carbon incl. blockchain overhead | ✗ | ✗ | ✗ | ✔ |
Fill "?" after reading; correct any ✔/✗ the papers contradict.

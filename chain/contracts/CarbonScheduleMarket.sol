// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title CarbonScheduleMarket — verifiable carbon-aware schedule competition (QICAS case-study demo)
/// @notice Flow per epoch: publish instance (contract computes its own baseline) -> solvers commit
///         hash(schedule, salt, sender) with a stake -> owner opens reveal -> solvers reveal ->
///         contract verifies capacity and recomputes carbon/cost/score (mirrors core/scoring.py)
///         -> finalize: best schedule wins, Merkle root stored, NET carbon saving minted as credits.
/// @dev Single-file and dependency-free on purpose (easy to compile and audit for a case study).
///      The full project splits this into TaskRegistry / DualMarket / GreenCredit using OpenZeppelin.
contract CarbonScheduleMarket {
    // ------------------------------------------------------------------ types
    enum Phase { None, Commit, Reveal, Finalized }

    struct Epoch {
        Phase phase;
        bytes32 instanceHash;
        uint8 m;
        uint256[] ci;          // g/kWh per region
        uint256[] price;       // µUSD/kWh per region
        uint256[] capacity;    // cores per region
        uint256[] cpu;         // cores per task
        uint256[] energy;      // Wh per task
        uint32[] edgeJ;
        uint32[] edgeK;
        uint256[] edgeVol;     // MB
        uint256 netEnergy;     // mWh per MB
        uint256 egress;        // nUSD per MB
        uint256 wCarbon;
        uint256 wCost;
        uint256 baselineScore;
        uint256 baselineCarbon;
        address bestSolver;
        uint256 bestScore;
        uint256 bestCarbon;
        uint256 bestCost;
        uint8[] bestSchedule;
        bytes32 merkleRoot;
        uint256 netSavingUg;
        address[] committers;
        mapping(address => bytes32) commitment;
        mapping(address => uint256) stake;
        mapping(address => bool) revealed;
    }

    // ------------------------------------------------------------------ storage
    address public immutable owner;
    uint256 public immutable minStake;
    uint256 public epochCount;
    mapping(uint256 => Epoch) internal epochs;
    mapping(address => uint256) public withdrawable;   // pull payments (refunds)
    uint256 public slashedPool;
    bool private locked;

    // minimal credit token: 1 unit = 1 gram CO2e of NET certified saving
    string public constant name = "QICAS Green Credit";
    string public constant symbol = "QGC";
    uint8 public constant decimals = 0;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;

    // ------------------------------------------------------------------ events
    event Published(uint256 indexed epochId, bytes32 instanceHash, uint256 baselineScore, uint256 baselineCarbon);
    event Committed(uint256 indexed epochId, address indexed solver);
    event RevealOpened(uint256 indexed epochId);
    event Revealed(uint256 indexed epochId, address indexed solver, uint256 score, uint256 carbonUg, uint256 costNusd, bool isBest);
    event Rejected(uint256 indexed epochId, address indexed solver, string reason);
    event Slashed(uint256 indexed epochId, address indexed solver, uint256 amount, string reason);
    event Finalized(uint256 indexed epochId, address indexed winner, uint256 bestScore, uint256 bestCarbon, uint256 netSavingUg, bytes32 merkleRoot);
    event Transfer(address indexed from, address indexed to, uint256 value);

    // ------------------------------------------------------------------ errors
    error NotOwner();
    error WrongPhase();
    error BadInput();
    error StakeTooLow();
    error AlreadyCommitted();
    error NoCommitment();
    error HashMismatch();
    error Reentrancy();
    error InfeasibleBaseline();

    modifier onlyOwner() { if (msg.sender != owner) revert NotOwner(); _; }
    modifier nonReentrant() { if (locked) revert Reentrancy(); locked = true; _; locked = false; }

    constructor(uint256 minStake_) {
        owner = msg.sender;
        minStake = minStake_;
    }

    // ------------------------------------------------------------------ publish
    /// @notice Publish an instance. regionData = [ci..., price..., capacity...] (3*m values).
    ///         taskData = [cpu..., energy...] (2*n values). params = [netEnergy, egress, wCarbon, wCost].
    function publish(
        bytes32 instanceHash,
        uint8 m,
        uint256[] calldata regionData,
        uint256[] calldata taskData,
        uint32[] calldata edgeJ,
        uint32[] calldata edgeK,
        uint256[] calldata edgeVol,
        uint256[4] calldata params
    ) external onlyOwner returns (uint256 epochId) {
        if (m == 0 || regionData.length != 3 * uint256(m) || taskData.length % 2 != 0) revert BadInput();
        if (edgeJ.length != edgeK.length || edgeJ.length != edgeVol.length) revert BadInput();
        uint256 n = taskData.length / 2;
        epochId = ++epochCount;
        Epoch storage e = epochs[epochId];
        e.instanceHash = instanceHash;
        e.m = m;
        for (uint256 d = 0; d < m; d++) {
            e.ci.push(regionData[d]);
            e.price.push(regionData[m + d]);
            e.capacity.push(regionData[2 * uint256(m) + d]);
        }
        for (uint256 j = 0; j < n; j++) {
            e.cpu.push(taskData[j]);
            e.energy.push(taskData[n + j]);
        }
        for (uint256 i = 0; i < edgeJ.length; i++) {
            if (edgeJ[i] >= n || edgeK[i] >= n) revert BadInput();
            e.edgeJ.push(edgeJ[i]);
            e.edgeK.push(edgeK[i]);
            e.edgeVol.push(edgeVol[i]);
        }
        e.netEnergy = params[0];
        e.egress = params[1];
        e.wCarbon = params[2];
        e.wCost = params[3];
        e.bestScore = type(uint256).max;

        uint8[] memory base = baselineSchedule(epochId);
        (uint256 s, uint256 c, , bool ok) = evaluate(epochId, base);
        if (!ok) revert InfeasibleBaseline();
        e.baselineScore = s;
        e.baselineCarbon = c;
        e.phase = Phase.Commit;
        emit Published(epochId, instanceHash, s, c);
    }

    // ------------------------------------------------------------------ scoring (mirror of core/scoring.py)
    /// @notice Recompute score, carbon (µg), cost (nUSD) and capacity feasibility of a schedule.
    function evaluate(uint256 epochId, uint8[] memory x)
        public view returns (uint256 score, uint256 carbonUg, uint256 costNusd, bool feasible)
    {
        Epoch storage e = epochs[epochId];
        uint256 n = e.cpu.length;
        uint8 m = e.m;
        if (x.length != n) revert BadInput();
        uint256[] memory loads = new uint256[](m);
        for (uint256 j = 0; j < n; j++) {
            uint8 d = x[j];
            if (d >= m) revert BadInput();
            carbonUg += e.energy[j] * e.ci[d] * 1000;
            costNusd += e.energy[j] * e.price[d];
            loads[d] += e.cpu[j];
        }
        for (uint256 i = 0; i < e.edgeJ.length; i++) {
            uint8 a = x[e.edgeJ[i]];
            uint8 b = x[e.edgeK[i]];
            if (a != b) {
                carbonUg += (e.edgeVol[i] * e.netEnergy) * (e.ci[a] + e.ci[b]) / 2;
                costNusd += e.edgeVol[i] * e.egress;
            }
        }
        feasible = true;
        for (uint256 d = 0; d < m; d++) {
            if (loads[d] > e.capacity[d]) { feasible = false; break; }
        }
        score = e.wCarbon * carbonUg + e.wCost * costNusd;
    }

    /// @notice Round-robin baseline (mirror of core/scoring.py::round_robin_baseline).
    function baselineSchedule(uint256 epochId) public view returns (uint8[] memory x) {
        Epoch storage e = epochs[epochId];
        uint256 n = e.cpu.length;
        uint8 m = e.m;
        uint256[] memory remaining = new uint256[](m);
        for (uint256 d = 0; d < m; d++) remaining[d] = e.capacity[d];
        x = new uint8[](n);
        for (uint256 j = 0; j < n; j++) {
            bool placed = false;
            for (uint256 step = 0; step < m; step++) {
                uint256 d = (j + step) % m;
                if (remaining[d] >= e.cpu[j]) {
                    remaining[d] -= e.cpu[j];
                    x[j] = uint8(d);
                    placed = true;
                    break;
                }
            }
            if (!placed) revert InfeasibleBaseline();
        }
    }

    // ------------------------------------------------------------------ commit / reveal
    /// @notice Must equal demo/chain_client.py::commit_hash byte-for-byte.
    function commitHashOf(uint256 epochId, uint8[] memory x, bytes32 salt, address solver) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(epochId, x, salt, solver));
    }

    function commit(uint256 epochId, bytes32 commitment) external payable {
        Epoch storage e = epochs[epochId];
        if (e.phase != Phase.Commit) revert WrongPhase();
        if (msg.value < minStake) revert StakeTooLow();
        if (e.commitment[msg.sender] != bytes32(0)) revert AlreadyCommitted();
        e.commitment[msg.sender] = commitment;
        e.stake[msg.sender] = msg.value;
        e.committers.push(msg.sender);
        emit Committed(epochId, msg.sender);
    }

    function openReveal(uint256 epochId) external onlyOwner {
        Epoch storage e = epochs[epochId];
        if (e.phase != Phase.Commit) revert WrongPhase();
        e.phase = Phase.Reveal;
        emit RevealOpened(epochId);
    }

    /// @notice Reveal a committed schedule. Hash mismatch reverts (protects against copying, since the
    ///         hash binds msg.sender). Structurally valid but infeasible schedules are rejected and slashed.
    function reveal(uint256 epochId, uint8[] calldata x, bytes32 salt) external {
        Epoch storage e = epochs[epochId];
        if (e.phase != Phase.Reveal) revert WrongPhase();
        bytes32 c = e.commitment[msg.sender];
        if (c == bytes32(0) || e.revealed[msg.sender]) revert NoCommitment();
        if (c != commitHashOf(epochId, x, salt, msg.sender)) revert HashMismatch();
        e.revealed[msg.sender] = true;
        uint256 st = e.stake[msg.sender];
        e.stake[msg.sender] = 0;

        if (x.length != e.cpu.length || !_regionsValid(x, e.m)) {
            _slash(epochId, msg.sender, st, "malformed schedule");
            return;
        }
        (uint256 s, uint256 carbon, uint256 cost, bool ok) = evaluate(epochId, x);
        if (!ok) {
            _slash(epochId, msg.sender, st, "capacity violated");
            return;
        }
        withdrawable[msg.sender] += st;     // honest reveal -> stake refundable
        bool isBest = s < e.bestScore;
        if (isBest) {
            e.bestScore = s;
            e.bestCarbon = carbon;
            e.bestCost = cost;
            e.bestSolver = msg.sender;
            e.bestSchedule = x;
        }
        emit Revealed(epochId, msg.sender, s, carbon, cost, isBest);
    }

    // ------------------------------------------------------------------ finalize
    /// @param overheadUg estimated carbon of this epoch's transactions (computed off-chain from gas used).
    function finalize(uint256 epochId, uint256 overheadUg) external onlyOwner {
        Epoch storage e = epochs[epochId];
        if (e.phase != Phase.Reveal) revert WrongPhase();
        e.phase = Phase.Finalized;
        for (uint256 i = 0; i < e.committers.length; i++) {      // slash non-revealers
            address a = e.committers[i];
            if (!e.revealed[a] && e.stake[a] > 0) {
                uint256 st = e.stake[a];
                e.stake[a] = 0;
                _slash(epochId, a, st, "did not reveal");
            }
        }
        if (e.bestSolver != address(0)) {
            e.merkleRoot = merkleRootOf(e.bestSchedule);
            uint256 spent = e.bestCarbon + overheadUg;
            e.netSavingUg = e.baselineCarbon > spent ? e.baselineCarbon - spent : 0;
            uint256 credits = e.netSavingUg / 1_000_000;           // µg -> g
            if (credits > 0) {
                totalSupply += credits;
                balanceOf[e.bestSolver] += credits;
                emit Transfer(address(0), e.bestSolver, credits);
            }
        }
        emit Finalized(epochId, e.bestSolver, e.bestScore, e.bestCarbon, e.netSavingUg, e.merkleRoot);
    }

    function withdraw() external nonReentrant {
        uint256 amt = withdrawable[msg.sender];
        withdrawable[msg.sender] = 0;                              // effects before interaction
        (bool ok, ) = payable(msg.sender).call{value: amt}("");
        require(ok, "transfer failed");
    }

    function transfer(address to, uint256 value) external returns (bool) {
        require(balanceOf[msg.sender] >= value, "balance");
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
        return true;
    }

    // ------------------------------------------------------------------ Merkle (mirror of core/merkle.py)
    function leaf(uint256 j, uint8 d) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(j, d));
    }

    function _pair(bytes32 a, bytes32 b) internal pure returns (bytes32) {
        return a < b ? keccak256(abi.encodePacked(a, b)) : keccak256(abi.encodePacked(b, a));
    }

    function merkleRootOf(uint8[] memory x) public pure returns (bytes32) {
        uint256 len = x.length;
        bytes32[] memory level = new bytes32[](len);
        for (uint256 j = 0; j < len; j++) level[j] = leaf(j, x[j]);
        while (len > 1) {
            uint256 next = (len + 1) / 2;
            for (uint256 i = 0; i < len / 2; i++) level[i] = _pair(level[2 * i], level[2 * i + 1]);
            if (len % 2 == 1) level[next - 1] = level[len - 1];
            len = next;
        }
        return level[0];
    }

    /// @notice Anyone can check one task's placement against the stored root.
    function verifyPlacement(uint256 epochId, uint256 j, uint8 d, bytes32[] calldata proof) external view returns (bool) {
        bytes32 h = leaf(j, d);
        for (uint256 i = 0; i < proof.length; i++) h = _pair(h, proof[i]);
        return h == epochs[epochId].merkleRoot;
    }

    // ------------------------------------------------------------------ views
    function summary(uint256 epochId) external view returns (
        uint8 phase, uint256 baselineScore, uint256 baselineCarbon, address bestSolver,
        uint256 bestScore, uint256 bestCarbon, uint256 bestCost, uint256 netSavingUg, bytes32 merkleRoot, uint256 committers
    ) {
        Epoch storage e = epochs[epochId];
        return (uint8(e.phase), e.baselineScore, e.baselineCarbon, e.bestSolver, e.bestScore, e.bestCarbon,
                e.bestCost, e.netSavingUg, e.merkleRoot, e.committers.length);
    }

    function bestSchedule(uint256 epochId) external view returns (uint8[] memory) {
        return epochs[epochId].bestSchedule;
    }

    // ------------------------------------------------------------------ internal
    function _regionsValid(uint8[] calldata x, uint8 m) internal pure returns (bool) {
        for (uint256 j = 0; j < x.length; j++) if (x[j] >= m) return false;
        return true;
    }

    function _slash(uint256 epochId, address solver, uint256 amount, string memory reason) internal {
        slashedPool += amount;
        emit Rejected(epochId, solver, reason);
        emit Slashed(epochId, solver, amount, reason);
    }
}

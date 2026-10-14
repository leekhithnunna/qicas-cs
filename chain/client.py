"""web3.py client for CarbonScheduleMarket. STATUS: IMPLEMENTED

Two modes:
  memory : in-process Ethereum (eth-tester + py-evm). No node, no install of Node.js needed.
  rpc    : any JSON-RPC node with unlocked accounts (e.g. `npx hardhat node` or Ganache) at rpc_url.
The contract is deployed from the precompiled artifact chain/build/CarbonScheduleMarket.json,
so no Solidity compiler is needed at runtime.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from web3 import Web3
from web3.logs import DISCARD

from core.hashing import keccak256
from core.instance import Instance

ARTIFACT = Path(__file__).parent / "build" / "CarbonScheduleMarket.json"


def commit_hash(epoch_id: int, schedule: Sequence[int], salt: bytes, solver: str) -> bytes:
    """keccak256(abi.encodePacked(uint256 epochId, uint8[] x, bytes32 salt, address solver)).
    NOTE: inside abi.encodePacked, each element of a dynamic array is padded to 32 bytes."""
    data = epoch_id.to_bytes(32, "big")
    for d in schedule:
        data += int(d).to_bytes(32, "big")
    data += salt + bytes.fromhex(solver[2:].lower())
    return keccak256(data)


def new_salt() -> bytes:
    return secrets.token_bytes(32)


@dataclass
class TxLog:
    action: str
    sender: str
    gas: int
    status: str
    detail: str = ""


@dataclass
class Chain:
    w3: Web3
    contract: Any
    accounts: list[str]
    txs: list[TxLog] = field(default_factory=list)

    # ---------------------------------------------------------------- connection / deploy
    @classmethod
    def start(cls, mode: str = "memory", rpc_url: str = "http://127.0.0.1:8545", min_stake: int = 10**18) -> "Chain":
        if mode == "memory":
            from web3 import EthereumTesterProvider
            w3 = Web3(EthereumTesterProvider())
        elif mode == "rpc":
            w3 = Web3(Web3.HTTPProvider(rpc_url))
        else:
            raise ValueError("mode must be 'memory' or 'rpc'")
        if not w3.is_connected():
            raise ConnectionError(f"cannot connect to chain ({mode} {rpc_url})")
        art = json.loads(ARTIFACT.read_text())
        accounts = list(w3.eth.accounts)
        factory = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
        tx = factory.constructor(min_stake).transact({"from": accounts[0]})
        rcpt = w3.eth.wait_for_transaction_receipt(tx)
        contract = w3.eth.contract(address=rcpt.contractAddress, abi=art["abi"])
        chain = cls(w3, contract, accounts)
        chain.txs.append(TxLog("deploy", accounts[0], rcpt.gasUsed, "ok", rcpt.contractAddress))
        return chain

    # ---------------------------------------------------------------- helpers
    def _error_name(self, exc: Exception) -> str:
        """Decode a Solidity custom error (e.g. HashMismatch) from a revert, whatever the provider."""
        selectors = {}
        for item in self.contract.abi:
            if item.get("type") == "error":
                sig = f"{item['name']}({','.join(i['type'] for i in item['inputs'])})"
                selectors[keccak256(sig.encode())[:4]] = item["name"]
        blobs: list[bytes] = []
        e: BaseException | None = exc
        while e is not None:
            for a in getattr(e, "args", ()):
                if isinstance(a, (bytes, bytearray)):
                    blobs.append(bytes(a))
                elif isinstance(a, str):
                    blobs.append(a.encode("latin1", "ignore"))
                    if "0x" in a:
                        for tok in a.replace("'", " ").replace('"', " ").split():
                            if tok.startswith("0x") and len(tok) >= 10:
                                try:
                                    blobs.append(bytes.fromhex(tok[2:10]))
                                except ValueError:
                                    pass
            data = getattr(e, "data", None)
            if isinstance(data, str) and data.startswith("0x") and len(data) >= 10:
                blobs.append(bytes.fromhex(data[2:10]))
            e = e.__cause__ or e.__context__
        for b in blobs:
            for sel, name in selectors.items():
                if sel in b:
                    return name
        return str(exc).split("\n")[0][:120]

    def _send(self, action: str, fn, sender: str, value: int = 0, detail: str = "") -> Any:
        try:
            fn.call({"from": sender, "value": value})          # dry-run to surface revert reasons
            tx = fn.transact({"from": sender, "value": value, "gas": 15_000_000})
            rcpt = self.w3.eth.wait_for_transaction_receipt(tx)
            if rcpt.status != 1:
                raise RuntimeError("transaction reverted")
            self.txs.append(TxLog(action, sender, rcpt.gasUsed, "ok", detail))
            return rcpt
        except Exception as exc:
            reason = self._error_name(exc)
            self.txs.append(TxLog(action, sender, 0, "REVERTED", f"{detail} -> {reason}".strip()))
            raise RuntimeError(reason) from exc

    def total_gas(self) -> int:
        return sum(t.gas for t in self.txs)

    # ---------------------------------------------------------------- protocol
    def publish(self, inst: Instance) -> int:
        m = inst.m
        region_data = ([r.ci_g_per_kwh for r in inst.regions] + [r.price_uusd_per_kwh for r in inst.regions]
                       + [r.capacity for r in inst.regions])
        task_data = [t.cpu for t in inst.tasks] + [t.energy_wh for t in inst.tasks]
        params = [inst.net_energy_mwh_per_mb, inst.egress_nusd_per_mb, inst.w_carbon, inst.w_cost]
        fn = self.contract.functions.publish(
            inst.instance_hash(), m, region_data, task_data,
            [e.j for e in inst.edges], [e.k for e in inst.edges], [e.volume_mb for e in inst.edges], params)
        rcpt = self._send("publish", fn, self.accounts[0], detail=f"{inst.n} tasks, {len(inst.edges)} edges")
        ev = self.contract.events.Published().process_receipt(rcpt, errors=DISCARD)[0]["args"]
        return int(ev["epochId"])

    def commit(self, epoch_id: int, solver: str, schedule: Sequence[int], salt: bytes, stake: int,
               override_hash: bytes | None = None) -> None:
        h = override_hash if override_hash is not None else commit_hash(epoch_id, schedule, salt, solver)
        self._send("commit", self.contract.functions.commit(epoch_id, h), solver, value=stake)

    def open_reveal(self, epoch_id: int) -> None:
        self._send("openReveal", self.contract.functions.openReveal(epoch_id), self.accounts[0])

    def reveal(self, epoch_id: int, solver: str, schedule: Sequence[int], salt: bytes, label: str = "") -> dict:
        """Returns {'status': 'accepted'|'rejected'|'reverted', ...}."""
        try:
            rcpt = self._send("reveal", self.contract.functions.reveal(epoch_id, list(schedule), salt), solver, detail=label)
        except Exception as exc:
            return {"status": "reverted", "reason": str(exc)}
        acc = self.contract.events.Revealed().process_receipt(rcpt, errors=DISCARD)
        if acc:
            a = acc[0]["args"]
            return {"status": "accepted", "score": int(a["score"]), "carbon_ug": int(a["carbonUg"]),
                    "cost_nusd": int(a["costNusd"]), "is_best": bool(a["isBest"]), "gas": rcpt.gasUsed}
        rej = self.contract.events.Rejected().process_receipt(rcpt, errors=DISCARD)
        return {"status": "rejected", "reason": rej[0]["args"]["reason"] if rej else "?", "gas": rcpt.gasUsed}

    def finalize(self, epoch_id: int, overhead_ug: int) -> dict:
        self._send("finalize", self.contract.functions.finalize(epoch_id, overhead_ug), self.accounts[0])
        return self.summary(epoch_id)

    # ---------------------------------------------------------------- views
    def evaluate(self, epoch_id: int, schedule: Sequence[int]) -> tuple[int, int, int, bool]:
        s, c, k, f = self.contract.functions.evaluate(epoch_id, list(schedule)).call()
        return int(s), int(c), int(k), bool(f)

    def baseline_schedule(self, epoch_id: int) -> list[int]:
        return list(self.contract.functions.baselineSchedule(epoch_id).call())

    def summary(self, epoch_id: int) -> dict:
        r = self.contract.functions.summary(epoch_id).call()
        keys = ["phase", "baseline_score", "baseline_carbon_ug", "best_solver", "best_score", "best_carbon_ug",
                "best_cost_nusd", "net_saving_ug", "merkle_root", "committers"]
        out = dict(zip(keys, r))
        out["merkle_root"] = "0x" + bytes(out["merkle_root"]).hex()
        return out

    def best_schedule(self, epoch_id: int) -> list[int]:
        return list(self.contract.functions.bestSchedule(epoch_id).call())

    def verify_placement(self, epoch_id: int, task: int, region: int, proof: Sequence[bytes]) -> bool:
        return bool(self.contract.functions.verifyPlacement(epoch_id, task, region, list(proof)).call())

    def credits(self, addr: str) -> int:
        return int(self.contract.functions.balanceOf(addr).call())

    def merkle_root_of(self, schedule: Sequence[int]) -> bytes:
        return bytes(self.contract.functions.merkleRootOf(list(schedule)).call())

    def commit_hash_onchain(self, epoch_id: int, schedule: Sequence[int], salt: bytes, solver: str) -> bytes:
        return bytes(self.contract.functions.commitHashOf(epoch_id, list(schedule), salt, solver).call())

"""Merkle tree identical to the contract (sorted-pair keccak, odd node promoted). STATUS: IMPLEMENTED.
leaf(j, d) = keccak256(abi.encodePacked(uint256 j, uint8 d))"""
from __future__ import annotations

from collections.abc import Sequence

from .hashing import keccak256


def leaf(j: int, d: int) -> bytes:
    return keccak256(j.to_bytes(32, "big") + d.to_bytes(1, "big"))


def _pair(a: bytes, b: bytes) -> bytes:
    return keccak256(a + b) if a < b else keccak256(b + a)


def levels(x: Sequence[int]) -> list[list[bytes]]:
    lv = [[leaf(j, d) for j, d in enumerate(x)]]
    while len(lv[-1]) > 1:
        cur = lv[-1]
        nxt = [_pair(cur[i], cur[i + 1]) for i in range(0, len(cur) - 1, 2)]
        if len(cur) % 2:
            nxt.append(cur[-1])
        lv.append(nxt)
    return lv


def root(x: Sequence[int]) -> bytes:
    return levels(x)[-1][0]


def proof(x: Sequence[int], j: int) -> list[bytes]:
    out, idx = [], j
    for level in levels(x)[:-1]:
        sib = idx ^ 1
        if sib < len(level):
            out.append(level[sib])
        idx //= 2
    return out


def verify(r: bytes, j: int, d: int, path: Sequence[bytes]) -> bool:
    h = leaf(j, d)
    for s in path:
        h = _pair(h, s)
    return h == r

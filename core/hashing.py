"""keccak256 + canonical JSON (must agree with Solidity). STATUS: IMPLEMENTED."""
from __future__ import annotations

import json
from typing import Any

from Crypto.Hash import keccak


def keccak256(data: bytes) -> bytes:
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def hash_json(obj: Any) -> bytes:
    return keccak256(canonical_json(obj))

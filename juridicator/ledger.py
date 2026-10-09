"""An append-only, hash-chained ledger of evidence, verdicts and human labels.

Each entry carries the hash of the one before it, so changing or removing any past entry breaks every later hash.
This detects tampering by anyone who does not also rewrite the whole tail and the published head. To make that
last step impossible too, publish `head()` somewhere the author of a case cannot edit (see docs/SECURITY.md).
Standard library only. Not yet signed: signatures are a documented gap, not a claim.
"""

from __future__ import annotations

import json
import os

from .evidence import canonical_json, sha256_text

GENESIS = "sha256:" + "0" * 64


def entry_hash(seq: int, kind: str, body: dict, prev: str) -> str:
    return "sha256:" + sha256_text(canonical_json({"seq": seq, "kind": kind, "body": body, "prev": prev}))


class Ledger:
    def __init__(self, path: str):
        self.path = path

    def entries(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    out.append(json.loads(line))
        return out

    def head(self) -> str:
        entries = self.entries()
        return entries[-1]["hash"] if entries else GENESIS

    def append(self, kind: str, body: dict) -> dict:
        entries = self.entries()
        prev = entries[-1]["hash"] if entries else GENESIS
        seq = len(entries)
        entry = {"seq": seq, "kind": kind, "body": body, "prev": prev, "hash": entry_hash(seq, kind, body, prev)}
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return entry

    def verify(self, expected_head: str | None = None) -> tuple[bool, int | None]:
        """(True, None) when the chain is intact, else (False, index of the first bad entry).
        With `expected_head` (the published one) a removed tail is caught too."""
        prev = GENESIS
        entries = self.entries()
        for i, e in enumerate(entries):
            if e.get("seq") != i or e.get("prev") != prev or e.get("hash") != entry_hash(i, e.get("kind", ""), e.get("body", {}), prev):
                return False, i
            prev = e["hash"]
        if expected_head is not None and prev != expected_head:
            return False, len(entries)
        return True, None

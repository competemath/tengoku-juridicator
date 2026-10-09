"""Command line: judge a case from files. Exit code 0 ACCEPT, 10 HOLD, 11 ESCALATE, 12 REJECT, 2 bad input."""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from . import policy as pol
from .ledger import Ledger
from .statute import decide

EXIT = {"ACCEPT": 0, "HOLD": 10, "ESCALATE": 11, "REJECT": 12}


def _read_json_records(path: str) -> list:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    return data if isinstance(data, list) else [data]


def load_evidence(paths: list[str]) -> list:
    files: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, "*.json")) + glob.glob(os.path.join(p, "*.jsonl")))
        else:
            files.append(p)
    out: list = []
    for f in files:
        out += _read_json_records(f)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="juridicator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("judge", help="decide a case from its evidence")
    j.add_argument("--case", required=True)
    j.add_argument("--evidence", nargs="+", required=True)
    j.add_argument("--policy")
    j.add_argument("--precedents")
    j.add_argument("--standing")
    j.add_argument("--ledger")
    v = sub.add_parser("ledger-verify", help="check a ledger's hash chain")
    v.add_argument("--ledger", required=True)
    v.add_argument("--head", help="the published head hash, to catch a removed tail")
    args = ap.parse_args(argv)

    if args.cmd == "ledger-verify":
        ok, bad = Ledger(args.ledger).verify(args.head)
        print(json.dumps({"ok": ok, "first_bad_entry": bad, "head": Ledger(args.ledger).head()}))
        return 0 if ok else 12

    try:
        with open(args.case, encoding="utf-8") as fh:
            case = json.load(fh)
        policy = pol.load(args.policy)
        evidence = load_evidence(args.evidence)
        precedents = _read_json_records(args.precedents) if args.precedents else []
        standing = None
        if args.standing:
            with open(args.standing, encoding="utf-8") as fh:
                standing = json.load(fh)
    except (OSError, ValueError, pol.PolicyError) as exc:
        print(f"juridicator: bad input: {exc}", file=sys.stderr)
        return 2
    verdict = decide(case, evidence, policy, precedents=precedents, standing=standing)
    if args.ledger:
        ledger = Ledger(args.ledger)
        known = {e["body"].get("id") for e in ledger.entries() if e["kind"] == "evidence"}
        for ev in evidence:
            if isinstance(ev, dict) and ev.get("id") not in known and ev.get("id"):
                ledger.append("evidence", ev)
        ledger.append("verdict", verdict)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return EXIT[verdict["decision"]]


if __name__ == "__main__":
    sys.exit(main())

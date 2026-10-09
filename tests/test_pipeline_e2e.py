"""The whole pipeline through the command lines, when the sibling wounder checkout is next door
(`../tengoku-wounder`, or $TENGOKU_WOUNDER_PATH) and ssh-keygen exists. In CI there is no sibling: these skip cleanly.
This is docs/PIPELINE.md as a test."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from juridicator.ledger import Ledger
from tests.helpers import HEAD, NOW, ev

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WOUNDER = os.environ.get("TENGOKU_WOUNDER_PATH") or os.path.join(os.path.dirname(ROOT), "tengoku-wounder")
HAVE = os.path.isfile(os.path.join(WOUNDER, "wounder", "cli.py")) and shutil.which("ssh-keygen") is not None
TEXT_GATE_RIGHT = ["axiom_declared", "comment_hidden_directive", "good_add_comm", "good_decide", "good_int_sub",
                    "good_keyword_in_identifier", "native_decide_used", "sorry_hidden_in_term", "sorry_present", "unsafe_or_implemented_by"]


def run(module, cwd, *args):
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": cwd, "LC_ALL": "C"}
    done = subprocess.run([sys.executable, "-m", module, *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    return done.returncode, done.stdout, done.stderr


@unittest.skipUnless(HAVE, "no sibling tengoku-wounder checkout, or no ssh-keygen")
class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name

    def p(self, *parts):
        return os.path.join(self.d, *parts)

    def dump(self, name, obj):
        with open(self.p(name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return self.p(name)

    def canaries(self, out, *only):
        args = ["run-canaries", "--corpus", os.path.join(WOUNDER, "corpus"), "--reference-gate", "--repo", "competemath/x", "--head", HEAD,
                "--class", "gate", "--out", self.p(out), "--created", NOW]
        for name in only:
            args += ["--only", name]
        code, _, err = run("wounder", WOUNDER, *args)
        self.assertEqual(code, 0, err)

    def standing(self, evdir):
        case = self.dump("gate-case.json", {"repo": "competemath/x", "head_sha": HEAD, "class": "gate"})
        code, out, err = run("juridicator", ROOT, "standing", "--case", case, "--evidence", self.p(evdir), "--out", self.p("standing.json"))
        return code, json.loads(out)["gate_health"] if out else err

    def test_text_only_gate_is_found_unhealthy_then_a_scoped_run_is_healthy(self):
        self.canaries("full")
        code, health = self.standing("full")
        self.assertEqual((code, health), (12, "REJECT"))  # the text gate misses the metaprogram axiom, vacuity and drift
        self.canaries("scoped", *TEXT_GATE_RIGHT)
        self.assertEqual(self.standing("scoped"), (0, "ACCEPT"))

    def test_signed_content_judged_under_a_healthy_gate_and_sampled_by_the_ledger_lottery(self):
        self.canaries("scoped", *TEXT_GATE_RIGHT)
        self.assertEqual(self.standing("scoped"), (0, "ACCEPT"))
        key = self.p("k")
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key], check=True, capture_output=True)
        with open(key + ".pub", encoding="ascii") as fh:
            pub = " ".join(fh.read().split()[:2])
        signers = self.p("allowed_signers")
        with open(signers, "w", encoding="ascii") as fh:
            for who in ("lean-kernel", "lean4lean", "axiom-gate", "sorry-gate"):
                fh.write(f'{who} namespaces="tengoku-evidence/1" {pub}\n')
        os.makedirs(self.p("ev"))
        records = [ev("mechanical.kernel_check", who="lean-kernel"), ev("mechanical.kernel_check", who="lean4lean"),
                   ev("mechanical.axiom_closure", who="axiom-gate"), ev("mechanical.no_sorry", who="sorry-gate")]
        with open(self.p("ev", "content.json"), "w", encoding="utf-8") as fh:
            json.dump(records, fh)
        sigs = self.p("sigs.jsonl")
        for who in ("lean-kernel", "lean4lean", "axiom-gate", "sorry-gate"):
            code, _, err = run("juridicator", ROOT, "sign", "--evidence", self.p("ev"), "--key", key, "--principal", who, "--out", self.p(f"s-{who}.jsonl"))
            self.assertEqual(code, 0, err)
        with open(sigs, "w", encoding="utf-8") as out:
            for who in ("lean-kernel", "lean4lean", "axiom-gate", "sorry-gate"):
                with open(self.p(f"s-{who}.jsonl"), encoding="utf-8") as fh:
                    out.write(fh.read())
        policy = self.dump("policy.json", {"require_signatures": True})
        case = self.dump("case.json", {"repo": "competemath/tengoku-sandbox", "head_sha": HEAD, "class": "content"})
        ledger = self.p("ledger.jsonl")
        # open a lottery batch first, then judge, then reveal
        salt = self.p("salt")
        with open(salt, "w", encoding="utf-8") as fh:
            fh.write("e" * 32)
        _, commit_body, _ = run("wounder", WOUNDER, "lottery", "commit-body", "--salt-file", salt)
        self.assertEqual(run("juridicator", ROOT, "append", "--ledger", ledger, "--kind", "lottery_commit", "--body", self.dump("c.json", json.loads(commit_body)))[0], 0)
        code, out, err = run("juridicator", ROOT, "judge", "--case", case, "--evidence", self.p("ev"), "--policy", policy, "--standing", self.p("standing.json"),
                             "--signatures", sigs, "--allowed-signers", signers, "--ledger", ledger)
        self.assertEqual(code, 0, out + err)
        _, reveal_body, _ = run("wounder", WOUNDER, "lottery", "reveal-body", "--salt-file", salt)
        self.assertEqual(run("juridicator", ROOT, "append", "--ledger", ledger, "--kind", "lottery_reveal", "--body", self.dump("r.json", json.loads(reveal_body)))[0], 0)
        self.assertEqual(Ledger(ledger).verify(), (True, None))
        code, plan, err = run("wounder", WOUNDER, "lottery", "plan", "--ledger", ledger)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(plan)["problems"], [])
        # the same content with no signatures offered is held, not accepted: nothing but attestations counts
        code, out, _ = run("juridicator", ROOT, "judge", "--case", case, "--evidence", self.p("ev"), "--policy", policy, "--standing", self.p("standing.json"))
        self.assertEqual(code, 10)


if __name__ == "__main__":
    unittest.main()

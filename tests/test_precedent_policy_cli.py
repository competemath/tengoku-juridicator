import json
import os
import subprocess
import sys
import tempfile
import unittest

from juridicator import precedent as prec
from juridicator.policy import DEFAULT_POLICY, PolicyError, digest, normalize
from tests.helpers import CASE, STANDING, good_set

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PrecedentTests(unittest.TestCase):
    def test_order_of_the_store_never_matters(self):
        store = [{"id": f"p{i}", "class": "content", "signature": ["a:pass", "b:pass"][: i % 2 + 1]} for i in range(6)]
        a = prec.nearest(["a:pass"], "content", store)
        b = prec.nearest(["a:pass"], "content", list(reversed(store)))
        self.assertEqual(a, b)

    def test_history_needs_enough_labeled_neighbours(self):
        one = [{"label": "reject"}]
        self.assertEqual(prec.history_signal(one), 0)
        self.assertEqual(prec.history_signal([{"label": "reject"}, {"label": "reject"}, {"label": None}]), 1)
        self.assertEqual(prec.history_signal([{"label": "reject"}, {"label": "accept"}]), 0)


class PolicyTests(unittest.TestCase):
    def test_default_policy_file_matches_the_code(self):
        with open(os.path.join(ROOT, "policy", "default.json"), encoding="utf-8") as fh:
            self.assertEqual(normalize(json.load(fh)), normalize(None))

    def test_bad_policies_are_refused_up_front(self):
        for bad in ({"ai_level": 3}, {"tier_audit_rate": [0.5, 0.1, 0.2, 1]}, {"tier_audit_rate": [0, 1, 1, 1]},
                    {"classes": {"x": {"base_tier": 9}}}):
            with self.assertRaises(PolicyError, msg=str(bad)):
                normalize(bad)

    def test_changing_the_policy_changes_the_verdicts_fingerprint(self):
        self.assertNotEqual(digest(normalize(None)), digest(normalize({"ai_level": 1})))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "juridicator", *args], cwd=ROOT, capture_output=True, text=True)

    def test_judge_and_ledger_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            case = os.path.join(d, "case.json")
            ev_path = os.path.join(d, "evidence.json")
            standing = os.path.join(d, "standing.json")
            ledger = os.path.join(d, "ledger.jsonl")
            for path, data in ((case, CASE), (ev_path, good_set()), (standing, STANDING)):
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh)
            r = self.run_cli("judge", "--case", case, "--evidence", ev_path, "--standing", standing, "--ledger", ledger)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)["decision"], "ACCEPT")
            v = self.run_cli("ledger-verify", "--ledger", ledger)
            self.assertEqual(v.returncode, 0)
            held = self.run_cli("judge", "--case", case, "--evidence", ev_path)  # no standing: gate health unproven
            self.assertEqual(held.returncode, 10)

    def test_bad_input_is_exit_two(self):
        r = self.run_cli("judge", "--case", "/nonexistent.json", "--evidence", "/nonexistent")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()

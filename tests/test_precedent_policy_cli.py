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


class LabelCommand(unittest.TestCase):
    def test_label_is_appended_to_the_chain_and_bad_sha_is_refused(self):
        import contextlib
        import io
        import os
        import tempfile

        from juridicator.cli import main
        from juridicator.ledger import Ledger

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.jsonl")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["label", "--ledger", path, "--repo", "r", "--head", "a" * 40, "--label", "reject", "--by", "maintainer"])
            self.assertEqual(code, 0)
            entries = Ledger(path).entries()
            self.assertEqual(entries[0]["kind"], "label")
            self.assertEqual(entries[0]["body"]["label"], "reject")
            self.assertEqual(Ledger(path).verify(), (True, None))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["label", "--ledger", path, "--repo", "r", "--head", "xyz", "--label", "accept", "--by", "m"]), 2)
            self.assertEqual(len(Ledger(path).entries()), 1)


class AppendCommand(unittest.TestCase):
    def test_only_lottery_kinds_can_be_appended_and_the_body_must_be_an_object(self):
        import contextlib
        import io
        from juridicator.cli import main
        from juridicator.ledger import Ledger

        with tempfile.TemporaryDirectory() as d:
            led, body = os.path.join(d, "l.jsonl"), os.path.join(d, "b.json")
            with open(body, "w", encoding="utf-8") as fh:
                json.dump({"commitment": "c" * 64}, fh)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["append", "--ledger", led, "--kind", "lottery_commit", "--body", body]), 0)
            self.assertEqual(Ledger(led).entries()[0]["kind"], "lottery_commit")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["append", "--ledger", led, "--kind", "verdict", "--body", body])
            with open(body, "w", encoding="utf-8") as fh:
                json.dump([1], fh)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["append", "--ledger", led, "--kind", "lottery_commit", "--body", body]), 2)
            self.assertEqual(len(Ledger(led).entries()), 1)


class StandingCommand(unittest.TestCase):
    def test_gate_health_is_written_from_the_canary_verdict(self):
        import contextlib
        import io
        from juridicator.cli import main
        from tests.helpers import ev

        gate = dict(CASE, **{"class": "gate"})
        with tempfile.TemporaryDirectory() as d:
            case, out = os.path.join(d, "case.json"), os.path.join(d, "standing.json")
            with open(case, "w", encoding="utf-8") as fh:
                json.dump(gate, fh)
            for name, outcome, code, health in (("ok.json", "pass", 0, "ACCEPT"), ("bad.json", "fail", 12, "REJECT")):
                path = os.path.join(d, name)
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump([ev("mechanical.canary", outcome, who="wounder", role="wounder", subject={"case": "c0"})], fh)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["standing", "--case", case, "--evidence", path, "--out", out]), code)
                with open(out, encoding="utf-8") as fh:
                    self.assertEqual(json.load(fh)["gate_health"], health)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["standing", "--case", os.path.join(d, "nope.json"), "--evidence", path, "--out", out]), 2)

    def test_a_non_gate_case_is_refused(self):
        import contextlib
        import io
        from juridicator.cli import main

        with tempfile.TemporaryDirectory() as d:
            case, ev_path = os.path.join(d, "case.json"), os.path.join(d, "e.json")
            for path, data in ((case, CASE), (ev_path, [])):
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["standing", "--case", case, "--evidence", ev_path, "--out", os.path.join(d, "o.json")]), 2)
            self.assertFalse(os.path.exists(os.path.join(d, "o.json")))

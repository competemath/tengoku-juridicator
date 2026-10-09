"""Rules added in version 2, each from a gap a sibling repository found while building against the contract."""

import unittest

from juridicator.statute import decide
from tests.helpers import CASE, STANDING, ev, good_set, merit_set


def run(evidence, **kw):
    kw.setdefault("standing", STANDING)
    return decide(CASE, evidence, kw.pop("policy", None), **kw)


GATE = dict(CASE, **{"class": "gate"})


def canaries(n, bad_index=None, error_index=None, report=None):
    out = []
    for i in range(n if report is None else report):
        outcome = "fail" if i == bad_index else "inconclusive" if i == error_index else "pass"
        out.append(ev("mechanical.canary", outcome, who="wounder", role="wounder", subject={"case": f"c{i}"}))
    return out


def manifest(n):
    return ev("manifest.declared", who="wounder", role="wounder", details={
        "checks": ["mechanical.canary"], "expected": [{"kind": "mechanical.canary", "subject": {"case": f"c{i}"}} for i in range(n)]})


class PartialReports(unittest.TestCase):
    def test_complete_canary_run_is_accepted(self):
        self.assertEqual(decide(GATE, [manifest(4)] + canaries(4), None, standing=STANDING)["decision"], "ACCEPT")

    def test_a_missing_subject_holds_even_though_the_kind_was_reported(self):
        v = decide(GATE, [manifest(4)] + canaries(4, report=3), None, standing=STANDING)
        self.assertEqual(v["decision"], "HOLD")
        self.assertTrue(any(r["rule"] == "R9" and "c3" in r["text"] for r in v["reasons"]))

    def test_someone_elses_report_does_not_cover_the_declared_subject(self):
        other = ev("mechanical.canary", "pass", who="someone-else", role="tooling", subject={"case": "c3"})
        v = decide(GATE, [manifest(4)] + canaries(4, report=3) + [other], None, standing=STANDING)
        self.assertEqual(v["decision"], "HOLD")

    def test_without_expected_only_the_kind_is_enforced(self):
        plain = ev("manifest.declared", who="wounder", role="wounder", details={"checks": ["mechanical.canary"]})
        v = decide(GATE, [plain] + canaries(3), None, standing=STANDING)
        self.assertEqual(v["decision"], "ACCEPT")


class CrashIsNotAPass(unittest.TestCase):
    def test_errored_canary_holds(self):
        v = decide(GATE, canaries(4, error_index=2), None, standing=STANDING)
        self.assertEqual(v["decision"], "HOLD")
        self.assertTrue(any(r["rule"] == "R12" for r in v["reasons"]))

    def test_failed_canary_still_rejects(self):
        self.assertEqual(decide(GATE, canaries(4, bad_index=1), None, standing=STANDING)["decision"], "REJECT")

    def test_an_inconclusive_checker_does_not_hold_if_another_passed_the_same_fact(self):
        v = run(good_set() + [ev("mechanical.kernel_check", "inconclusive", who="slow-checker")])
        self.assertEqual(v["decision"], "ACCEPT")


class TrackRecordIsNotTrustedOnItsFace(unittest.TestCase):
    def test_forged_record_without_verification_lowers_nothing(self):
        merit = merit_set()
        base = run(good_set())["tier"]
        self.assertEqual(run(good_set() + merit)["tier"], base)
        verified = [e["id"] for e in merit]
        self.assertEqual(run(good_set() + merit, verified=verified)["tier"], base - 1)

    def test_verifying_other_evidence_does_not_verify_the_record(self):
        merit = merit_set()
        others = [e["id"] for e in merit if e["kind"] != "reproducible.track_record"]
        self.assertEqual(run(good_set() + merit, verified=others)["tier"], run(good_set())["tier"])

    def test_policy_can_turn_the_requirement_off(self):
        merit = merit_set()
        v = run(good_set() + merit, policy={"track_record_requires_verification": False})
        self.assertEqual(v["tier"], run(good_set())["tier"] - 1)


class NewAuthorsAreNotHeld(unittest.TestCase):
    def test_an_inconclusive_track_record_is_context_not_a_failed_check(self):
        r = ev("reproducible.track_record", "inconclusive", who="praiser", role="praiser", details={"lower_bound": 0.0})
        self.assertEqual(run(good_set() + [r])["decision"], "ACCEPT")


class DisputedRestatement(unittest.TestCase):
    def test_non_matching_restatement_goes_to_a_person_not_a_rejection(self):
        r = ev("mechanical.restatement_match", "fail", who="matcher")
        self.assertEqual(run(good_set() + [r])["decision"], "ESCALATE")

    def test_a_person_clears_it(self):
        r = ev("mechanical.restatement_match", "fail", who="matcher")
        human = ev("judgment.human_review", "pass", who="maintainer", role="human")
        self.assertEqual(run(good_set() + [r, human])["decision"], "ACCEPT")

    def test_other_mechanical_failures_still_reject(self):
        self.assertEqual(run(good_set() + [ev("mechanical.no_sorry", "fail", who="g2", subject={"m": 1})])["decision"], "REJECT")


if __name__ == "__main__":
    unittest.main()

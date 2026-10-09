import random
import unittest

from juridicator.statute import decide
from tests.helpers import CASE, HEAD, STANDING, ev, good_set, merit_set


def run(evidence, **kw):
    kw.setdefault("standing", STANDING)
    return decide(CASE, evidence, kw.pop("policy", None), **kw)


class AcceptPath(unittest.TestCase):
    def test_healthy_case_is_accepted(self):
        v = run(good_set())
        self.assertEqual(v["decision"], "ACCEPT", v["reasons"])
        self.assertEqual(v["tier"], 1)

    def test_same_inputs_same_verdict_in_any_order(self):
        evidence = good_set() + merit_set()
        base = run(evidence)
        for seed in range(5):
            shuffled = evidence[:]
            random.Random(seed).shuffle(shuffled)
            self.assertEqual(run(shuffled), base)


class RejectIsNotOverriddenByPraise(unittest.TestCase):
    def test_failed_kernel_check_rejects_despite_every_merit(self):
        v = run(good_set() + merit_set() + [ev("mechanical.no_sorry", "fail", who="other-gate", subject={"module": "M"})])
        self.assertEqual(v["decision"], "REJECT")

    def test_attested_praise_has_no_effect_at_all(self):
        plain = run(good_set())
        praised = run(good_set() + [ev("attested.team", who="praiser", role="praiser", claim="a famous, careful team"),
                                    ev("attested.model", who="praiser", role="praiser", claim="the strongest model")])
        self.assertEqual(praised["decision"], plain["decision"])
        self.assertEqual(praised["tier"], plain["tier"])

    def test_praise_cannot_turn_a_hold_into_an_accept(self):
        v = run(good_set()[:1] + merit_set()[1:])  # one checker only, plenty of merit
        self.assertEqual(v["decision"], "HOLD")


class Screening(unittest.TestCase):
    def test_evidence_about_another_commit_is_ignored(self):
        stale = [ev("mechanical.kernel_check", who=w, head="b" * 40) for w in ("lean-kernel", "lean4lean")]
        v = run(stale + good_set()[2:])
        self.assertEqual(v["decision"], "HOLD")
        self.assertEqual(sum("another commit" in i["why"] for i in v["ignored_evidence"]), 2)

    def test_author_cannot_vouch_for_their_own_work(self):
        own = [ev("mechanical.kernel_check", who="agent-7", role="author-system")]
        v = run(own + good_set()[1:])
        self.assertEqual(v["decision"], "HOLD")
        self.assertTrue(any("author cannot vouch" in i["why"] for i in v["ignored_evidence"]))

    def test_author_may_attest_and_it_is_shown_not_weighed(self):
        v = run(good_set() + [ev("attested.provenance", who="agent-7", role="author-system")])
        self.assertEqual(v["decision"], "ACCEPT")
        self.assertEqual(v["ignored_evidence"], [])

    def test_invalid_and_duplicate_evidence_is_ignored(self):
        dup = good_set()[0]
        bad = dict(good_set()[1], claim="tampered")
        v = run(good_set() + [dup, bad])
        self.assertEqual(v["decision"], "ACCEPT")
        reasons = " ".join(i["why"] for i in v["ignored_evidence"])
        self.assertIn("duplicate", reasons)
        self.assertIn("invalid", reasons)


class Disguise(unittest.TestCase):
    def test_an_attested_record_cannot_wear_a_mechanical_name_to_satisfy_a_requirement(self):
        from juridicator.evidence import compute_id
        e = ev("mechanical.kernel_check", who="lean4lean")
        body = {k: v for k, v in e.items() if k != "id"}
        body.update(verifiability="attested", reproduce=None)
        body["id"] = compute_id(body)  # a correctly stamped lie: it still fails validation
        v = run([good_set()[0], body] + good_set()[2:])
        self.assertEqual(v["decision"], "HOLD")
        self.assertTrue(any("invalid" in i["why"] for i in v["ignored_evidence"]))


class Disagreement(unittest.TestCase):
    def test_checkers_that_disagree_go_to_a_person(self):
        s = {"module": "M"}
        v = run([ev("mechanical.kernel_check", "pass", who="lean-kernel", subject=s),
                 ev("mechanical.kernel_check", "fail", who="lean4lean", subject=s)] + good_set()[2:])
        self.assertEqual(v["decision"], "ESCALATE")
        self.assertTrue(any(r["rule"] == "R7" for r in v["reasons"]))

    def test_one_failing_reproducible_check_holds_two_reject(self):
        one = run(good_set() + [ev("reproducible.fuzz", "fail", who="fuzz-a")])
        two = run(good_set() + [ev("reproducible.fuzz", "fail", who="fuzz-a"), ev("reproducible.fuzz", "fail", who="fuzz-b")])
        self.assertEqual(one["decision"], "HOLD")
        self.assertEqual(two["decision"], "REJECT")


class Requirements(unittest.TestCase):
    def test_missing_required_kind_holds(self):
        v = run([e for e in good_set() if e["kind"] != "mechanical.no_sorry"])
        self.assertEqual(v["decision"], "HOLD")
        self.assertIn("mechanical.no_sorry", v["missing"])

    def test_one_producer_twice_is_not_independent(self):
        v = run([ev("mechanical.kernel_check", who="lean-kernel", subject={"module": "A"}),
                 ev("mechanical.kernel_check", who="lean-kernel", subject={"module": "B"})] + good_set()[2:])
        self.assertEqual(v["decision"], "HOLD")

    def test_declared_manifest_must_be_reported_in_full(self):
        manifest = ev("manifest.declared", who="wounder", role="wounder",
                      details={"checks": ["mechanical.canary", "mechanical.sensitivity"]})
        reported = ev("mechanical.canary", who="wounder", role="wounder")
        v = run(good_set() + [manifest, reported])
        self.assertEqual(v["decision"], "HOLD")
        self.assertIn("mechanical.sensitivity", v["missing"])
        full = run(good_set() + [manifest, reported, ev("mechanical.sensitivity", who="wounder", role="wounder")])
        self.assertEqual(full["decision"], "ACCEPT")

    def test_silence_in_a_manifest_is_not_a_pass_even_when_not_run_is_reported(self):
        manifest = ev("manifest.declared", who="wounder", role="wounder", details={"checks": ["mechanical.canary"]})
        v = run(good_set() + [manifest, ev("mechanical.canary", "not_run", who="wounder", role="wounder")])
        self.assertEqual(v["decision"], "HOLD")

    def test_unhealthy_gate_blocks_acceptance(self):
        self.assertEqual(run(good_set(), standing={"gate_health": "REJECT"})["decision"], "HOLD")
        self.assertEqual(run(good_set(), standing=None)["decision"], "HOLD")

    def test_gate_class_does_not_need_gate_health(self):
        gate_case = dict(CASE, **{"class": "gate"})
        e = ev("mechanical.canary", who="wounder", role="wounder")
        self.assertEqual(decide(gate_case, [e], None, standing=None)["decision"], "ACCEPT")


class Reviewers(unittest.TestCase):
    def concern(self, **ai):
        return ev("judgment.review", "fail", who="reviewer-1", role="judge-ai", claim="the statement looks weaker than the source",
                  ai=dict({"used": True, "role": "reviewer", "model": "m", "family": "family-b"}, **ai))

    def test_reviewer_concern_escalates(self):
        self.assertEqual(run(good_set() + [self.concern()])["decision"], "ESCALATE")

    def test_only_a_person_clears_it(self):
        human = ev("judgment.human_review", "pass", who="alice", role="human")
        self.assertEqual(run(good_set() + [self.concern(), human])["decision"], "ACCEPT")

    def test_a_person_can_reject(self):
        human = ev("judgment.human_review", "fail", who="alice", role="human", claim="wrong claim")
        self.assertEqual(run(good_set() + [human])["decision"], "REJECT")

    def test_same_family_reviewer_is_not_independent_at_higher_tiers(self):
        same = ev("judgment.review", "pass", who="reviewer-1", role="judge-ai",
                  ai={"used": True, "role": "reviewer", "model": "m", "family": "family-a"})
        low = run(good_set() + [same])
        self.assertEqual(low["decision"], "ACCEPT")  # tier 1: not required
        tooling_case = dict(CASE, **{"class": "tooling"})
        high = decide(tooling_case, [ev("mechanical.ci"), same], None, standing=STANDING)
        self.assertEqual(high["decision"], "ESCALATE")


class Scrutiny(unittest.TestCase):
    def test_merit_lowers_tier_by_one_only_when_all_of_it_is_falsifiable_and_present(self):
        base = run(good_set())["tier"]
        merit = merit_set()
        verified = [e["id"] for e in merit]
        full = run(good_set() + merit, verified=verified)
        self.assertEqual(full["tier"], base - 1)
        for drop in range(len(merit)):
            partial = merit[:drop] + merit[drop + 1:]
            v = run(good_set() + partial, verified=verified)
            self.assertEqual(v["tier"], base, f"dropping merit item {drop} must keep the tier")

    def test_weak_track_record_does_not_lower_tier(self):
        weak = [ev("reproducible.track_record", who="praiser", role="praiser", details={"lower_bound": 0.5})]
        v = run(good_set() + merit_set()[:3] + weak, verified=[e["id"] for e in weak])
        self.assertEqual(v["tier"], run(good_set())["tier"])

    def test_inconclusive_check_raises_tier(self):
        v = run(good_set() + [ev("mechanical.lint", "inconclusive")])
        self.assertEqual(v["tier"], run(good_set())["tier"] + 1)

    def test_bad_history_raises_tier_good_history_never_lowers_it(self):
        sig = ["mechanical.axiom_closure:pass", "mechanical.kernel_check:pass", "mechanical.no_sorry:pass"]
        bad = [{"id": f"p{i}", "class": "content", "signature": sig, "decision": "ACCEPT", "label": "reject"} for i in range(3)]
        good = [{"id": f"q{i}", "class": "content", "signature": sig, "decision": "ACCEPT", "label": "accept"} for i in range(3)]
        base = run(good_set())["tier"]
        self.assertEqual(run(good_set(), precedents=bad)["tier"], base + 1)
        self.assertEqual(run(good_set(), precedents=good)["tier"], base)

    def test_tier_is_clamped_and_audit_rate_follows_it(self):
        merit = merit_set()
        v = run(good_set() + merit, verified=[e["id"] for e in merit])
        self.assertEqual(v["audit_rate"], 0.05)
        self.assertGreaterEqual(v["tier"], 0)


class Shape(unittest.TestCase):
    def test_verdict_carries_what_is_needed_to_audit_it(self):
        v = run(good_set())
        for key in ("schema", "decision", "tier", "policy_sha256", "evidence_digest", "reasons", "ignored_evidence"):
            self.assertIn(key, v)


if __name__ == "__main__":
    unittest.main()

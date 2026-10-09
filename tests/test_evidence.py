import unittest

from juridicator.evidence import compute_id, make_evidence, validate
from tests.helpers import ev


class EvidenceTests(unittest.TestCase):
    def test_well_formed_record_validates(self):
        self.assertEqual(validate(ev("mechanical.kernel_check")), [])

    def test_tampering_breaks_the_id(self):
        e = ev("mechanical.kernel_check")
        e["claim"] = "something else"
        self.assertIn("id does not match the content", validate(e))

    def test_mechanical_needs_a_way_to_reproduce(self):
        e = ev("mechanical.kernel_check")
        body = {k: v for k, v in e.items() if k != "id"}
        body["reproduce"] = None
        body["id"] = compute_id(body)
        self.assertTrue(any("how to reproduce" in m for m in validate(body)))

    def test_kind_must_match_verifiability(self):
        e = ev("mechanical.kernel_check")
        body = {k: v for k, v in e.items() if k != "id"}
        body["verifiability"] = "judgment"
        body["id"] = compute_id(body)
        self.assertTrue(any("must equal verifiability" in m for m in validate(body)))

    def test_manifest_is_attested(self):
        self.assertEqual(validate(ev("manifest.declared", details={"checks": []})), [])

    def test_control_characters_are_refused(self):
        e = ev("mechanical.kernel_check", claim="line one\nline two")
        self.assertTrue(any("control character" in m for m in validate(e)))

    def test_ai_must_be_declared_coherently(self):
        bad = ev("judgment.review", "pass", ai={"used": True, "role": "none"})
        self.assertTrue(any("ai.used is true" in m for m in validate(bad)))
        bad2 = ev("judgment.review", "pass", ai={"used": False, "role": "reviewer"})
        self.assertTrue(any("ai.used is false" in m for m in validate(bad2)))

    def test_short_sha_is_refused(self):
        self.assertTrue(any("40-hex" in m for m in validate(ev("mechanical.ci", head="abc123"))))

    def test_oversized_details_are_refused(self):
        self.assertTrue(any("larger than" in m for m in validate(ev("attested.note", details={"x": "y" * 9000}))))

    def test_not_an_object(self):
        self.assertEqual(validate("hello"), ["not an object"])


if __name__ == "__main__":
    unittest.main()

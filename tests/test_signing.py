import json
import os
import shutil
import subprocess
import tempfile
import unittest

from juridicator import signing
from juridicator.statute import decide
from tests.helpers import CASE, STANDING, ev, good_set

HAVE = shutil.which("ssh-keygen") is not None


def keygen(d, name):
    path = os.path.join(d, name)
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", path], check=True, capture_output=True)
    with open(path + ".pub", encoding="ascii") as fh:
        return path, fh.read().strip()


@unittest.skipUnless(HAVE, "ssh-keygen not available")
class Signing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = self.tmp.name
        self.k_kernel, pub_kernel = keygen(d, "lean-kernel")
        self.k_evil, pub_evil = keygen(d, "evil")
        self.allowed = os.path.join(d, "allowed_signers")
        with open(self.allowed, "w", encoding="ascii") as fh:
            for who, pub in (("lean-kernel", pub_kernel), ("lean4lean", pub_kernel), ("evil", pub_evil)):
                fh.write(f'{who} namespaces="{signing.NAMESPACE}" {" ".join(pub.split()[:2])}\n')

    def test_round_trip_and_tampering(self):
        e = ev("mechanical.kernel_check", who="lean-kernel")
        sc = signing.sign_id(e["id"], self.k_kernel, "lean-kernel")
        self.assertTrue(signing.verify_sidecar(sc, self.allowed))
        self.assertFalse(signing.verify_sidecar(dict(sc, id=ev("mechanical.kernel_check", "fail", who="lean-kernel")["id"]), self.allowed))
        self.assertFalse(signing.verify_sidecar(dict(sc, principal="evil"), self.allowed))
        self.assertFalse(signing.verify_sidecar(dict(sc, signature=sc["signature"][:-30]), self.allowed))
        self.assertFalse(signing.verify_sidecar({"id": "x"}, self.allowed))

    def test_a_key_listed_for_another_principal_does_not_vouch(self):
        e = ev("mechanical.kernel_check", who="lean-kernel")
        forged = signing.sign_id(e["id"], self.k_evil, "lean-kernel")  # the evil key claims to be lean-kernel
        self.assertFalse(signing.verify_sidecar(forged, self.allowed))

    def test_authenticate_requires_signer_to_equal_producer_identity(self):
        e = ev("mechanical.kernel_check", who="lean4lean")
        by_wrong = signing.sign_id(e["id"], self.k_kernel, "lean-kernel")  # valid signature, but not by this record's producer
        self.assertEqual(signing.authenticate([e], [by_wrong], self.allowed), set())
        ok = signing.sign_id(e["id"], self.k_kernel, "lean4lean")
        self.assertEqual(signing.authenticate([e], [ok], self.allowed), {e["id"]})

    def test_statute_ignores_unsigned_records_when_signatures_are_required(self):
        evidence = good_set()
        pol = {"require_signatures": True}
        self.assertEqual(decide(CASE, evidence, pol, standing=STANDING)["decision"], "HOLD")
        signed = {e["id"] for e in evidence}
        v = decide(CASE, evidence, pol, standing=STANDING, authenticated=signed)
        self.assertEqual(v["decision"], "ACCEPT")
        partial = decide(CASE, evidence, pol, standing=STANDING, authenticated=signed - {evidence[0]["id"]})
        self.assertEqual(partial["decision"], "HOLD")
        self.assertTrue(any("not signed" in i["why"] for i in partial["ignored_evidence"]))

    def test_attested_records_need_no_signature_and_default_policy_does_not_require_any(self):
        self.assertEqual(decide(CASE, good_set(), None, standing=STANDING)["decision"], "ACCEPT")
        note = ev("attested.note", who="author")
        v = decide(CASE, good_set() + [note], {"require_signatures": True}, standing=STANDING, authenticated={e["id"] for e in good_set()})
        self.assertNotIn(note["id"], [i["id"] for i in v["ignored_evidence"]])
        self.assertEqual(v["decision"], "ACCEPT")

    def test_bad_principal_and_id_are_refused_before_ssh_keygen_runs(self):
        for bad in ("-oProxy", "a b", "", "x" * 200):
            with self.assertRaises(signing.SigningError):
                signing.sign_id("sha256:" + "0" * 64, self.k_kernel, bad)
        with self.assertRaises(signing.SigningError):
            signing.sign_id("sha256:zz", self.k_kernel, "ok")

    def test_cli_sign_then_judge_requires_matching_signatures(self):
        from juridicator.cli import main
        import contextlib, io
        d = self.tmp.name
        evdir = os.path.join(d, "ev")
        os.makedirs(evdir)
        recs = [e for e in good_set() if e["producer"]["identity"] in ("lean-kernel", "lean4lean")]
        rest = [e for e in good_set() if e not in recs]
        with open(os.path.join(evdir, "all.json"), "w", encoding="utf-8") as fh:
            json.dump(good_set(), fh)
        case = os.path.join(d, "case.json")
        with open(case, "w", encoding="utf-8") as fh:
            json.dump(CASE, fh)
        standing = os.path.join(d, "standing.json")
        with open(standing, "w", encoding="utf-8") as fh:
            json.dump(STANDING, fh)
        pol = os.path.join(d, "pol.json")
        with open(pol, "w", encoding="utf-8") as fh:
            json.dump({"require_signatures": True}, fh)
        sigs = os.path.join(d, "sigs.jsonl")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["sign", "--evidence", evdir, "--key", self.k_kernel, "--principal", "lean-kernel", "--out", sigs]), 0)
            code = main(["judge", "--case", case, "--evidence", evdir, "--policy", pol, "--standing", standing,
                         "--signatures", sigs, "--allowed-signers", self.allowed])
        self.assertEqual(code, 10)  # only lean-kernel's record is signed: the rest is ignored, so the case is held
        self.assertTrue(recs and rest)


if __name__ == "__main__":
    unittest.main()

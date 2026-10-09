"""Who really wrote this record? Detached SSH signatures over an evidence id, checked with `ssh-keygen -Y`.

Until now a producer's identity was only a string anyone could type. A signature binds the record (through its content
hash, the `id`) to a key listed in an `allowed_signers` file that the maintainers control. Nothing new to install:
OpenSSH ships `ssh-keygen -Y sign|verify|check-novalidate`, and GitHub, Git and the runners already speak it.

    allowed_signers line:   <principal> namespaces="tengoku-evidence/1" ssh-ed25519 AAAA...
    sidecar signature:      {"id": "<evidence id>", "principal": "<producer.identity>", "signature": "-----BEGIN SSH SIGNATURE-----..."}

A record is *authenticated* when a sidecar signature for its id verifies under the key of the principal that equals the
record's `producer.identity`. The statute never runs this itself (it stays pure); the caller authenticates first and passes
the set of ids, and with `require_signatures` in the policy anything mechanical, reproducible or judgment that is not in
that set is ignored (fail closed). Attested records need no signature: they weigh nothing anyway.

Honest limits: a stolen key signs anything; revocation is whatever you do to the allowed_signers file; this proves who,
not that the producer's tool was honest. Standard library only; no shell; a timeout on every call.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Iterable

NAMESPACE = "tengoku-evidence/1"
PRINCIPAL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]{0,99}$")
ID = re.compile(r"^sha256:[0-9a-f]{64}$")
SIGNATURE_MAX = 4096
TIMEOUT = 20


class SigningError(RuntimeError):
    pass


def _run(args: list[str], *, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["ssh-keygen", *args], input=stdin, capture_output=True, timeout=TIMEOUT, check=False,
                              env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SigningError(f"ssh-keygen could not run: {type(exc).__name__}") from exc


def sign_id(evidence_id: str, key_path: str, principal: str) -> dict:
    """A sidecar signature for one evidence id, made with the private key at `key_path` (an unencrypted or agent key)."""
    if not ID.match(evidence_id) or not PRINCIPAL.match(principal):
        raise SigningError("bad evidence id or principal")
    with tempfile.TemporaryDirectory() as d:
        data = os.path.join(d, "data")
        with open(data, "w", encoding="ascii") as fh:
            fh.write(evidence_id)
        done = _run(["-Y", "sign", "-f", key_path, "-n", NAMESPACE, data])
        if done.returncode != 0:
            raise SigningError("signing failed: " + done.stderr.decode("utf-8", "replace")[:200])
        with open(data + ".sig", encoding="ascii") as fh:
            sig = fh.read()
    return {"id": evidence_id, "principal": principal, "signature": sig}


def verify_sidecar(sidecar: dict, allowed_signers: str) -> bool:
    if not isinstance(sidecar, dict):
        return False
    eid, principal, sig = sidecar.get("id"), sidecar.get("principal"), sidecar.get("signature")
    if not (isinstance(eid, str) and ID.match(eid) and isinstance(principal, str) and PRINCIPAL.match(principal)
            and isinstance(sig, str) and 0 < len(sig) <= SIGNATURE_MAX and sig.isascii()):
        return False
    with tempfile.TemporaryDirectory() as d:
        sigfile = os.path.join(d, "sig")
        with open(sigfile, "w", encoding="ascii") as fh:
            fh.write(sig)
        try:
            done = _run(["-Y", "verify", "-f", allowed_signers, "-I", principal, "-n", NAMESPACE, "-s", sigfile], stdin=eid.encode("ascii"))
        except SigningError:
            return False
    return done.returncode == 0


def authenticate(evidence: Iterable[dict], sidecars: Iterable[dict], allowed_signers: str) -> set[str]:
    """Ids of records whose producer identity signed them. A signature by anyone else, or for another id, counts for nothing."""
    by_id = {}
    for ev in evidence:
        if isinstance(ev, dict) and isinstance(ev.get("id"), str) and isinstance(ev.get("producer"), dict):
            by_id[ev["id"]] = ev["producer"].get("identity")
    ok: set[str] = set()
    for sc in sidecars:
        if not isinstance(sc, dict):
            continue
        eid = sc.get("id")
        if eid in by_id and sc.get("principal") == by_id[eid] and verify_sidecar(sc, allowed_signers):
            ok.add(eid)
    return ok

from juridicator.evidence import make_evidence

HEAD = "a" * 40
CASE = {"repo": "competemath/tengoku-sandbox", "head_sha": HEAD, "class": "content",
        "author": {"identity": "agent-7", "family": "family-a"}}
NOW = "2026-10-09T00:00:00Z"


def ev(kind, outcome="pass", *, who="ci", role="tooling", verifiability=None, subject=None, claim=None,
       ai=None, details=None, head=HEAD, command="make check"):
    v = verifiability or kind.split(".")[0]
    if v == "manifest":
        v = "attested"
    reproduce = {"command": command} if v in ("mechanical", "reproducible") else None
    return make_evidence(
        case={"repo": CASE["repo"], "head_sha": head, "class": "content"},
        producer={"role": role, "name": who, "identity": who},
        kind=kind, claim=claim or f"{kind} {outcome}", outcome=outcome, verifiability=v,
        created=NOW, subject=subject, reproduce=reproduce, ai=ai, details=details)


def good_set():
    """The evidence a healthy content case needs: two independent kernel checks, axioms, no sorry."""
    return [
        ev("mechanical.kernel_check", who="lean-kernel"),
        ev("mechanical.kernel_check", who="lean4lean"),
        ev("mechanical.axiom_closure", who="axiom-gate"),
        ev("mechanical.no_sorry", who="sorry-gate"),
    ]


def merit_set():
    return [
        ev("mechanical.kernel_check", who="nanoda"),
        ev("mechanical.provenance_consistent", who="praiser", role="praiser"),
        ev("reproducible.rebuild_match", who="rebuilder", role="praiser"),
        ev("reproducible.track_record", who="praiser", role="praiser", details={"lower_bound": 0.93}),
    ]


STANDING = {"gate_health": "ACCEPT"}

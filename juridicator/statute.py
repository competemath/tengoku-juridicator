"""The statute: a deterministic decision from a case, its evidence, a policy, past precedents and standing conditions.

No clock, no randomness, no network, no AI. The same inputs give the same verdict, whatever order the evidence
arrives in (tests/test_statute.py checks this). The rules, in the order they matter:

  R0  Only well formed evidence about this exact commit counts; the author cannot vouch for their own work
      (an author may only attest, and attestations are shown, not weighed).
  R7  Checkers that disagree on the same fact are not a verdict: the case goes to a person (the disagreement may be
      a bug in a checker, which is exactly what we most want to know about).
  R1  A failed mechanical check on a blocking kind rejects the case, however much praise exists.
  R1b A failed reproducible check holds the case for a re-run; failed by two independent producers it rejects.
  R9  A producer who declared a manifest of checks must report every one of them. Silence is not a pass.
  R3  Every kind the class requires needs a mechanical pass, from as many independent producers as the class says.
  R11 The gate's own health (planted-defect canaries) must be proven, or nothing is accepted.
  R5  A reviewer's concern escalates; only a person clears it. R10: a reviewer from the author's own model family
      does not count as independent at higher tiers.
  Tier   Scrutiny is set by the class, raised by history and doubt, lowered by one step at most, and only by
      falsifiable merit (see policy.merit_reduction). Attested praise has weight zero.
"""

from __future__ import annotations

import fnmatch
from typing import Any, Iterable

from . import precedent as prec
from .evidence import canonical_json, sha256_text, validate
from .policy import digest, normalize

RULES_VERSION = "1"
VERDICT_SCHEMA = "tengoku-verdict/1"
DECISIONS = ("ACCEPT", "HOLD", "ESCALATE", "REJECT")


def _is_author(ev: dict, case: dict) -> bool:
    author = (case.get("author") or {}).get("identity")
    return bool(author) and ev["producer"]["identity"] == author


def _key(ev: dict) -> tuple[str, str]:
    return ev["kind"], canonical_json(ev.get("subject"))


def _ids(evs: Iterable[dict]) -> list[str]:
    return sorted({ev["id"] for ev in evs})


def _screen(case: dict, evidence: Iterable[Any]) -> tuple[list[dict], list[dict]]:
    live, ignored, seen = [], [], set()
    for ev in evidence:
        errors = validate(ev)
        if errors:
            ignored.append({"id": ev.get("id") if isinstance(ev, dict) else None, "why": "invalid: " + "; ".join(errors[:3])})
        elif ev["id"] in seen:
            ignored.append({"id": ev["id"], "why": "duplicate"})
        elif ev["case"]["repo"] != case["repo"] or ev["case"]["head_sha"] != case["head_sha"]:
            ignored.append({"id": ev["id"], "why": "about another commit (stale or misfiled)"})
        elif _is_author(ev, case) and ev["verifiability"] != "attested":
            ignored.append({"id": ev["id"], "why": "the author cannot vouch for their own work"})
        else:
            seen.add(ev["id"])
            live.append(ev)
    live.sort(key=lambda e: e["id"])
    ignored.sort(key=lambda d: (str(d["id"]), d["why"]))
    return live, ignored


def _merit_ok(live: list[dict], pol: dict) -> tuple[bool, list[str]]:
    m = pol["merit_reduction"]
    unmet = []
    checkers = {e["producer"]["identity"] for e in live
                if e["kind"] == m["checker_kind"] and e["outcome"] == "pass" and e["verifiability"] == "mechanical"}
    if len(checkers) < m["min_independent_checkers"]:
        unmet.append(f"{len(checkers)} of {m['min_independent_checkers']} independent checkers")
    if m.get("needs_provenance_consistent") and not any(
            e["kind"] == "mechanical.provenance_consistent" and e["outcome"] == "pass" for e in live):
        unmet.append("provenance not shown consistent")
    if m.get("needs_rebuild_match") and not any(
            e["kind"] == "reproducible.rebuild_match" and e["outcome"] == "pass" for e in live):
        unmet.append("no matching independent rebuild")
    floor = m.get("min_track_lower_bound")
    if floor is not None:
        bounds = [e["details"].get("lower_bound") for e in live
                  if e["kind"] == "reproducible.track_record" and e["outcome"] == "pass"]
        if not any(isinstance(b, (int, float)) and b >= floor for b in bounds):
            unmet.append("track record below the floor or absent")
    return not unmet, unmet


def decide(
    case: dict,
    evidence: Iterable[Any],
    policy: dict | None = None,
    *,
    precedents: Iterable[dict] = (),
    standing: dict | None = None,
) -> dict:
    pol = normalize(policy)
    cls = pol["classes"].get(case["class"], pol["default_class"])
    live, ignored = _screen(case, evidence)

    reasons: list[dict] = []
    missing: list[str] = []

    def why(rule: str, text: str, evs: Iterable[dict] = ()) -> None:
        reasons.append({"rule": rule, "text": text, "evidence": _ids(evs)})

    # R7: the same fact, checked by someone, passing and failing.
    by_key: dict[tuple[str, str], list[dict]] = {}
    for ev in live:
        if ev["verifiability"] == "mechanical" and ev["outcome"] in ("pass", "fail"):
            by_key.setdefault(_key(ev), []).append(ev)
    conflicts = {k: v for k, v in by_key.items() if {e["outcome"] for e in v} == {"pass", "fail"}}
    for (kind, _), evs in sorted(conflicts.items()):
        who = sorted({e["producer"]["identity"] for e in evs})
        why("R7", f"checkers disagree on {kind} ({', '.join(who)}): a person must look, the checker may be what is wrong", evs)

    # R1: failed mechanical checks on blocking kinds (a human reviewer's rejection counts the same).
    rejects = []
    for key, evs in sorted(by_key.items()):
        if key in conflicts:
            continue
        for ev in evs:
            if ev["outcome"] == "fail" and any(fnmatch.fnmatch(ev["kind"], g) for g in pol["blocking"]):
                rejects.append(ev)
    for ev in rejects:
        why("R1", f"{ev['kind']} failed: {ev['claim']}", [ev])
    for ev in live:
        if ev["producer"]["role"] == "human" and ev["kind"] == "judgment.human_review" and ev["outcome"] == "fail":
            rejects.append(ev)
            why("R1", f"a person rejected this: {ev['claim']}", [ev])

    # R1b: failed reproducible checks.
    holds: list[tuple[str, str]] = []
    repro: dict[tuple[str, str], list[dict]] = {}
    for ev in live:
        if ev["verifiability"] == "reproducible" and ev["outcome"] == "fail":
            repro.setdefault(_key(ev), []).append(ev)
    for (kind, _), evs in sorted(repro.items()):
        producers = {e["producer"]["identity"] for e in evs}
        if len(producers) >= 2:
            rejects.extend(evs)
            why("R1b", f"{kind} failed for {len(producers)} independent producers", evs)
        else:
            holds.append(("R1b", f"{kind} failed once: re-run it before anything else"))
            why("R1b", f"{kind} failed once: re-run it before anything else", evs)

    # R9: a declared manifest must be reported in full.
    for ev in live:
        if not ev["kind"].startswith("manifest.") or _is_author(ev, case):
            continue
        declared = ev["details"].get("checks")
        if not isinstance(declared, list):
            continue
        for kind in sorted({d for d in declared if isinstance(d, str)}):
            done = any(e["kind"] == kind and e["producer"]["identity"] == ev["producer"]["identity"]
                       and e["outcome"] in ("pass", "fail", "inconclusive") for e in live)
            if not done:
                holds.append(("R9", f"{ev['producer']['identity']} declared {kind} and did not report it"))
                why("R9", f"{ev['producer']['identity']} declared {kind} and did not report it", [ev])
                missing.append(kind)

    # R3: what the class requires.
    need = dict.fromkeys(cls["required"], 1)
    for kind, n in cls["independent"].items():
        need[kind] = max(need.get(kind, 1), n)
    for kind, n in sorted(need.items()):
        passes = [e for e in live if e["kind"] == kind and e["verifiability"] == "mechanical" and e["outcome"] == "pass"]
        producers = {e["producer"]["identity"] for e in passes}
        if len(producers) < n:
            text = f"{kind} needs {n} independent producer{'s' if n > 1 else ''}, has {len(producers)}"
            holds.append(("R3", text))
            why("R3", text, passes)
            missing.append(kind)

    # R11: the gate itself must be shown healthy.
    if pol["require_gate_health"] and case["class"] != "gate" and (standing or {}).get("gate_health") != "ACCEPT":
        holds.append(("R11", "the gate's health (planted-defect canaries) is not proven"))
        why("R11", "the gate's health (planted-defect canaries) is not proven")

    # Precedents and tier.
    near = prec.nearest(prec.signature(live), case["class"], precedents, pol["history"]["k"])
    tier = cls["base_tier"]
    if pol["history"].get("raise_if_reject_majority") and prec.history_signal(near, pol["history"]["min_labeled"]):
        tier += 1
        why("T1", "similar past cases were mostly rejected afterwards: scrutiny raised one step")
    if any(e["outcome"] == "inconclusive" and e["verifiability"] in ("mechanical", "reproducible") for e in live):
        tier += 1
        why("T2", "a check was inconclusive: scrutiny raised one step")
    ok, unmet = _merit_ok(live, pol)
    if ok and tier > 0:
        tier -= 1
        why("T3", "independent checkers, matching rebuild, consistent provenance and a sound track record: scrutiny lowered one step")
    tier = max(0, min(3, tier))

    # R5 / R10: reviewers' concerns need a person.
    cleared = any(e["producer"]["role"] == "human" and e["kind"] == "judgment.human_review" and e["outcome"] == "pass" for e in live)
    escalations: list[tuple[str, str]] = []
    for ev in live:
        if ev["verifiability"] == "judgment" and ev["outcome"] == "fail" and ev["producer"]["role"] != "human":
            escalations.append(("R5", f"a reviewer raised a concern: {ev['claim']}"))
            why("R5", f"a reviewer raised a concern: {ev['claim']}", [ev])
    family = (case.get("author") or {}).get("family")
    if family and tier >= pol["independence_min_tier"]:
        for ev in live:
            if ev["ai"].get("used") and ev["ai"].get("role") == "reviewer" and ev["ai"].get("family") == family:
                escalations.append(("R10", "a reviewer from the author's own model family is not independent at this tier"))
                why("R10", "a reviewer from the author's own model family is not independent at this tier", [ev])
    if cleared and escalations:
        why("R5", "a person cleared the reviewers' concerns")
        escalations = []

    if conflicts:
        decision = "ESCALATE"
    elif rejects:
        decision = "REJECT"
    elif holds:
        decision = "HOLD"
    elif escalations:
        decision = "ESCALATE"
    else:
        decision = "ACCEPT"

    reasons.sort(key=lambda r: (r["rule"], r["text"]))
    return {
        "schema": VERDICT_SCHEMA,
        "rules_version": RULES_VERSION,
        "case": {"repo": case["repo"], "head_sha": case["head_sha"], "class": case["class"]},
        "decision": decision,
        "tier": tier,
        "audit_rate": pol["tier_audit_rate"][tier],
        "reasons": reasons,
        "missing": sorted(set(missing)),
        "merit_unmet": unmet,
        "ignored_evidence": ignored,
        "precedents": [{"id": p.get("id"), "similarity": p["similarity"], "decision": p.get("decision"), "label": p.get("label")} for p in near],
        "policy_sha256": digest(pol),
        "evidence_digest": "sha256:" + sha256_text(canonical_json(_ids(live))),
        "ai": {"level": pol["ai_level"], "advice": None},
    }

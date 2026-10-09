"""Comparison with similar past cases, by a deterministic measure (no AI needed to retrieve a precedent).

A precedent is a record of a past case: its class, its evidence signature (which kinds came out how), the decision
taken, and, when a person later reviewed it, the label. Only labeled precedents can push a case up in scrutiny.
"""

from __future__ import annotations

from typing import Iterable


def signature(evidence: Iterable[dict]) -> list[str]:
    return sorted({f"{ev['kind']}:{ev['outcome']}" for ev in evidence})


def similarity(sig_a: Iterable[str], class_a: str, sig_b: Iterable[str], class_b: str) -> float:
    a, b = set(sig_a), set(sig_b)
    union = a | b
    jaccard = (len(a & b) / len(union)) if union else 1.0
    return round(0.9 * jaccard + (0.1 if class_a == class_b else 0.0), 6)


def nearest(sig: Iterable[str], cls: str, store: Iterable[dict], k: int = 3) -> list[dict]:
    """The k most similar precedents, ties broken by id so the answer never depends on input order."""
    scored = []
    for rec in store:
        score = similarity(sig, cls, rec.get("signature", []), rec.get("class", ""))
        scored.append((-score, str(rec.get("id", "")), score, rec))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [dict(rec, similarity=score) for _, _, score, rec in scored[:k]]


def history_signal(near: list[dict], min_labeled: int = 2) -> int:
    """+1 when the labeled neighbours were mostly rejected afterwards: history says look harder. Never negative:
    a run of good precedents is not a reason to look less hard (that is the praiser's job, with falsifiable evidence)."""
    labeled = [r for r in near if r.get("label") in ("accept", "reject")]
    if len(labeled) < min_labeled:
        return 0
    rejects = sum(1 for r in labeled if r["label"] == "reject")
    return 1 if rejects * 2 > len(labeled) else 0

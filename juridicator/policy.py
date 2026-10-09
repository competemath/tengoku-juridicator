"""The policy: which evidence a class of case needs, how scrutiny is set, how far AI may go.

Everything the statute reads from here is data, so a change to the rules is a visible, reviewable diff to a JSON
file (policy/default.json), never a change in code paths. The policy is hashed into every verdict.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from .evidence import canonical_json, sha256_text

DEFAULT_CLASS = {
    "base_tier": 2,
    "required": [],
    "independent": {},
}

DEFAULT_POLICY: dict[str, Any] = {
    "version": 1,
    # Scrutiny tier: 0 spot-check, 1 routine, 2 elevated, 3 every case audited by a person.
    "tier_audit_rate": [0.05, 0.20, 0.50, 1.00],
    "classes": {
        "content": {
            "base_tier": 1,
            "required": ["mechanical.kernel_check", "mechanical.axiom_closure", "mechanical.no_sorry"],
            "independent": {"mechanical.kernel_check": 2},
        },
        "native": {
            "base_tier": 1,
            "required": ["mechanical.kernel_check", "mechanical.axiom_closure", "mechanical.no_sorry"],
            "independent": {"mechanical.kernel_check": 2},
        },
        "tooling": {"base_tier": 2, "required": ["mechanical.ci"], "independent": {}},
        "gate": {"base_tier": 2, "required": ["mechanical.canary"], "independent": {}},
    },
    "default_class": DEFAULT_CLASS,
    # A failed mechanical check on a kind matching one of these globs rejects the case, whoever produced it.
    "blocking": ["mechanical.*"],
    # Tier reduction (at most one step, never below 0) needs every one of these, all of them falsifiable.
    "merit_reduction": {
        "min_independent_checkers": 3,
        "checker_kind": "mechanical.kernel_check",
        "needs_provenance_consistent": True,
        "needs_rebuild_match": True,
        "min_track_lower_bound": 0.90,
    },
    "history": {"k": 3, "min_labeled": 2, "raise_if_reject_majority": True},
    "require_gate_health": True,
    "independence_min_tier": 2,
    # AI in the judge: 0 ignored, 1 explanation only, 2 may make a case more cautious (never less). 3 is locked
    # behind measured calibration (calibration.py) and is not available in this version.
    "ai_level": 0,
    "ai_required": False,
}


class PolicyError(ValueError):
    pass


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict) and key != "classes":
            out[key] = _merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def normalize(policy: dict | None) -> dict:
    """Defaults filled in, and every value checked, so the statute never meets a malformed policy halfway through."""
    pol = _merge(DEFAULT_POLICY, policy or {})
    rates = pol["tier_audit_rate"]
    if not (isinstance(rates, list) and len(rates) == 4 and all(isinstance(r, (int, float)) and 0 < r <= 1 for r in rates)):
        raise PolicyError("tier_audit_rate must be four numbers in (0, 1]")
    if rates != sorted(rates):
        raise PolicyError("tier_audit_rate must not decrease with the tier")
    if pol["ai_level"] not in (0, 1, 2):
        raise PolicyError("ai_level must be 0, 1 or 2 (3 is locked behind calibration)")
    for name, cls in list(pol["classes"].items()) + [("default_class", pol["default_class"])]:
        if not isinstance(cls, dict) or cls.get("base_tier") not in (0, 1, 2, 3):
            raise PolicyError(f"class {name}: base_tier must be 0..3")
        cls.setdefault("required", [])
        cls.setdefault("independent", {})
        for kind, n in cls["independent"].items():
            if not isinstance(n, int) or n < 1:
                raise PolicyError(f"class {name}: independent[{kind}] must be a positive integer")
    return pol


def load(path: str | None) -> dict:
    if not path:
        return normalize(None)
    with open(path, encoding="utf-8") as fh:
        return normalize(json.load(fh))


def digest(policy: dict) -> str:
    return "sha256:" + sha256_text(canonical_json(policy))

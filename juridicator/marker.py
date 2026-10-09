"""The one-time verdict marker, in the form the warden defines (vendor/warden/verdict.py).

Before an AI reader sees untrusted text, the runner makes a fresh random marker and tells the reader to print it, then its
answer, last. Only what follows the LAST occurrence of the marker is parsed, it must be exactly one JSON object, and every field
of it is checked against a closed schema (a malformed `findings` list is an error, never a crash). Anything an attacker planted
earlier, including a forged marker or a ready-made "approved" object, is discarded. Parsing fails closed: a missing marker,
malformed JSON or a verdict outside `none/hold/escalate` means "no answer", never a default.

The idea is Tau Ceti's review runner (`runner/verdict.py`); the implementation is tengoku-warden's, vendored byte for byte and
pinned (`vendor/warden/PIN`, tests/test_warden_vendor.py). This module only fixes the three verdicts the judge accepts.
"""

from __future__ import annotations

import re

from vendor.warden import verdict as wv

ALLOWED_ACTIONS = ("none", "hold", "escalate")
MAX_FINDINGS = 20
MARKER_RE = re.compile(r"TENGOKU-VERDICT-[0-9a-f]{24}")
INJECTION_CATEGORY = wv.INJECTION_CATEGORY
Parsed = wv.Parsed
ParseError = wv.ParseError

new_marker = wv.new_marker


def instructions(marker: str, allowed: tuple = ALLOWED_ACTIONS) -> str:
    """The trusted text that goes LAST in the prompt: the marker and the exact shape of the answer."""
    return wv.instructions(marker, allowed)


def parse(text: str, marker: str, allowed=ALLOWED_ACTIONS) -> "wv.Parsed | wv.ParseError":
    """The warden's parse: `Parsed` or a `ParseError` whose kind says why. Never raises on bad reply text."""
    if not isinstance(marker, str) or not MARKER_RE.fullmatch(marker):
        return wv.ParseError("no_marker", "no usable marker")
    return wv.parse(text, marker, allowed_verdicts=tuple(allowed), max_findings=MAX_FINDINGS)


def extract(text: str, marker: str, allowed_actions=ALLOWED_ACTIONS) -> dict | None:
    """Compatibility view of `parse`: the answer as a plain dict, or None when there is no valid answer."""
    parsed = parse(text, marker, tuple(sorted(allowed_actions)))
    if not isinstance(parsed, wv.Parsed):
        return None
    return {
        "action": parsed.verdict,
        "explanation": parsed.summary,
        "reasons": [f.title for f in parsed.findings],
        "injection_attempt": parsed.flagged_injection,
    }

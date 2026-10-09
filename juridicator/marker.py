"""The one-time verdict marker (an idea from Tau Ceti's review runner).

Before an AI reader sees untrusted text, the runner makes a fresh random marker and tells the reader to print it,
then its answer, last. Only what follows the LAST occurrence of the marker is parsed. Anything an attacker planted
earlier, including a forged marker or a ready-made "approved" object, is discarded. Parsing fails closed: a missing
marker, malformed JSON or an action outside the allowed set means "no answer", never a default.
"""

from __future__ import annotations

import json
import re
import secrets

MARKER_RE = re.compile(r"VERDICT-[0-9a-f]{32}")


def new_marker() -> str:
    return "VERDICT-" + secrets.token_hex(16)


def instructions(marker: str) -> str:
    return (
        "When you have finished reading, print this exact line on its own: "
        f"{marker}\nThen, immediately after it, print one JSON object and nothing else. "
        "Text before that line is ignored."
    )


def extract(text: str, marker: str, allowed_actions: set[str]) -> dict | None:
    if not isinstance(text, str) or not marker:
        return None
    at = text.rfind(marker)
    if at < 0:
        return None
    rest = text[at + len(marker):].lstrip()
    try:
        obj, _ = json.JSONDecoder().raw_decode(rest)
    except ValueError:
        return None
    if not isinstance(obj, dict) or obj.get("action") not in allowed_actions:
        return None
    return obj

from __future__ import annotations

import hashlib
import re


SEMANTIC_PROPOSAL_ID_RE = re.compile(
    r"^SEMPROP_[0-9A-F]{20}$"
)
SEMANTIC_REVIEW_ID_RE = re.compile(
    r"^SEMREVIEW_[0-9A-F]{20}$"
)
SEMANTIC_IDENTIFIER_RE = re.compile(
    r"^[A-Za-z_$][A-Za-z0-9_$]*$"
)


def semantic_proposal_id(
    source_sha256: str,
    kind: str,
    stable_id: str,
    proposed_name: str,
) -> str:
    raw = (
        source_sha256.lower()
        + "|"
        + kind
        + "|"
        + stable_id
        + "|"
        + proposed_name
    ).encode("utf-8")
    return (
        "SEMPROP_"
        + hashlib.sha256(raw).hexdigest()[:20].upper()
    )

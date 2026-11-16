#!/usr/bin/env python3
"""R430 owner-opt-in SOURCE-ONLY audit of existing R415-R417 admission fence.

Reads only exact pinned isolated R421 LootHistoryStore.java source. Never
opens real history, exports source/classes, builds a JAR, changes data, or
authorizes a write/cleanup. If the private SHA or guard structure changes,
REFUSE instead of guessing. Desktop Commander is quota paused, so this audit
has NOT been executed against the owner's actual private source.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.r417.audit_private_ack_fence import verify_ack_guard, Refused as R417Refused

PRIVATE_SOURCE_SHA256 = (
    "0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29"
)


class Refused(RuntimeError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def audit_source(path: Path, expected_sha: str = PRIVATE_SOURCE_SHA256) -> dict:
    require(re.fullmatch("[0-9a-f]{64}", expected_sha) is not None,
            "R430_INVALID_SHA_FORMAT")
    require(path.name == "LootHistoryStore.java" and
            path.is_file() and not path.is_symlink(),
            "R430_WRONG_OR_SYMLINK_SOURCE")
    data = path.read_bytes()
    require(sha256(data).hexdigest() == expected_sha,
            "R430_PRIVATE_SOURCE_SHA_PIN_MISMATCH")
    source = data.decode("utf-8")
    # Reuse previously verified R417 read-only source structural checker.
    try:
        previous = verify_ack_guard(source)
    except R417Refused:
        raise Refused("R430_EXISTING_R417_ACK_GUARD_NOT_VERIFIED")

    # Additional narrow source-existence checks. The previous auditor
    # verifies exact ack names, NOFOLLOW, and guard ordering relative to
    # the R414 intent state; we do NOT claim these checks prove runtime.
    for symbol in (
        "r411StageState", "r417UnresolvedAckEvidence",
        "r414IntentState", "r411RefuseUnresolvedStage",
        "r419ActivateOwner", "r419CloseOwner", "r419WithOwner",
        "loadForMerge", "saveWithReceipt", "clearWithReceipt",
    ):
        require(symbol in source, "R430_MISSING_PRIVATE_ADMISSION_SYMBOL")

    return {
        "status": "R430_OWNER_PRIVATE_SOURCE_READONLY_ADMISSION_AUDIT_PASS",
        "source_sha256": expected_sha,
        "existing_r417_ack_guard": previous,
        "writes_authorized": False,
        "delete_authorized": False,
        "marker_cleanup_authorized": False,
        "source_modified": False,
        "private_client_executed": False,
        "runtime_integration_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated-private-store-java", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(audit_source(args.isolated_private_store_java),
                         sort_keys=True))
        return 0
    except (Refused, OSError, UnicodeError, ValueError) as error:
        print(json.dumps({
            "status": "R430_PRIVATE_ADMISSION_AUDIT_REFUSED",
            "reason": str(error) if isinstance(error, Refused) else
                      "R430_BAD_SOURCE_OR_ENCODING",
            "writes_authorized": False,
            "delete_authorized": False,
            "marker_cleanup_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

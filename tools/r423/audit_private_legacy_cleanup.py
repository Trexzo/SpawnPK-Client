#!/usr/bin/env python3
"""R423 read-only SHA-pinned audit of the *old* private legacy cleanup shape.

It recognizes the risky File.listFiles() + recursive deleteTree() implementation
in an exact owner-supplied LootHistoryStore.java. It does NOT patch, execute,
export or approve any recovered private code; no player history is accessed.
A source mismatch always requires a new review, never marks the code safe.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re


class Refused(RuntimeError):
    pass


def require(value: bool, reason: str) -> None:
    if not value:
        raise Refused(reason)


def method(source: str, name: str) -> str:
    hit = re.search(r"\b" + re.escape(name) +
                    r"\s*\([^;{}]*\)\s*(?:throws\s+\w+\s*)?\{", source)
    require(hit is not None, "R423_METHOD_MISSING_" + name)
    start = source.index("{", hit.start())
    balance = 0
    for end in range(start, len(source)):
        if source[end] == "{":
            balance += 1
        elif source[end] == "}":
            balance -= 1
            if balance == 0:
                return source[start + 1:end]
    raise Refused("R423_UNBALANCED_" + name)


def inspect_source(source: str) -> dict:
    # Only executable-looking text in old implementation counts as evidence.
    without_comments = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", " ", source)
    delete = method(without_comments, "deleteTree")
    caller = method(without_comments, "r419DeleteStaleLeased")

    require("file.listFiles()" in delete,
            "R423_RISK_SHAPE_CHANGED_LISTFILES_NOT_FOUND")
    require("deleteTree(child)" in delete,
            "R423_RISK_SHAPE_CHANGED_RECURSION_NOT_FOUND")
    require("Files.deleteIfExists(file.toPath())" in delete,
            "R423_RISK_SHAPE_CHANGED_FILE_DELETION_NOT_FOUND")
    require("deleteTree(parts)" in caller,
            "R423_RISK_SHAPE_CHANGED_CALLER_NOT_FOUND")
    require("r411RefuseUnresolvedStage(" in caller,
            "R423_PREVIOUS_STAGE_GATE_MISSING")
    require("r419WithOwner(this::r419DeleteStaleLeased)" in without_comments,
            "R423_PREVIOUS_LEASE_GATE_MISSING")
    require("LinkOption.NOFOLLOW_LINKS" not in delete and
            "Files.walkFileTree(" not in delete,
            "R423_OLD_METHOD_CHANGED_REQUIRES_NEW_AUDIT")
    return {
        "status": "R423_PRIVATE_RECURSIVE_SYMLINK_RISK_REVIEW_REQUIRED",
        "recursive_file_listfiles": True,
        "unbounded_original_delete_tree": True,
        "missing_nofollow_guard_in_delete_tree": True,
        "existing_stage_fence_present": True,
        "existing_cooperative_owner_wrapper_present": True,
        "release_authorized": False,
        "private_runtime_tested": False,
        "private_source_modified": False,
    }


def audit(source_path: Path, expected_sha256: str) -> dict:
    require(re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None,
            "R423_INVALID_SHA_PIN")
    require(source_path.name == "LootHistoryStore.java", "R423_UNEXPECTED_FILE_NAME")
    require(source_path.is_file() and not source_path.is_symlink(),
            "R423_SOURCE_UNREADABLE_OR_SYMLINK")
    payload = source_path.read_bytes()
    require(sha256(payload).hexdigest() == expected_sha256,
            "R423_SOURCE_SHA_PIN_MISMATCH")
    try:
        source = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("R423_SOURCE_INVALID_UTF8")
    result = inspect_source(source)
    result["source_sha256_verified"] = expected_sha256
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    try:
        result = audit(args.source, args.expected_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else "R423_INVALID_OR_UNREADABLE_INPUT"
        print(json.dumps({"status": "R423_REFUSED", "reason": reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

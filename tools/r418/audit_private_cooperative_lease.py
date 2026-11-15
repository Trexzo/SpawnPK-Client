#!/usr/bin/env python3
"""R418 SHA-pinned read-only audit of dormant private cooperative lease.

Uses explicit owner-private source/class directory inputs only. Never prints
private source, launches a game, opens real player history or approves release.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

SOURCE = "rs/plugins/loottracker/LootHistoryStore.java"
CLASS = "rs/plugins/loottracker/LootHistoryStore.class"
LEASE = "rs/plugins/loottracker/LootHistoryStore$R418CooperativeLease.class"


class Refused(RuntimeError):
    pass


def require(ok: bool, reason: str):
    if not ok:
        raise Refused(reason)


def inventory(directory: Path, ext: str) -> dict[str, str]:
    require(directory.is_dir() and not directory.is_symlink(), "INVALID_INPUT_DIRECTORY")
    found: dict[str, str] = {}
    for path in directory.rglob("*" + ext):
        require(path.is_file() and not path.is_symlink(), "UNSAFE_TREE_ENTRY")
        relative = path.relative_to(directory).as_posix()
        require(relative not in found, "DUPLICATE_ENTRY")
        found[relative] = sha256(path.read_bytes()).hexdigest()
    return found


def method_body(source: str, name: str) -> str:
    match = re.search(r"\b" + re.escape(name) + r"\s*\([^)]*\)\s*(?:throws\s+\w+\s*)?\{", source)
    require(match is not None, "MISSING_METHOD_" + name)
    start = source.index("{", match.start())
    depth = 0
    for offset in range(start, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if not depth:
                return source[start + 1:offset]
    raise Refused("UNBALANCED_METHOD_" + name)


def check_structure(source: str, previous: str) -> dict:
    require("r418TryAcquireCooperativeLease" not in previous,
            "LEASE_ALREADY_PRESENT_IN_PRIOR")
    # Strip comments so explanatory text cannot satisfy source assertions.
    source = re.sub(r"/\*[\s\S]*?\*/", " ", source)
    source = re.sub(r"//[^\n]*", "", source)
    acquire = method_body(source, "r418TryAcquireCooperativeLease")
    owns = method_body(source, "owns")
    with_owner = method_body(source, "withOwner")
    close = method_body(source, "close")
    require(source.count("r418TryAcquireCooperativeLease(") == 1,
            "LEASE_USED_OUTSIDE_DORMANT_DECLARATION")
    for token in (
        '"loot-history.writer.lock"', "Files.readAttributes(",
        "LinkOption.NOFOLLOW_LINKS", "StandardOpenOption.CREATE",
        "StandardOpenOption.WRITE", "channel.tryLock()",
        "OverlappingFileLockException", "FileChannel.open(",
        "return null;", "lock.isValid()", "channel.close()",
    ):
        require(token in source, "MISSING_LEASE_GUARD_" + token)
    require(acquire.index("Files.readAttributes(") < acquire.index("FileChannel.open(")
            < acquire.index("channel.tryLock()"),
            "INCORRECT_ACQUISITION_ORDER")
    require("catch (OverlappingFileLockException" in acquire and
            "catch (IOException | SecurityException" in acquire,
            "FAIL_CLOSED_EXCEPTION_HANDLING_MISSING")
    for forbidden in ("Files.delete", "Files.move", "Files.copy",
                      "Files.createLink", "Files.newOutputStream",
                      "StandardOpenOption.TRUNCATE_EXISTING"):
        require(forbidden not in acquire and forbidden not in close,
                "LEASE_MUST_NOT_MODIFY_HISTORY_OR_REMOVE_LOCK_" + forbidden)
    require("UUID.randomUUID()" in source, "SESSION_TOKEN_NOT_UNIQUE")
    require("!released && lock.isValid() && ownerSession.equals(claimed)" in owns,
            "REVOKED_OR_INVALID_LOCK_MUST_REJECT_TOKEN")
    require(with_owner.index("!owns(claimed)") < with_owner.index("action.run()"),
            "ACTION_RUN_BEFORE_SESSION_ADMISSION")
    require("synchronized boolean withOwner" in source and
            "synchronized boolean owns" in source and
            "synchronized void close" in source,
            "LEASE_CLOSE_AND_ADMISSION_MONITOR_MISSING")
    require(close.index("released = true;") < close.index("lock.release()")
            < close.index("channel.close()"),
            "CLOSE_MUST_REVOKE_BEFORE_NATIVE_LOCK_RELEASE")
    # The existing history admission path remains in place, and is not
    # automatically elevated merely by the new dormant owner API.
    require("r417UnresolvedAckEvidence()" in source and
            "r414IntentState() != R414IntentState.NONE" in source,
            "PREVIOUS_RESTART_QUARANTINE_GATES_REMOVED")
    return {"dormant_only": True, "nonblocking_os_lock_try": True,
            "per_session_uuid_fence": True, "close_revokes_before_release": True,
            "no_lockfile_cleanup": True, "prior_intent_ack_gates_preserved": True}


def audit(prior_sources: Path, candidate_sources: Path,
          prior_classes: Path, candidate_classes: Path,
          prior_sha: str, candidate_sha: str,
          source_count: int = 1277, prior_class_count: int = 1393) -> dict:
    for value in (prior_sha, candidate_sha):
        require(re.fullmatch(r"[0-9a-f]{64}", value) is not None, "INVALID_SHA_PIN")
    a = inventory(prior_sources, ".java")
    b = inventory(candidate_sources, ".java")
    c = inventory(prior_classes, ".class")
    d = inventory(candidate_classes, ".class")
    require(len(a) == len(b) == source_count and a.keys() == b.keys(),
            "SOURCE_INVENTORY_DRIFT")
    require(len(c) == prior_class_count and len(d) == prior_class_count + 1,
            "CLASS_COUNT_DRIFT")
    require(sorted(k for k in a if a[k] != b[k]) == [SOURCE],
            "NOT_EXACTLY_ONE_MODIFIED_SOURCE")
    require(sorted(k for k in c if k in d and c[k] != d[k]) == [CLASS],
            "NOT_EXACTLY_ONE_MODIFIED_EXISTING_CLASS")
    require(sorted(set(d) - set(c)) == [LEASE] and not (set(c) - set(d)),
            "UNEXPECTED_NEW_OR_REMOVED_CLASS")
    require(a[SOURCE] == prior_sha and b[SOURCE] == candidate_sha,
            "EXACT_SOURCE_SHA_PIN_MISMATCH")
    checks = check_structure(
        (candidate_sources / SOURCE).read_text("utf-8"),
        (prior_sources / SOURCE).read_text("utf-8"))
    return {"status": "R418_PRIVATE_DORMANT_LEASE_STATIC_GATE_PASS",
            "sources": source_count,
            "classes": len(d),
            "modified_private_sources": 1,
            "modified_existing_classes": 1,
            "added_nested_classes": 1,
            **checks,
            "client_executed": False,
            "production_modified": False,
            "lease_wired_into_client": False,
            "private_release_authorized": False}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("prior-sources", "candidate-sources",
                 "prior-classes", "candidate-classes"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--prior-sha256", required=True)
    ap.add_argument("--candidate-sha256", required=True)
    args = ap.parse_args()
    try:
        result = audit(args.prior_sources, args.candidate_sources,
                       args.prior_classes, args.candidate_classes,
                       args.prior_sha256, args.candidate_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError, UnicodeError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else "UNREADABLE_OR_INVALID_INPUT"
        print(json.dumps({"status": "R418_REFUSED", "reason": reason}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

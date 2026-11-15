#!/usr/bin/env python3
"""R417 public-only, read-only audit of private ack-sidecar admission delta.

Inputs are explicit SHA-pinned owner-private source/class directories. The
script never copies or prints recovered source/class bytes, accesses live
history, starts a client, or authorizes cleanup or release.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys


SOURCE = "rs/plugins/loottracker/LootHistoryStore.java"
CLASS = "rs/plugins/loottracker/LootHistoryStore.class"


class Refused(RuntimeError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Refused(reason)


def tree(root: Path, ext: str) -> dict[str, str]:
    require(root.is_dir() and not root.is_symlink(), "INVALID_TREE_ROOT")
    found = {}
    for path in root.rglob("*" + ext):
        require(path.is_file() and not path.is_symlink(), "SYMLINK_OR_NONREGULAR_INPUT")
        rel = path.relative_to(root).as_posix()
        require(rel not in found, "DUPLICATE_SOURCE_PATH")
        found[rel] = sha256(path.read_bytes()).hexdigest()
    return found


def mask_comments(text: str) -> str:
    # Source under inspection uses no Java text blocks in these method bodies.
    # This is a narrow structural diagnostic, not a full Java parser.
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    return re.sub(r"//[^\n]*", "", text)


def extract(body: str, pattern: str) -> str:
    match = re.search(pattern + r"\s*\([^)]*\)\s*\{", body)
    require(match is not None, "MISSING_METHOD_" + pattern)
    first = body.index("{", match.start())
    depth = 0
    for offset in range(first, len(body)):
        if body[offset] == "{":
            depth += 1
        elif body[offset] == "}":
            depth -= 1
            if depth == 0:
                return body[first + 1:offset]
    raise Refused("UNBALANCED_METHOD_" + pattern)


def verify_ack_guard(source: str) -> dict:
    clean = mask_comments(source)
    admission = extract(clean, r"R411StageState\s+r411StageState")
    guard = extract(clean, r"boolean\s+r417UnresolvedAckEvidence")
    require(admission.count("r417UnresolvedAckEvidence()") == 1,
            "R417_ADMISSION_MUST_CALL_GUARD_ONCE")
    require("return R411StageState.UNSAFE;" in admission,
            "R417_FAIL_CLOSED_ADMISSION_MISSING")
    require(admission.find("r417UnresolvedAckEvidence()") <
            admission.find("r414IntentState()"),
            "R417_ACK_FENCE_MUST_PRECEDE_EXISTING_INTENT_CHECK")
    for term in (
        "loot-history.delete.ack",
        "loot-history.delete.ack.tmp",
        "Files.readAttributes(",
        "LinkOption.NOFOLLOW_LINKS",
        "NoSuchFileException",
        "IOException | SecurityException",
    ):
        require(term in guard, "R417_GUARD_TERM_MISSING_" + term)
    for forbidden in (
        "Files.delete", "Files.move", "Files.copy",
        "Files.write", "Files.newInputStream", "Files.newOutputStream",
        "Files.newByteChannel", "Files.createLink", "FileChannel.open",
        "return false;\n      }\n      catch",
    ):
        require(forbidden not in guard, "R417_GUARD_SIDE_EFFECT_" + forbidden)
    require("return true;" in guard and "return false;" in guard,
            "R417_NOT_FAIL_CLOSED_ON_UNRESOLVED_EVIDENCE")
    for method in ("loadForMerge", "saveWithReceipt", "clearWithReceipt", "deleteStale"):
        require(method in clean, "R417_EXISTING_ADMISSION_PATH_MISSING_" + method)
    return {"ack_marker_and_stage_fenced": True,
            "read_only_metadata_admission": True,
            "no_cleanup_or_writer_unblock": True,
            "original_r414_gate_preserved": True}


def audit(prev_src: Path, next_src: Path, prev_cls: Path, next_cls: Path,
          expected_sources: int, expected_classes: int,
          prior_sha: str, candidate_sha: str) -> dict:
    for value in (prior_sha, candidate_sha):
        require(bool(re.fullmatch(r"[0-9a-f]{64}", value)), "INVALID_SHA_PIN")
    a, b = tree(prev_src, ".java"), tree(next_src, ".java")
    c, d = tree(prev_cls, ".class"), tree(next_cls, ".class")
    require(len(a) == len(b) == expected_sources and a.keys() == b.keys(),
            "R417_SOURCE_INVENTORY_DRIFT")
    require(len(c) == len(d) == expected_classes and c.keys() == d.keys(),
            "R417_CLASS_INVENTORY_DRIFT")
    require(sorted(k for k in a if a[k] != b[k]) == [SOURCE],
            "R417_EXACT_ONE_SOURCE_DELTA_REQUIRED")
    require(sorted(k for k in c if c[k] != d[k]) == [CLASS],
            "R417_EXACT_ONE_CLASS_DELTA_REQUIRED")
    require(a[SOURCE] == prior_sha and b[SOURCE] == candidate_sha,
            "R417_OWNER_SOURCE_SHA_PIN_DRIFT")
    checks = verify_ack_guard((next_src / SOURCE).read_text("utf-8"))
    return {"status": "R417_PRIVATE_ACK_SIDECAR_ADMISSION_GATE_PASS",
            "java_sources": len(b),
            "compiled_classes": len(d),
            "changed_existing_sources": 1,
            "changed_existing_classes": 1,
            **checks,
            "client_executed": False,
            "production_history_opened": False,
            "private_release_authorized": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("prior-sources", "candidate-sources",
                "prior-classes", "candidate-classes"):
        parser.add_argument("--" + arg, type=Path, required=True)
    parser.add_argument("--prior-source-sha256", required=True)
    parser.add_argument("--candidate-source-sha256", required=True)
    parser.add_argument("--source-count", type=int, default=1277)
    parser.add_argument("--class-count", type=int, default=1393)
    args = parser.parse_args(argv)
    try:
        result = audit(
            args.prior_sources, args.candidate_sources,
            args.prior_classes, args.candidate_classes,
            args.source_count, args.class_count,
            args.prior_source_sha256, args.candidate_source_sha256,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, UnicodeError, OSError, ValueError) as error:
        reason = str(error) if isinstance(error, Refused) else "INVALID_INPUT"
        print(json.dumps({"status": "R417_REFUSED", "reason": reason}))
        return 2


if __name__ == "__main__":
    sys.exit(main())

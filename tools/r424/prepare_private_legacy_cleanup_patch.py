#!/usr/bin/env python3
"""Prepare owner-private R424 SOURCE overlay from exact SHA-pinned R421 source.

No client invocation, live history, JAR packaging, auto-deployment, or mutation
of the input tree.  The output is a fresh TEMP-only source tree; dry-run legacy
cleanup remains hard-coded and the old recursive deleteTree() is removed.

Run only with owner-controlled isolated source roots; the SHA pin is a gate,
NOT a cryptographic trust or runtime-compatibility claim.  The generated
private code must be compiled and tested separately before any release.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile

STORE = Path("rs/plugins/loottracker/LootHistoryStore.java")
HELPER = Path("rs/plugins/loottracker/LootLegacyCleanupR424.java")
PINNED_R421_STORE_SHA = "0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29"
PINNED_PUBLIC_HELPER_SHA = "10b547561a7631315c5f44db118376c1a94f6a4cf259f7744f79af8453df18d7"
EXPECTED_SOURCE_COUNT = 1277


class Refused(RuntimeError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical_helper_bytes(data: bytes) -> bytes:
    # Git checkout may convert a public Java fixture to CRLF on Windows.
    # Only ordinary LF or CRLF source is admitted; lone CR is refused.
    normalized = data.replace(b"\r\n", b"\n")
    require(b"\r" not in normalized, "R424_PUBLIC_HELPER_INVALID_LINE_ENDING")
    require(digest(normalized) == PINNED_PUBLIC_HELPER_SHA,
            "R424_PUBLIC_HELPER_SHA_PIN_MISMATCH")
    return normalized


def unique_method_span(source: str, name: str) -> tuple[int, int, str]:
    pattern = re.compile(
        r"^[ \t]*(?:private|protected|public)?[ \t]*(?:static[ \t]+)?"
        r"[\w<>\[\]]+[ \t]+" + re.escape(name)
        + r"\s*\([^;{}]*\)\s*\{", re.MULTILINE)
    found = list(pattern.finditer(source))
    require(len(found) == 1, "R424_METHOD_SIGNATURE_AMBIGUOUS_" + name)
    match = found[0]
    brace = source.index("{", match.start())
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return match.start(), i + 1, source[match.start():i + 1]
    raise Refused("R424_METHOD_UNBALANCED_" + name)


REPLACEMENT_METHOD = '''   // R424: the prior recursive File.listFiles() deletion is disabled.
   // This private candidate performs a complete no-follow inspection only;
   // deletion stays OFF until source-exact and runtime acceptance are proven.
   private void r419DeleteStaleLeased()
   {
      if (r411RefuseUnresolvedStage("legacy cleanup"))
      {
         return;
      }
      final File parent = file.getParentFile();
      if (parent == null)
      {
         return;
      }
      final LootLegacyCleanupR424.Receipt receipt = LootLegacyCleanupR424.run(
         parent.toPath(),
         () -> r411StageState() == R411StageState.CLEAR,
         false); // R424: hard-coded non-destructive policy; do not enable.
      if (receipt.status == LootLegacyCleanupR424.Status.REFUSED ||
          receipt.status == LootLegacyCleanupR424.Status.INTERRUPTED ||
          receipt.status == LootLegacyCleanupR424.Status.PARTIAL)
      {
         log.warn("LootTracker: R424 legacy cleanup inspection refused: {}", receipt);
      }
      else if (receipt.status == LootLegacyCleanupR424.Status.SCANNED)
      {
         log.info("LootTracker: R424 inspected retired history safely; automatic deletion remains disabled: {}", receipt);
      }
   }'''


def patch_source_text(original: str, expected_sha256: str) -> str:
    require(re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None,
            "R424_BAD_SOURCE_PIN_FORMAT")
    require(digest(original.encode("utf-8")) == expected_sha256,
            "R424_PRIOR_STORE_SHA_MISMATCH")
    require("LootLegacyCleanupR424" not in original,
            "R424_ALREADY_PATCHED_OR_FOREIGN_HELPER")
    begin, end, old_cleanup = unique_method_span(original, "r419DeleteStaleLeased")
    require('r411RefuseUnresolvedStage("legacy cleanup")' in old_cleanup,
            "R424_OLD_STAGE_CHECK_CHANGED")
    require("deleteTree(parts)" in old_cleanup,
            "R424_UNSAFE_LEGACY_TREE_CALL_CHANGED")
    require("seenKeys.delete()" in old_cleanup,
            "R424_OLD_KEYS_DELETE_CHANGED")
    a, b, old_delete = unique_method_span(original, "deleteTree")
    require("file.listFiles()" in old_delete and
            "deleteTree(child)" in old_delete and
            "Files.deleteIfExists(file.toPath())" in old_delete,
            "R424_OLD_RECURSIVE_DELETE_SHAPE_CHANGED")
    require(end < a, "R424_METHOD_ORDER_UNEXPECTED")
    require(original.count("deleteTree(") == 3,
            "R424_UNEXPECTED_OTHER_LEGACY_RECURSION_CALLERS")
    # Retire the old method's immediately preceding documentation with it.
    # Otherwise its obsolete "Deletes a file or a directory" javadoc would
    # misleadingly attach to the next (read-only) load() method.
    doc_start = original.rfind("/**", end, a)
    require(doc_start >= 0, "R424_OLD_DELETE_JAVADOC_MISSING")
    doc_end = original.find("*/", doc_start, a)
    require(doc_end >= 0 and
            not original[doc_end+2:a].strip() and
            "Deletes a file or a directory and everything in it." in
                original[doc_start:doc_end],
            "R424_OLD_DELETE_JAVADOC_CHANGED")

    # Work from original offsets backwards so no unrelated text is modified.
    result = original[:doc_start] + original[b:]
    newline = "\r\n" if "\r\n" in original else "\n"
    replacement = REPLACEMENT_METHOD.replace("\n", newline)
    result = result[:begin] + replacement + result[end:]
    require("private static boolean deleteTree" not in result,
            "R424_OLD_DELETE_METHOD_NOT_REMOVED")
    require("deleteTree(parts)" not in result and
            "seenKeys.delete()" not in result,
            "R424_OLD_DESTRUCTIVE_CALL_REMAINED")
    require(result.count("LootLegacyCleanupR424.run(") == 1 and
            result.count("         false); // R424:") == 1,
            "R424_PREPARATION_MUST_REMAIN_DRY_RUN_ONLY")
    return result


def stage(source_root: Path, helper_source: Path, destination: Path) -> dict:
    temp_root = Path(tempfile.gettempdir()).resolve()
    dest = destination.resolve(strict=False)
    require(dest.parent == temp_root and
            dest.name.startswith("R424-Private-Candidate-"),
            "R424_DESTINATION_MUST_BE_FRESH_DIRECT_TEMP_CHILD")
    require(not dest.exists() and not dest.is_symlink(),
            "R424_REFUSE_EXISTING_DESTINATION")
    require(not source_root.is_symlink(), "R424_SYMLINK_SOURCE_ROOT")
    root = source_root.resolve(strict=True)
    require(root.is_dir() and not root.is_symlink(),
            "R424_MISSING_OR_SYMLINK_SOURCE_ROOT")
    for path in root.rglob("*"):
        require(not path.is_symlink(), "R424_SOURCE_TREE_CONTAINS_SYMLINK")
    sources = list(root.rglob("*.java"))
    require(len(sources) == EXPECTED_SOURCE_COUNT,
            "R424_SOURCE_COUNT_DRIFT")
    store_path = root / STORE
    require(store_path.is_file() and not store_path.is_symlink(),
            "R424_PARENT_STORE_NOT_REGULAR_FILE")
    original = store_path.read_bytes()
    require(digest(original) == PINNED_R421_STORE_SHA,
            "R424_PARENT_STORE_SHA_PIN_MISMATCH")
    require(not (root / HELPER).exists(), "R424_HELPER_ALREADY_IN_PARENT")
    require(helper_source.is_file() and not helper_source.is_symlink(),
            "R424_PUBLIC_HELPER_NOT_REGULAR_FILE")
    public_bytes = canonical_helper_bytes(helper_source.read_bytes())
    patch = patch_source_text(original.decode("utf-8"), PINNED_R421_STORE_SHA)
    # Only after ALL admission checks succeed may a fresh output be created.
    dest.mkdir()
    shutil.copytree(root, dest / "source")
    new_store = dest / "source" / STORE
    new_store.write_bytes(patch.encode("utf-8"))
    helper_target = dest / "source" / HELPER
    helper_target.write_bytes(public_bytes)
    after = sorted((dest / "source").rglob("*.java"))
    require(len(after) == EXPECTED_SOURCE_COUNT + 1,
            "R424_OUTPUT_INVENTORY_MISMATCH")
    receipt = {
        "status": "R424_PRIVATE_DRY_RUN_LEGACY_CLEANUP_PATCH_PREPARED_NOT_COMPILED",
        "prior_store_sha256": PINNED_R421_STORE_SHA,
        "candidate_store_sha256": digest(new_store.read_bytes()),
        "helper_sha256": digest(helper_target.read_bytes()),
        "previous_source_count": EXPECTED_SOURCE_COUNT,
        "candidate_source_count": len(after),
        "modified_existing_sources": [STORE.as_posix()],
        "added_sources": [HELPER.as_posix()],
        "automatic_legacy_deletion_enabled": False,
        "private_java_compiled": False,
        "game_executed": False,
        "production_history_opened": False,
        "release_authorized": False,
    }
    (dest / "R424-Preparation-Receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-private-source-root", type=Path, required=True)
    parser.add_argument("--public-helper-source", type=Path, required=True)
    parser.add_argument("--fresh-temp-destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = stage(args.owner_private_source_root,
                       args.public_helper_source,
                       args.fresh_temp_destination)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, ValueError, UnicodeError) as problem:
        print(json.dumps({"status": "R424_PREPARATION_REFUSED",
                          "reason": str(problem) if isinstance(problem, Refused)
                          else "INVALID_OR_UNREADABLE_SOURCE"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

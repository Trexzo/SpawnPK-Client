"""Compare two R182 javac reports without conflating incompatible build profiles.

A profile lock is a separately pinned description of a compiler invocation and
all allowed inputs. Identical human-readable profile labels are not sufficient.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

REQUIRED_LOCK = (
    "toolchain_sha256",
    "javac_command_sha256",
    "dependency_manifest_sha256",
    "source_scope_sha256",
    "dependency_policy",
)

def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _load_pinned(path: Path, sha: str) -> dict:
    actual = _digest_file(path)
    if actual.lower() != sha.lower():
        raise ValueError("Report or profile SHA-256 mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object")
    return value

def _lock(value: dict) -> dict:
    missing = [key for key in REQUIRED_LOCK if not isinstance(value.get(key), str) or not value[key]]
    if missing:
        raise ValueError("Incomplete profile lock: " + ", ".join(missing))
    if value["dependency_policy"] != "no-original-client-binary":
        raise ValueError("Only strict no-original-client-binary policy supported")
    for key in REQUIRED_LOCK[:4]:
        v = value[key]
        if len(v) != 64 or any(c not in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("Invalid SHA256 value: " + key)
    return {key: value[key].lower() if key.endswith("_sha256") else value[key] for key in REQUIRED_LOCK}

def _error_counter(report: dict) -> Counter:
    if report.get("schema") != "spk.javac-frontier.r182.v1":
        raise ValueError("Unexpected R182 report schema")
    if report.get("complete_error_inventory") is not True:
        raise ValueError("Refusing incomplete javac diagnostic inventory")
    if report.get("unparsed_line_count") != 0:
        raise ValueError("Unparsed lines prevent authoritative comparison")
    entries = report.get("diagnostics")
    if not isinstance(entries, list):
        raise ValueError("Missing diagnostics")
    errors = Counter()
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            raise ValueError("Malformed diagnostic record")
        if item["key"].startswith("compiler.err."):
            identity = (item["file"], item["line"], item["column"], item["key"], item["message"])
            errors[identity] += 1
    if sum(errors.values()) != report.get("parsed_error_count") or (
        sum(errors.values()) != report.get("summary_error_count")
    ):
        raise ValueError("Error inventory count mismatch")
    return errors

def compare(before: dict, after: dict, before_lock: dict, after_lock: dict) -> dict:
    if before.get("profile") != after.get("profile"):
        raise ValueError("Different build profile labels")
    if _lock(before_lock) != _lock(after_lock):
        raise ValueError("Different toolchain, command, scope or dependency profile")
    old, new = _error_counter(before), _error_counter(after)
    removed, added = old - new, new - old
    # Files and messages may contain private information. Do not copy them
    # into the aggregate output.
    return {
        "schema": "spk.javac-frontier-compare.r182.v1",
        "profile": before["profile"],
        "before_errors": sum(old.values()),
        "after_errors": sum(new.values()),
        "delta_errors": sum(new.values()) - sum(old.values()),
        "removed_error_occurrences": sum(removed.values()),
        "added_error_occurrences": sum(added.values()),
        "unchanged_error_occurrences": sum((old & new).values()),
        "interpretation": "diagnostic-count delta only; no root cause or recovered-source acceptance",
    }

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("before", "after", "before_lock", "after_lock"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
        p.add_argument("--" + name.replace("_", "-") + "-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    old = _load_pinned(a.before, a.before_sha256)
    new = _load_pinned(a.after, a.after_sha256)
    lock_a = _load_pinned(a.before_lock, a.before_lock_sha256)
    lock_b = _load_pinned(a.after_lock, a.after_lock_sha256)
    result = compare(old, new, lock_a, lock_b)
    with a.output.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(result, out, indent=2, sort_keys=True)
        out.write("\n")

if __name__ == "__main__":
    main()

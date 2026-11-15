#!/usr/bin/env python3
"""Read-only R420 owner-private exact-inventory / bounded-retry safety audit.

Uses explicit path/SHA pins. Does not execute Java, open player histories,
publish recovered source, alter files, acquire locks or authorize release.
Static checks are NOT proof of runtime, fairness, or EDT nonblocking behavior.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

PLUGIN = "rs/plugins/loottracker/LootTrackerPlugin.java"
STORE = "rs/plugins/loottracker/LootHistoryStore.java"
CLASS = "rs/plugins/loottracker/LootTrackerPlugin.class"

class Refused(Exception):
    pass

def need(condition: bool, reason: str):
    if not condition:
        raise Refused(reason)

def tree(root: Path, suffix: str) -> dict[str, str]:
    need(root.is_dir() and not root.is_symlink(), "R420_BAD_TREE_ROOT")
    result = {}
    for p in root.rglob("*" + suffix):
        need(p.is_file() and not p.is_symlink(), "R420_UNSAFE_TREE_MEMBER")
        key = p.relative_to(root).as_posix()
        need(key not in result, "R420_DUPLICATE_PATH")
        result[key] = sha256(p.read_bytes()).hexdigest()
    return result

def clean(text: str) -> str:
    return re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", " ", text)

def body(source: str, name: str) -> str:
    pattern = r"\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*(?:throws\s+\w+\s*)?\{"
    match = re.search(pattern, source)
    need(match is not None, "R420_METHOD_MISSING_" + name)
    start = source.index("{", match.start())
    depth = 0
    for idx in range(start, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start+1:idx]
    raise Refused("R420_UNBALANCED_" + name)

def order(source: str, *parts: str) -> bool:
    pos = 0
    for part in parts:
        found = source.find(part, pos)
        if found < 0:
            return False
        pos = found + len(part)
    return True

def check_contract(previous: str, candidate: str) -> dict:
    a = clean(previous)
    b = clean(candidate)
    need("r420AcquireRestoreLeaseWithBoundedRetry" not in a,
         "R420_RETRY_ALREADY_PRESENT_IN_PARENT")
    need(b.count("r420AcquireRestoreLeaseWithBoundedRetry(") == 2,
         "R420_ONE_DECLARATION_ONE_CALL_REQUIRED")
    helper = body(b, "r420AcquireRestoreLeaseWithBoundedRetry")
    restore = body(b, "loadHistory")
    need("if (SwingUtilities.isEventDispatchThread())" in helper and
         "return false;" in helper,
         "R420_EDT_FAIL_CLOSED_MISSING")
    need(re.search(r"long\s*\[\s*\]\s+retryDelayMillis\s*=\s*\{\s*0L\s*,\s*75L\s*,\s*150L\s*,\s*300L\s*,\s*450L\s*\}",helper) is not None,
         "R420_EXACT_FINITE_BACKOFF_BOUND_MISSING")
    need("for (long delay : retryDelayMillis)" in helper and
         "while (" not in helper,
         "R420_RETRY_MUST_HAVE_FINITE_FOR")
    need(helper.count("Thread.sleep(delay)") == 1 and
         helper.count("synchronized (r395HistoryGate)") == 1,
         "R420_SLEEP_AND_SESSION_GATE_COUNT_DRIFT")
    need(order(helper, "Thread.sleep(delay)",
               "Thread.currentThread().isInterrupted()",
               "synchronized (r395HistoryGate)",
               "restoreStore.r419ActivateOwner()"),
         "R420_SLEEP_MUST_BE_OUTSIDE_SESSION_MONITOR")
    need(order(helper, "catch (InterruptedException canceled)",
               "Thread.currentThread().interrupt();",
               "return false;"),
         "R420_INTERRUPTION_MUST_PRESERVE_FLAG_AND_REFUSE")
    for requirement in ("generation != r395HistoryGeneration",
                        "!r399AcceptingDrops", "instance != this",
                        "historyStore != restoreStore"):
        need(requirement in helper, "R420_SESSION_FENCE_MISSING_" + requirement)
    need(helper.count("restoreStore.r419ActivateOwner()") == 1,
         "R420_OWNER_ACQUISITION_COUNT_DRIFT")
    need("if (!r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation))" in restore,
         "R420_RESTORE_MUST_USE_BOUNDED_RETRY")
    need("if (!restoreStore.r419ActivateOwner())" not in restore,
         "R420_OLD_SINGLE_TRY_STILL_USED")
    need(order(restore, "r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)",
               "generation != r395HistoryGeneration",
               "restoreStore.deleteStale()", "restoreStore.loadForMerge()"),
         "R420_RESTORE_ADMISSION_ORDER_DRIFT")
    for unsafe in ("Files.delete", "Files.move", "Files.copy",
                   "Files.createLink", "Files.newOutputStream",
                   "SwingUtilities.invokeAndWait"):
        need(unsafe not in helper, "R420_RETRY_SIDE_EFFECT_" + unsafe)
    return {
        "retry_background_only": True,
        "finite_five_attempts": True,
        "retry_max_backoff_ms": 975,
        "sleep_outside_history_gate": True,
        "stale_session_refusal": True,
        "interrupt_flag_preserved": True,
        "unresolved_journals_untouched": True,
    }

def audit(prior_src: Path, candidate_src: Path, prior_cls: Path,
          candidate_cls: Path, prior_sha: str, candidate_sha: str,
          source_count: int = 1277, class_count: int = 1394) -> dict:
    for value in (prior_sha, candidate_sha):
        need(re.fullmatch("[0-9a-f]{64}", value) is not None,
             "R420_INVALID_SHA256_PIN")
    a, b = tree(prior_src, ".java"), tree(candidate_src, ".java")
    c, d = tree(prior_cls, ".class"), tree(candidate_cls, ".class")
    need(len(a) == len(b) == source_count and a.keys() == b.keys(),
         "R420_SOURCE_INVENTORY_DRIFT")
    need(len(c) == len(d) == class_count and c.keys() == d.keys(),
         "R420_CLASS_INVENTORY_DRIFT")
    need(sorted(k for k in a if a[k] != b[k]) == [PLUGIN],
         "R420_EXACT_PLUGIN_SOURCE_ONLY")
    need(sorted(k for k in c if c[k] != d[k]) == [CLASS],
         "R420_EXACT_PLUGIN_CLASS_ONLY")
    need(a[PLUGIN] == prior_sha and b[PLUGIN] == candidate_sha,
         "R420_SOURCE_PIN_MISMATCH")
    need(a[STORE] == b[STORE], "R420_STORE_SOURCE_CHANGED")
    checked=check_contract(
        (prior_src/PLUGIN).read_text("utf-8"),
        (candidate_src/PLUGIN).read_text("utf-8"))
    return {
        "status": "R420_PRIVATE_BOUNDED_RETRY_STATIC_GATE_PASS",
        "source_count": len(b),
        "class_count": len(d),
        "source_delta": [PLUGIN],
        "class_delta": [CLASS],
        **checked,
        "game_executed": False,
        "production_data_opened": False,
        "private_release_authorized": False,
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("prior-sources", "candidate-sources",
                 "prior-classes", "candidate-classes"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--prior-source-sha256", required=True)
    p.add_argument("--candidate-source-sha256", required=True)
    args = p.parse_args()
    try:
        result = audit(args.prior_sources, args.candidate_sources,
                       args.prior_classes, args.candidate_classes,
                       args.prior_source_sha256, args.candidate_source_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, OSError, UnicodeError, ValueError, KeyError) as e:
        reason = str(e) if isinstance(e, Refused) else "R420_INVALID_OR_UNREADABLE_INPUT"
        print(json.dumps({"status":"R420_REFUSED","reason":reason}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())

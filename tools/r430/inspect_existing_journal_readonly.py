#!/usr/bin/env python3
"""R430 read-only bridge to the EXISTING R415-R417 synthetic protocol model.

Uses the existing public R417 classifier as the *only* parser of intent/ack
evidence. It adds no new ledger format, no ack publisher, no file deletion,
no write admission, no recovery or retry.

This command may inspect ONLY an existing real-directory R430-Synthetic-*
direct child of the Python tempfile root. It does not consume owner-private
sources, current player history, or any real SpawnPK profile.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.r417 import restart_ack_model as legacy

# This is the R429 *experimental* ledger. It is not part of the private
# protocol and must NEVER be mistaken for an R415-R417 ack or permit writes.
EXPERIMENTAL_LEDGER = "R429-synthetic-intent.ledger"
MONITORED = (
    legacy.HISTORY,
    legacy.HISTORY_TMP,
    legacy.INTENT,
    legacy.INTENT_TMP,
    legacy.ACK,
    legacy.ACK_TMP,
    EXPERIMENTAL_LEDGER,
)

class Refused(RuntimeError):
    pass


@dataclass(frozen=True)
class Gate:
    status: str
    classifier_state: str
    writer_authorized: bool = False
    delete_authorized: bool = False
    marker_cleanup_authorized: bool = False
    client_executed: bool = False
    private_source_inspected: bool = False
    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Refused(reason)


def synthetic_root(requested: Path) -> Path:
    root = requested.absolute()
    # Refuse any lexical .. or indirection before normalization.
    require(".." not in root.parts, "R430_UNSAFE_PATH_TRAVERSAL")
    tmp = Path(tempfile.gettempdir()).absolute()
    require(root.parent == tmp and root.name.startswith("R430-Synthetic-"),
            "R430_NOT_DIRECT_SYNTHETIC_TEMP")
    for ancestor in (root, *root.parents):
        try:
            metadata = ancestor.lstat()
        except OSError:
            raise Refused("R430_MISSING_OR_UNREADABLE_ANCESTOR")
        require(stat.S_ISDIR(metadata.st_mode) and
                not stat.S_ISLNK(metadata.st_mode),
                "R430_SYMLINK_OR_NON_DIRECTORY_ANCESTOR")
    return root


def snapshot(root: Path) -> tuple[tuple[str, Any], ...]:
    """Metadata snapshot, including exact file bytes for *bounded* regular files.

    Does not open any symlink or unknown file type. When an entry is unreadable
    or mutating, refuse the whole inspection instead of calling it absent.
    Snapshot is not an anchored directory descriptor and is NOT race-proof.
    """
    result: list[tuple[str, Any]] = []
    for name in MONITORED:
        path = root / name
        try:
            before = path.lstat()
        except FileNotFoundError:
            result.append((name, None))
            continue
        except OSError:
            raise Refused("R430_UNREADABLE_MARKER_METADATA")
        if stat.S_ISLNK(before.st_mode):
            # Classifier must quarantine, regardless of dangling target.
            result.append((name, ("SYMLINK",)))
            continue
        if not stat.S_ISREG(before.st_mode):
            result.append((name, ("UNSUPPORTED_ENTRY", before.st_mode)))
            continue
        maximum = legacy.MAX_HISTORY if name == legacy.HISTORY else legacy.MAX_MARKER
        require(0 <= before.st_size <= maximum,
                "R430_OVERSIZE_EVIDENCE")
        # No-follow open is used on Linux; Windows identity/mtime snapshots
        # are an optimistic check only, not defense against a hostile swap.
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags)
            try:
                opened = os.fstat(fd)
                require(stat.S_ISREG(opened.st_mode),
                        "R430_NONREGULAR_OPENED_EVIDENCE")
                with os.fdopen(fd, "rb", closefd=False) as fp:
                    payload = fp.read(maximum + 1)
            finally:
                os.close(fd)
            after = path.lstat()
        except OSError:
            raise Refused("R430_EVIDENCE_READ_UNCERTAIN")
        require(
            stat.S_ISREG(after.st_mode)
            and len(payload) <= maximum
            and before.st_size == len(payload) == opened.st_size == after.st_size
            and before.st_mtime_ns == opened.st_mtime_ns == after.st_mtime_ns
            and (before.st_dev, before.st_ino) ==
                (opened.st_dev, opened.st_ino) ==
                (after.st_dev, after.st_ino),
            "R430_EVIDENCE_CHANGED_DURING_READ"
        )
        result.append((name, ("REGULAR", before.st_size, sha256(payload).hexdigest())))
    return tuple(result)


def inspect_only(root_path: Path) -> Gate:
    root = synthetic_root(root_path)
    before = snapshot(root)
    # Do not allow an experimental synthetic ledger to silently coexist
    # with the existing protocol, even when there are no old markers.
    experimental = next(v for k, v in before if k == EXPERIMENTAL_LEDGER)
    first = legacy.inspect(root)
    second = legacy.inspect(root)
    after = snapshot(root)
    require(before == after, "R430_EVIDENCE_DRIFT_DURING_INSPECTION")
    require(first == second, "R430_INCONSISTENT_PASSIVE_CLASSIFICATION")
    require(first.state in {
        legacy.NONE, legacy.ABORTED, legacy.COMMITTED,
        legacy.ACKED, legacy.QUARANTINED
    }, "R430_UNKNOWN_CLASSIFIER_STATE")
    if experimental is not None:
        return Gate("R430_EXPERIMENTAL_LEDGER_PRESENT_FENCED",
                    first.state)
    if first.state == legacy.NONE:
        # NONE is an observation, NOT a legal Store.commit permission.
        return Gate("R430_NO_EVIDENCE_OWNER_LEASE_AND_STAGE_GATES_STILL_REQUIRED",
                    first.state)
    if first.state == legacy.ABORTED:
        return Gate("R430_ABORTED_BEFORE_REPLACE_FENCED", first.state)
    if first.state == legacy.COMMITTED:
        return Gate("R430_COMMITTED_UNACKED_FENCED", first.state)
    if first.state == legacy.ACKED:
        # Even a valid ACK cannot unblock write admission or cleanup.
        return Gate("R430_ACK_RECORDED_BUT_STILL_FENCED", first.state)
    return Gate("R430_QUARANTINED", first.state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-temp-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = inspect_only(args.synthetic_temp_root).as_dict()
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, ValueError, OSError, PermissionError) as error:
        reason = str(error) if isinstance(error, Refused) else \
            "R430_INPUT_UNREADABLE_OR_INVALID"
        print(json.dumps({
            "status": "R430_REFUSED",
            "reason": reason,
            "writer_authorized": False,
            "delete_authorized": False,
            "marker_cleanup_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

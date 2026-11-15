"""R417: invented, isolated model of durable restart acknowledgment evidence.

This module NEVER touches real history, never removes the delete-intent marker,
never restores a real client, and never authorizes subsequent history writes.
It is NOT a private-client implementation or an interprocess locking proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from typing import Callable

INTENT = "loot-history.delete.intent"
ACK = "loot-history.delete.ack"
INTENT_TMP = INTENT + ".tmp"
ACK_TMP = ACK + ".tmp"
HISTORY = "loot-history.json"
HISTORY_TMP = HISTORY + ".tmp"
MAX_MARKER = 512
MAX_HISTORY = 64 * 1024 * 1024
SERIAL = r"[1-9][0-9]{0,15}"
NONCE = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
HEX = r"[0-9a-f]{64}"

NONE = "NONE"
ABORTED = "ABORTED_NO_ADOPTION"
COMMITTED = "COMMITTED_UNACKED_FENCED"
ACKED = "ACK_RECORDED_FENCED"
QUARANTINED = "QUARANTINED"


@dataclass(frozen=True)
class Evidence:
    state: str
    marker_sha: str = ""
    history_sha: str = ""
    serial: str = ""
    nonce: str = ""


def _hash(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _exists(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return True  # Unknown evidence must not be treated as absent.


def _regular(path: Path, limit: int) -> bytes | None:
    """Bounded no-follow read with pre/post metadata checks (not a race-proof lease)."""
    try:
        a = path.lstat()
        if not stat.S_ISREG(a.st_mode) or a.st_size > limit or a.st_size < 0:
            return None
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > limit:
                return None
            with os.fdopen(fd, "rb", closefd=False) as stream:
                payload = stream.read(limit + 1)
        finally:
            os.close(fd)
        b = path.lstat()
        if (len(payload) > limit or len(payload) != a.st_size
                or a.st_size != b.st_size or a.st_mtime_ns != b.st_mtime_ns
                or a.st_ino != b.st_ino or a.st_dev != b.st_dev
                or opened.st_ino != a.st_ino or opened.st_dev != a.st_dev):
            return None
        return payload
    except (OSError, ValueError):
        return None


def _parse_intent(payload: bytes) -> tuple[str, str, str, str] | None:
    if not (100 <= len(payload) <= MAX_MARKER):
        return None
    try:
        text = payload.decode("ascii", "strict")
    except UnicodeError:
        return None
    match = re.fullmatch(
        r"v=1\nserial=(" + SERIAL + r")\nnonce=(" + NONCE +
        r")\nbefore=(ABSENT|" + HEX + r")\nafter=(" + HEX + r")\n",
        text, flags=re.ASCII,
    )
    if match is None or match.group(3) == match.group(4):
        return None
    return match.group(1), match.group(2), match.group(3), match.group(4)


def _parse_ack(payload: bytes) -> tuple[str, str, str] | None:
    if not (100 <= len(payload) <= MAX_MARKER):
        return None
    try:
        text = payload.decode("ascii", "strict")
    except UnicodeError:
        return None
    match = re.fullmatch(
        r"v=1\nserial=(" + SERIAL + r")\nnonce=(" + NONCE +
        r")\nafter=(" + HEX + r")\nacked=1\n",
        text, flags=re.ASCII,
    )
    return None if match is None else match.groups()


def _valid_json_exact(payload: bytes) -> bool:
    """Synthetic strict format, not the recovered client's Gson implementation."""
    try:
        document = json.loads(payload.decode("utf-8", "strict"))
        if (not isinstance(document, dict)
                or set(document) != {"version", "records"}
                or type(document["version"]) is not int
                or document["version"] != 1
                or not isinstance(document["records"], list)):
            return False
        types = {"NPC", "PLAYER", "CLUE", "OTHER"}
        for row in document["records"]:
            if (not isinstance(row, dict)
                    or set(row) != {"title", "subtitle", "type", "kills",
                                   "timestamp", "items"}
                    or not isinstance(row["title"], str) or not row["title"]
                    or not isinstance(row["subtitle"], str)
                    or row["type"] not in types
                    or type(row["kills"]) is not int
                    or type(row["timestamp"]) is not int
                    or not isinstance(row["items"], list)
                    or len(row["items"]) > 4096):
                return False
            for item in row["items"]:
                if (not isinstance(item, dict)
                        or set(item) != {"id", "name", "quantity", "price", "hidden"}
                        or type(item["id"]) is not int
                        or not isinstance(item["name"], str)
                        or type(item["quantity"]) is not int or item["quantity"] < 0
                        or type(item["price"]) is not int or item["price"] < 0
                        or type(item["hidden"]) is not bool):
                    return False
        return json.dumps(
            document, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8") == payload
    except (ValueError, UnicodeError, TypeError, KeyError):
        return False


def inspect(directory: Path) -> Evidence:
    """Observe only: no file mutation, no adoption, and no writer admission."""
    root = Path(directory)
    if any(_exists(root / name) for name in (INTENT_TMP, ACK_TMP, HISTORY_TMP)):
        return Evidence(QUARANTINED)

    if not _exists(root / INTENT):
        return Evidence(QUARANTINED if _exists(root / ACK) else NONE)
    intent_raw = _regular(root / INTENT, MAX_MARKER)
    if intent_raw is None:
        return Evidence(QUARANTINED)
    marker = _parse_intent(intent_raw)
    if marker is None:
        return Evidence(QUARANTINED)
    serial, nonce, before, after = marker

    has_history = _exists(root / HISTORY)
    current = _regular(root / HISTORY, MAX_HISTORY) if has_history else None
    if has_history and current is None:
        return Evidence(QUARANTINED)
    actual_sha = "ABSENT" if not has_history else _hash(current)
    if actual_sha == before:
        # A forged or stale acknowledgment must never be honored for old image.
        return Evidence(QUARANTINED if _exists(root / ACK) else ABORTED,
                        _hash(intent_raw), actual_sha, serial, nonce)
    if actual_sha != after or current is None or not _valid_json_exact(current):
        return Evidence(QUARANTINED)

    # Revalidate that both the marker and the committed image remained stable
    # through the read. This is only optimistic; foreign writers remain unsafe.
    if (_regular(root / INTENT, MAX_MARKER) != intent_raw
            or _regular(root / HISTORY, MAX_HISTORY) != current):
        return Evidence(QUARANTINED)

    if not _exists(root / ACK):
        return Evidence(COMMITTED, _hash(intent_raw), actual_sha, serial, nonce)

    ack_raw = _regular(root / ACK, MAX_MARKER)
    parsed_ack = _parse_ack(ack_raw) if ack_raw is not None else None
    if parsed_ack != (serial, nonce, after):
        return Evidence(QUARANTINED)
    if (_regular(root / ACK, MAX_MARKER) != ack_raw
            or _regular(root / INTENT, MAX_MARKER) != intent_raw
            or _regular(root / HISTORY, MAX_HISTORY) != current):
        return Evidence(QUARANTINED)
    return Evidence(ACKED, _hash(intent_raw), actual_sha, serial, nonce)


def publish_ack(directory: Path, evidence: Evidence, *,
                adoption_confirmed: bool = False,
                after_step: Callable[[str], None] | None = None) -> str:
    """Model a manual acknowledgment. NEVER remove intent or admit writes.

    The adoption_confirmed flag represents a separate verified caller contract
    which is NOT implemented in the recovered client. No user data is handled.
    An interrupted stage or link remains on disk and forces quarantine.
    """
    root = Path(directory)
    if not adoption_confirmed or evidence.state != COMMITTED:
        return "REFUSED_NO_ADOPTION"
    if inspect(root) != evidence:
        return "REFUSED_CHANGED_EVIDENCE"
    tmp = root / ACK_TMP
    final = root / ACK
    encoded = (f"v=1\nserial={evidence.serial}\nnonce={evidence.nonce}\n"
               f"after={evidence.history_sha}\nacked=1\n").encode("ascii")
    if not (100 <= len(encoded) <= MAX_MARKER):
        return "REFUSED_MARKER_FORMAT"

    try:
        # CREATE_NEW and a separate no-clobber hardlink are intentional.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if after_step:
            after_step("ACK_TEMP_FORCED")
        if inspect(root).state != QUARANTINED:
            # After staging the file, inspect MUST quarantine.
            return "REFUSED_MISSING_STAGING_FENCE"
        if not (_regular(root / INTENT, MAX_MARKER) and
                _hash(_regular(root / INTENT, MAX_MARKER)) == evidence.marker_sha
                and (committed_bytes := _regular(root / HISTORY, MAX_HISTORY)) is not None
                and _hash(committed_bytes) == evidence.history_sha
                and _valid_json_exact(committed_bytes)):
            return "REFUSED_CHANGED_EVIDENCE_AFTER_STAGE"
        # os.link never overwrites an existing acknowledged record.
        os.link(tmp, final)
        if after_step:
            after_step("ACK_FINAL_LINKED")
        tmp.unlink()
        if after_step:
            after_step("ACK_TEMP_REMOVED")
        return "ACK_RECORDED_FENCED" if inspect(root).state == ACKED \
            else "ACK_RECORDED_BUT_QUARANTINED"
    except (OSError, ValueError):
        # Never unlink anything on an ambiguous failure.
        return "REFUSED_OR_INTERRUPTED_FENCED"


def ordinary_writer_permitted(directory: Path) -> bool:
    """In R417 synthetic design, acknowledgment is NEVER a write-unblock token."""
    state = inspect(directory).state
    return False  # No writer is modeled; all persistence is intentionally fenced.


def synth_intent(before: bytes | None, after: bytes, *,
                 serial: str = "1",
                 nonce: str = "00000000-0000-4000-8000-000000000001") -> bytes:
    return (f"v=1\nserial={serial}\nnonce={nonce}\n"
            f"before={'ABSENT' if before is None else _hash(before)}\n"
            f"after={_hash(after)}\n").encode("ascii")


def synth_history() -> bytes:
    return b'{"version":1,"records":[]}'

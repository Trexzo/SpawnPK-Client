from __future__ import annotations

import hashlib
from pathlib import Path


def canonical_source_bytes(data: bytes) -> bytes:
    """Canonicalize text line endings for cross-platform source authority.

    Java source semantics do not distinguish LF, CRLF, or lone CR line
    endings. Authority digests therefore bind the source text content rather
    than the host OS newline encoding.
    """
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sorted_java_files(root: Path) -> list[Path]:
    return sorted(
        root.rglob("*.java"),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def source_tree_digest(
    root: Path,
) -> tuple[str, list[Path], int]:
    files = sorted_java_files(root)
    h = hashlib.sha256()
    total_bytes = 0

    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = canonical_source_bytes(path.read_bytes())

        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)

        total_bytes += len(data)

    return h.hexdigest(), files, total_bytes

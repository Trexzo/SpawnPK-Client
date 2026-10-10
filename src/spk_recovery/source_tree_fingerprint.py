"""Deterministic whole-Java-source-tree provenance for private client recovery.

No source text, relative file paths, or proprietary class/member coordinates
are emitted by the CLI. Symlinks and changing trees are rejected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


class SourceTreeError(ValueError):
    """Source-tree provenance cannot be established."""


def _fail(ok: bool, message: str) -> None:
    if not ok:
        raise SourceTreeError(message)


def _sha256(path: Path) -> bytes:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.digest()


def fingerprint_java_source_tree(source_root: Path) -> dict[str, Any]:
    """Hash *all* .java files with relative paths and file content.

    This deliberately does not follow symlinks. A source-root containing any
    symlink, including one hidden in an otherwise unselected directory, is
    rejected. A relative path, not the machine-specific absolute root, is
    part of the digest; the result is portable across private workspaces.
    """
    root = Path(source_root)
    _fail(root.is_dir() and not root.is_symlink(), "SOURCE_ROOT_INVALID")
    root = root.resolve(strict=True)
    files: list[tuple[str, Path]] = []
    def reject_walk_error(_error: OSError) -> None:
        raise SourceTreeError("SOURCE_TREE_WALK_FAILED")

    for folder, directories, filenames in os.walk(
        root, followlinks=False, onerror=reject_walk_error,
    ):
        parent = Path(folder)
        for dirname in directories:
            _fail(not (parent / dirname).is_symlink(),
                  "SOURCE_TREE_SYMLINK_NOT_ALLOWED")
        for filename in filenames:
            path = parent / filename
            _fail(path.is_file() and not path.is_symlink(),
                  "SOURCE_TREE_NONREGULAR_OR_SYMLINK_FILE")
            if path.suffix != ".java":
                continue
            relative = path.relative_to(root).as_posix()
            _fail(
                relative and all(part not in (".", "..", "") for part in relative.split("/"))
                and "\x00" not in relative and "\\" not in relative,
                "SOURCE_TREE_INVALID_RELATIVE_PATH",
            )
            files.append((relative, path))
    _fail(bool(files), "SOURCE_TREE_HAS_NO_JAVA_FILES")
    files.sort(key=lambda entry: entry[0].encode("utf-8"))
    digest = hashlib.sha256()
    for relative, path in files:
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(_sha256(path))
    return {
        "schema_version": 1,
        "kind": "private_java_source_tree_pin",
        "source_tree_sha256": digest.hexdigest(),
        "source_java_file_count": len(files),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(
            fingerprint_java_source_tree(args.source_root),
            indent=2, sort_keys=True,
        ))
    except SourceTreeError as exc:
        parser.error(str(exc))
    except (OSError, ValueError):
        parser.error("SOURCE_TREE_FINGERPRINT_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

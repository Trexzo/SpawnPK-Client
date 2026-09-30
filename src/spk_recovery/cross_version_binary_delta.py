from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile


class CrossVersionBinaryDeltaError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _index_entries(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            if info.filename in rows:
                raise CrossVersionBinaryDeltaError(
                    f"duplicate ZIP entry is unsupported: {info.filename}"
                )
            data = archive.read(info)
            rows[info.filename] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
                "crc32": f"{info.CRC:08x}",
            }
    return rows


def build_cross_version_binary_delta(
    old_jar: Path,
    new_jar: Path,
    *,
    old_build_id: str,
    new_build_id: str,
) -> dict[str, Any]:
    if not old_build_id or not new_build_id:
        raise CrossVersionBinaryDeltaError(
            "old_build_id and new_build_id must be non-empty"
        )
    if old_build_id == new_build_id:
        raise CrossVersionBinaryDeltaError(
            "old_build_id and new_build_id must differ"
        )

    old_jar = old_jar.resolve()
    new_jar = new_jar.resolve()
    if not old_jar.is_file():
        raise CrossVersionBinaryDeltaError(
            f"old JAR does not exist: {old_jar}"
        )
    if not new_jar.is_file():
        raise CrossVersionBinaryDeltaError(
            f"new JAR does not exist: {new_jar}"
        )

    old_sha = _sha256_file(old_jar)
    new_sha = _sha256_file(new_jar)
    if old_sha == new_sha:
        raise CrossVersionBinaryDeltaError(
            "old and new JAR authorities must differ"
        )

    old_entries = _index_entries(old_jar)
    new_entries = _index_entries(new_jar)

    old_paths = set(old_entries)
    new_paths = set(new_entries)
    old_only = sorted(old_paths - new_paths)
    new_only = sorted(new_paths - old_paths)

    changed: list[dict[str, Any]] = []
    for path in sorted(old_paths & new_paths):
        old_row = old_entries[path]
        new_row = new_entries[path]
        if old_row["sha256"] == new_row["sha256"]:
            continue
        changed.append(
            {
                "path": path,
                "class_entry": path.endswith(".class"),
                "old_sha256": old_row["sha256"],
                "new_sha256": new_row["sha256"],
                "old_size": old_row["size"],
                "new_size": new_row["size"],
                "old_crc32": old_row["crc32"],
                "new_crc32": new_row["crc32"],
            }
        )

    summary = {
        "old_entry_count": len(old_entries),
        "new_entry_count": len(new_entries),
        "old_only_entries": len(old_only),
        "new_only_entries": len(new_only),
        "changed_entries": len(changed),
        "changed_class_entries": sum(
            1 for row in changed if row["class_entry"]
        ),
    }
    material = {
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "summary": summary,
        "old_only": old_only,
        "new_only": new_only,
        "changed": changed,
    }
    report_id = (
        "XVERBIN_"
        + hashlib.sha256(_stable_json(material))
        .hexdigest()[:20]
        .upper()
    )

    return {
        "schema_version": 1,
        "kind": "cross_version_binary_delta",
        "report_id": report_id,
        "old_build_id": old_build_id,
        "new_build_id": new_build_id,
        "old_sha256": old_sha,
        "new_sha256": new_sha,
        "summary": summary,
        "old_only": old_only,
        "new_only": new_only,
        "changed": changed,
        "note": (
            "This report compares exact ZIP/JAR entry bytes only. It proves "
            "archive-level delta provenance and makes no semantic claim about "
            "the meaning of changed bytecode."
        ),
    }


def write_cross_version_binary_delta(
    report: dict[str, Any],
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

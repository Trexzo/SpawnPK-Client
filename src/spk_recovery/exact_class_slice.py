"""Build deterministic, SHA-pinned private class slices for targeted decompilation.

Original JARs are read-only. This never accepts or changes recovery lineage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from zipfile import ZipFile, ZipInfo, ZIP_STORED


class ClassSliceError(ValueError):
    pass


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise ClassSliceError(code)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_class_entry(entry: str) -> None:
    _require(isinstance(entry, str) and entry.endswith(".class"),
             "INVALID_CLASS_ENTRY")
    _require(not entry.startswith("/") and "\\" not in entry,
             "INVALID_CLASS_ENTRY")
    parts = entry.split("/")
    _require(all(part and part not in (".", "..") and ":" not in part
                 for part in parts), "INVALID_CLASS_ENTRY")
    _require(bool(re.fullmatch(r"[A-Za-z0-9_$./-]+", entry)),
             "INVALID_CLASS_ENTRY")


def build_class_slice(
    original_jar: Path,
    out_jar: Path,
    *,
    original_sha256: str,
    class_entry: str,
    include_nested: bool = True,
) -> dict[str, Any]:
    """Reject changed binaries, duplicate input entries and output overwrite."""
    _validate_class_entry(class_entry)
    _require(
        isinstance(original_sha256, str)
        and bool(re.fullmatch(r"[0-9a-fA-F]{64}", original_sha256)),
        "INVALID_ORIGINAL_JAR_PIN",
    )
    original_jar, out_jar = Path(original_jar), Path(out_jar)
    _require(original_jar.is_file(), "ORIGINAL_JAR_MISSING")
    before = _sha256(original_jar)
    _require(before.lower() == original_sha256.lower(),
             "ORIGINAL_JAR_PIN_MISMATCH")
    nested_prefix = class_entry[:-6] + "$"
    content: dict[str, bytes] = {}
    with ZipFile(original_jar) as archive:
        chosen = [
            info for info in archive.infolist()
            if info.filename == class_entry
            or (include_nested and info.filename.startswith(nested_prefix)
                and info.filename.endswith(".class"))
        ]
        _require(any(info.filename == class_entry for info in chosen),
                 "ORIGINAL_CLASS_MISSING")
        _require(all(not info.is_dir() for info in chosen),
                 "CLASS_ENTRY_IS_DIRECTORY")
        _require(len({info.filename for info in chosen}) == len(chosen),
                 "DUPLICATE_SELECTED_CLASS_ENTRY")
        for info in chosen:
            _validate_class_entry(info.filename)
            data = archive.read(info)
            _require(len(data) >= 10 and data[:4] == b"\xca\xfe\xba\xbe",
                     "INVALID_CLASSFILE_MAGIC")
            content[info.filename] = data
    _require(_sha256(original_jar) == before,
             "ORIGINAL_JAR_CHANGED_DURING_READ")
    _require(original_jar.resolve() != out_jar.resolve(),
             "OUTPUT_EQUALS_ORIGINAL")
    out_jar.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out_jar.open("xb") as output:
            try:
                with ZipFile(output, "w", compression=ZIP_STORED) as archive:
                    for name in sorted(content):
                        info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                        info.compress_type = ZIP_STORED
                        info.create_system = 3
                        info.external_attr = 0o100644 << 16
                        archive.writestr(info, content[name])
            except BaseException:
                output.close()
                out_jar.unlink(missing_ok=True)
                raise
    except FileExistsError as exc:
        raise ClassSliceError("OUTPUT_ALREADY_EXISTS") from exc

    if _sha256(original_jar) != before:
        out_jar.unlink(missing_ok=True)
        raise ClassSliceError("ORIGINAL_JAR_CHANGED_AFTER_SLICE")
    return {
        "schema_version": 1,
        "kind": "private_original_class_slice",
        "research_only": True,
        "accepted_class_identities": 0,
        "original_jar_sha256": before,
        "slice_sha256": _sha256(out_jar),
        "included_class_count": len(content),
        "includes_nested": bool(include_nested),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("class_entry")
    parser.add_argument("out_jar", type=Path)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--exclude-nested", action="store_true")
    args = parser.parse_args()
    try:
        report = build_class_slice(
            args.original_jar, args.out_jar,
            original_sha256=args.original_sha256,
            class_entry=args.class_entry,
            include_nested=not args.exclude_nested,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (ClassSliceError, OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

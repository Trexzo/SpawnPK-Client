"""R387: bounded, read-only v309 original resource-companion verification.

Reads only two explicitly supplied owner-private local archives. No extraction,
mutation, execution, network access, class loading, or stage cleanup. JSON
results contain only aggregate counts and already-known whole-archive hashes.
"""
from __future__ import annotations
import argparse, hashlib, json, stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile

ORIGINAL_SHA = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
COMPANION_SHA = "9a6a23750bedd39f49563c54bbbf89a0214f40e7f8fd8e0b1c08ba3da863fde4"
MAX_ZIP_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 20000
MAX_MEMBER_UNCOMPRESSED = 128 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 512 * 1024 * 1024

class Refused(ValueError):
    """Sanitized, fail-closed rejection without disclosing archive member names."""

def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _safe(info) -> None:
    name = info.filename
    raw_name = info.orig_filename  # zipfile normalizes backslashes on Windows
    mode = stat.S_IFMT(info.external_attr >> 16)
    if (not name or raw_name != name or name.startswith("/") or "\\" in name or "\x00" in name
        or any(part in ("", ".", "..") for part in name.split("/"))
        or info.is_dir() or info.flag_bits & 1 or mode == stat.S_IFLNK
        or info.file_size > MAX_MEMBER_UNCOMPRESSED):
        raise Refused("UNSAFE_ARCHIVE_MEMBER")

def _inspect(path: Path, expected_sha: str) -> tuple[dict[str, str], int, int]:
    if (not path.is_file() or path.is_symlink()
        or path.stat().st_size > MAX_ZIP_BYTES
        or len(expected_sha) != 64
        or any(x not in "0123456789abcdef" for x in expected_sha)):
        raise Refused("UNSAFE_INPUT_OR_PIN")
    if file_sha256(path) != expected_sha:
        raise Refused("PIN_MISMATCH")
    resources = {}
    count_class = 0
    total_size = 0
    try:
        with ZipFile(path, "r") as archive:
            members = archive.infolist()
            if len(members) > MAX_MEMBERS:
                raise Refused("TOO_MANY_MEMBERS")
            seen = set()
            for info in members:
                _safe(info)
                if info.filename in seen:
                    raise Refused("DUPLICATE_ARCHIVE_MEMBER")
                seen.add(info.filename)
                total_size += info.file_size
                if total_size > MAX_TOTAL_UNCOMPRESSED:
                    raise Refused("UNCOMPRESSED_LIMIT")
                if info.filename.endswith(".class"):
                    count_class += 1
                    continue
                h = hashlib.sha256()
                consumed = 0
                with archive.open(info, "r") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        consumed += len(chunk)
                        if consumed > info.file_size or consumed > MAX_MEMBER_UNCOMPRESSED:
                            raise Refused("MEMBER_LENGTH_DRIFT")
                        h.update(chunk)
                if consumed != info.file_size:
                    raise Refused("MEMBER_LENGTH_DRIFT")
                resources[info.filename] = h.hexdigest()
    except (BadZipFile, RuntimeError, OSError, EOFError) as exc:
        raise Refused("UNREADABLE_ARCHIVE") from exc
    return resources, count_class, len(members)

def verify(original: Path, companion: Path, *,
           original_sha: str = ORIGINAL_SHA,
           companion_sha: str = COMPANION_SHA,
           expected_classes: int = 10502,
           expected_resources: int = 419) -> dict:
    if original.resolve(strict=False) == companion.resolve(strict=False):
        raise Refused("IDENTICAL_INPUT_PATHS")
    original_resources, original_classes, original_entries = _inspect(original, original_sha)
    companion_resources, companion_classes, companion_entries = _inspect(companion, companion_sha)
    if original_classes != expected_classes or len(original_resources) != expected_resources:
        raise Refused("ORIGINAL_ENTRY_COUNT_DRIFT")
    if companion_classes != 0 or companion_entries != expected_resources:
        raise Refused("COMPANION_NOT_RESOURCE_ONLY")
    if original_resources != companion_resources:
        raise Refused("RESOURCE_NAME_OR_BYTES_DRIFT")
    return {
        "status": "R387_RESOURCE_PRESERVATION_PASS",
        "original_archive_sha256": original_sha,
        "companion_archive_sha256": companion_sha,
        "original_entries": original_entries,
        "original_class_entries": original_classes,
        "resource_entries_preserved": expected_resources,
        "companion_class_entries": 0,
        "runtime_equivalence_proven": False,
        "original_binary_parity_proven": False,
        "resource_classpath_accepted": False,
        "stage_cleanup_authorized": False,
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--companion", type=Path, required=True)
    parser.add_argument("--original-sha", default=ORIGINAL_SHA)
    parser.add_argument("--companion-sha", default=COMPANION_SHA)
    args = parser.parse_args(argv)
    try:
        result = verify(args.original, args.companion,
                        original_sha=args.original_sha, companion_sha=args.companion_sha)
    except (Refused, OSError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else "FILE_ACCESS_FAILED"
        print(json.dumps({"status": "R387_REFUSED", "reason": reason}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

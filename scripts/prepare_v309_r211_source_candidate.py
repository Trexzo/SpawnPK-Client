"""R351: stage the owner-private R211 v309 Java candidate without publishing it.

This is a private *candidate* tree, never recovered-source/v309 or a clean build.
The external CFR source has renamed/missing original declarations and edited
configuration. Pin the complete archive, verify its inner file manifest and
retain every source byte. The caller owns the private output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path
from zipfile import ZipFile, BadZipFile

R211_SHA256 = "3f8ade7a37a1c8fe21dea367cf48660418c25a4905d943fe9358aa8846c275f0"
R211_JAVA_COUNT = 1275
ORIGINAL_R315_JAVA_COUNT = 1277
MAX_UNCOMPRESSED = 32 * 1024 * 1024
MAX_MEMBER = 4 * 1024 * 1024
MAX_MEMBERS = 1500
OBF_CLASS_NAME = re.compile(r"(?:^|/)Class[0-9]+\.java$")
OBF_FIELD = re.compile(r"\bfield[0-9]+\b")
OBF_METHOD = re.compile(r"\bmethod[0-9]+\b")
OBF_TYPE = re.compile(r"\bClass[0-9]+\b")

class CandidateRefused(ValueError):
    pass

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def archive_digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()

def _read_candidate(path: Path, expected_sha: str, expected_count: int):
    if path.is_symlink() or not path.is_file():
        raise CandidateRefused("ARCHIVE_MISSING_OR_SYMLINK")
    if archive_digest(path) != expected_sha:
        raise CandidateRefused("ARCHIVE_SHA256_NOT_PINNED")
    with ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            raise CandidateRefused("ARCHIVE_MEMBER_BUDGET")
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise CandidateRefused("DUPLICATE_ZIP_ENTRY")
        if len(names) != len(set(name.casefold() for name in names)):
            raise CandidateRefused("WINDOWS_PATH_COLLISION")
        if "PRIVATE_SOURCE_SHA256_MANIFEST.json" not in names:
            raise CandidateRefused("MISSING_INNER_MANIFEST")
        sources = {}
        total_bytes = 0
        for item in infos:
            name = item.filename
            parts = name.split("/")
            if (not name or name.startswith("/") or "\\" in name
                or any(part in ("", ".", "..") for part in parts)
                or (len(parts[0]) > 1 and parts[0][1] == ":")):
                raise CandidateRefused("UNSAFE_MEMBER_PATH")
            mode = item.external_attr >> 16
            if stat.S_IFMT(mode) == stat.S_IFLNK:
                raise CandidateRefused("SYMLINK_ARCHIVE_MEMBER")
            if item.flag_bits & 1:
                raise CandidateRefused("ENCRYPTED_MEMBER")
            if item.is_dir():
                raise CandidateRefused("UNEXPECTED_DIRECTORY_ENTRY")
            if item.file_size > MAX_MEMBER:
                raise CandidateRefused("OVERSIZED_ARCHIVE_MEMBER")
            total_bytes += item.file_size
            if total_bytes > MAX_UNCOMPRESSED:
                raise CandidateRefused("UNCOMPRESSED_BUDGET")
            if name == "PRIVATE_SOURCE_SHA256_MANIFEST.json":
                continue
            if not name.startswith("src/") or not name.endswith(".java"):
                raise CandidateRefused("UNEXPECTED_NON_SOURCE_ENTRY")
            with archive.open(item) as reader:
                data = reader.read(MAX_MEMBER + 1)
            if len(data) != item.file_size:
                raise CandidateRefused("INCOMPLETE_SOURCE_ENTRY")
            sources[name[4:]] = data
        if len(sources) != expected_count:
            raise CandidateRefused("JAVA_SOURCE_COUNT_MISMATCH")
        raw = archive.read("PRIVATE_SOURCE_SHA256_MANIFEST.json")
        manifest = json.loads(raw.decode("utf-8-sig"))
        if (set(manifest) != {"count", "files"} or
            manifest["count"] != expected_count or
            not isinstance(manifest["files"], dict) or
            set(manifest["files"]) != set(sources)):
            raise CandidateRefused("INNER_MANIFEST_FILE_SET_MISMATCH")
        for name, data in sources.items():
            if digest(data) != manifest["files"][name]:
                raise CandidateRefused("SOURCE_SHA_MISMATCH")
        return sources

def prepare_candidate(archive_path: Path, output: Path,
                      *, expected_sha=R211_SHA256,
                      expected_count=R211_JAVA_COUNT):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise CandidateRefused("OUTPUT_MUST_BE_NEW")
    sources = _read_candidate(Path(archive_path), expected_sha, expected_count)
    files = []
    tree_hash = hashlib.sha256()
    for name, data in sorted(sources.items()):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CandidateRefused("SOURCE_NOT_UTF8") from exc
        relative = name.encode("utf-8")
        tree_hash.update(len(relative).to_bytes(4, "big"))
        tree_hash.update(relative)
        tree_hash.update(len(data).to_bytes(8, "big"))
        tree_hash.update(data)
        files.append({
            "path": name,
            "bytes": len(data),
            "sha256": digest(data),
            "class_number_filename": bool(OBF_CLASS_NAME.search(name)),
            "has_field_number": bool(OBF_FIELD.search(text)),
            "has_method_number": bool(OBF_METHOD.search(text)),
            "has_class_number_reference": bool(OBF_TYPE.search(text)),
        })
    summary = {
        "status": "PRIVATE_V309_SOURCE_CANDIDATE_STAGED_UNVERIFIED",
        "source_archive": "R211_COMPLETE_SOURCE_PRIVATE",
        "source_archive_sha256": expected_sha,
        "java_files": len(files),
        "comparison_r315_manifest_java_files": ORIGINAL_R315_JAVA_COUNT,
        "count_delta_from_r315": ORIGINAL_R315_JAVA_COUNT - len(files),
        "source_tree_sha256": tree_hash.hexdigest(),
        "readability": {
            "class_number_filename_files": sum(x["class_number_filename"] for x in files),
            "files_with_field_number": sum(x["has_field_number"] for x in files),
            "files_with_method_number": sum(x["has_method_number"] for x in files),
            "files_with_class_number_reference": sum(x["has_class_number_reference"] for x in files),
        },
        "verified_original_v309_semantic_source": False,
        "buildable_client": False,
        "publishable_recovered_source": False,
        "exact_r315_source_tree_match": False,
        "source_files": files,
    }
    output.mkdir(parents=True, exist_ok=False)
    for name, data in sources.items():
        destination = output / "src" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (output / "PRIVATE_CANDIDATE_MANIFEST.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--new-private-output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = prepare_candidate(args.archive, args.new_private_output)
    except (CandidateRefused, BadZipFile, OSError, ValueError) as exc:
        print(json.dumps({"status": "R351_SOURCE_INTAKE_BLOCKED", "reason": str(exc)}))
        return 2
    # Keep private source paths and symbols in the local manifest only.
    print(json.dumps({key: report[key] for key in report if key != "source_files"},
                     indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())

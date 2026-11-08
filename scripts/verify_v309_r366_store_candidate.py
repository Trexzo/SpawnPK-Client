"""R366: verify private source-archive provenance without publishing private Java.

Static SHA/content check only. This program does not execute game code or prove
crash consistency, runtime compatibility, GUI behavior, or original-JAR parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import stat
from pathlib import Path
from zipfile import BadZipFile, ZipFile

OWNER = "rs/gui/loadouts/io/LoadoutStore.java"
COUNT = 1277
OLD_MANIFEST = "PRIVATE_R365_SERIALIZER_COMPATIBILITY_MANIFEST.json"
NEW_MANIFEST = "PRIVATE_R366_READABILITY_MANIFEST.json"
NEW_STATUS = "R366_PRIVATE_LOADOUT_STORE_ATOMIC_REPLACEMENT_CANDIDATE"

class Refused(ValueError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def inspect(path: Path, pin: str, manifest_name: str, count: int = COUNT):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or file_sha(path) != pin:
        raise Refused("SOURCE_ARCHIVE_SHA_DRIFT")
    with ZipFile(path) as archive:
        members = archive.infolist()
        names = [entry.filename for entry in members]
        if (len(members) != count + 1 or manifest_name not in names or
                len(set(names)) != len(names) or len(set(n.casefold() for n in names)) != len(names)):
            raise Refused("UNEXPECTED_ARCHIVE_MEMBERS")
        payloads = {}
        total = 0
        for item in members:
            if item.filename == manifest_name:
                if item.file_size > 300_000 or item.flag_bits & 1:
                    raise Refused("UNSAFE_MANIFEST")
                continue
            name = item.filename
            parts = name.split("/")
            if (not name.startswith("source/") or not name.endswith(".java") or
                    any(p in ("", ".", "..") for p in parts) or "\\" in name or
                    item.is_dir() or item.flag_bits & 1 or
                    stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK or
                    item.file_size > 4_000_000):
                raise Refused("UNSAFE_JAVA_MEMBER")
            total += item.file_size
            if total > 24_000_000:
                raise Refused("SOURCE_BYTE_BUDGET_EXCEEDED")
            raw = archive.read(item)
            if len(raw) != item.file_size:
                raise Refused("TRUNCATED_SOURCE_MEMBER")
            raw.decode("utf-8")
            payloads[name[7:]] = sha(raw)
        report = json.loads(archive.read(manifest_name))
        if (not isinstance(report, dict) or report.get("source_count") != count or
                not isinstance(report.get("source_sha256"), dict) or
                report["source_sha256"] != payloads or len(payloads) != count):
            raise Refused("SOURCE_MANIFEST_MISMATCH")
        return payloads, report

def evaluate(prior: Path, candidate: Path, witness: dict, *, count=COUNT):
    required = {"prior_source_archive_sha256", "new_source_archive_sha256",
                "prior_owner_sha256", "new_owner_sha256", "source_count",
                "candidate_jar_sha256"}
    if set(witness) != required or witness["source_count"] != count:
        raise Refused("WITNESS_SCHEMA_MISMATCH")
    before, _ = inspect(prior, witness["prior_source_archive_sha256"], OLD_MANIFEST, count)
    after, report = inspect(candidate, witness["new_source_archive_sha256"], NEW_MANIFEST, count)
    changed = sorted(path for path in before if before[path] != after.get(path))
    if (set(before) != set(after) or changed != [OWNER] or
            before[OWNER] != witness["prior_owner_sha256"] or
            after[OWNER] != witness["new_owner_sha256"]):
        raise Refused("UNEXPECTED_SOURCE_DIFF")
    if (report.get("status") != NEW_STATUS or
            report.get("changed_source_paths") != [OWNER] or
            report.get("prior_source_sha256") != before[OWNER] or
            report.get("new_source_sha256") != after[OWNER] or
            report.get("private_source_release_approved") is not False or
            report.get("original_v309_binary_parity") != "NOT_TESTED" or
            report.get("live_client_acceptance") != "NOT_TESTED"):
        raise Refused("RELEASE_GATE_OR_RECEIPT_DRIFT")
    return {"status": "R366_STATIC_SOURCE_PROVENANCE_PASS",
            "source_count": count, "changed_source_paths": changed,
            "original_v309_binary_parity": "NOT_TESTED",
            "live_client_acceptance": "NOT_TESTED",
            "private_source_release_approved": False}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r365-private-source", required=True, type=Path)
    parser.add_argument("--r366-private-source", required=True, type=Path)
    parser.add_argument("--witness", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        evidence = json.loads(args.witness.read_text("utf-8"))
        verdict = evaluate(args.r365_private_source, args.r366_private_source, evidence)
    except (ValueError, OSError, UnicodeError, BadZipFile, KeyError, TypeError) as error:
        print(json.dumps({"status":"R366_STATIC_SOURCE_PROVENANCE_REFUSED", "reason": str(error)}))
        return 2
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

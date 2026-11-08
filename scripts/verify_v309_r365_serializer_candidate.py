"""R365 fail-closed one-source archive delta verifier. No private Java is emitted."""
from __future__ import annotations
import argparse
import hashlib
import json
import stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile

OLD_ARCHIVE_SHA = "b3f3073f23b49405fa591adff8e7e9ee177397eab1df24b76bb36427e5607bcc"
NEW_ARCHIVE_SHA = "671a627540009372ea2af45d19c239fce7953c34fe3a613372570715d069ac98"
OLD_MANIFEST = "PRIVATE_R364_READABILITY_MANIFEST.json"
NEW_MANIFEST = "PRIVATE_R365_SERIALIZER_COMPATIBILITY_MANIFEST.json"
OWNER = "rs/gui/loadouts/io/LoadoutSerializer.java"
OLD_OWNER_SHA = "91d89f75a9992fada787cc9615e9d4144497ba06f30cbd0ae0f50e7328da06cc"
NEW_OWNER_SHA = "9fb79da5af7812cf373f218b228d9794beb03c3411cb5de37cac1481f9c8f3a0"
SOURCE_COUNT = 1277

class Refused(ValueError):
    pass

def sha(data):
    return hashlib.sha256(data).hexdigest()

def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def inspect(path, expected_sha, manifest_name, count):
    path = Path(path)
    if (not path.is_file() or path.is_symlink() or
            path.stat().st_size > 40000000 or file_sha(path) != expected_sha):
        raise Refused("ARCHIVE_IDENTITY_MISMATCH")
    with ZipFile(path) as archive:
        info = archive.infolist()
        names = [x.filename for x in info]
        if (len(info) != count + 1 or names.count(manifest_name) != 1 or
                len(names) != len(set(names)) or
                len(names) != len({x.casefold() for x in names})):
            raise Refused("UNEXPECTED_ARCHIVE_MEMBERS")
        manifest_info = archive.getinfo(manifest_name)
        if manifest_info.is_dir() or manifest_info.file_size > 200000:
            raise Refused("INVALID_MANIFEST")
        manifest = json.loads(archive.read(manifest_name))
        pins = manifest.get("source_sha256")
        if (manifest.get("source_count") != count or not isinstance(pins, dict)
                or len(pins) != count):
            raise Refused("MANIFEST_CENSUS_CHANGED")
        actual = {}
        budget = 0
        for entry in info:
            if entry.filename == manifest_name:
                continue
            name = entry.filename
            if (not name.startswith("source/") or not name.endswith(".java") or
                    "\\" in name or any(p in ("", ".", "..") for p in name.split("/")) or
                    entry.is_dir() or entry.flag_bits & 1 or
                    stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK or
                    entry.file_size > 4000000):
                raise Refused("UNSAFE_ARCHIVE_MEMBER")
            budget += entry.file_size
            if budget > 24000000:
                raise Refused("SOURCE_BUDGET_EXCEEDED")
            actual[name[7:]] = sha(archive.read(entry))
        if actual != pins:
            raise Refused("SOURCE_HASH_CENSUS_CHANGED")
    return actual, manifest

def verify_pair(old, new, *, old_sha=OLD_ARCHIVE_SHA, new_sha=NEW_ARCHIVE_SHA,
                old_manifest=OLD_MANIFEST, new_manifest=NEW_MANIFEST,
                count=SOURCE_COUNT, owner=OWNER,
                old_owner=OLD_OWNER_SHA, new_owner=NEW_OWNER_SHA):
    prior, _ = inspect(old, old_sha, old_manifest, count)
    current, receipt = inspect(new, new_sha, new_manifest, count)
    changed = [p for p in sorted(prior) if prior[p] != current.get(p)]
    if (set(prior) != set(current) or changed != [owner] or
            prior.get(owner) != old_owner or current.get(owner) != new_owner):
        raise Refused("SINGLE_EXPECTED_SOURCE_DELTA_MISMATCH")
    if (receipt.get("changed_source_files") != [owner] or
            receipt.get("old_owner_sha256") != old_owner or
            receipt.get("new_owner_sha256") != new_owner or
            receipt.get("old_source_zip_sha256") != old_sha or
            receipt.get("serialized_format_changed") is not False or
            receipt.get("private_source_release_approved") is not False or
            receipt.get("original_v309_binary_parity") != "NOT_TESTED" or
            receipt.get("real_game_runtime") != "NOT_TESTED"):
        raise Refused("UNTRUSTED_PRIVATE_RECEIPT")
    return {"status":"R365_ONE_SOURCE_DELTA_VERIFIED", "changed_source_files":1,
            "source_count":count, "original_v309_binary_parity":"NOT_TESTED",
            "original_game_runtime":"NOT_TESTED", "release_approved":False}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r364-private-source", required=True, type=Path)
    p.add_argument("--r365-private-source", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        result = verify_pair(args.r364_private_source, args.r365_private_source)
    except (Refused, OSError, ValueError, KeyError, BadZipFile) as e:
        print(json.dumps({"status":"R365_REFUSED","reason":str(e)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

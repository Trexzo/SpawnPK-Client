"""Public-safe, offline SHA source-archive witness for v309 R370 -> R371.
Synthetic CI only: this never executes Java or publishes recovered private source.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile

PREVIOUS = "PRIVATE_R370_READABILITY_MANIFEST.json"
CURRENT = "PRIVATE_R371_READABILITY_MANIFEST.json"
OWNERS = ("rs/gui/loadouts/LoadoutFolders.java",
          "rs/gui/loadouts/io/LoadoutStore.java")
COUNT = 1277

class Refused(ValueError):
    pass

def sha(data):
    return hashlib.sha256(data).hexdigest()

def hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None

def inspect(path, pinned_hash, manifest_name, count):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000_000:
        raise Refused("INVALID_PRIVATE_ARCHIVE")
    if hash_file(path) != pinned_hash:
        raise Refused("ARCHIVE_SHA_MISMATCH")
    with ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if (len(names) != count + 1 or manifest_name not in names or
            len(names) != len(set(names)) or len(names) != len(set(n.casefold() for n in names))):
            raise Refused("SOURCE_FILE_SET_CHANGED")
        meta = json.loads(z.read(manifest_name))
        pins = meta.get("source_sha256")
        if (meta.get("source_count") != count or not isinstance(pins, dict)
            or len(pins) != count or any(not digest(x) for x in pins.values())):
            raise Refused("MANIFEST_SOURCE_HASHES_INVALID")
        found = {}
        size = 0
        for item in infos:
            if item.filename == manifest_name:
                if item.file_size > 3_000_000:
                    raise Refused("MANIFEST_TOO_LARGE")
                continue
            name = item.filename
            if (not name.startswith("source/") or not name.endswith(".java") or
                "\\" in name or any(x in ("", ".", "..") for x in name.split("/")) or
                item.is_dir() or item.flag_bits & 1 or
                stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK or
                item.file_size > 4_000_000):
                raise Refused("UNSAFE_JAVA_SOURCE_MEMBER")
            size += item.file_size
            if size > 24_000_000:
                raise Refused("SOURCE_SIZE_BUDGET")
            data = z.read(item)
            relative = name[7:]
            if len(data) != item.file_size or sha(data) != pins.get(relative):
                raise Refused("JAVA_SOURCE_SHA_DRIFT")
            found[relative] = sha(data)
        if set(found) != set(pins):
            raise Refused("SOURCE_MANIFEST_PATH_DRIFT")
        return found, meta

def verify(before, after, witness, *, count=COUNT):
    expected = {"source_count", "previous_zip_sha256", "candidate_zip_sha256",
        "previous_owner_sha256", "candidate_owner_sha256", "candidate_jar_sha256",
        "changed_paths", "multi_file_transaction_proven", "power_loss_durability_tested",
        "original_game_runtime_tested", "private_source_release_approved"}
    if not isinstance(witness, dict) or set(witness) != expected:
        raise Refused("UNEXPECTED_WITNESS_SCHEMA")
    if (witness["source_count"] != count or witness["changed_paths"] != list(OWNERS) or
        not isinstance(witness["previous_owner_sha256"], dict) or
        not isinstance(witness["candidate_owner_sha256"], dict) or
        set(witness["previous_owner_sha256"]) != set(OWNERS) or
        set(witness["candidate_owner_sha256"]) != set(OWNERS) or
        any(witness[k] is not False for k in ("multi_file_transaction_proven",
            "power_loss_durability_tested", "original_game_runtime_tested",
            "private_source_release_approved")) or
        any(not digest(witness[k]) for k in ("previous_zip_sha256",
            "candidate_zip_sha256", "candidate_jar_sha256")) or
        any(not digest(v) for key in ("previous_owner_sha256",
            "candidate_owner_sha256") for v in witness[key].values())):
        raise Refused("INVALID_WITNESS")
    old, _ = inspect(before, witness["previous_zip_sha256"], PREVIOUS, count)
    new, receipt = inspect(after, witness["candidate_zip_sha256"], CURRENT, count)
    if set(old) != set(new) or sorted(k for k in old if old[k] != new[k]) != list(OWNERS):
        raise Refused("UNEXPECTED_SOURCE_DELTA")
    if (any(old[p] != witness["previous_owner_sha256"][p] or
            new[p] != witness["candidate_owner_sha256"][p] for p in OWNERS) or
        receipt.get("changed_files") != list(OWNERS) or
        receipt.get("previous_r370_source_zip_sha256") != witness["previous_zip_sha256"] or
        receipt.get("same_source_built_jar_sha256") != witness["candidate_jar_sha256"] or
        receipt.get("private_source_release_approved") is not False or
        receipt.get("multi_file_transaction") != "NOT_IMPLEMENTED" or
        receipt.get("power_loss_durability") != "NOT_TESTED" or
        receipt.get("original_client_runtime") != "NOT_TESTED"):
        raise Refused("OWNER_OR_RELEASE_GATE_MISMATCH")
    return {"status": "R371_PRIVATE_SOURCE_DELTA_VERIFIED",
        "java_sources": len(old), "changed_paths": list(OWNERS),
        "source_integrity_verified": True, "multi_file_transaction_proven": False,
        "power_loss_durability_tested": False, "original_game_runtime_tested": False,
        "private_source_release_approved": False}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r370-private-source", required=True, type=Path)
    p.add_argument("--r371-private-source", required=True, type=Path)
    p.add_argument("--witness", required=True, type=Path)
    a = p.parse_args(argv)
    try:
        result = verify(a.r370_private_source, a.r371_private_source,
                        json.loads(a.witness.read_text("utf-8")))
    except (Refused, KeyError, OSError, ValueError, BadZipFile) as error:
        print(json.dumps({"status": "R371_REFUSED", "reason": str(error)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

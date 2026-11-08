"""R368: SHA-pinned, source-only provenance verifier for a PRIVATE candidate.

This program never runs original game code, private client code, network calls,
or live user data. It is not proof of GUI rendering, game parity or power loss.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile

OWNERS = (
    "rs/gui/loadouts/LoadoutsPanel.java",
    "rs/gui/loadouts/io/LoadoutStore.java",
)
COUNT = 1277
OLD_MANIFEST = "PRIVATE_R367_READABILITY_MANIFEST.json"
NEW_MANIFEST = "PRIVATE_R368_READABILITY_MANIFEST.json"
STATUS = "R368_PRIVATE_LOADOUT_LOCK_GUI_CANDIDATE"

class Refused(ValueError): pass

def sha(data): return hashlib.sha256(data).hexdigest()

def file_sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1_048_576), b""):
            h.update(part)
    return h.hexdigest()

def inspect(path: Path, pin: str, manifest: str, *, count=COUNT):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or file_sha(path) != pin:
        raise Refused("SOURCE_ARCHIVE_SHA_MISMATCH")
    with ZipFile(path) as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        if (len(members) != count+1 or names.count(manifest) != 1 or
                len(names) != len(set(names)) or len(names) != len(set(n.casefold() for n in names))):
            raise Refused("SOURCE_ARCHIVE_MEMBER_SET_MISMATCH")
        digests = {}
        budget = 0
        for member in members:
            if member.filename == manifest:
                if member.file_size > 300_000 or member.flag_bits & 1:
                    raise Refused("UNSAFE_PRIVATE_MANIFEST")
                continue
            path_name = member.filename
            components = path_name.split("/")
            if (not path_name.startswith("source/") or not path_name.endswith(".java") or
                    "\\" in path_name or any(x in ("", ".", "..") for x in components) or
                    member.is_dir() or member.flag_bits & 1 or
                    stat.S_IFMT(member.external_attr >> 16) == stat.S_IFLNK or
                    member.file_size > 4_000_000):
                raise Refused("UNSAFE_PRIVATE_JAVA_PATH")
            budget += member.file_size
            if budget > 24_000_000:
                raise Refused("JAVA_BYTE_BUDGET_EXCEEDED")
            raw = archive.read(member)
            if len(raw) != member.file_size:
                raise Refused("PRIVATE_SOURCE_TRUNCATED")
            raw.decode("utf-8")
            digests[path_name[7:]] = sha(raw)
        evidence = json.loads(archive.read(manifest))
        if (not isinstance(evidence, dict) or evidence.get("source_count") != count or
                evidence.get("source_sha256") != digests or len(digests) != count):
            raise Refused("PRIVATE_SOURCE_MANIFEST_DRIFT")
        return digests, evidence

def evaluate(prior: Path, candidate: Path, witness: dict, *, count=COUNT):
    required={"prior_source_archive_sha256", "new_source_archive_sha256",
              "prior_owner_sha256", "new_owner_sha256", "source_count",
              "candidate_jar_sha256"}
    if not isinstance(witness, dict) or set(witness) != required or witness.get("source_count") != count:
        raise Refused("WITNESS_SCHEMA_DRIFT")
    for key in ("prior_owner_sha256","new_owner_sha256"):
        if not isinstance(witness[key],dict) or set(witness[key])!=set(OWNERS):
            raise Refused("OWNER_SOURCE_SCOPE_DRIFT")
    before, _ = inspect(prior,witness["prior_source_archive_sha256"],OLD_MANIFEST,count=count)
    after, report = inspect(candidate,witness["new_source_archive_sha256"],NEW_MANIFEST,count=count)
    changed = sorted(path for path in before if before[path] != after.get(path))
    if set(before) != set(after) or changed != list(OWNERS):
        raise Refused("EXACT_TWO_SOURCE_DIFF_REQUIRED")
    if (witness["prior_owner_sha256"] != {p:before[p] for p in OWNERS} or
            witness["new_owner_sha256"] != {p:after[p] for p in OWNERS}):
        raise Refused("DECLARING_OWNER_HASH_DRIFT")
    if (report.get("status") != STATUS or
            report.get("changed_source_paths") != list(OWNERS) or
            report.get("prior_owner_sha256") != witness["prior_owner_sha256"] or
            report.get("new_owner_sha256") != witness["new_owner_sha256"] or
            report.get("candidate_jar_sha256") != witness["candidate_jar_sha256"] or
            report.get("source_backed_store_assertions") != 44 or
            report.get("serializer_assertions_across_two_charsets") != 60 or
            report.get("cooperative_cross_jvm_lock_fixture") != "PASS_OFFLINE" or
            report.get("gui_failure_callback_fixture") != "PASS_OFFLINE_STUB" or
            report.get("original_gui_rendering") != "NOT_TESTED" or
            report.get("uncooperative_writer_exclusion") != "NOT_PROVEN" or
            report.get("crash_durability") != "NOT_TESTED" or
            report.get("original_v309_binary_parity") != "NOT_TESTED" or
            report.get("live_client_acceptance") != "NOT_TESTED" or
            report.get("private_source_release_approved") is not False):
        raise Refused("UNSUPPORTED_RELEASE_OR_RUNTIME_CLAIM")
    return {"status":"R368_STATIC_SOURCE_PROVENANCE_PASS",
            "source_count":count,"changed_source_paths":changed,
            "cooperative_cross_jvm_lock_fixture":"PASS_OFFLINE",
            "gui_failure_callback_fixture":"PASS_OFFLINE_STUB",
            "original_gui_rendering":"NOT_TESTED",
            "uncooperative_writer_exclusion":"NOT_PROVEN",
            "original_v309_binary_parity":"NOT_TESTED",
            "private_source_release_approved":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r367-private-source",type=Path,required=True)
    parser.add_argument("--r368-private-source",type=Path,required=True)
    parser.add_argument("--witness",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=evaluate(args.r367_private_source,args.r368_private_source,
                        json.loads(args.witness.read_text("utf-8")))
    except (Refused, ValueError, OSError, KeyError, TypeError, UnicodeError, BadZipFile) as failure:
        print(json.dumps({"status":"R368_STATIC_SOURCE_PROVENANCE_REFUSED","reason":str(failure)}))
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())

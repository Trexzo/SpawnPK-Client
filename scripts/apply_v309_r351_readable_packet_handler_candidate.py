"""R351: private, narrowly scoped readable Java source rename candidate.

Applies one *inferred* source type name to a SHA-verified R351 R211 stage:
rs.scriptpacket.Class260 -> rs.scriptpacket.AbstractScriptPacketHandler.
No original-JAR class identity is accepted; no raw Java is committed to Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

OLD = "Class260"
NEW = "AbstractScriptPacketHandler"
OLD_PATH = "rs/scriptpacket/Class260.java"
NEW_PATH = "rs/scriptpacket/AbstractScriptPacketHandler.java"
R211_SHA = "3f8ade7a37a1c8fe21dea367cf48660418c25a4905d943fe9358aa8846c275f0"
EXPECTED_FILES = 1275
EXPECTED_TOUCHES = 71
EXPECTED_OCCURRENCES = 144
NAME = re.compile(r"\bClass260\b")

class RenameRefused(ValueError):
    pass

def sha(data):
    return hashlib.sha256(data).hexdigest()

def transform(sources, expected_files=EXPECTED_FILES,
              expected_touches=EXPECTED_TOUCHES,
              expected_occurrences=EXPECTED_OCCURRENCES):
    if len(sources) != expected_files:
        raise RenameRefused("WRONG_CANDIDATE_SOURCE_FILE_SET")
    if OLD_PATH not in sources or NEW_PATH in sources:
        raise RenameRefused("MISSING_OR_DUPLICATE_SCRIPT_PACKET_BASE")
    original = sources[OLD_PATH].decode("utf-8")
    for required in ("public abstract class Class260 implements Module",
                     "void handlePacket()", "setPacket(Packet",
                     "setClient(Client"):
        if required not in original:
            raise RenameRefused("SCRIPT_PACKET_SOURCE_SHAPE_CHANGED")
    rewritten = {}
    touches = 0
    occurrences = 0
    for path, raw in sorted(sources.items()):
        if not isinstance(raw, bytes) or not isinstance(path, str):
            raise RenameRefused("INVALID_PRIVATE_SOURCE_ENTRY")
        text = raw.decode("utf-8")
        count = len(NAME.findall(text))
        if count:
            if (path != OLD_PATH and
                "import rs.scriptpacket.Class260;" not in text and
                "rs.scriptpacket.Class260" not in text and
                not path.startswith("rs/scriptpacket/") and
                path != "rs/debug/UiPacketDecoder.java"):
                raise RenameRefused("UNACCOUNTED_CROSS_PACKAGE_CLASS_REFERENCE")
            touches += 1
            occurrences += count
        replacement = NAME.sub(NEW, text).encode("utf-8")
        output_path = NEW_PATH if path == OLD_PATH else path
        if output_path in rewritten:
            raise RenameRefused("RENAME_DESTINATION_COLLISION")
        rewritten[output_path] = replacement
    if touches != expected_touches or occurrences != expected_occurrences:
        raise RenameRefused("RENAME_REFERENCE_WITNESS_CHANGED")
    if any(NAME.search(x.decode("utf-8")) for x in rewritten.values()):
        raise RenameRefused("OLD_REFERENCE_STILL_PRESENT")
    return rewritten, {
        "source_files": expected_files,
        "modified_java_files": touches,
        "changed_lexical_occurrences": occurrences,
        "from": "rs.scriptpacket.Class260",
        "to": "rs.scriptpacket.AbstractScriptPacketHandler",
        "candidate_name_not_original_identity": True,
        "original_v309_class_parity": "NOT_TESTED",
        "full_project_clean_compile": "NOT_TESTED",
    }

def load_verified_stage(stage):
    stage = Path(stage)
    f = stage / "PRIVATE_CANDIDATE_MANIFEST.json"
    if not f.is_file() or f.is_symlink() or stage.is_symlink():
        raise RenameRefused("R351_MANIFEST_MISSING")
    manifest = json.loads(f.read_text(encoding="utf-8"))
    records = manifest.get("source_files")
    if (manifest.get("source_archive_sha256") != R211_SHA or
        manifest.get("java_files") != EXPECTED_FILES or
        not isinstance(records, list) or len(records) != EXPECTED_FILES or
        manifest.get("publishable_recovered_source") is not False):
        raise RenameRefused("R351_SOURCE_PROVENANCE_NOT_PINNED")
    result = {}
    for record in records:
        name = record.get("path")
        if (not isinstance(name, str) or
            not name.endswith(".java") or
            "\\" in name or name.startswith("/") or
            ".." in name.split("/") or name in result):
            raise RenameRefused("R351_UNSAFE_SOURCE_MEMBER")
        p = stage / "src" / name
        if p.is_symlink() or not p.is_file():
            raise RenameRefused("R351_SOURCE_NOT_REGULAR")
        data = p.read_bytes()
        if len(data) != record.get("bytes") or sha(data) != record.get("sha256"):
            raise RenameRefused("R351_SOURCE_FILE_CHANGED")
        result[name] = data
    return result

def apply(stage, new_private_output):
    dest = Path(new_private_output)
    if dest.exists() or dest.is_symlink():
        raise RenameRefused("RENAME_OUTPUT_MUST_BE_NEW")
    sources = load_verified_stage(stage)
    out, witness = transform(sources)
    dest.mkdir(parents=True, exist_ok=False)
    for path, data in sorted(out.items()):
        target = dest / "src" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    report = {
        "status": "PRIVATE_V309_READABLE_RENAME_CANDIDATE_UNVERIFIED",
        "input_archive_sha256": R211_SHA,
        "semantic_candidate": witness,
        "verified_original_client_source": False,
        "publishable_source": False,
        "output_java_sha256": {k: sha(v) for k, v in sorted(out.items())},
    }
    (dest / "PRIVATE_SEMANTIC_RENAME_MANIFEST.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r351-private-stage", required=True, type=Path)
    parser.add_argument("--new-private-output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = apply(args.r351_private_stage, args.new_private_output)
    except (OSError, ValueError, UnicodeError, RenameRefused) as exc:
        print(json.dumps({"status": "PRIVATE_RENAME_REFUSED", "reason": str(exc)}))
        return 2
    print(json.dumps({
        "status": report["status"],
        "semantic_candidate": report["semantic_candidate"],
        "publishable_source": False,
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())

"""R361: reversible, SHA-pinned private v309 loadout model/store readability pass.

Public source/tool only; the 1,277 recovered private Java files never enter GitHub.
This changes Java identifiers, NOT binary behavior, serialization or author identity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

SOURCE_SHA = "31d4612bce93fc1ce30964a893d8df96d5feca7464569071daa4b2995024d5c4"
OLD_MANIFEST = "PRIVATE_R359_READABILITY_MANIFEST.json"
NEW_MANIFEST = "PRIVATE_R361_READABILITY_MANIFEST.json"
TOTAL = 1277
MAX_BYTES = 24_000_000

class Refused(ValueError):
    pass

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()

def identifiers(src: str):
    """Yield (identifier, char position) outside comments, char/string literals."""
    i = 0
    while i < len(src):
        if src.startswith("//", i):
            j = src.find("\n", i + 2)
            i = len(src) if j < 0 else j + 1
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j < 0: raise Refused("UNCLOSED_BLOCK_COMMENT")
            i = j + 2
        elif src[i] in ('"', "'"):
            if src.startswith('"""', i):
                raise Refused("JAVA_TEXT_BLOCK_NOT_SUPPORTED")
            quote = src[i]
            i += 1
            while i < len(src):
                if src[i] == "\\":
                    i += 2
                elif src[i] == quote:
                    i += 1
                    break
                elif src[i] in "\r\n":
                    raise Refused("UNTERMINATED_LITERAL")
                else:
                    i += 1
            else:
                raise Refused("UNTERMINATED_LITERAL")
        elif src[i].isalpha() or src[i] in "_$":
            begin = i
            i += 1
            while i < len(src) and (src[i].isalnum() or src[i] in "_$"):
                i += 1
            yield src[begin:i], begin
        else:
            i += 1

def census(sources: dict[str, bytes], tokens: set[str]) -> dict[str, dict[str, int]]:
    result = {token: {} for token in tokens}
    for path, raw in sources.items():
        counts: dict[str, int] = {}
        for token, _ in identifiers(raw.decode("utf-8")):
            if token in result: counts[token] = counts.get(token, 0) + 1
        for token, count in counts.items():
            result[token][path] = count
    return result

def verified_input(archive_path: Path, expected_sha: str = SOURCE_SHA,
                   expected_count: int = TOTAL) -> dict[str, bytes]:
    archive_path = Path(archive_path)
    if not archive_path.is_file() or archive_path.is_symlink() or sha_file(archive_path) != expected_sha:
        raise Refused("PRIVATE_R359_ARCHIVE_HASH_MISMATCH")
    with ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if (len(infos) != expected_count + 1 or OLD_MANIFEST not in names or
                len(names) != len(set(names)) or len(names) != len(set(n.casefold() for n in names))):
            raise Refused("SOURCE_FILE_SET_UNEXPECTED")
        manifest = json.loads(archive.read(OLD_MANIFEST))
        pins = manifest.get("source_sha256")
        if not isinstance(pins, dict) or manifest.get("source_count") != expected_count or len(pins) != expected_count:
            raise Refused("MANIFEST_COUNT_MISMATCH")
        source = {}
        total = 0
        for info in infos:
            name = info.filename
            if name == OLD_MANIFEST: continue
            components = name.split("/")
            if (not name.startswith("source/") or not name.endswith(".java") or
                    "\\" in name or any(c in ("", ".", "..") for c in components) or
                    info.is_dir() or info.flag_bits & 1 or
                    stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK or
                    info.file_size > 4_000_000):
                raise Refused("UNSAFE_SOURCE_MEMBER")
            total += info.file_size
            if total > MAX_BYTES: raise Refused("SOURCE_SIZE_BUDGET_EXCEEDED")
            data = archive.read(info)
            relative = name[7:]
            if len(data) != info.file_size or pins.get(relative) != sha(data):
                raise Refused("SOURCE_FILE_DIGEST_DRIFT")
            data.decode("utf-8")
            source[relative] = data
        if set(source) != set(pins): raise Refused("SOURCE_PATH_MANIFEST_DRIFT")
        return source

def apply(source: dict[str, bytes], witness: dict, *, expected_count=TOTAL,
          expected_archive_sha=SOURCE_SHA):
    if len(source) != expected_count or witness.get("source_count") != expected_count:
        raise Refused("SOURCE_COUNT_MISMATCH")
    if witness.get("source_archive_sha256") != expected_archive_sha:
        raise Refused("SOURCE_AUTHORITY_CHANGED")
    if set(witness) != {"source_archive_sha256", "source_count", "owner_sha256", "fields", "methods", "token_references"}:
        raise Refused("UNEXPECTED_WITNESS_SCHEMA")
    mapping = {**witness["fields"], **witness["methods"]}
    if (set(witness["fields"]) & set(witness["methods"]) or
            not mapping or len(mapping) != len(set(mapping.values())) or
            any(not re.fullmatch(r"(?:field|method)\d+", old) for old in mapping) or
            any(not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", new) for new in mapping.values())):
        raise Refused("UNSAFE_RENAME_MAPPING")
    for owner, pin in witness["owner_sha256"].items():
        if owner not in source or sha(source[owner]) != pin:
            raise Refused("DECLARING_OWNER_SHA_CHANGED")
    observed = census(source, set(mapping))
    if observed != witness["token_references"] or any(not occurrences for occurrences in observed.values()):
        raise Refused("REFERENCE_CENSUS_CHANGED")
    # Prevent accidentally binding a previously distinct identifier to another symbol.
    targets = set(mapping.values())
    existing = census(source, targets)
    if any(existing.values()):
        raise Refused("DESTINATION_IDENTIFIER_COLLISION")
    result = {path: raw.decode("utf-8") for path, raw in source.items()}
    changes = []
    for old, new in mapping.items():
        positions = {}
        for path, expected in observed[old].items():
            text = result[path]
            offsets = [at for token, at in identifiers(text) if token == old]
            if len(offsets) != expected: raise Refused("INTERMEDIATE_CENSUS_CHANGED")
            for at in reversed(offsets):
                text = text[:at] + new + text[at+len(old):]
            result[path] = text
            positions[path] = [at+i*(len(new)-len(old)) for i, at in enumerate(offsets)]
        changes.append((old, new, positions))
    backward = dict(result)
    for old, new, locations in reversed(changes):
        for path, offsets in locations.items():
            text = backward[path]
            for at in reversed(offsets):
                if text[at:at+len(new)] != new:
                    raise Refused("INVERSE_POSITION_DRIFT")
                text = text[:at] + old + text[at+len(new):]
            backward[path] = text
    if {path: text.encode("utf-8") for path, text in backward.items()} != source:
        raise Refused("NOT_BYTE_EXACTLY_REVERSIBLE")
    return {path: text.encode("utf-8") for path, text in result.items()}, sum(
        len(offsets) for _,_,loc in changes for offsets in loc.values())

def produce(private_source: Path, witness_file: Path, output: Path):
    output = Path(output)
    if output.exists() or output.is_symlink(): raise Refused("OUTPUT_ALREADY_EXISTS")
    witness = json.loads(Path(witness_file).read_text("utf-8"))
    source, edits = apply(verified_input(private_source), witness)
    report = {
        "status": "R361_PRIVATE_READABLE_JAVA_CANDIDATE",
        "source_count": len(source),
        "field_renames": len(witness["fields"]),
        "method_renames": len(witness["methods"]),
        "identifier_occurrences_changed": edits,
        "exact_inverse_passed": True,
        "original_v309_binary_parity": "NOT_TESTED",
        "private_source_release_approved": False,
        "source_sha256": {path:sha(raw) for path,raw in sorted(source.items())}
    }
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path, raw in sorted(source.items()): archive.writestr("source/"+path, raw)
        archive.writestr(NEW_MANIFEST, json.dumps(report,indent=2,sort_keys=True)+"\n")
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r359-private-source",required=True,type=Path)
    parser.add_argument("--witness",required=True,type=Path)
    parser.add_argument("--new-private-output",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        report=produce(args.r359_private_source,args.witness,args.new_private_output)
    except (OSError, Refused, ValueError, UnicodeError, BadZipFile, KeyError) as error:
        print(json.dumps({"status":"R361_REFUSED","reason":str(error)}))
        return 2
    print(json.dumps({k:v for k,v in report.items() if k != "source_sha256"},indent=2,sort_keys=True))
    return 0

if __name__ == "__main__": raise SystemExit(main())

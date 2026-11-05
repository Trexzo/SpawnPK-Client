"""R359: reproducible Java-aware, SHA-pinned v309 loadout UI readability pass.

Reads only the owner-private R358 candidate source ZIP. Java identifiers in
strings/comments are untouched. Names are inferred, not original-JAR parity.
Public GitHub CI uses synthetic sources; private Java never enters this repo.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import stat
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

SOURCE_SHA = "95f4319993bce5988d47d34f76709d96e72e8b0d59b319d406fa773be748cb68"
OLD_MANIFEST = "PRIVATE_R358_READABILITY_MANIFEST.json"
NEW_MANIFEST = "PRIVATE_R359_READABILITY_MANIFEST.json"
TOTAL = 1277

class Refused(ValueError):
    pass

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def identifiers(text):
    """Yield (Java identifier, start index); skip comments and quoted literals."""
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i + 2)
            i = n if j < 0 else j + 1
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                raise Refused("UNCLOSED_BLOCK_COMMENT")
            i = j + 2
            continue
        if c in ('"', "'"):
            if text.startswith('"""', i):
                raise Refused("TEXT_BLOCK_UNSUPPORTED_FOR_JAVA11")
            quote = c
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                if text[i] in "\r\n":
                    raise Refused("UNTERMINATED_JAVA_LITERAL")
                i += 1
            else:
                raise Refused("UNTERMINATED_JAVA_LITERAL")
            continue
        if c.isalpha() or c in "_$":
            start = i
            i += 1
            while i < n and (text[i].isalnum() or text[i] in "_$"):
                i += 1
            yield text[start:i], start
            continue
        i += 1

def references(sources, tokens):
    """One complete source lexical pass instead of one pass per symbol."""
    result = {symbol: {} for symbol in tokens}
    for path, raw in sources.items():
        counts = {}
        for word, _ in identifiers(raw.decode("utf-8")):
            if word in tokens:
                counts[word] = counts.get(word, 0) + 1
        for word, count in counts.items():
            result[word][path] = count
    return result

def replace_identifier(text, old, new):
    places = [i for word, i in identifiers(text) if word == old]
    changed = text
    for at in reversed(places):
        changed = changed[:at] + new + changed[at + len(old):]
    return changed, [at + k * (len(new) - len(old)) for k, at in enumerate(places)]

def undo_identifier(text, new, old, positions):
    for at in reversed(positions):
        if text[at:at + len(new)] != new:
            raise Refused("INVERSE_POSITION_CHANGED")
        text = text[:at] + old + text[at + len(new):]
    return text

def verified_input(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or sha_file(path) != SOURCE_SHA:
        raise Refused("R358_ARCHIVE_SHA_MISMATCH")
    with ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if (len(infos) != TOTAL + 1 or OLD_MANIFEST not in names or
                len(set(names)) != len(names) or
                len(set(name.casefold() for name in names)) != len(names)):
            raise Refused("UNEXPECTED_SOURCE_MEMBERS")
        manifest = json.loads(archive.read(OLD_MANIFEST))
        pins = manifest.get("source_sha256")
        if (manifest.get("source_count") != TOTAL or
                not isinstance(pins, dict) or len(pins) != TOTAL):
            raise Refused("SOURCE_MANIFEST_CHANGED")
        sources = {}
        total_bytes = 0
        for item in infos:
            name = item.filename
            if name == OLD_MANIFEST:
                continue
            parts = name.split("/")
            if (not name.startswith("source/") or not name.endswith(".java") or
                    "\\" in name or any(p in ("", ".", "..") for p in parts) or
                    item.is_dir() or item.flag_bits & 1 or
                    stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK or
                    item.file_size > 4000000):
                raise Refused("UNSAFE_JAVA_SOURCE_PATH")
            total_bytes += item.file_size
            if total_bytes > 24000000:
                raise Refused("SOURCE_BYTE_BUDGET")
            data = archive.read(item)
            relative = name[7:]
            if len(data) != item.file_size or sha(data) != pins.get(relative):
                raise Refused("JAVA_SOURCE_DIGEST_DRIFT")
            data.decode("utf-8")
            sources[relative] = data
        if set(sources) != set(pins):
            raise Refused("SOURCE_FILE_SET_DRIFT")
        return sources

def transform(source, witness, *, expected_count=TOTAL):
    if len(source) != expected_count or witness.get("source_count") != expected_count:
        raise Refused("SOURCE_COUNT_CHANGED")
    if witness.get("source_archive_sha256") != SOURCE_SHA:
        raise Refused("SOURCE_AUTHORITY_CHANGED")
    types = witness["types"]
    fields = witness["fields"]
    methods = witness["methods"]
    plan = [("type", Path(path).stem, name, path) for path, name in types.items()]
    plan += [("field", old, new, None) for old, new in fields.items()]
    plan += [("method", old, new, None) for old, new in methods.items()]
    for owner in types:
        if owner not in source or sha(source[owner]) != witness["owner_sha256"].get(owner):
            raise Refused("ORIGINAL_DECLARING_TYPE_CHANGED")
    observed = references(source, {item[1] for item in plan})
    if observed != witness["token_references"]:
        raise Refused("GLOBAL_JAVA_REFERENCE_CENSUS_CHANGED")
    result = {p: b.decode("utf-8") for p, b in source.items()}
    history = []
    for kind, old, new, owner in plan:
        new_path = None
        if kind == "type":
            if owner not in result:
                raise Refused("DECLARING_OWNER_MISSING")
            if old not in [word for word, _ in identifiers(result[owner])]:
                raise Refused("TYPE_DECLARATION_MISSING")
            new_path = owner[:-len(old) - 5] + new + ".java"
            if new_path in result:
                raise Refused("RENAMED_OWNER_COLLISION")
        witness_refs = observed.get(old, {})
        if not witness_refs:
            raise Refused("EMPTY_SYMBOL_REFERENCE_WITNESS")
        positions = {}
        for original_path, count in witness_refs.items():
            path = original_path
            if path not in result and path in types:
                old_type = Path(path).stem
                path = path[:-len(old_type) - 5] + types[path] + ".java"
            if path not in result:
                raise Refused("RENAMED_REFERENCE_PATH_MISSING")
            text, indices = replace_identifier(result[path], old, new)
            if len(indices) != count:
                raise Refused("INTERMEDIATE_SOURCE_REFERENCE_CHANGED")
            result[path] = text
            positions[new_path if path == owner else path] = indices
        if new_path:
            result[new_path] = result.pop(owner)
        history.append((old, new, owner, new_path, positions))
    backward = dict(result)
    for old, new, owner, new_path, positions in reversed(history):
        for path, indices in positions.items():
            backward[path] = undo_identifier(backward[path], new, old, indices)
        if new_path:
            backward[owner] = backward.pop(new_path)
    if {p: s.encode("utf-8") for p, s in backward.items()} != source:
        raise Refused("NOT_EXACTLY_REVERSIBLE")
    return {p: s.encode("utf-8") for p, s in result.items()}, history

def produce(input_zip, witness_file, output_zip):
    output_zip = Path(output_zip)
    if output_zip.exists() or output_zip.is_symlink():
        raise Refused("OUTPUT_MUST_BE_NEW")
    witness = json.loads(Path(witness_file).read_text("utf-8"))
    source, steps = transform(verified_input(input_zip), witness)
    changes = sum(len(indices) for *_, edits in steps for indices in edits.values())
    if len(source) != TOTAL or changes != 107:
        raise Refused("BOUNDED_RENAME_WITNESS_DRIFT")
    report = {
        "status": "R359_PRIVATE_READABLE_JAVA_CANDIDATE",
        "source_count": TOTAL,
        "class_renames": len(witness["types"]),
        "field_renames": len(witness["fields"]),
        "method_renames": len(witness["methods"]),
        "identifier_changes": changes,
        "exact_inverse_passed": True,
        "string_literals_and_comments_untouched": True,
        "source_archive_sha256": SOURCE_SHA,
        "original_v309_jar_parity": "NOT_TESTED",
        "source_milestone_publishable": False,
        "source_sha256": {p: sha(raw) for p, raw in sorted(source.items())}
    }
    with ZipFile(output_zip, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(source.items()):
            archive.writestr("source/" + name, raw)
        archive.writestr(NEW_MANIFEST, json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r358-private-source", type=Path, required=True)
    parser.add_argument("--witness", type=Path, required=True)
    parser.add_argument("--new-private-output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = produce(args.r358_private_source, args.witness, args.new_private_output)
    except (Refused, OSError, KeyError, ValueError, UnicodeError, BadZipFile) as error:
        print(json.dumps({"status": "R359_REFUSED", "reason": str(error)}))
        return 2
    print(json.dumps({k: v for k, v in report.items() if k != "source_sha256"},
                     indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

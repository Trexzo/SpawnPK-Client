"""R358 — owner-private complete v309 Java readability pass 7.

Transforms the SHA-pinned R357 *candidate* source tree; never accesses live
servers or original client installation. All names are inferred, not certified
original symbols. Private Java/JARs stay outside public GitHub and CI.
"""
from __future__ import annotations
import argparse, hashlib, json, re, stat, zipfile
from pathlib import Path

INPUT_SHA = "9cd9d3ccd2287d7f0fcd917b57c1e0148f803c930499ebac6ada6efe40b31c55"
INPUT_MANIFEST = "PRIVATE_R357_READABILITY_MANIFEST.json"
OUTPUT_MANIFEST = "PRIVATE_R358_READABILITY_MANIFEST.json"
SOURCE_COUNT = 1277
TYPES = [
    ("rs/definitions/Class42.java", "SceneObjectOverrideRecord"),
    ("rs/definitions/Class43.java", "SceneObjectOverrideRegistry"),
    ("rs/ui/components/Class99.java", "ComponentReorderListener"),
    ("rs/runelite/api/Class302.java", "EntityDrawCallback"),
    ("rs/gpu/Class113.java", "SkyboxColorSampler"),
    ("rs/util/Class80.java", "HeavyweightPopupFactory"),
    ("rs/gui/loadouts/dialogs/Class131.java", "CreateLoadoutActionListener"),
    ("rs/gui/loadouts/dialogs/Class140.java", "DismissLoadoutDialogListener"),
    ("rs/util/Class83.java", "ClassLoaderLookupBridge"),
]
MEMBERS = [
    ("field1196", "objectId"), ("field1197", "tileX"),
    ("field1198", "tileY"), ("field1199", "plane"),
    ("field1200", "objectRotation"), ("field1201", "objectType"),
    ("field1202", "overridesByLocation"),
    ("method1280", "onComponentReordered"),
    ("method1914", "sampleSkyboxColor"),
    ("method1785", "defineClassBytes"),
    ("method2468", "getMethodHandlesLookup"),
    ("method2476", "installMethodHandlesLookup"),
]

class Refused(ValueError):
    pass

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_input(path, *, expected_sha=INPUT_SHA):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise Refused("PRIVATE_INPUT_MISSING")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    if h.hexdigest() != expected_sha:
        raise Refused("INPUT_SHA_MISMATCH")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if (len(infos) != SOURCE_COUNT + 1
                or len(names) != len(set(names))
                or len(names) != len(set(n.casefold() for n in names))
                or INPUT_MANIFEST not in names):
            raise Refused("INVALID_MEMBER_SET")
        manifest = json.loads(archive.read(INPUT_MANIFEST))
        pins = manifest.get("source_sha256")
        if (manifest.get("source_count") != SOURCE_COUNT
                or not isinstance(pins, dict)
                or len(pins) != SOURCE_COUNT):
            raise Refused("SOURCE_MANIFEST_DRIFT")
        sources = {}
        total = 0
        for info in infos:
            if info.filename == INPUT_MANIFEST:
                continue
            name = info.filename
            parts = name.split("/")
            if (not name.startswith("source/") or not name.endswith(".java")
                    or any(segment in ("", ".", "..") for segment in parts)
                    or "\\" in name or info.is_dir()
                    or stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK
                    or info.flag_bits & 1 or info.file_size > 4000000):
                raise Refused("UNSAFE_ENTRY")
            total += info.file_size
            if total > 24000000:
                raise Refused("UNSAFE_TOTAL_SIZE")
            contents = archive.read(info)
            relative = name[7:]
            if len(contents) != info.file_size or sha(contents) != pins.get(relative):
                raise Refused("SOURCE_HASH_MISMATCH")
            contents.decode("utf8")
            sources[relative] = contents
        if set(sources) != set(pins):
            raise Refused("FILE_SET_MISMATCH")
        return sources

def occurrences(sources, term):
    pattern = re.compile(r"\b" + re.escape(term) + r"\b")
    return {path: len(pattern.findall(contents.decode("utf8")))
            for path, contents in sources.items()
            if pattern.search(contents.decode("utf8"))}

def substitute(text, old, new):
    pattern = re.compile(r"\b" + re.escape(old) + r"\b")
    fragments = []
    previous = 0
    position = 0
    positions = []
    for match in pattern.finditer(text):
        unchanged = text[previous:match.start()]
        fragments.extend((unchanged, new))
        position += len(unchanged)
        positions.append(position)
        position += len(new)
        previous = match.end()
    fragments.append(text[previous:])
    return "".join(fragments), positions

def inverse(text, positions, old, new):
    for at in reversed(positions):
        if text[at:at + len(new)] != new:
            raise Refused("REVERSE_POSITION_DRIFT")
        text = text[:at] + old + text[at + len(new):]
    return text

def transform(source, *, types=TYPES, members=MEMBERS,
              expected, owner_hashes, expected_count=SOURCE_COUNT):
    if len(source) != expected_count:
        raise Refused("WRONG_SOURCE_COUNT")
    result = dict(source)
    history = []
    for index, (owner, new) in enumerate(types):
        old = Path(owner).stem
        if owner not in result:
            raise Refused("MISSING_TYPE_OWNER_" + old)
        # Later owners may refer to a class renamed earlier; pin their
        # ORIGINAL R357 bytes, not their intermediate edited bytes.
        if sha(source[owner]) != owner_hashes.get(owner):
            raise Refused("OWNER_SHA_DRIFT_" + old)
        if not re.search(r"\b(?:class|interface|enum)\s+" + old + r"\b",
                         result[owner].decode("utf8")):
            raise Refused("DECLARATION_MISSING_" + old)
        new_owner = owner[:-len(old) - 5] + new + ".java"
        if new_owner in result:
            raise Refused("TYPE_PATH_COLLISION")
        found = occurrences(result, old)
        mapped = {}
        for original_path, count in expected.get(old, {}).items():
            rebased = original_path
            for previous_owner, previous_new in types[:index]:
                if rebased == previous_owner:
                    rebased = (previous_owner[:-len(Path(previous_owner).stem) - 5]
                               + previous_new + ".java")
            mapped[rebased] = count
        if found != mapped:
            raise Refused("TYPE_REFS_CHANGED_" + old)
        positions = {}
        for path in found:
            edited, points = substitute(result[path].decode("utf8"), old, new)
            result[path] = edited.encode("utf8")
            positions[new_owner if path == owner else path] = points
        result[new_owner] = result.pop(owner)
        history.append((old, new, owner, new_owner, positions))
    for old, new in members:
        found = occurrences(result, old)
        mapped = {}
        for original_path, count in expected.get(old, {}).items():
            rebased = original_path
            for owner, rename in types:
                if rebased == owner:
                    rebased = owner[:-len(Path(owner).stem) - 5] + rename + ".java"
            mapped[rebased] = count
        if found != mapped or not found:
            raise Refused("MEMBER_REFS_CHANGED_" + old)
        positions = {}
        for path in found:
            edited, points = substitute(result[path].decode("utf8"), old, new)
            result[path] = edited.encode("utf8")
            positions[path] = points
        history.append((old, new, None, None, positions))
    restored = dict(result)
    for old, new, owner, new_owner, positions in reversed(history):
        for path, points in positions.items():
            restored[path] = inverse(
                restored[path].decode("utf8"), points, old, new
            ).encode("utf8")
        if owner:
            restored[owner] = restored.pop(new_owner)
    if restored != source:
        raise Refused("NOT_BYTE_EXACT_REVERSAL")
    return result, history

def package(source_zip, output_zip, witness):
    output_zip = Path(output_zip)
    if output_zip.exists() or output_zip.is_symlink():
        raise Refused("REFUSE_OVERWRITE")
    result, history = transform(
        read_input(source_zip),
        expected=witness["expected_refs"],
        owner_hashes=witness["owner_hashes"]
    )
    edits = sum(sum(len(points) for points in locations.values())
                for *_, locations in history)
    if edits != 117 or len(result) != SOURCE_COUNT:
        raise Refused("TOTAL_SOURCE_WITNESS_DRIFT")
    manifest = {
        "status": "R358_PRIVATE_READABLE_CANDIDATE",
        "r357_input_sha256": INPUT_SHA,
        "source_count": SOURCE_COUNT,
        "class_renames": len(TYPES),
        "member_renames": len(MEMBERS),
        "identifier_edits": edits,
        "reversal_restores_all_1277_bytes": True,
        "semantic_authority": "INFERRED_NOT_ORIGINAL",
        "original_jar_parity": "NOT_TESTED",
        "source_milestone_publishable": False,
        "source_sha256": {p: sha(contents) for p, contents in sorted(result.items())}
    }
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for path, contents in sorted(result.items()):
            archive.writestr("source/" + path, contents)
        archive.writestr(OUTPUT_MANIFEST,
                         json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r357-private-source", type=Path, required=True)
    parser.add_argument("--new-private-output", type=Path, required=True)
    parser.add_argument("--witness", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        witness = json.loads(args.witness.read_text("utf8"))
        report = package(args.r357_private_source,
                         args.new_private_output, witness)
    except (Refused, OSError, ValueError, KeyError, UnicodeError,
            zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "R358_REFUSED", "reason": str(exc)}))
        return 2
    print(json.dumps({k: v for k, v in report.items() if k != "source_sha256"},
                     indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

"""R364: SHA-pinned reversible inferred naming for private v309 loadout actions.

This PUBLIC tool reads only an owner-provided private R363 source ZIP. It does
not ship Java client sources, run the game, contact servers or alter v312.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

SOURCE_SHA = '035837ec988fff706bbfb241e593277e8a5c39c448821982667a33b26f990450'
OLD_MANIFEST = 'PRIVATE_R363_READABILITY_MANIFEST.json'
NEW_MANIFEST = 'PRIVATE_R364_READABILITY_MANIFEST.json'
TOTAL = 1277
MAX_SOURCE_BYTES = 24_000_000
TYPES = {
    'rs/gui/loadouts/SaveLoadoutAction.java': 'DeleteLoadoutConfirmAction',
    'rs/gui/loadouts/MoveFolderDownAction.java': 'MoveLoadoutDownAction',
    'rs/gui/loadouts/MoveFolderUpAction.java': 'MoveLoadoutUpAction',
}
METHODS = {'saveLoadout': 'deleteLoadoutByName', 'moveFolder': 'swapLoadoutsInFolder'}
OWNERS = set(TYPES) | {'rs/gui/loadouts/LoadoutFolders.java'}
EXPECTED_EDITS = 14

class Refused(ValueError): pass

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def identifiers(src: str):
    """Iterate Java identifiers excluding comments and string/character literals."""
    i, n = 0, len(src)
    while i < n:
        if src.startswith('//', i):
            j = src.find('\n', i + 2)
            i = n if j < 0 else j + 1
        elif src.startswith('/*', i):
            j = src.find('*/', i + 2)
            if j < 0: raise Refused('UNCLOSED_COMMENT')
            i = j + 2
        elif src[i] in ('"', "'"):
            if src.startswith('"""', i): raise Refused('JAVA11_TEXT_BLOCK_UNSUPPORTED')
            quote = src[i]; i += 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    if i > n: raise Refused('UNTERMINATED_ESCAPE')
                elif src[i] == quote:
                    i += 1; break
                elif src[i] in '\r\n':
                    raise Refused('UNTERMINATED_LITERAL')
                else:
                    i += 1
            else: raise Refused('UNTERMINATED_LITERAL')
        elif src[i].isalpha() or src[i] in '_$':
            first = i; i += 1
            while i < n and (src[i].isalnum() or src[i] in '_$'):
                i += 1
            yield src[first:i], first
        else: i += 1

def census(source: dict[str, bytes], tokens: set[str]) -> dict[str, dict[str, int]]:
    result = {word: {} for word in tokens}
    for path, raw in source.items():
        counts = {}
        for word, _ in identifiers(raw.decode('utf-8')):
            if word in result: counts[word] = counts.get(word, 0) + 1
        for word, count in counts.items(): result[word][path] = count
    return result

def read_private_source(path: Path, expected_sha=SOURCE_SHA, expected_count=TOTAL):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or file_sha(path) != expected_sha:
        raise Refused('PRIVATE_INPUT_SHA_DRIFT')
    with ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if (len(infos) != expected_count + 1 or len(set(names)) != len(names)
                or len(set(x.casefold() for x in names)) != len(names)
                or OLD_MANIFEST not in names):
            raise Refused('ZIP_FILE_SET_DRIFT')
        manifest = json.loads(archive.read(OLD_MANIFEST))
        pins = manifest.get('source_sha256')
        if (manifest.get('source_count') != expected_count or not isinstance(pins, dict)
                or len(pins) != expected_count or manifest.get('exact_inverse_passed') is not True):
            raise Refused('SOURCE_MANIFEST_DRIFT')
        source, size = {}, 0
        for info in infos:
            name = info.filename
            if name == OLD_MANIFEST: continue
            components = name.split('/')
            if (not name.startswith('source/') or not name.endswith('.java')
                    or '\\' in name or any(c in ('', '.', '..') for c in components)
                    or info.is_dir() or info.flag_bits & 1
                    or stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK
                    or info.file_size > 4_000_000):
                raise Refused('UNSAFE_ZIP_MEMBER')
            size += info.file_size
            if size > MAX_SOURCE_BYTES: raise Refused('SOURCE_SIZE_BUDGET')
            data = archive.read(info)
            relative = name[7:]
            if len(data) != info.file_size or sha(data) != pins.get(relative):
                raise Refused('SOURCE_FILE_HASH_DRIFT')
            data.decode('utf-8')
            source[relative] = data
        if set(source) != set(pins): raise Refused('SOURCE_PATH_DRIFT')
        return source

def rename_source(source: dict[str, bytes], witness: dict, *, expected_count=TOTAL,
                  expected_sha=SOURCE_SHA):
    keys = {'source_archive_sha256', 'source_count', 'owner_sha256', 'types',
            'methods', 'token_references'}
    if set(witness) != keys: raise Refused('WITNESS_SCHEMA_DRIFT')
    if (witness['source_archive_sha256'] != expected_sha
            or len(source) != expected_count or witness['source_count'] != expected_count):
        raise Refused('SOURCE_AUTHORITY_DRIFT')
    if (witness['types'] != TYPES or witness['methods'] != METHODS
            or set(witness['owner_sha256']) != OWNERS):
        raise Refused('R364_SCOPE_DRIFT')
    mapping = {**{Path(p).stem: name for p, name in TYPES.items()}, **METHODS}
    if (len(set(mapping.values())) != len(mapping)
            or any(not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', new)
                   for new in mapping.values())):
        raise Refused('UNSAFE_RENAME_TARGET')
    for path, digest in witness['owner_sha256'].items():
        if path not in source or sha(source[path]) != digest:
            raise Refused('DECLARING_OWNER_HASH_DRIFT')
    for path in TYPES:
        old = Path(path).stem
        if not re.search(r'\bclass\s+' + re.escape(old) + r'\b',
                         source[path].decode('utf-8')):
            raise Refused('DECLARING_CLASS_MISSING')
    actual = census(source, set(mapping))
    if actual != witness['token_references'] or any(not sites for sites in actual.values()):
        raise Refused('REFERENCE_CENSUS_DRIFT')
    if any(census(source, set(mapping.values())).values()):
        raise Refused('TARGET_IDENTIFIER_COLLISION')
    result: dict[str, bytes] = {}
    edited = 0
    for path, raw in source.items():
        original = raw.decode('utf-8')
        replacements = [(at, token, mapping[token]) for token, at in identifiers(original)
                        if token in mapping]
        parts, cursor, delta, inverse_positions = [], 0, 0, []
        for at, old, new in replacements:
            parts.append(original[cursor:at]); parts.append(new)
            inverse_positions.append((at + delta, old, new))
            cursor = at + len(old)
            delta += len(new) - len(old)
        parts.append(original[cursor:])
        changed = ''.join(parts)
        restored = changed
        for at, old, new in reversed(inverse_positions):
            if restored[at:at + len(new)] != new: raise Refused('INVERSE_OFFSET_DRIFT')
            restored = restored[:at] + old + restored[at + len(new):]
        if restored.encode('utf-8') != raw: raise Refused('NOT_BYTE_EXACTLY_REVERSIBLE')
        outpath = path
        if path in TYPES:
            outpath = str(Path(path).with_name(TYPES[path] + '.java')).replace('\\', '/')
        if outpath in result or (outpath in source and outpath != path):
            raise Refused('RENAMED_CLASS_PATH_COLLISION')
        result[outpath] = changed.encode('utf-8')
        edited += len(replacements)
    if len(set(path.casefold() for path in result)) != len(result):
        raise Refused('RENAMED_CLASS_CASEFOLD_COLLISION')
    if len(result) != len(source) or (expected_count == TOTAL and edited != EXPECTED_EDITS):
        raise Refused('SOURCE_OR_EDIT_COUNT_DRIFT')
    return result, edited

def produce(source_zip: Path, witness_file: Path, new_output: Path):
    new_output = Path(new_output)
    if new_output.exists() or new_output.is_symlink(): raise Refused('OUTPUT_ALREADY_EXISTS')
    witness = json.loads(Path(witness_file).read_text('utf-8'))
    source, edits = rename_source(read_private_source(source_zip), witness)
    report = {
        'status': 'R364_PRIVATE_READABLE_JAVA_CANDIDATE',
        'source_count': len(source),
        'class_renames': len(TYPES), 'method_renames': len(METHODS),
        'identifier_occurrences_changed': edits,
        'exact_inverse_passed': True,
        'original_v309_binary_parity': 'NOT_TESTED',
        'serializer_behavior_modified': False,
        'private_source_release_approved': False,
        'source_sha256': {p: sha(raw) for p, raw in sorted(source.items())},
    }
    with ZipFile(new_output, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for path, raw in sorted(source.items()): archive.writestr('source/' + path, raw)
        archive.writestr(NEW_MANIFEST, json.dumps(report, indent=2, sort_keys=True) + '\n')
    return report

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r363-private-source', required=True, type=Path)
    p.add_argument('--witness', required=True, type=Path)
    p.add_argument('--new-private-output', required=True, type=Path)
    a = p.parse_args(argv)
    try: report = produce(a.r363_private_source, a.witness, a.new_private_output)
    except (OSError, UnicodeError, ValueError, KeyError, BadZipFile) as error:
        print(json.dumps({'status': 'R364_REFUSED', 'reason': str(error)})); return 2
    print(json.dumps({k:v for k,v in report.items() if k != 'source_sha256'}, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__': raise SystemExit(main())

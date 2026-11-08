"""R363: SHA-pinned, reversible original-v309 *candidate* source readability pass.

Owner-private recovered Java is not published. The only edits are identifier
renames. No original JAR parity, UI behavior or serialization safety is implied.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

SOURCE_SHA = 'f7b3d76a747b99accf33e8088eccfb5d32c7018ab25473d7430fe3f7190f6183'
OLD_MANIFEST = 'PRIVATE_R362_READABILITY_MANIFEST.json'
NEW_MANIFEST = 'PRIVATE_R363_READABILITY_MANIFEST.json'
OWNER = 'rs/gui/loadouts/LoadoutsPanel.java'
TOTAL = 1277
MAX_SOURCE_BYTES = 24_000_000
FIELDS = {'field3305': 'folderMenuButton', 'field3306': 'activeStatEditorDialog'}
METHODS = {
    'method812': 'rebuildFolderPopupMenu',
    'method2809': 'resetLoadoutSelector',
    'method3472': 'rebuildLoadoutSelector',
    'method1976': 'requestLoadoutRepaint',
    'method1483': 'getFolderMenuButton',
    'method3578': 'disposeStatEditorDialog',
    'method1012': 'buildControlRows',
}

class Refused(ValueError):
    pass

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def identifiers(src: str):
    """Scan Java identifiers without touching comments, string/char literals."""
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
            else:
                raise Refused('UNTERMINATED_LITERAL')
        elif src[i].isalpha() or src[i] in '_$':
            first = i; i += 1
            while i < n and (src[i].isalnum() or src[i] in '_$'):
                i += 1
            yield src[first:i], first
        else:
            i += 1

def census(source: dict[str, bytes], tokens: set[str]) -> dict[str, dict[str, int]]:
    result = {x: {} for x in tokens}
    for path, raw in source.items():
        found = {}
        for word, _ in identifiers(raw.decode('utf-8')):
            if word in tokens: found[word] = found.get(word, 0) + 1
        for word, count in found.items(): result[word][path] = count
    return result

def read_private_source(path: Path, expected_sha=SOURCE_SHA, expected_count=TOTAL):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or file_sha(path) != expected_sha:
        raise Refused('PRIVATE_INPUT_SHA_DRIFT')
    with ZipFile(path) as archive:
        infos = archive.infolist(); names = [i.filename for i in infos]
        if len(infos) != expected_count + 1 or len(set(names)) != len(names) or \
           len(set(x.casefold() for x in names)) != len(names) or OLD_MANIFEST not in names:
            raise Refused('ZIP_FILE_SET_DRIFT')
        manifest = json.loads(archive.read(OLD_MANIFEST))
        pins = manifest.get('source_sha256')
        if manifest.get('source_count') != expected_count or not isinstance(pins, dict) or len(pins) != expected_count or manifest.get('byte_exact_inverse_passed') is not True:
            raise Refused('SOURCE_MANIFEST_DRIFT')
        source, size = {}, 0
        for info in infos:
            name = info.filename
            if name == OLD_MANIFEST: continue
            parts = name.split('/')
            if not name.startswith('source/') or not name.endswith('.java') or '\\' in name or \
               any(p in ('', '.', '..') for p in parts) or info.is_dir() or info.flag_bits & 1 or \
               stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK or info.file_size > 4_000_000:
                raise Refused('UNSAFE_ZIP_MEMBER')
            size += info.file_size
            if size > MAX_SOURCE_BYTES: raise Refused('SOURCE_SIZE_BUDGET')
            data = archive.read(info); relative = name[7:]
            if len(data) != info.file_size or sha(data) != pins.get(relative):
                raise Refused('SOURCE_FILE_HASH_DRIFT')
            data.decode('utf-8'); source[relative] = data
        if set(source) != set(pins): raise Refused('SOURCE_PATH_DRIFT')
        return source

def transform(source: dict[str, bytes], witness: dict, *, expected_count=TOTAL, expected_sha=SOURCE_SHA):
    expected_keys = {'source_archive_sha256', 'source_count', 'owner_sha256', 'fields', 'methods', 'token_references'}
    if set(witness) != expected_keys: raise Refused('WITNESS_SCHEMA_DRIFT')
    if witness['source_archive_sha256'] != expected_sha or len(source) != expected_count or witness['source_count'] != expected_count:
        raise Refused('SOURCE_AUTHORITY_DRIFT')
    fields, methods = witness['fields'], witness['methods']
    mapping = {**fields, **methods}
    if not mapping or set(fields) & set(methods) or len(set(mapping.values())) != len(mapping) or \
       any(not re.fullmatch(r'field\d+', k) for k in fields) or \
       any(not re.fullmatch(r'method\d+', k) for k in methods) or \
       any(not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', v) for v in mapping.values()):
        raise Refused('UNSAFE_SYMBOL_PLAN')
    if expected_count == TOTAL and (fields != FIELDS or methods != METHODS or set(witness['owner_sha256']) != {OWNER}):
        raise Refused('R363_SCOPE_DRIFT')
    for path, expected in witness['owner_sha256'].items():
        if path not in source or sha(source[path]) != expected:
            raise Refused('DECLARING_OWNER_HASH_DRIFT')
    actual = census(source, set(mapping))
    if actual != witness['token_references'] or any(not sites for sites in actual.values()):
        raise Refused('REFERENCE_CENSUS_DRIFT')
    if any(census(source, set(mapping.values())).values()):
        raise Refused('TARGET_NAME_COLLISION')
    result = {path: raw.decode('utf-8') for path, raw in source.items()}
    changes = []
    for old, new in mapping.items():
        positions = {}
        for path, expected_count_for_path in actual[old].items():
            src = result[path]
            offsets = [at for word, at in identifiers(src) if word == old]
            if len(offsets) != expected_count_for_path: raise Refused('INTERMEDIATE_CENSUS_DRIFT')
            for at in reversed(offsets): src = src[:at] + new + src[at + len(old):]
            result[path] = src
            positions[path] = [at + i * (len(new) - len(old)) for i, at in enumerate(offsets)]
        changes.append((old, new, positions))
    restored = dict(result)
    for old, new, positions in reversed(changes):
        for path, offsets in positions.items():
            src = restored[path]
            for at in reversed(offsets):
                if src[at:at + len(new)] != new: raise Refused('INVERSE_OFFSET_DRIFT')
                src = src[:at] + old + src[at + len(new):]
            restored[path] = src
    if {p: s.encode('utf-8') for p, s in restored.items()} != source:
        raise Refused('NOT_BYTE_EXACTLY_REVERSIBLE')
    edits = sum(len(offsets) for _, _, paths in changes for offsets in paths.values())
    if expected_count == TOTAL and edits != 42:
        raise Refused('R363_EXPECTED_EDITS_DRIFT')
    return {p: s.encode('utf-8') for p, s in result.items()}, edits

def produce(source_zip: Path, witness_file: Path, new_output: Path):
    new_output = Path(new_output)
    if new_output.exists() or new_output.is_symlink(): raise Refused('OUTPUT_ALREADY_EXISTS')
    witness = json.loads(Path(witness_file).read_text('utf-8'))
    source, edits = transform(read_private_source(source_zip), witness)
    report = {
        'status': 'R363_PRIVATE_READABLE_JAVA_CANDIDATE',
        'source_count': len(source),
        'field_renames': len(witness['fields']),
        'method_renames': len(witness['methods']),
        'identifier_occurrences_changed': edits,
        'exact_inverse_passed': True,
        'original_v309_binary_parity': 'NOT_TESTED',
        'private_source_release_approved': False,
        'source_sha256': {p: sha(raw) for p, raw in sorted(source.items())},
    }
    with ZipFile(new_output, 'w', ZIP_DEFLATED, compresslevel=9) as z:
        for path, raw in sorted(source.items()): z.writestr('source/' + path, raw)
        z.writestr(NEW_MANIFEST, json.dumps(report, indent=2, sort_keys=True) + '\n')
    return report

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r362-private-source', required=True, type=Path)
    p.add_argument('--witness', required=True, type=Path)
    p.add_argument('--new-private-output', required=True, type=Path)
    a = p.parse_args(argv)
    try: report = produce(a.r362_private_source, a.witness, a.new_private_output)
    except (OSError, UnicodeError, ValueError, KeyError, BadZipFile) as error:
        print(json.dumps({'status': 'R363_REFUSED', 'reason': str(error)})); return 2
    print(json.dumps({k: v for k, v in report.items() if k != 'source_sha256'}, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__': raise SystemExit(main())

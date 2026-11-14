#!/usr/bin/env python3
"""R385: class-byte/ZIP-metadata triage for two local, class-only Java archives.

No owner-private sources, filenames or class bytecode are sent to a server. The
report uses only counts, archive SHA-256 and hashed class identifiers. A match
of class bytes is not proof of equivalent runtime behavior.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys
import zipfile

MAX_JAR_BYTES = 40_000_000
MAX_EXPANDED_BYTES = 40_000_000
MAX_CLASS_BYTES = 2_000_000
MAX_ENTRIES = 4000

class Refused(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def class_name_is_safe(name: str) -> bool:
    return bool(name.endswith('.class') and not name.startswith(('/', '\\'))
                and '\\' not in name and ':' not in name
                and all(x not in ('', '.', '..') for x in name.split('/')))


def inspect_jar(path: Path) -> dict:
    if (not path.is_file() or path.is_symlink() or
            path.stat().st_size > MAX_JAR_BYTES):
        raise Refused('MISSING_UNSAFE_OR_OVERSIZED_JAR')
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if not infos or len(infos) > MAX_ENTRIES:
            raise Refused('INVALID_ENTRY_COUNT')
        if len(set(names)) != len(names) or len(set(n.casefold() for n in names)) != len(names):
            raise Refused('DUPLICATE_OR_CASE_COLLISION')
        if any((not class_name_is_safe(i.filename) or i.is_dir() or i.flag_bits & 1
                or stat.S_IFMT(i.external_attr >> 16) == stat.S_IFLNK
                or i.file_size > MAX_CLASS_BYTES) for i in infos):
            raise Refused('UNSAFE_OR_NONCLASS_ENTRY')
        if sum(i.file_size for i in infos) > MAX_EXPANDED_BYTES:
            raise Refused('JAR_EXPANSION_BUDGET_EXCEEDED')
        classes = {i.filename: sha(z.read(i)) for i in infos}
        metadata = [(i.filename, i.create_system, i.external_attr, i.date_time,
                     i.compress_type, i.flag_bits, i.extra.hex(), i.comment.hex()) for i in infos]
        return {'jar_sha256': digest_file(path), 'class_count': len(classes),
                'class_hashes': classes, 'metadata': metadata,
                'archive_comment': z.comment.hex()}


def compare(reference: Path, candidate: Path) -> dict:
    a, b = inspect_jar(reference), inspect_jar(candidate)
    common = a['class_hashes'].keys() & b['class_hashes'].keys()
    differing = sorted(n for n in common if a['class_hashes'][n] != b['class_hashes'][n])
    absent = sorted(a['class_hashes'].keys() - b['class_hashes'].keys())
    added = sorted(b['class_hashes'].keys() - a['class_hashes'].keys())
    # Avoid public exposure of owner-private class names: emit bounded hashes only.
    label = lambda n: sha(n.encode('utf-8'))[:16]
    archive_match = a['jar_sha256'] == b['jar_sha256']
    if archive_match:
        status = 'EXACT_HASH_MATCH'
    elif absent or added:
        status = 'CLASS_SET_DRIFT'
    elif differing:
        status = 'CLASSFILE_BYTE_DRIFT'
    else:
        status = 'CLASS_BYTES_EQUAL_ARCHIVE_DRIFT'
    return {
        'status': status,
        'jar_reference_sha256': a['jar_sha256'],
        'jar_candidate_sha256': b['jar_sha256'],
        'class_count_reference': a['class_count'],
        'class_count_candidate': b['class_count'],
        'missing_classes': len(absent), 'new_classes': len(added),
        'changed_class_bytes': len(differing),
        'missing_class_ids_sha16': [label(n) for n in absent[:10]],
        'new_class_ids_sha16': [label(n) for n in added[:10]],
        'changed_class_ids_sha16': [label(n) for n in differing[:10]],
        'zip_entry_metadata_equal': a['metadata'] == b['metadata'],
        'zip_archive_comments_equal': a['archive_comment'] == b['archive_comment'],
        'actual_windows_full_compile_tested': False,
        'source_release_approved': False,
        'safe_cleanup_proven': False,
        'note': ('Local artifact comparison only; class-byte equality does not '
                 'establish runtime parity or safe staging deletion'),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', required=True, type=Path)
    p.add_argument('--candidate', required=True, type=Path)
    p.add_argument('--output', type=Path, help='optional NEW JSON report path')
    a = p.parse_args(argv)
    try:
        result = compare(a.reference, a.candidate)
        code = 0 if result['status'] == 'EXACT_HASH_MATCH' else 1
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        result = {'status':'REFUSED', 'reason':str(exc), 'source_release_approved':False,
                  'actual_windows_full_compile_tested':False}
        code = 2
    result_json = json.dumps(result, indent=2, sort_keys=True) + '\n'
    print(result_json)
    if a.output is not None:
        if a.output.exists() or a.output.is_symlink():
            print('REFUSED_EXISTING_OUTPUT', file=sys.stderr)
            return 2
        a.output.write_text(result_json, encoding='utf-8')
    return code

if __name__ == '__main__':
    raise SystemExit(main())

"""Offline SHA-pinned source-receipt checker for owner-private R368 -> R369.

This program DOES NOT contain source code or launch the client. Public CI uses
synthetic archives; the real private archive verification is operator-local.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile

OWNER = 'rs/gui/loadouts/io/LoadoutStore.java'
PREVIOUS_MANIFEST = 'PRIVATE_R368_READABILITY_MANIFEST.json'
CURRENT_MANIFEST = 'PRIVATE_R369_READABILITY_MANIFEST.json'
EXPECTED_COUNT = 1277

class Refused(ValueError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return digest.hexdigest()

def inspect(path: Path, archive_sha: str, manifest_name: str, expected_count: int):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 32_000_000:
        raise Refused('INVALID_PRIVATE_ARCHIVE')
    if hash_file(path) != archive_sha:
        raise Refused('ARCHIVE_SHA256_CHANGED')
    with ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if (len(names) != expected_count + 1 or manifest_name not in names or
            len(set(names)) != len(names) or len(set(n.casefold() for n in names)) != len(names)):
            raise Refused('ARCHIVE_FILE_SET_CHANGED')
        manifest = json.loads(archive.read(manifest_name))
        pins = manifest.get('source_sha256')
        if (manifest.get('source_count') != expected_count or
            not isinstance(pins, dict) or len(pins) != expected_count):
            raise Refused('MANIFEST_MISMATCH')
        sources = {}
        total_bytes = 0
        for item in infos:
            if item.filename == manifest_name:
                continue
            path_name = item.filename
            parts = path_name.split('/')
            if (not path_name.startswith('source/') or not path_name.endswith('.java') or
                '\\' in path_name or any(v in ('', '.', '..') for v in parts) or
                item.is_dir() or item.flag_bits & 1 or
                stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK or
                item.file_size > 4_000_000):
                raise Refused('UNSAFE_SOURCE_MEMBER')
            total_bytes += item.file_size
            if total_bytes > 24_000_000:
                raise Refused('SOURCE_BYTE_BUDGET')
            content = archive.read(item)
            rel = path_name[len('source/'):]
            if len(content) != item.file_size or pins.get(rel) != sha(content):
                raise Refused('SOURCE_SHA256_MISMATCH')
            sources[rel] = sha(content)
        if set(sources) != set(pins):
            raise Refused('SOURCE_PATH_MISMATCH')
        return sources, manifest

def verify(previous, current, witness, *, expected_count=EXPECTED_COUNT):
    if set(witness) != {'previous_zip_sha256', 'candidate_zip_sha256', 'source_count',
                        'owner', 'previous_owner_sha256', 'candidate_owner_sha256',
                        'candidate_jar_sha256', 'changed_paths', 'private_source_release_approved',
                        'original_game_runtime_tested', 'multi_file_transaction_proven',
                        'power_loss_durability_tested'}:
        raise Refused('UNEXPECTED_WITNESS_SCHEMA')
    if (expected_count != witness['source_count'] or witness['owner'] != OWNER or
        witness['changed_paths'] != [OWNER] or
        witness['private_source_release_approved'] is not False or
        witness['original_game_runtime_tested'] is not False or
        witness['multi_file_transaction_proven'] is not False or
        witness['power_loss_durability_tested'] is not False or
        any(not isinstance(witness[k], str) or not re.fullmatch(r'[0-9a-f]{64}',witness[k]) for k in
            ('previous_zip_sha256','candidate_zip_sha256','previous_owner_sha256',
             'candidate_owner_sha256','candidate_jar_sha256'))):
        raise Refused('INVALID_WITNESS')
    before,_ = inspect(previous,witness['previous_zip_sha256'],PREVIOUS_MANIFEST,expected_count)
    after,metadata = inspect(current,witness['candidate_zip_sha256'],CURRENT_MANIFEST,expected_count)
    if set(before) != set(after) or [k for k in sorted(before) if before[k] != after[k]] != [OWNER]:
        raise Refused('UNEXPECTED_JAVA_CHANGES')
    if (before[OWNER] != witness['previous_owner_sha256'] or
        after[OWNER] != witness['candidate_owner_sha256'] or
        metadata.get('changed_files') != [OWNER] or
        metadata.get('private_source_release_approved') is not False or
        metadata.get('multi_file_transaction') != 'NOT_IMPLEMENTED' or
        metadata.get('power_loss_durability') != 'NOT_TESTED' or
        metadata.get('same_source_built_jar_sha256') != witness['candidate_jar_sha256']):
        raise Refused('OWNER_OR_RELEASE_GATE_MISMATCH')
    return {'status':'R369_PRIVATE_SOURCE_RECEIPT_PASS','source_count':len(before),
            'changed_paths':[OWNER],'source_hashes_match':True,
            'original_game_runtime_tested':False,'multi_file_transaction_proven':False,
            'power_loss_durability_tested':False,'private_source_release_approved':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r368-private-source',required=True,type=Path)
    parser.add_argument('--r369-private-source',required=True,type=Path)
    parser.add_argument('--witness',required=True,type=Path)
    opts=parser.parse_args(argv)
    try:
        evidence=json.loads(opts.witness.read_text('utf8'))
        result=verify(opts.r368_private_source,opts.r369_private_source,evidence)
    except (Refused,KeyError,ValueError,OSError,BadZipFile) as error:
        print(json.dumps({'status':'R369_REFUSED','reason':str(error)}))
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__ == '__main__':raise SystemExit(main())

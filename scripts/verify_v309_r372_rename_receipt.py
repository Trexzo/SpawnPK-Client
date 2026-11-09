"""Public, offline, fail-closed verifier for R371 -> R372 private Java source receipts.

The complete recovered Java sources are owner-private and never committed here.
Hosted CI exercises only tiny synthetic archives; source-backed Java evidence
and the reproducible full-source build were run separately in private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import BadZipFile, ZipFile

PREVIOUS_MANIFEST = 'PRIVATE_R371_READABILITY_MANIFEST.json'
CURRENT_MANIFEST = 'PRIVATE_R372_READABILITY_MANIFEST.json'
EXPECTED_COUNT = 1277
EXPECTED_CLASSFILES = 1388
OWNERS = ('rs/gui/loadouts/LoadoutFolders.java', 'rs/gui/loadouts/io/LoadoutStore.java')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
WITNESS_KEYS = {
    'previous_zip_sha256', 'candidate_zip_sha256', 'source_count',
    'changed_paths', 'previous_owner_sha256', 'candidate_owner_sha256',
    'candidate_jar_sha256', 'expected_classfiles', 'private_source_release_approved',
    'original_game_runtime_tested', 'multi_file_transaction_proven',
    'power_loss_durability_tested', 'uncooperative_writer_safety_proven',
}

class Refused(ValueError):
    """Evidence did not satisfy a mandatory integrity or release gate."""

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: Path) -> str:
    hash_value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hash_value.update(block)
    return hash_value.hexdigest()

def inspect(path: Path, expected_sha: str, manifest_name: str, count: int):
    path = Path(path)
    if (path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000_000):
        raise Refused('INVALID_PRIVATE_ARCHIVE')
    if sha_file(path) != expected_sha:
        raise Refused('ARCHIVE_SHA256_CHANGED')
    with ZipFile(path) as archive:
        files = archive.infolist()
        names = [item.filename for item in files]
        if (len(files) != count + 1 or manifest_name not in names or
                len(names) != len(set(names)) or
                len(names) != len(set(name.casefold() for name in names))):
            raise Refused('ARCHIVE_FILE_SET_CHANGED')
        try:
            manifest = json.loads(archive.read(manifest_name))
        except (json.JSONDecodeError, UnicodeError):
            raise Refused('MALFORMED_MANIFEST')
        pinned = manifest.get('source_sha256')
        if (manifest.get('source_count') != count or not isinstance(pinned, dict) or
                len(pinned) != count):
            raise Refused('MANIFEST_COUNT_CHANGED')
        source_sha = {}
        total = 0
        for item in files:
            if item.filename == manifest_name:
                if item.flag_bits & 1 or item.is_dir() or item.file_size > 250_000:
                    raise Refused('UNSAFE_MANIFEST')
                continue
            name = item.filename
            parts = name.split('/')
            if (not name.startswith('source/') or not name.endswith('.java') or
                '\\' in name or any(part in ('', '.', '..') for part in parts) or
                item.is_dir() or item.flag_bits & 1 or item.file_size > 4_000_000 or
                stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK):
                raise Refused('UNSAFE_SOURCE_MEMBER')
            total += item.file_size
            if total > 24_000_000:
                raise Refused('SOURCE_BYTE_BUDGET_EXCEEDED')
            content = archive.read(item)
            rel = name[len('source/'):]
            digest = sha(content)
            if len(content) != item.file_size or pinned.get(rel) != digest:
                raise Refused('SOURCE_DIGEST_DRIFT')
            source_sha[rel] = digest
        if set(source_sha) != set(pinned):
            raise Refused('SOURCE_PATH_SET_CHANGED')
        return source_sha, manifest

def verify(previous_path: Path, candidate_path: Path, witness: dict, *, expected_count=EXPECTED_COUNT):
    if set(witness) != WITNESS_KEYS:
        raise Refused('UNEXPECTED_WITNESS_SCHEMA')
    if (witness.get('source_count') != expected_count or
            witness.get('changed_paths') != list(OWNERS) or
            witness.get('expected_classfiles') != EXPECTED_CLASSFILES or
            any(witness.get(flag) is not False for flag in (
                'private_source_release_approved', 'original_game_runtime_tested',
                'multi_file_transaction_proven', 'power_loss_durability_tested',
                'uncooperative_writer_safety_proven')) or
            any(not isinstance(witness.get(name), str) or not HEX64.fullmatch(witness[name])
                for name in ('previous_zip_sha256','candidate_zip_sha256','candidate_jar_sha256')) or
            set(witness.get('previous_owner_sha256', {})) != set(OWNERS) or
            set(witness.get('candidate_owner_sha256', {})) != set(OWNERS) or
            any(not isinstance(v, str) or not HEX64.fullmatch(v)
                for mapping in ('previous_owner_sha256','candidate_owner_sha256')
                for v in witness[mapping].values())):
        raise Refused('INVALID_WITNESS')
    before, _ = inspect(previous_path, witness['previous_zip_sha256'],
                        PREVIOUS_MANIFEST, expected_count)
    after, manifest = inspect(candidate_path, witness['candidate_zip_sha256'],
                              CURRENT_MANIFEST, expected_count)
    if set(before) != set(after) or [k for k in sorted(before) if before[k] != after[k]] != list(OWNERS):
        raise Refused('UNEXPECTED_JAVA_SOURCE_DELTA')
    if any(before[p] != witness['previous_owner_sha256'][p] or
           after[p] != witness['candidate_owner_sha256'][p] for p in OWNERS):
        raise Refused('DECLARING_OWNER_SHA_CHANGED')
    if (manifest.get('changed_files') != list(OWNERS) or
            manifest.get('previous_source_zip_sha256') != witness['previous_zip_sha256'] or
            manifest.get('private_source_release_approved') is not False or
            manifest.get('original_game_runtime_tested') is not False or
            manifest.get('multi_file_transaction_proven') is not False or
            manifest.get('power_loss_durability_tested') is not False or
            manifest.get('rename_receipt_replay') != 'SOURCE_BACKED_TEST_PASS_56'):
        raise Refused('MANIFEST_RELEASE_GATE_DRIFT')
    return {
        'status':'R372_PRIVATE_SOURCE_RECEIPT_PASS',
        'source_count':len(after),
        'changed_paths':list(OWNERS),
        'expected_classfiles':EXPECTED_CLASSFILES,
        'source_hashes_match':True,
        'original_game_runtime_tested':False,
        'multi_file_transaction_proven':False,
        'power_loss_durability_tested':False,
        'uncooperative_writer_safety_proven':False,
        'private_source_release_approved':False,
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r371-private-source', required=True, type=Path)
    parser.add_argument('--r372-private-source', required=True, type=Path)
    parser.add_argument('--witness', required=True, type=Path)
    args=parser.parse_args(argv)
    try:
        witness=json.loads(args.witness.read_text('utf-8'))
        evidence=verify(args.r371_private_source, args.r372_private_source, witness)
    except (Refused, ValueError, KeyError, OSError, UnicodeError, BadZipFile) as error:
        print(json.dumps({'status':'R372_REFUSED','reason':str(error)}))
        return 2
    print(json.dumps(evidence,sort_keys=True,indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

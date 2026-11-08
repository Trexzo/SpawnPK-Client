"""R370: offline SHA-pinned private recovered Java source-delta verifier.

No original game execution, network login or private Java source publication.
Public CI uses tiny synthetic fixtures; it cannot attest the owner's runtime.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile

PREVIOUS_MANIFEST = 'PRIVATE_R369_READABILITY_MANIFEST.json'
CURRENT_MANIFEST = 'PRIVATE_R370_READABILITY_MANIFEST.json'
EXPECTED_COUNT = 1277
OWNERS = ('rs/gui/loadouts/io/LoadoutStore.java', 'rs/gui/loadouts/io/LoadoutVersion.java')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')

class Refused(ValueError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def hash_file(path: Path) -> str:
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()

def inspect(archive_file: Path, expected_sha: str, manifest_name: str, count: int):
    archive_file = Path(archive_file)
    if (archive_file.is_symlink() or not archive_file.is_file() or
            archive_file.stat().st_size > 32_000_000):
        raise Refused('PRIVATE_ARCHIVE_TYPE_OR_SIZE_REFUSED')
    if hash_file(archive_file) != expected_sha:
        raise Refused('PRIVATE_ARCHIVE_SHA_CHANGED')
    with ZipFile(archive_file) as bundle:
        infos = bundle.infolist()
        names = [info.filename for info in infos]
        if (len(infos) != count + 1 or manifest_name not in names or
                len(set(names)) != len(names) or
                len(set(name.casefold() for name in names)) != len(names)):
            raise Refused('ARCHIVE_MEMBER_SET_CHANGED')
        info_map = {info.filename: info for info in infos}
        manifest_info = info_map[manifest_name]
        if manifest_info.file_size > 400_000 or manifest_info.flag_bits & 1:
            raise Refused('UNSAFE_MANIFEST')
        manifest = json.loads(bundle.read(manifest_info))
        pins = manifest.get('source_sha256')
        if (manifest.get('source_count') != count or
                not isinstance(pins, dict) or len(pins) != count):
            raise Refused('SOURCE_MANIFEST_CHANGED')
        scanned = {}
        total_bytes = 0
        for info in infos:
            if info.filename == manifest_name:
                continue
            path = info.filename
            parts = path.split('/')
            if (not path.startswith('source/') or not path.endswith('.java') or
                    any(part in ('', '.', '..') for part in parts) or '\\' in path or
                    info.is_dir() or info.flag_bits & 1 or
                    stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK or
                    info.file_size > 4_000_000):
                raise Refused('UNSAFE_JAVA_MEMBER')
            total_bytes += info.file_size
            if total_bytes > 24_000_000:
                raise Refused('SOURCE_SIZE_BUDGET_EXCEEDED')
            raw = bundle.read(info)
            relative = path[len('source/'):]
            if len(raw) != info.file_size or sha(raw) != pins.get(relative):
                raise Refused('JAVA_SHA_DRIFT')
            raw.decode('utf-8')
            scanned[relative] = sha(raw)
        if set(scanned) != set(pins):
            raise Refused('JAVA_SOURCE_SET_DRIFT')
        return scanned, manifest

def verify(previous: Path, candidate: Path, witness: dict,
           *, expected_count: int = EXPECTED_COUNT) -> dict:
    keys = {'previous_zip_sha256', 'candidate_zip_sha256', 'source_count',
            'changed_paths', 'previous_owner_sha256', 'candidate_owner_sha256',
            'candidate_jar_sha256', 'private_source_release_approved',
            'original_game_runtime_tested', 'multi_file_transaction_proven',
            'power_loss_durability_tested', 'fault_injection_verified_privately'}
    if set(witness) != keys:
        raise Refused('WITNESS_SCHEMA_CHANGED')
    hashes = ['previous_zip_sha256', 'candidate_zip_sha256', 'candidate_jar_sha256']
    if (witness['source_count'] != expected_count or
        witness['changed_paths'] != list(OWNERS) or
        any(witness[flag] is not False for flag in (
            'private_source_release_approved', 'original_game_runtime_tested',
            'multi_file_transaction_proven', 'power_loss_durability_tested')) or
        witness['fault_injection_verified_privately'] is not True or
        any(not isinstance(witness[k], str) or not HEX64.fullmatch(witness[k]) for k in hashes) or
        set(witness['previous_owner_sha256']) != set(OWNERS) or
        set(witness['candidate_owner_sha256']) != set(OWNERS) or
        any(not isinstance(value, str) or not HEX64.fullmatch(value)
            for name in ('previous_owner_sha256', 'candidate_owner_sha256')
            for value in witness[name].values())):
        raise Refused('INVALID_WITNESS_CONTENTS')
    before, _ = inspect(previous, witness['previous_zip_sha256'],
                        PREVIOUS_MANIFEST, expected_count)
    after, metadata = inspect(candidate, witness['candidate_zip_sha256'],
                              CURRENT_MANIFEST, expected_count)
    if (set(before) != set(after) or
            [path for path in sorted(before) if before[path] != after[path]] != list(OWNERS)):
        raise Refused('UNEXPECTED_PRIVATE_JAVA_CHANGES')
    if any(before[p] != witness['previous_owner_sha256'][p] or
           after[p] != witness['candidate_owner_sha256'][p] for p in OWNERS):
        raise Refused('DECLARING_SOURCE_SHA_CHANGED')
    if (metadata.get('changed_files') != list(OWNERS) or
        metadata.get('private_source_release_approved') is not False or
        metadata.get('multi_file_transaction') != 'NOT_IMPLEMENTED' or
        metadata.get('power_loss_durability') != 'NOT_TESTED' or
        metadata.get('same_source_built_jar_sha256') != witness['candidate_jar_sha256']):
        raise Refused('PRIVATE_RECEIPT_DRIFT')
    return {'status':'R370_PRIVATE_VERSION_RECEIPT_SOURCE_WITNESS_PASS',
            'java_source_count':len(before), 'changed_paths':list(OWNERS),
            'source_hashes_verified':True,'private_source_release_approved':False,
            'multi_file_transaction_proven':False,'power_loss_durability_tested':False,
            'original_game_runtime_tested':False}

def main(argv=None):
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument('--r369-private-source', type=Path, required=True)
    cmd.add_argument('--r370-private-source', type=Path, required=True)
    cmd.add_argument('--witness', type=Path, required=True)
    opts = cmd.parse_args(argv)
    try:
        result = verify(opts.r369_private_source, opts.r370_private_source,
                        json.loads(opts.witness.read_text('utf-8')))
    except (OSError, ValueError, Refused, KeyError, BadZipFile, UnicodeError) as exc:
        print(json.dumps({'status':'R370_REFUSED', 'reason':str(exc)}))
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

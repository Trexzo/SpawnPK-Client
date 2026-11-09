"""Public-safe SHA witness for private R371 -> R372 source snapshots.

No recovered Java source is published here. Hosted CI uses synthetic archives;
actual private build and source-backed tests are independently executed offline.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
from zipfile import ZipFile, BadZipFile

PREVIOUS = 'PRIVATE_R371_READABILITY_MANIFEST.json'
CURRENT = 'PRIVATE_R372_READABILITY_MANIFEST.json'
OWNERS = ('rs/gui/loadouts/LoadoutFolders.java', 'rs/gui/loadouts/io/LoadoutStore.java')
COUNT = 1277

class Refused(ValueError):
    pass

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as input:
        for part in iter(lambda: input.read(1 << 20), b''):
            h.update(part)
    return h.hexdigest()

def valid_hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None

def inspect(path: Path, expected_sha: str, manifest_name: str, count: int):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32_000_000:
        raise Refused('INVALID_SOURCE_ZIP')
    if hash_file(path) != expected_sha:
        raise Refused('SOURCE_ZIP_SHA_MISMATCH')
    with ZipFile(path) as z:
        infos = z.infolist()
        names = [x.filename for x in infos]
        if (len(names) != count + 1 or manifest_name not in names or
                len(set(names)) != len(names) or len(set(n.casefold() for n in names)) != len(names)):
            raise Refused('SOURCE_FILE_SET_DRIFT')
        manifestinfo = z.getinfo(manifest_name)
        if manifestinfo.file_size > 3_000_000:
            raise Refused('MANIFEST_TOO_LARGE')
        metadata = json.loads(z.read(manifest_name))
        pins = metadata.get('source_sha256')
        if (metadata.get('source_count') != count or not isinstance(pins, dict) or
                len(pins) != count or any(not valid_hash(h) for h in pins.values())):
            raise Refused('SOURCE_MANIFEST_INVALID')
        observed = {}
        byte_count = 0
        for item in infos:
            if item.filename == manifest_name:
                continue
            name = item.filename
            chunks = name.split('/')
            if (not name.startswith('source/') or not name.endswith('.java') or
                    '\\' in name or any(x in ('','.','..') for x in chunks) or
                    item.is_dir() or item.flag_bits & 1 or
                    stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK or
                    item.file_size > 4_000_000):
                raise Refused('UNSAFE_SOURCE_MEMBER')
            byte_count += item.file_size
            if byte_count > 24_000_000:
                raise Refused('SOURCE_TOO_LARGE')
            content = z.read(item)
            relative = name[len('source/'):]
            if len(content) != item.file_size or sha(content) != pins.get(relative):
                raise Refused('SOURCE_BYTES_MISMATCH')
            observed[relative] = sha(content)
        if set(observed) != set(pins):
            raise Refused('MANIFEST_PATH_MISMATCH')
        return observed, metadata

def verify(before: Path, after: Path, witness: dict, *, count: int = COUNT):
    keys = {'source_count','previous_zip_sha256','candidate_zip_sha256',
            'previous_owner_sha256','candidate_owner_sha256',
            'candidate_jar_sha256','changed_paths','compiled_classfiles',
            'multi_file_transaction_proven','power_loss_durability_tested',
            'original_game_runtime_tested','private_source_release_approved'}
    if not isinstance(witness, dict) or set(witness) != keys:
        raise Refused('UNEXPECTED_WITNESS_SCHEMA')
    if (witness['source_count'] != count or witness['compiled_classfiles'] != 1387 or
            witness['changed_paths'] != list(OWNERS) or
            any(witness[k] is not False for k in
                ('multi_file_transaction_proven','power_loss_durability_tested',
                 'original_game_runtime_tested','private_source_release_approved')) or
            not all(valid_hash(witness[k]) for k in
                ('previous_zip_sha256','candidate_zip_sha256','candidate_jar_sha256')) or
            not all(isinstance(witness[k], dict) and set(witness[k]) == set(OWNERS) and
                all(valid_hash(v) for v in witness[k].values()) for k in
                ('previous_owner_sha256','candidate_owner_sha256'))):
        raise Refused('INVALID_WITNESS')
    old, oldmeta = inspect(before, witness['previous_zip_sha256'], PREVIOUS, count)
    new, newmeta = inspect(after, witness['candidate_zip_sha256'], CURRENT, count)
    if set(old) != set(new) or sorted(x for x in old if old[x] != new[x]) != list(OWNERS):
        raise Refused('UNEXPECTED_SOURCE_CHANGE')
    if (any(old[p] != witness['previous_owner_sha256'][p] or
                new[p] != witness['candidate_owner_sha256'][p] for p in OWNERS) or
            newmeta.get('changed_files') != list(OWNERS) or
            newmeta.get('previous_source_zip_sha256') != witness['previous_zip_sha256'] or
            newmeta.get('jar_sha256') != witness['candidate_jar_sha256'] or
            newmeta.get('classfiles') != witness['compiled_classfiles'] or
            any(newmeta.get(k) is not False for k in
                ('multi_file_transaction_proven','power_loss_durability_tested',
                 'original_game_runtime_tested','private_source_release_approved'))):
        raise Refused('RECEIPT_RELEASE_GATE_MISMATCH')
    return {'status':'R372_SOURCE_WITNESS_VERIFIED','sources':len(old),
            'changed_paths':list(OWNERS),'compiled_classfiles':1387,
            'private_source_release_approved':False,
            'multi_file_transaction_proven':False,
            'power_loss_durability_tested':False,
            'original_game_runtime_tested':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r371-private-source',required=True,type=Path)
    parser.add_argument('--r372-private-source',required=True,type=Path)
    parser.add_argument('--witness',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        witness=json.loads(args.witness.read_text('utf-8'))
        result=verify(args.r371_private_source,args.r372_private_source,witness)
    except (Refused,ValueError,KeyError,OSError,BadZipFile) as error:
        print(json.dumps({'status':'R372_REFUSED','reason':str(error)}))
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0
if __name__=='__main__':raise SystemExit(main())

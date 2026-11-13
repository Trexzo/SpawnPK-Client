"""R380: verify private v309 source-archive delta, not game/runtime behavior.

Public CI uses tiny synthetic ZIPs. Never publish private source archives or JARs.
"""
from __future__ import annotations
import argparse, hashlib, json, re, stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile
OWNER = 'rs/gui/loadouts/io/LoadoutStore.java'
PREVIOUS_MANIFEST = 'PRIVATE_R379_READABILITY_MANIFEST.json'
CURRENT_MANIFEST = 'PRIVATE_R380_READABILITY_MANIFEST.json'
EXPECTED_SOURCE_COUNT = 1277
EXPECTED_CLASSES = 1388
HASH = re.compile(r'[0-9a-f]{64}\Z')
FIELDS = {'previous_zip_sha256','candidate_zip_sha256','previous_owner_sha256',
          'candidate_owner_sha256','candidate_jar_sha256','source_count',
          'generated_classfiles','changed_paths','new_source_backed_assertions',
          'inherited_source_backed_assertions','folder_stage_digest_correlation_verified',
          'legacy_folder_staging_lock_ownership_inferred',
          'folder_lock_probe_is_stage_ownership_proof',
          'cooperative_order_lock_probe_verified','stage_cleanup_safe_proven',
          'automatic_stage_cleanup_enabled','original_game_runtime_tested',
          'private_source_release_approved','power_loss_durability_tested',
          'multi_file_transaction_proven','active_writer_owner_identified',
          'windows_genuine_source_runtime_tested'}
class Refused(ValueError):pass
def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def hash_file(path:Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
    return h.hexdigest()

def inspect(path:Path,expected_hash:str,manifest_name:str,count:int):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size>32_000_000:
        raise Refused('INVALID_ARCHIVE')
    if hash_file(path)!=expected_hash:raise Refused('ARCHIVE_HASH_CHANGED')
    with ZipFile(path) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        if (len(infos)!=count+1 or manifest_name not in names or
            len(names)!=len(set(names)) or len(names)!=len(set(x.casefold() for x in names))):
            raise Refused('ARCHIVE_MEMBERS_CHANGED')
        item=z.getinfo(manifest_name)
        if item.file_size>300_000 or item.flag_bits&1 or item.is_dir():raise Refused('UNSAFE_MANIFEST')
        manifest=json.loads(z.read(item))
        pins=manifest.get('source_sha256')
        if (manifest.get('source_count')!=count or not isinstance(pins,dict) or len(pins)!=count):
            raise Refused('MANIFEST_SOURCE_COUNT_CHANGED')
        hashes={};total=0
        for item in infos:
            if item.filename==manifest_name:continue
            name=item.filename;parts=name.split('/')
            if (not name.startswith('source/') or not name.endswith('.java') or
                '\\' in name or any(x in ('','.','..') for x in parts) or item.is_dir() or
                item.flag_bits&1 or item.file_size>4_000_000 or
                stat.S_IFMT(item.external_attr>>16)==stat.S_IFLNK):
                raise Refused('UNSAFE_SOURCE_ENTRY')
            total+=item.file_size
            if total>24_000_000:raise Refused('SOURCE_BUDGET_EXCEEDED')
            content=z.read(item);relative=name[len('source/'):]
            if len(content)!=item.file_size or pins.get(relative)!=sha(content):
                raise Refused('SOURCE_PIN_DRIFT')
            hashes[relative]=sha(content)
        if set(hashes)!=set(pins):raise Refused('SOURCE_PATH_DRIFT')
        return hashes,manifest

def verify(previous:Path,candidate:Path,witness:dict,*,expected_count=EXPECTED_SOURCE_COUNT):
    if set(witness)!=FIELDS:raise Refused('WITNESS_SCHEMA_CHANGED')
    checks=(witness.get('source_count')==expected_count,
            witness.get('generated_classfiles')==EXPECTED_CLASSES,
            witness.get('changed_paths')==[OWNER],
            witness.get('new_source_backed_assertions')==24,
            witness.get('inherited_source_backed_assertions')==442,
            witness.get('folder_stage_digest_correlation_verified') is True,
            witness.get('cooperative_order_lock_probe_verified') is True)
    negative=('legacy_folder_staging_lock_ownership_inferred',
              'folder_lock_probe_is_stage_ownership_proof','stage_cleanup_safe_proven',
              'automatic_stage_cleanup_enabled','original_game_runtime_tested',
              'private_source_release_approved','power_loss_durability_tested',
              'multi_file_transaction_proven','active_writer_owner_identified',
              'windows_genuine_source_runtime_tested')
    if (not all(checks) or any(witness.get(k) is not False for k in negative) or
        any(not isinstance(witness.get(k),str) or not HASH.fullmatch(witness[k]) for k in
            ('previous_zip_sha256','candidate_zip_sha256','previous_owner_sha256',
             'candidate_owner_sha256','candidate_jar_sha256'))):raise Refused('WITNESS_INVALID')
    before,_=inspect(previous,witness['previous_zip_sha256'],PREVIOUS_MANIFEST,expected_count)
    after,receipt=inspect(candidate,witness['candidate_zip_sha256'],CURRENT_MANIFEST,expected_count)
    if set(before)!=set(after) or [p for p in sorted(before) if before[p]!=after[p]]!=[OWNER]:
        raise Refused('UNEXPECTED_SOURCE_DELTA')
    if before[OWNER]!=witness['previous_owner_sha256'] or after[OWNER]!=witness['candidate_owner_sha256']:
        raise Refused('OWNER_SHA_DRIFT')
    if (receipt.get('changed_files')!=[OWNER] or
        receipt.get('previous_source_zip_sha256')!=witness['previous_zip_sha256'] or
        receipt.get('same_source_built_jar_sha256')!=witness['candidate_jar_sha256'] or
        receipt.get('generated_classfiles')!=EXPECTED_CLASSES or
        receipt.get('new_source_backed_assertions_passed')!=24 or
        receipt.get('inherited_source_backed_assertions_passed')!=442 or
        receipt.get('folder_stage_digest_correlation_verified') is not True or
        receipt.get('cooperative_order_lock_probe_verified') is not True or
        any(receipt.get(key) is not False for key in negative)):
        raise Refused('RECEIPT_DRIFT')
    return {'status':'R380_PRIVATE_SOURCE_DELTA_PASS','source_count':expected_count,
            'changed_paths':[OWNER],'private_source_release_approved':False,
            'stage_cleanup_safe_proven':False,'original_game_runtime_tested':False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r379-private-source',type=Path,required=True)
    p.add_argument('--r380-private-source',type=Path,required=True)
    p.add_argument('--witness',type=Path,required=True)
    opts=p.parse_args(argv)
    try:
        w=json.loads(opts.witness.read_text('utf-8'))
        result=verify(opts.r379_private_source,opts.r380_private_source,w)
    except (Refused,OSError,KeyError,ValueError,UnicodeError,BadZipFile) as exc:
        print(json.dumps({'status':'R380_REFUSED','reason':str(exc)}));return 2
    print(json.dumps(result,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())

"""R371: public-safe SHA-pinned private source-delta verifier.

Does not contain recovered Java code or invoke a client. Hosted CI uses synthetic
archives only. Actual private source verification must be run locally.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile

PREVIOUS_MANIFEST='PRIVATE_R370_READABILITY_MANIFEST.json'
CURRENT_MANIFEST='PRIVATE_R371_READABILITY_MANIFEST.json'
OWNERS=('rs/gui/loadouts/LoadoutFolders.java','rs/gui/loadouts/io/LoadoutStore.java')
EXPECTED_COUNT=1277
HEX64=re.compile('[0-9a-f]{64}\\Z')

class Refused(ValueError): pass

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def file_hash(path:Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def inspect(path:Path, expected_sha:str, manifest_name:str, source_count:int):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>32_000_000:
        raise Refused('INVALID_SOURCE_ARCHIVE')
    if file_hash(path)!=expected_sha:raise Refused('ARCHIVE_HASH_MISMATCH')
    with ZipFile(path) as archive:
        infos=archive.infolist()
        names=[m.filename for m in infos]
        if (len(infos)!=source_count+1 or manifest_name not in names or
            len(names)!=len(set(names)) or len(names)!=len({s.casefold() for s in names})):
            raise Refused('UNEXPECTED_ARCHIVE_MEMBERS')
        metadata=json.loads(archive.read(manifest_name))
        pins=metadata.get('source_sha256')
        if (not isinstance(pins,dict) or metadata.get('source_count')!=source_count or
            len(pins)!=source_count):raise Refused('INVALID_SOURCE_MANIFEST')
        observed={}
        total=0
        for info in infos:
            if info.filename==manifest_name:continue
            name=info.filename
            parts=name.split('/')
            if (not name.startswith('source/') or not name.endswith('.java') or
                '\\' in name or any(part in ('','.','..') for part in parts) or
                info.is_dir() or info.flag_bits&1 or
                stat.S_IFMT(info.external_attr>>16)==stat.S_IFLNK or
                info.file_size>4_000_000):
                raise Refused('UNSAFE_SOURCE_MEMBER')
            total+=info.file_size
            if total>24_000_000:raise Refused('EXCESSIVE_UNCOMPRESSED_SIZE')
            data=archive.read(info)
            rel=name[len('source/'):]
            if pins.get(rel)!=sha(data) or len(data)!=info.file_size:
                raise Refused('SOURCE_HASH_CHANGED')
            observed[rel]=sha(data)
        if set(observed)!=set(pins):raise Refused('SOURCE_FILE_SET_CHANGED')
        return observed,metadata

def verify(previous:Path,candidate:Path,witness:dict,*,count=EXPECTED_COUNT):
    schema={'previous_zip_sha256','candidate_zip_sha256','previous_owner_sha256',
      'candidate_owner_sha256','candidate_jar_sha256','source_count','changed_files',
      'private_source_release_approved','original_game_runtime_tested',
      'multi_file_transaction_proven','power_loss_durability_tested'}
    if set(witness)!=schema:raise Refused('WITNESS_SCHEMA_CHANGED')
    if (witness['source_count']!=count or witness['changed_files']!=list(OWNERS) or
        any(witness[k] is not False for k in ('private_source_release_approved',
              'original_game_runtime_tested','multi_file_transaction_proven',
              'power_loss_durability_tested'))):raise Refused('INVALID_WITNESS')
    hashes=['previous_zip_sha256','candidate_zip_sha256','candidate_jar_sha256']
    if any(not isinstance(witness[k],str) or not HEX64.fullmatch(witness[k]) for k in hashes):
        raise Refused('INVALID_HASH_PIN')
    for ownerkey in ('previous_owner_sha256','candidate_owner_sha256'):
        d=witness[ownerkey]
        if (not isinstance(d,dict) or set(d)!=set(OWNERS) or
            any(not isinstance(x,str) or not HEX64.fullmatch(x) for x in d.values())):
            raise Refused('INVALID_OWNER_HASHES')
    before,oldmeta=inspect(previous,witness['previous_zip_sha256'],PREVIOUS_MANIFEST,count)
    after,newmeta=inspect(candidate,witness['candidate_zip_sha256'],CURRENT_MANIFEST,count)
    changed=sorted(p for p in before if before[p]!=after.get(p))
    if set(before)!=set(after) or changed!=list(OWNERS):raise Refused('UNEXPECTED_SOURCE_DELTA')
    if (any(before[p]!=witness['previous_owner_sha256'][p] or
            after[p]!=witness['candidate_owner_sha256'][p] for p in OWNERS) or
        newmeta.get('changed_files')!=['rs/gui/loadouts/io/LoadoutStore.java','rs/gui/loadouts/LoadoutFolders.java'] or
        newmeta.get('previous_source_zip_sha256')!=witness['previous_zip_sha256'] or
        newmeta.get('private_source_release_approved') is not False or
        newmeta.get('multi_file_transaction_proven') is not False or
        newmeta.get('power_loss_durability_tested') is not False):
        raise Refused('OWNER_OR_RELEASE_GATE_MISMATCH')
    return {'status':'R371_PRIVATE_SOURCE_DELTA_PASS','source_count':count,
      'changed_files':changed,'private_source_release_approved':False,
      'original_game_runtime_tested':False,'multi_file_transaction_proven':False,
      'power_loss_durability_tested':False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r370-private-source',type=Path,required=True)
    p.add_argument('--r371-private-source',type=Path,required=True)
    p.add_argument('--witness',type=Path,required=True)
    opts=p.parse_args(argv)
    try: result=verify(opts.r370_private_source,opts.r371_private_source,
                      json.loads(opts.witness.read_text('utf8')))
    except (Refused,KeyError,ValueError,OSError,BadZipFile,UnicodeError) as err:
        print(json.dumps({'status':'R371_REFUSED','reason':str(err)}));return 2
    print(json.dumps(result,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())

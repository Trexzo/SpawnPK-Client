"""Fail-closed, offline private-source receipt verifier for R372 -> R373.

Hosted CI tests only synthetic archives. No proprietary recovered Java source
or binary dependencies are included in this public tool.
"""
from __future__ import annotations
import argparse, hashlib, json, re, stat
from pathlib import Path
from zipfile import ZipFile, BadZipFile

OWNER = 'rs/gui/loadouts/io/LoadoutStore.java'
PREVIOUS_MANIFEST = 'PRIVATE_R372_READABILITY_MANIFEST.json'
CURRENT_MANIFEST = 'PRIVATE_R373_READABILITY_MANIFEST.json'
EXPECTED_COUNT = 1277
EXPECTED_CLASSES = 1388
HEX = re.compile(r'[0-9a-f]{64}\Z')
WITNESS_KEYS = {
 'previous_zip_sha256','candidate_zip_sha256','source_count','changed_paths',
 'previous_owner_sha256','candidate_owner_sha256','candidate_jar_sha256',
 'expected_classes','r372_stale_order_regression_reproduced','order_assertions',
 'inherited_assertions','private_source_release_approved','original_game_runtime_tested',
 'multi_file_transaction_proven','power_loss_durability_tested','uncooperative_writer_safety_proven',
}

class Refused(ValueError):
 pass

def sha(raw: bytes) -> str:
 return hashlib.sha256(raw).hexdigest()

def sha_file(path: Path) -> str:
 digest=hashlib.sha256()
 with path.open('rb') as stream:
  for part in iter(lambda:stream.read(1024*1024),b''):
   digest.update(part)
 return digest.hexdigest()

def inspect(path: Path, expected_sha: str, manifest_name: str, count: int):
 path=Path(path)
 if path.is_symlink() or not path.is_file() or path.stat().st_size>32_000_000:
  raise Refused('INVALID_PRIVATE_ARCHIVE')
 if sha_file(path)!=expected_sha: raise Refused('ARCHIVE_SHA256_CHANGED')
 with ZipFile(path) as z:
  members=z.infolist();names=[i.filename for i in members]
  if (len(members)!=count+1 or manifest_name not in names or len(set(names))!=len(names) or
      len(set(n.casefold() for n in names))!=len(names)):
   raise Refused('ARCHIVE_FILE_SET_DRIFT')
  manifest=json.loads(z.read(manifest_name))
  hashes=manifest.get('source_sha256')
  if (manifest.get('source_count')!=count or not isinstance(hashes,dict) or
      len(hashes)!=count):raise Refused('MANIFEST_COUNT_MISMATCH')
  result={};total=0
  for info in members:
   name=info.filename
   if name==manifest_name:
    if info.file_size>250_000 or info.is_dir() or info.flag_bits&1:
     raise Refused('UNSAFE_MANIFEST')
    continue
   bits=name.split('/')
   if (not name.startswith('source/') or not name.endswith('.java') or
       '\\' in name or any(p in ('','.','..') for p in bits) or info.is_dir() or
       info.flag_bits&1 or info.file_size>4_000_000 or
       stat.S_IFMT(info.external_attr>>16)==stat.S_IFLNK):
    raise Refused('UNSAFE_SOURCE_MEMBER')
   total+=info.file_size
   if total>24_000_000:raise Refused('SOURCE_BYTE_BUDGET')
   data=z.read(info);rel=name[7:];digest=sha(data)
   if len(data)!=info.file_size or hashes.get(rel)!=digest:
    raise Refused('SOURCE_HASH_DRIFT')
   result[rel]=digest
  if set(result)!=set(hashes):raise Refused('SOURCE_SET_DRIFT')
  return result,manifest

def verify(previous, candidate, witness: dict, *, count=EXPECTED_COUNT):
 if set(witness)!=WITNESS_KEYS:raise Refused('UNEXPECTED_WITNESS_SCHEMA')
 if (witness.get('source_count')!=count or
     witness.get('changed_paths')!=[OWNER] or
     witness.get('expected_classes')!=EXPECTED_CLASSES or
     witness.get('r372_stale_order_regression_reproduced') is not True or
     witness.get('order_assertions')!=45 or witness.get('inherited_assertions')!=233 or
     any(witness.get(flag) is not False for flag in (
      'private_source_release_approved','original_game_runtime_tested',
      'multi_file_transaction_proven','power_loss_durability_tested',
      'uncooperative_writer_safety_proven')) or
     any(not isinstance(witness.get(k),str) or not HEX.fullmatch(witness[k])
         for k in ('previous_zip_sha256','candidate_zip_sha256','previous_owner_sha256',
                   'candidate_owner_sha256','candidate_jar_sha256'))):
  raise Refused('INVALID_WITNESS')
 before,_=inspect(previous,witness['previous_zip_sha256'],PREVIOUS_MANIFEST,count)
 after,manifest=inspect(candidate,witness['candidate_zip_sha256'],CURRENT_MANIFEST,count)
 if set(before)!=set(after) or [k for k in sorted(before) if before[k]!=after[k]]!=[OWNER]:
  raise Refused('UNEXPECTED_SOURCE_DELTA')
 if before[OWNER]!=witness['previous_owner_sha256'] or after[OWNER]!=witness['candidate_owner_sha256']:
  raise Refused('OWNER_DIGEST_DRIFT')
 if (manifest.get('changed_files')!=[OWNER] or
     manifest.get('previous_source_zip_sha256')!=witness['previous_zip_sha256'] or
     manifest.get('source_backed_order_assertions_passed')!=45 or
     manifest.get('inherited_source_backed_assertions_passed')!=233 or
     manifest.get('r372_stale_order_regression_reproduced') is not True or
     manifest.get('generated_classfiles')!=EXPECTED_CLASSES or
     manifest.get('same_source_built_jar_sha256')!=witness['candidate_jar_sha256'] or
     any(manifest.get(k) is not False for k in (
        'private_source_release_approved','original_game_runtime_tested',
        'multi_file_transaction_proven','power_loss_durability_tested'))):
  raise Refused('PRIVATE_MANIFEST_GATE_CHANGED')
 return {'status':'R373_PRIVATE_SOURCE_RECEIPT_PASS','source_count':count,
         'changed_paths':[OWNER],'source_hashes_match':True,
         'original_game_runtime_tested':False,'private_source_release_approved':False,
         'multi_file_transaction_proven':False,'power_loss_durability_tested':False}

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--r372-private-source',required=True,type=Path)
 parser.add_argument('--r373-private-source',required=True,type=Path)
 parser.add_argument('--witness',required=True,type=Path)
 opts=parser.parse_args(argv)
 try:
  witness=json.loads(opts.witness.read_text('utf-8'))
  result=verify(opts.r372_private_source,opts.r373_private_source,witness)
 except (Refused,OSError,ValueError,KeyError,UnicodeError,BadZipFile) as exc:
  print(json.dumps({'status':'R373_REFUSED','reason':str(exc)}));return 2
 print(json.dumps(result,sort_keys=True,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())

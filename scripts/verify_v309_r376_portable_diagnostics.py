"""R376: offline source archive integrity verifier (public, synthetic CI only).

No reconstructed proprietary Java, executable binary, or remote client operations.
Only compares two already-owned, SHA-pinned private source archives when passed
explicit local paths by the owner. Public CI uses synthetic micro-archives.
"""
from __future__ import annotations
import argparse,hashlib,json,re,stat
from pathlib import Path
from zipfile import ZipFile,BadZipFile

PREVIOUS_MANIFEST='PRIVATE_R375_READABILITY_MANIFEST.json'
CURRENT_MANIFEST='PRIVATE_R376_READABILITY_MANIFEST.json'
OWNER='rs/gui/loadouts/io/LoadoutStore.java'
EXPECTED_COUNT=1277
CLASS_COUNT=1388
HEX=re.compile(r'[a-f0-9]{64}\Z')
WITNESS_KEYS={
 'previous_zip_sha256','candidate_zip_sha256','previous_owner_sha256',
 'candidate_owner_sha256','candidate_jar_sha256','source_count',
 'generated_classfiles','changed_paths','new_source_backed_assertions',
 'inherited_source_backed_assertions','read_only_staging_inventory_verified','advisory_directory_sync_preserved','unsupported_provider_probe_passed',
 'directory_warning_once_verified','directory_fsync_durability_proven','power_loss_durability_tested',
 'multi_file_transaction_proven','uncooperative_writer_safety_proven',
 'original_game_runtime_tested','private_source_release_approved',
 'automatic_stage_cleanup_enabled','windows_genuine_source_runtime_tested'
}
class Refused(ValueError):pass

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def hash_file(path:Path)->str:
 h=hashlib.sha256()
 with Path(path).open('rb') as file:
  for data in iter(lambda:file.read(1048576),b''):h.update(data)
 return h.hexdigest()

def inspect(path:Path,expected_sha:str,manifest_name:str,expected_count:int):
 path=Path(path)
 if not path.is_file() or path.is_symlink() or path.stat().st_size>32_000_000:
  raise Refused('INVALID_ARCHIVE_FILE')
 if hash_file(path)!=expected_sha:raise Refused('ARCHIVE_SHA256_CHANGED')
 with ZipFile(path) as zipfile:
  infos=zipfile.infolist();names=[member.filename for member in infos]
  if (len(infos)!=expected_count+1 or manifest_name not in names or
      len(set(names))!=len(names) or len(set(n.casefold() for n in names))!=len(names)):
   raise Refused('ARCHIVE_FILE_SET_MISMATCH')
  manifest_info=zipfile.getinfo(manifest_name)
  if (manifest_info.file_size>300000 or manifest_info.flag_bits&1 or
      manifest_info.is_dir()):raise Refused('UNSAFE_MANIFEST')
  manifest=json.loads(zipfile.read(manifest_info))
  pins=manifest.get('source_sha256')
  if (manifest.get('source_count')!=expected_count or not isinstance(pins,dict) or
      len(pins)!=expected_count):raise Refused('PRIVATE_MANIFEST_MISMATCH')
  data={};total=0
  for info in infos:
   if info.filename==manifest_name:continue
   filename=info.filename;bits=filename.split('/')
   if (not filename.startswith('source/') or not filename.endswith('.java') or
       '\\' in filename or any(b in ('','.','..') for b in bits) or
       info.is_dir() or info.flag_bits&1 or info.file_size>4000000 or
       stat.S_IFMT(info.external_attr>>16)==stat.S_IFLNK):
    raise Refused('UNSAFE_SOURCE_MEMBER')
   total+=info.file_size
   if total>24000000:raise Refused('SOURCE_SIZE_LIMIT')
   content=zipfile.read(info)
   rel=filename[7:]
   digest=sha(content)
   if len(content)!=info.file_size or pins.get(rel)!=digest:
    raise Refused('SOURCE_SHA256_MISMATCH')
   data[rel]=digest
  if set(data)!=set(pins):raise Refused('SOURCE_PATH_DRIFT')
  return data,manifest

def verify(previous:Path,candidate:Path,witness:dict,*,expected_count=EXPECTED_COUNT):
 if set(witness)!=WITNESS_KEYS:raise Refused('UNEXPECTED_WITNESS_KEYS')
 if (witness.get('source_count')!=expected_count or
     witness.get('generated_classfiles')!=CLASS_COUNT or
     witness.get('changed_paths')!=[OWNER] or
     witness.get('new_source_backed_assertions')!=23 or
     witness.get('inherited_source_backed_assertions')!=334 or
     witness.get('read_only_staging_inventory_verified') is not True or
     witness.get('directory_warning_once_verified') is not True or
     witness.get('advisory_directory_sync_preserved') is not True or
     witness.get('unsupported_provider_probe_passed') is not True or
     any(witness.get(key) is not False for key in (
       'directory_fsync_durability_proven','power_loss_durability_tested',
       'multi_file_transaction_proven','uncooperative_writer_safety_proven',
       'original_game_runtime_tested','private_source_release_approved',
 'automatic_stage_cleanup_enabled','windows_genuine_source_runtime_tested')) or
     any(not isinstance(witness.get(key),str) or not HEX.fullmatch(witness[key])
       for key in ('previous_zip_sha256','candidate_zip_sha256',
                   'previous_owner_sha256','candidate_owner_sha256','candidate_jar_sha256'))):
  raise Refused('INVALID_WITNESS')
 before,_=inspect(previous,witness['previous_zip_sha256'],PREVIOUS_MANIFEST,expected_count)
 after,manifest=inspect(candidate,witness['candidate_zip_sha256'],CURRENT_MANIFEST,expected_count)
 if set(before)!=set(after) or [x for x in sorted(before) if before[x]!=after[x]]!=[OWNER]:
  raise Refused('UNEXPECTED_PRIVATE_SOURCE_DELTA')
 if (before[OWNER]!=witness['previous_owner_sha256'] or
     after[OWNER]!=witness['candidate_owner_sha256']):raise Refused('OWNER_SHA_DRIFT')
 if (manifest.get('changed_files')!=[OWNER] or
     manifest.get('previous_source_zip_sha256')!=witness['previous_zip_sha256'] or
     manifest.get('generated_classfiles')!=CLASS_COUNT or
     manifest.get('source_backed_portability_assertions_passed')!=23 or
     manifest.get('inherited_source_backed_assertions_passed')!=334 or
     manifest.get('same_source_built_jar_sha256')!=witness['candidate_jar_sha256'] or
     any(manifest.get(key) is not False for key in (
       'original_game_runtime_tested','power_loss_durability_tested',
       'directory_fsync_durability_proven','multi_file_transaction_proven',
       'private_source_release_approved',
       'automatic_stage_cleanup_enabled','windows_genuine_source_runtime_tested'))):
  raise Refused('PRIVATE_RECEIPT_DRIFT')
 return {'status':'R376_PRIVATE_SOURCE_CHECK_PASS','source_count':expected_count,
         'changed_paths':[OWNER],'private_source_release_approved':False,
         'power_loss_durability_tested':False,'multi_file_transaction_proven':False}

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--r375-private-source',type=Path,required=True)
 parser.add_argument('--r376-private-source',type=Path,required=True)
 parser.add_argument('--witness',type=Path,required=True)
 args=parser.parse_args(argv)
 try:
  witness=json.loads(args.witness.read_text('utf-8'))
  result=verify(args.r375_private_source,args.r376_private_source,witness)
 except (Refused,OSError,KeyError,ValueError,BadZipFile,UnicodeError) as exc:
  print(json.dumps({'status':'R376_REFUSED','reason':str(exc)}));return 2
 print(json.dumps(result,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())

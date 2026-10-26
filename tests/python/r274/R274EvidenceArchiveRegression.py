#!/usr/bin/env python3
"""Standard-library-only integrity/behavior-evidence check; never executes binaries."""
import hashlib,json,re,sys,zipfile
from pathlib import Path
EXPECTED_JAR='09920fc5db420f384a43a267ca6d976df49b8a587c8dde8d1c77b47ab8b416b4'
EXPECTED={'R274_OBJECT_SCENE_MENU_PASS':39,'R274_REAL_SCENE_MODEL_INSERTION_PASS':21,
          'R273_INBOUND_REAL_OBJECT_SPAWN_PASS':12,'R272_NPC_OPTIONS_REAL_CLIENT_PASS':64,
          'R272_REAL_NPC_SPAWN_DECODE_PASS':19,'R270_CLIENT_REAL_WALK_PACKET_PASS':23,
          'R267_AUTHENTIC_KIT_ACTOR_PASS':75,'R268_TELEPORT_APPEARANCE_CLIENT_DISPATCH_PASS':63}
def verify(path):
 checks=0
 def ck(ok,why):
  nonlocal checks
  if not ok:raise AssertionError(why)
  checks+=1
 with zipfile.ZipFile(path) as z:
  ck(z.testzip() is None,'outer ZIP CRC')
  files=set(z.namelist())
  meta=json.loads(z.read('MANIFEST.json'))
  ck(meta['milestone']=='R274' and meta['production_java_files_modified']==1,'wrong milestone/scope')
  ck(meta['complete_source_files']==1277 and meta['compiled_classfiles']==1386,'false source build count')
  ck(files==set(meta['files'])|{'MANIFEST.json'},'unexpected/missing entries')
  for name,fields in meta['files'].items():
   blob=z.read(name)
   ck(len(blob)==fields['bytes'],'size mismatch '+name)
   ck(hashlib.sha256(blob).hexdigest()==fields['sha256'],'SHA256 mismatch '+name)
  jar=z.read('bin/R274_SOURCE_BUILT_CLASS_ONLY.jar')
  ck(hashlib.sha256(jar).hexdigest()==EXPECTED_JAR,'unverified source-built class binary')
  with zipfile.ZipFile(__import__('io').BytesIO(jar)) as inner:
   ck(inner.testzip() is None,'class-only JAR CRC')
   ck(len(inner.namelist())==1386,'class file count')
   ck('rs/Client.class' in inner.namelist(),'missing patched rs.Client class')
  patch=z.read('patch/R274_CLIENT_GUARD.diff').decode()
  ck(patch.count('if (n == -1 || n5 == -1)')==1,'missing or repeated stale lookup guard')
  ck(patch.count('-        if (n == -1)')==1,'wrong guard preimage')
  build=z.read('evidence/DETERMINISTIC_REBUILD_PASS.log').decode()
  ck('R274_PINNED_BINARY_REPRODUCED_PASS' in build,'rebuild byte-reproducibility absent')
  ck('files=1277 classes=1386' in build,'full javac result absent')
  red=z.read('evidence/STALE_OBJECT_PREIMAGE_EXPECTED_FAIL.log').decode()
  ck('AssertionError: stale object lookup allowed an outbound item-on-object packet' in red,'preimage red failure unverified')
  green=z.read('evidence/STALE_OBJECT_POSTIMAGE_PASS.log').decode()
  ck('R274_STALE_OBJECT_GUARD_PASS scene_hash_missing_item_use_bytes=0' in green,'guard positive evidence absent')
  suites=z.read('evidence/REAL_JAR_316_ASSERTIONS_PASS.log').decode()
  ck('R274_FULL_REBUILT_CLIENT_ALL_SELECTED_REGRESSIONS_PASS suites=8' in suites,'all suites not completed')
  sum_checks=0
  for marker,count in EXPECTED.items():
   ck(marker+' ' in suites or marker+'\n' in suites,'suite missing '+marker)
   segment=suites[suites.find(marker):].splitlines()[0]
   ck(f'checks={count}' in segment,f'suite check count incorrect: {marker}')
   sum_checks+=count
  ck(sum_checks==316,'assertions do not total 316')
  gui=z.read('evidence/GUI_LOCAL_SERVER_BROKEN_PIPE.log').decode()
  ck('BrokenPipeError' in gui,'failed GUI acceptance evidence absent')
 print(f'R274_PRIVATE_REBUILD_EVIDENCE_PASS checks={checks} suites=8 assertions=316 rebuilt_classes=1386 GUI=NOT_VERIFIED')
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: python R274EvidenceArchiveRegression.py <package.zip>')
 verify(sys.argv[1])

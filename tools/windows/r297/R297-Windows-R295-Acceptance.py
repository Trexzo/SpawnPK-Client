#!/usr/bin/env python3
"""R291: checksum-pinned R295 owner-native acceptance, no proprietary redistribution.

Default is read-only preflight. --run-native-gui stages an isolated disposable
home and calls the authentic R286 Windows harness with a tightly guarded R295
binary overlay. No client is launched on Linux. Never install into game folders.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

R286 = ('SpawnPK_v309_R286_WINDOWS_GUARDED_ACCEPTANCE_SOURCE_ONLY.zip',
        '2cacd2c551d6169be45e695f324d6c70a6d2a0b73a59b15fc5bce444f88a9877')
R295 = ('SpawnPK_v309_R295_SCENE_HASH_BOUNDS_PRIVATE.zip',
        '277fb5016d60e5b36bb22cede2b3b2500b9773636f433c65774db18a34e401f6')
OWNER = {
 'r278':('SpawnPK_v309_R278_FULL_SOURCE_OBJECT_AUTHORITY_GUARDS.zip','e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280'),
 'r265':('SpawnPK_v309_R265_UNIFIED_CACHE_R246_PLAYER_APPEARANCE_DIAGNOSTIC_PRIVATE.zip','9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'),
 'assets':('.spawnpk (4).zip','8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565'),
 'original':('client(20261015-104312).jar','ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38'),
 'r230':('SpawnPK_v309_R230_AUTHENTIC_ASSETS_LOGIN_PRIVATE.zip','5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125'),
}
R278_JAR='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'
R295_JAR='f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35'
R286_FILES={
 'scripts/R286-Windows-Acceptance.py':'0269f3d1a046d46f3833c5622b7b760f27e7a5f357afef5d32cab2270985d59b',
 'scripts/probe/run_r286_windows_gui.py':'dd33b4c5f6b2fb95ebeaf3db31e07edbd925bf35ec08143eab7a26211c9df797',
}

class GuardError(RuntimeError): pass

def sha256_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()

def sha256_bytes(data): return hashlib.sha256(data).hexdigest()

def replace_once(source,needle,new):
 if source.count(needle)!=1:raise GuardError('R291_OVERLAY_ANCHOR_NOT_UNIQUE '+needle[:75])
 return source.replace(needle,new)

def overlay(filename,data):
 text=data.decode('utf-8')
 if filename=='scripts/R286-Windows-Acceptance.py':
  text=replace_once(text,"    'r230': '5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125',", "    'r230': '5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125',\n    'r295': '"+R295[1]+"',")
  text=replace_once(text,"R278_JAR = '"+R278_JAR+"'", "R295_JAR = '"+R295_JAR+"'")
  text=replace_once(text,"with zipfile.ZipFile(inputs['r278']) as z:","with zipfile.ZipFile(inputs['r295']) as z:")
  text=replace_once(text,"jar = testhome/'R278_SOURCE_BUILT_CLASS_ONLY.jar'","jar = testhome/'R295_SOURCE_BUILT_CLASS_ONLY.jar'")
  text=replace_once(text,"z.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar')","z.read('bin/R295_SOURCE_BUILT_CLASS_ONLY.jar')")
  text=replace_once(text,"if digest(jar) != R278_JAR:","if digest(jar) != R295_JAR:")
  text=replace_once(text,"    except (AttributeError, OSError):\n        dpi = 96",
   "    except (AttributeError, OSError) as ex:\n        raise AcceptanceError('R291_CANNOT_VERIFY_WINDOWS_DPI') from ex")
  # R291 window safety: the expected Robot viewport and target must actually lie
  # inside the verified foreground Java window, not just the same desktop.
  marker="    return {'pid': pid.value, 'window_rect': [rect.left, rect.top, rect.right, rect.bottom]}"
  text=replace_once(text,marker,
   "    if not (rect.left <= 136 and rect.top <= 185 and rect.right >= 640 and rect.bottom >= 520):\n"
   "        raise AcceptanceError('R291_CLIENT_WINDOW_NOT_AT_VERIFIED_ROBOT_ANCHORS')\n"+marker)
 elif filename=='scripts/probe/run_r286_windows_gui.py':
  text=replace_once(text,"jar = base/'R278_SOURCE_BUILT_CLASS_ONLY.jar'","jar = base/'R295_SOURCE_BUILT_CLASS_ONLY.jar'")
  text=replace_once(text,"if API.digest(jar)!=API.R278_JAR:","if API.digest(jar)!=API.R295_JAR:")
 else:raise GuardError('R291_UNLISTED_OVERLAY '+filename)
 return text.encode('utf-8')

def pinned_inputs(input_dir):
 return {key:input_dir/filename for key,(filename,_) in {'r286':R286,'r295':R295,**OWNER}.items()}

def safe_output(output, input_dir):
 output=output.absolute(); parent=output.parent
 if output.exists() or output.is_symlink() or not parent.is_dir() or parent.is_symlink():
  raise GuardError('R291_REFUSE_EXISTING_OR_UNSAFE_OUTPUT')
 resolved=parent.resolve(); root=input_dir.resolve()
 if output==Path(output.anchor) or output==Path.home() or resolved==root or root in resolved.parents:
  raise GuardError('R291_REFUSE_UNSAFE_OUTPUT_LOCATION')
 if resolved==output or not os.access(parent,os.W_OK):
  raise GuardError('R291_REFUSE_UNWRITABLE_OUTPUT_PARENT')

def preflight(input_dir, output):
 if not input_dir.is_dir() or input_dir.is_symlink():raise GuardError('R291_BAD_INPUT_DIRECTORY')
 safe_output(output,input_dir)
 inputs=pinned_inputs(input_dir)
 expected={'r286':R286[1],'r295':R295[1],**{k:v[1] for k,v in OWNER.items()}}
 for key,path in inputs.items():
  if not path.is_file() or path.is_symlink():raise GuardError('R291_MISSING_OR_SYMLINK_INPUT '+key)
  if sha256_file(path)!=expected[key]:raise GuardError('R291_INPUT_SHA256_MISMATCH '+key)
 with zipfile.ZipFile(inputs['r295']) as z:
  member=z.read('bin/R295_SOURCE_BUILT_CLASS_ONLY.jar')
  if sha256_bytes(member)!=R295_JAR:raise GuardError('R291_R295_JAR_SHA256_MISMATCH')
 with zipfile.ZipFile(inputs['r286']) as z:
  if z.testzip() is not None:raise GuardError('R291_R286_ZIP_CORRUPT')
  for path,expected_hash in R286_FILES.items():
   data=z.read(path)
   if sha256_bytes(data)!=expected_hash:raise GuardError('R291_R286_SOURCE_SHA256_MISMATCH '+path)
   overlay(path,data) # verify all anchor sets before any staging
 return inputs

def stage_overlay(r286_zip, scratch):
 with zipfile.ZipFile(r286_zip) as z:
  for info in z.infolist():
   name=info.filename
   if name.startswith('/') or '\\' in name or '..' in Path(name).parts or info.is_dir():
    raise GuardError('R291_UNSAFE_R286_ZIP_MEMBER')
   target=scratch/name;target.parent.mkdir(parents=True,exist_ok=True)
   data=z.read(name)
   if name in R286_FILES:data=overlay(name,data)
   target.write_bytes(data)
 return scratch/'scripts/R286-Windows-Acceptance.py'

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--input-dir',required=True,type=Path)
 p.add_argument('--output',required=True,type=Path)
 p.add_argument('--run-native-gui',action='store_true',help='EXPLICIT owner opt-in to real AWT input on Windows')
 a=p.parse_args(argv)
 inp=a.input_dir.expanduser().absolute(); out=a.output.expanduser().absolute()
 sources=preflight(inp,out)
 report={'milestone':'R291','mode':'NATIVE_GUI_OPT_IN' if a.run_native_gui else 'READ_ONLY',
         'private_archive_hashes':'PASS','r295_jar_hash':'PASS','r286_overlay_anchors':'PASS',
         'native_windows_gui':'NOT_TESTED','output_created':False}
 if not a.run_native_gui:
  print('R291_PINNED_READ_ONLY_PREFLIGHT_PASS '+json.dumps(report,sort_keys=True))
  return 0
 if sys.platform!='win32':raise GuardError('R291_REFUSE_NOT_NATIVE_WINDOWS')
 # The real R286 desktop/window and local 127.0.0.1-only protocol checks remain
 # authoritative. Do not override or suppress any of those runtime guards.
 with tempfile.TemporaryDirectory(prefix='spawnpk-r291-source-') as d:
  entry=stage_overlay(sources['r286'],Path(d))
  cmd=[sys.executable,'-u',str(entry)]
  for key in ('r278','r265','assets','original','r230','r295'):
   cmd+=['--'+key,str(sources[key])]
  cmd+=['--output',str(out)]
  result=subprocess.run(cmd,check=False)
  if result.returncode:raise GuardError('R291_NATIVE_GUI_RUNNER_FAILED exit='+str(result.returncode))
 print('R291_R295_NATIVE_GUI_RUNNER_REPORTED_PASS '+str(out))
 return 0

if __name__=='__main__':
 try:raise SystemExit(main())
 except (GuardError,FileNotFoundError,KeyError,zipfile.BadZipFile) as ex:
  print('R291_FAIL_CLOSED '+str(ex),file=sys.stderr)
  raise SystemExit(1)

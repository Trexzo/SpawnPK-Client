#!/usr/bin/env python3
"""Run source-built R298 through original pinned R285 GUI Cook acceptance.

Uses SHA-locked original R285 evidence scripts and all six original owner-private
inputs. Creates a new disposable output, never installs or connects to a live
server, and captures native AWT/RuneScape local mock-server receipts. Linux/Xvfb
only. Source-only code; private JARs, caches and screenshots remain private.
"""
from __future__ import annotations
import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

PINS={
 'r278':('SpawnPK_v309_R278_FULL_SOURCE_OBJECT_AUTHORITY_GUARDS.zip','e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280'),
 'r265':('SpawnPK_v309_R265_UNIFIED_CACHE_R246_PLAYER_APPEARANCE_DIAGNOSTIC_PRIVATE.zip','9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'),
 'assets':('.spawnpk (4).zip','8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565'),
 'original':('client(20261015-104312).jar','ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38'),
 'r230':('SpawnPK_v309_R230_AUTHENTIC_ASSETS_LOGIN_PRIVATE.zip','5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125'),
 'r298':('SpawnPK_v309_R298_READ_ONLY_SCENE_QUERY_GUARDS_PRIVATE.zip','af18427ffa9dddbe0e03f375a08b55ca381788b30ccf035e586942fb75cf47f1'),
 'r285':('SpawnPK_v309_R285_FRESH_GUI_OSRS_COOK_REPLAY_EVIDENCE.zip','99665e0404c2273b24b47935a8db6b5f169a2a1d17fff7d09fda928aaf021d33'),
}
SCRIPTS={
 'scripts/Run-R285-Fresh-GUI.py':'4eead8990b28c5e62377cfe45d5ac7fdb681393fcd9e23f4783c6f22bf0068fe',
 'scripts/probe/run_r285_gui.py':'cc0be1d64f19320594dcba06284e19e0d6457b09544da6e5f225feae56cba31e',
 'scripts/stage_owner_inputs.py':'f58ce6954efa53ced0497c4fd1a9ba69998d0cd8adb5b2db24caac6eaf3f5e1b',
}
R278_JAR='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'
R298_JAR='be86b334f9ddc471cc7353f4a9493587c8a8317ded4a3a6e538f0ba96c08fbc9'
R298_PACKAGE=PINS['r298'][1]

def sha256(data):return hashlib.sha256(data).hexdigest()
def hash_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
 return h.hexdigest()
def replace_one(content,a,b):
 if content.count(a)!=1:raise ValueError('R298_OVERLAY_SOURCE_ANCHOR_DRIFT '+a[:65])
 return content.replace(a,b)
def patch_wrapper(s):
 s=replace_one(s,"JAR='"+R278_JAR+"'","JAR='"+R298_JAR+"'")
 s=replace_one(s,"for name in (*EXPECTED,'output'):p.add_argument('--'+name,required=True)","for name in (*EXPECTED,'r298','output'):p.add_argument('--'+name,required=True)")
 s=replace_one(s,"print('R285_ALL_FIVE_ORIGINAL_OWNER_SHA256_PASS',flush=True)","""if digest(a.r298)!='af18427ffa9dddbe0e03f375a08b55ca381788b30ccf035e586942fb75cf47f1':raise SystemExit('R298_R298_RELEASE_HASH_MISMATCH')
print('R298_ALL_FIVE_OWNER_AND_R298_SHA256_PASS',flush=True)""")
 s=replace_one(s,"with zipfile.ZipFile(a.r278) as z:\n  jar=stage/'R278_SOURCE_BUILT_CLASS_ONLY.jar';jar.write_bytes(z.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar'))","with zipfile.ZipFile(a.r298) as z:\n  jar=stage/'R298_SOURCE_BUILT_CLASS_ONLY.jar';jar.write_bytes(z.read('bin/R298_SOURCE_BUILT_CLASS_ONLY.jar'))")
 s=replace_one(s,'R285_FRESH_ARCHIVE_STAGE_PASS','R298_R298_FRESH_ARCHIVE_STAGE_PASS')
 s=replace_one(s,'R285_FRESH_FIVE_ARCHIVE_GUI_COOK_PASS','R298_R298_FRESH_GUI_COOK_PASS')

 return s
def patch_probe(s):
 before="B/'R278_SOURCE_BUILT_CLASS_ONLY.jar'"
 if s.count(before)!=2:raise ValueError('R298_TWO_JAR_REFERENCES_REQUIRED')
 s=s.replace(before,"B/'R298_SOURCE_BUILT_CLASS_ONLY.jar'")
 s=replace_one(s,"expected='"+R278_JAR+"'","expected='"+R298_JAR+"'")
 s=replace_one(s,"'R285 private R278 JAR hash mismatch'","'R298 private R298 JAR hash mismatch'")
 return s

def preflight(root):
 files={key:root/name for key,(name,sha) in PINS.items()}
 for label,path in files.items():
  if not path.is_file() or path.is_symlink() or hash_file(path)!=PINS[label][1]:
   raise ValueError('R298_PINNED_PRIVATE_INPUT_REFUSED '+label)
 with zipfile.ZipFile(files['r298']) as z:
  if sha256(z.read('bin/R298_SOURCE_BUILT_CLASS_ONLY.jar'))!=R298_JAR:raise ValueError('R298_R298_JAR_MISMATCH')
 with zipfile.ZipFile(files['r285']) as z:
  if z.testzip():raise ValueError('R298_R285_ZIP_CRC_FAILURE')
  for k,sha in SCRIPTS.items():
   if sha256(z.read(k))!=sha:raise ValueError('R298_ORIGINAL_R285_SCRIPT_DRIFT '+k)
  patch_wrapper(z.read('scripts/Run-R285-Fresh-GUI.py').decode())
  patch_probe(z.read('scripts/probe/run_r285_gui.py').decode())
 return files

def create_kit(r285,kit):
 if kit.exists():raise FileExistsError('R298_REFUSE_EXISTING_KIT')
 kit.mkdir()
 with zipfile.ZipFile(r285) as z:
  for item in z.infolist():
   if not item.filename.startswith('scripts/') or item.is_dir():continue
   parts=pathlib.PurePosixPath(item.filename)
   if parts.is_absolute() or '..' in parts.parts:raise ValueError('R298_ZIP_TRAVERSAL')
   target=kit/item.filename;target.parent.mkdir(parents=True,exist_ok=True)
   data=z.read(item)
   if item.filename=='scripts/Run-R285-Fresh-GUI.py':data=patch_wrapper(data.decode()).encode()
   if item.filename=='scripts/probe/run_r285_gui.py':data=patch_probe(data.decode()).encode()
   target.write_bytes(data)
 return kit/'scripts/Run-R285-Fresh-GUI.py'

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--input-dir',required=True,type=pathlib.Path)
 p.add_argument('--output',required=True,type=pathlib.Path)
 p.add_argument('--preflight-only',action='store_true')
 a=p.parse_args(argv)
 input_dir=a.input_dir.expanduser().absolute();output=a.output.expanduser().absolute()
 if output.exists() or output.is_symlink() or not output.parent.is_dir() or output.parent.is_symlink():raise ValueError('R298_UNSAFE_EXISTING_OR_MISSING_OUTPUT')
 if input_dir.resolve() in output.parent.resolve().parents or output.parent.resolve()==input_dir.resolve():raise ValueError('R298_OUTPUT_WITHIN_INPUTS')
 archives=preflight(input_dir)
 print('R298_ALL_SEVEN_INPUTS_AND_SOURCE_OVERLAYS_PINNED',flush=True)
 if a.preflight_only:return 0
 if sys.platform!='linux':raise ValueError('R298_ONLY_XVFB_LINUX_SUPPORTED')
 with tempfile.TemporaryDirectory(prefix='r298-provenance-') as t:
  runner=create_kit(archives['r285'],pathlib.Path(t)/'kit')
  cmd=[sys.executable,'-u',str(runner)]
  for label in ('r278','r265','assets','original','r230','r298'):
   cmd.extend(['--'+label,str(archives[label])])
  cmd.extend(['--output',str(output)])
  subprocess.run(cmd,check=True,timeout=120)
 print('R298_R298_SOURCE_BUILT_LINUX_GUI_REPLAY_PASS '+str(output),flush=True)
 return 0
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Run a bounded source-built v309 OSRS Cook probe from five checksum-locked owner archives.

Never overwrites existing output, modifies installed client, or connects to live SpawnPK.
Only local mock host 127.0.0.1:43594, no credentials supplied by user.
"""
import argparse,hashlib,json,os,pathlib,shutil,signal,subprocess,sys,time,zipfile
P=pathlib.Path(__file__).resolve().parent
EXPECTED={
 'r278':'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280',
 'r265':'9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb',
 'assets':'8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565',
 'original':'ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38',
 'r230':'5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125'}
JAR='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'
p=argparse.ArgumentParser()
for name in (*EXPECTED,'output'):p.add_argument('--'+name,required=True)
a=p.parse_args()
root=pathlib.Path(a.output).resolve()
if root.exists() or root==pathlib.Path('/') or root==pathlib.Path.home():raise SystemExit('R285_REFUSE_EXISTING_OR_UNSAFE_OUTPUT '+str(root))
def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as stream:
  for block in iter(lambda:stream.read(2**20),b''):h.update(block)
 return h.hexdigest()
for name,expect in EXPECTED.items():
 filename=getattr(a,name)
 if digest(filename)!=expect:raise SystemExit('R285_INPUT_HASH_MISMATCH '+name)
print('R285_ALL_FIVE_ORIGINAL_OWNER_SHA256_PASS',flush=True)
root.mkdir(parents=True)
try:
 stage=root/'testhome'
 command=[sys.executable,str(P/'stage_owner_inputs.py')]
 for name in ('r265','assets','original','r230'):command.extend(['--'+name,str(getattr(a,name))])
 command.extend(['--output',str(stage)])
 subprocess.run(command,check=True,timeout=90)
 with zipfile.ZipFile(a.r278) as z:
  jar=stage/'R278_SOURCE_BUILT_CLASS_ONLY.jar';jar.write_bytes(z.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar'))
 if digest(jar)!=JAR:raise RuntimeError('staged private R278 JAR hash incorrect')
 scripts=root/'scripts'
 # Copy authored scripts/fixture, never copy original cached assets to published evidence.
 shutil.copytree(P,scripts,ignore=shutil.ignore_patterns('__pycache__','robot_classes','*.log','*.png','*.json'))
 probe=scripts/'probe';classes=probe/'robot_classes';classes.mkdir()
 subprocess.run(['javac','--release','11','-encoding','UTF-8','-d',str(classes),str(probe/'RobotLogin.java'),str(probe/'CookRobotR285.java')],check=True,timeout=35)
 print('R285_FRESH_ARCHIVE_STAGE_PASS files=10772 client_jar='+JAR,flush=True)
 command=['xvfb-run','-a','-s','-screen 0 1400x900x24',sys.executable,'-u',str(probe/'run_r285_gui.py'),'--testhome',str(stage)]
 with (root/'R285_outer.log').open('w') as sink:
  proc=subprocess.Popen(command,stdout=sink,stderr=subprocess.STDOUT,start_new_session=True)
  try:return_code=proc.wait(timeout=85)
  except subprocess.TimeoutExpired:
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    proc.wait(timeout=3)
   raise RuntimeError('R285_FRESH_GUI_DEADLINE_EXCEEDED; child process group terminated')
 if return_code!=0:raise RuntimeError('R285_FRESH_GUI_EXIT='+str(return_code))
 timeline=json.loads((probe/'R285_timeline.json').read_text())
 if timeline['status']!='PASS':raise RuntimeError('GUI subprocess did not attest successful acceptance')
 r=json.loads((probe/'r276_object_action_receipt.json').read_text())
 wire=(probe/'r276_object_action_wire.bin').read_bytes()
 if len(r['object_interactions'])!=1 or len(r['acknowledged_objects'])!=1:raise RuntimeError('Cook count not 1')
 v=r['object_interactions'][0];ack=r['acknowledged_objects'][0]
 if (v['opcode'],v['length'],v['object_id'],v['world_x'],v['world_y'])!=(132,6,114,3362,4769):raise RuntimeError('decoded object action mismatched')
 if (ack['requested_opcode'],ack['response_opcode'],ack['object_id'])!=(132,253,114):raise RuntimeError('no paired reply')
 if hashlib.sha256(wire).hexdigest()!=r['wire_sha256']:raise RuntimeError('wire witness hash mismatch')
 if '[Regions] Loaded region ID: 13386 (field1134)' not in (probe/'R285_client.log').read_text():raise RuntimeError('wrong region bank')
 for name in ('R285_Cook_context.png','R285_after_Cook.png','R285_osrs_world.png'):
  if not (probe/name).exists():raise RuntimeError('missing GUI image '+name)
 print('R285_FRESH_FIVE_ARCHIVE_GUI_COOK_PASS archive_assets=10772 region13386=field1134 Cook114_opcode132 reply253 wire_sha256='+r['wire_sha256'],flush=True)
except Exception as ex:
 (root/'R285_wrapper_error.json').write_text(json.dumps({'type':type(ex).__name__,'error':str(ex)},indent=2)+'\n')
 raise

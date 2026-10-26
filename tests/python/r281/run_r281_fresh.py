#!/usr/bin/env python3
"""Read-only, exact-owner-input fresh-home R281 Cave Enter -> walk GUI replay."""
import argparse,hashlib,json,pathlib,subprocess,shutil,sys,zipfile
P=pathlib.Path(__file__).resolve().parent
q=argparse.ArgumentParser()
for opt in ('r278','r265','assets','original','r230','output'):q.add_argument('--'+opt,required=True)
a=q.parse_args();root=pathlib.Path(a.output).resolve()
if root.exists() or root==pathlib.Path('/'):
 raise SystemExit('R281_REFUSE_EXISTING_DESTINATION '+str(root))
sha=lambda x:hashlib.file_digest(open(x,'rb'),'sha256').hexdigest()
if sha(a.r278)!='e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280':raise SystemExit('R281_R278_OWNER_HASH_MISMATCH')
subprocess.run([sys.executable,str(P/'stage_owner_inputs.py'),'--r265',a.r265,'--assets',a.assets,'--original',a.original,'--r230',a.r230,'--output',str(root)],check=True)
with zipfile.ZipFile(a.r278) as z:
 jar=root/'R278_SOURCE_BUILT_CLASS_ONLY.jar';jar.write_bytes(z.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar'))
if sha(jar)!='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd':raise SystemExit('R281_CLASS_ONLY_JAR_MISMATCH')
(root/'isolated_home').rename(root/'isolated_home3')
shutil.copytree(P/'probe',root/'probe')
classes=root/'probe'/'robot_classes';classes.mkdir()
subprocess.run(['javac','--release','11','-d',str(classes),str(root/'probe'/'RobotLogin.java'),str(root/'probe'/'CaveEnterRobot.java')],check=True)
cmd=['xvfb-run','-a','-s','-screen 0 1400x900x24',sys.executable,str(root/'probe'/'run_r281_cave.py')]
print('R281_ORIGINAL_PRIVATE_INPUT_HASHES_PASS_AND_JAVA11_ROBOTS_COMPILED',flush=True)
run=subprocess.run(cmd,capture_output=True,text=True,timeout=100)
(root/'r281_process.log').write_text(run.stdout+'\nSTDERR:\n'+run.stderr)
print(run.stdout[-6000:],flush=True)
if run.returncode!=0:raise SystemExit('R281_CAVE_GUI_EXIT_'+str(run.returncode))
assert 'R281_COMPLETE_REAL_GUI_PASS' in run.stdout
r=json.loads((root/'probe'/'r276_object_action_receipt.json').read_text());w=json.loads((root/'probe'/'R280_live_walk_ack.json').read_text())
assert r['map_ready'] and r['error'] is None and len(r['object_interactions'])==1
assert (r['object_interactions'][0]['opcode'],r['object_interactions'][0]['object_id'],r['object_interactions'][0]['world_x'],r['object_interactions'][0]['world_y'])==(132,2,3201,3202)
assert w['object_ids']==[2] and w['parser_error'] is None and w['walk']['local_target']==[46,51]
print('R281_FRESH_OWNER_ARCHIVE_GUI_CAVE_AND_WALK_PASS',flush=True)

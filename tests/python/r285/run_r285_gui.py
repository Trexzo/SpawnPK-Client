#!/usr/bin/env python3
"""Bounded isolated GUI replay using already checksum-staged private owner test home.
Never connects outside 127.0.0.1; no game source or private assets emitted.
"""
import argparse,hashlib,json,os,pathlib,signal,subprocess,sys,time,traceback
from PIL import ImageGrab,Image
R=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--testhome',required=True)
a=p.parse_args()
B=pathlib.Path(a.testhome).resolve();HOME=B/'isolated_home'
CP=os.pathsep.join(str(path) for path in [B/'R278_SOURCE_BUILT_CLASS_ONLY.jar',B/'runtime/dependencies/R239_EXACT_RUNTIME_LIB.jar',B/'runtime/dependencies/R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar',B/'resources_only.jar'])
ENV=dict(os.environ,HOME=str(HOME),R276_SESSION_LIMIT='50',PYTHONUNBUFFERED='1')
PROCS=[];HANDLES=[]
T=time.monotonic();timeline=[]
def stamp(kind,**kw):
 event={'elapsed':round(time.monotonic()-T,3),'event':kind,**kw};timeline.append(event)
 print('R285_STAGE '+json.dumps(event,sort_keys=True),flush=True)
def launch(command,name):
 output=(R/name).open('w');HANDLES.append(output)
 process=subprocess.Popen(command,env=ENV,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
 PROCS.append((name,process));stamp('launched',name=name,pid=process.pid);return process
def alive(*procs):
 for proc in procs:
  if proc.poll() is not None:raise RuntimeError('required child exited: '+str(proc.pid)+'='+str(proc.returncode))
def contains(path,needle):
 try:return needle in path.read_text(errors='replace')
 except FileNotFoundError:return False
def await_condition(label,seconds,condition,requires=()):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  alive(*requires)
  if condition():stamp(label);return
  time.sleep(.2)
 raise TimeoutError(label+' timed out after '+str(seconds)+'s')
def snap(name):
 tmp=R/(name+'.partial.png')
 ImageGrab.grab().save(tmp)
 with Image.open(tmp) as image:
  img=image.convert('RGB');assert img.size==(1400,900),img.size
  crop=img.crop((136,185,640,520))
  ratio=sum(max(rgb)>30 for rgb in crop.getdata())/(crop.width*crop.height)
 if ratio<=.95:raise AssertionError('view not rendered '+name+' ratio='+str(ratio))
 os.replace(tmp,R/(name+'.png'));stamp('rendered_screenshot',name=name,nonblack=round(ratio,5))
def robot(classname,name,timeout=25):
 proc=launch(['java','-Djava.awt.headless=false','-cp',str(R/'robot_classes'),classname,*( [str(R)] if classname=='CookRobotR285' else [] )],name)
 try:code=proc.wait(timeout=timeout)
 except subprocess.TimeoutExpired as ex:raise TimeoutError(classname+' timed out') from ex
 if code!=0:raise RuntimeError(classname+' failed '+str(code))
 stamp('robot_completed',classname=classname)
 return proc

def valid_receipt():
 f=R/'r276_object_action_receipt.json'
 if not f.exists():return False
 try:
  obj=json.loads(f.read_text())
  if obj['source']!='actual-localhost-wire-ISAAC' or not obj['map_ready'] or obj['error'] is not None:return False
  if len(obj['object_interactions'])!=1 or len(obj['acknowledged_objects'])!=1:return False
  item=obj['object_interactions'][0];ack=obj['acknowledged_objects'][0]
  return (item['opcode'],item['length'],item['object_id'],item['world_x'],item['world_y'])==(132,6,114,3362,4769) and (ack['object_id'],ack['requested_opcode'],ack['response_opcode'])==(114,132,253)
 except (KeyError,ValueError,TypeError,IndexError):return False

status='FAIL'
try:
 expected='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'
 jar=B/'R278_SOURCE_BUILT_CLASS_ONLY.jar'
 if not jar.is_file() or hashlib.sha256(jar.read_bytes()).hexdigest()!=expected:raise RuntimeError('R285 private R278 JAR hash mismatch')
 stamp('pinned_jar_verified')
 for name in ('r276_object_action_receipt.json','r276_object_action_wire.bin','R284_Cook_context.png','R284_after_Cook.png','R285_Cook_context.png','R285_after_Cook.png','R285_after_login.png','R285_osrs_world.png'):
  (R/name).unlink(missing_ok=True)
 server=launch([sys.executable,'-u',str(R/'local_probe_r284.py')],'R285_server.log')
 time.sleep(1)
 client=launch(['java','-Djava.awt.headless=false','-Duser.home='+str(HOME),'-Dspk.serverHost=127.0.0.1','-Dspk.serverPort=43594','-Dspk.offlineProbe=true','-Dspk.capture=true','-Dspk.capture.dir='+str(R/'capture'),'-cp',CP,'rs.gui.Launcher'],'R285_client.log')
 # Avoid hitting login before AWT window appears; bounded wait plus time for UI initialization.
 await_condition('client_ui_loaded',30,lambda:contains(R/'R285_client.log','Unpacking media load time'),(client,server))
 time.sleep(1.2)
 robot('RobotLogin','R285_login.log',24)
 await_condition('legacy_osrs_region_selected',28,lambda:contains(R/'R285_client.log','[Regions] Loaded region ID: 13386 (field1134)'),(client,server))
 await_condition('mapready_and_object_spawn',20,lambda:contains(R/'R285_server.log','R276_LIVE_OBJECT_SPAWN_SENT_POST_MAPREADY'),(client,server))
 # Real object model insertion can lag an otherwise populated terrain. Use a
 # bounded post-spawn settling interval, not the older immediate terrain gate.
 stamp('model_settle_started');end=time.monotonic()+5
 while time.monotonic()<end:alive(client,server);time.sleep(.2)
 snap('R285_osrs_world')
 robot('CookRobotR285','R285_robot.log',24)
 await_condition('actual_cook_receipt',12,valid_receipt,(client,server))
 snap('R285_after_login')
 receipt=json.loads((R/'r276_object_action_receipt.json').read_text())
 wire=(R/'r276_object_action_wire.bin').read_bytes()
 assert hashlib.sha256(wire).hexdigest()==receipt['wire_sha256'] and len(wire)==receipt['wire_bytes']
 assert contains(R/'R285_client.log','[Regions] Loaded region ID: 13386 (field1134)')
 stamp('cook_packet_and_reply_verified',wire_bytes=len(wire),wire_sha256=receipt['wire_sha256'])
 status='PASS'
 print('R285_BOUND_ISOLATED_OSRS_COOK_GUI_PASS id=114 opcode132=6 reply253 region13386 bank=field1134',flush=True)
except Exception as exc:
 stamp('failure',reason=type(exc).__name__+': '+str(exc))
 traceback.print_exc()
finally:
 for name,proc in reversed(PROCS):
  if proc.poll() is None:
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
 for name,proc in reversed(PROCS):
  try:proc.wait(timeout=2)
  except subprocess.TimeoutExpired:
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   try:proc.wait(timeout=2)
   except subprocess.TimeoutExpired:pass
  stamp('child_cleaned',name=name,code=proc.poll())
 for handle in HANDLES:handle.close()
 (R/'R285_timeline.json').write_text(json.dumps({'status':status,'events':timeline},indent=2)+'\n')
 print('R285_SESSION_TERMINATED status='+status,flush=True)
if status!='PASS':sys.exit(1)

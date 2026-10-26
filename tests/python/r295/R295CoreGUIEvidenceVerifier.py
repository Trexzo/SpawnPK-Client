#!/usr/bin/env python3
"""R295: verify actual *inner* GUI receipts without upgrading timed-out outer wrapper status.

Source-only verifier, no game resources or Java bytecode. The outer wrapper must
NOT be called a full pass when its success marker is absent.
"""
from pathlib import Path
import hashlib, io, json, zipfile, sys
from PIL import Image

PINNED_R295='f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35'

def verify(path):
 count=0
 def ck(assertion, reason):
  nonlocal count
  if not assertion:raise AssertionError('R295_INVALID_CORE_GUI_EVIDENCE '+reason)
  count+=1
 with zipfile.ZipFile(path) as z:
  ck(z.testzip() is None,'CRC check')
  m=json.loads(z.read('MANIFEST.json'))
  ck(m['milestone']=='R295','milestone mismatch')
  ck(m['compiled_r295_jar_sha256']==PINNED_R295,'wrong reconstructed client')
  ck(m['sessions']==2,'missing independent fresh sessions')
  ck(m['inner_gui_status']=='PASS_BOTH','no inner status success')
  ck(m['outer_wrapper_status']=='TIMEOUT_BOTH_NOT_ACCEPTED','outer wrapper must not be called pass')
  ck(m['native_windows_gui']=='NOT_TESTED','false native Windows status')
  ck(m['contains_client_classes_or_original_assets'] is False,'private game bytes disallowed')
  ck(set(z.namelist())==set(m['files'])|{'MANIFEST.json'},'unexpected additional entries')
  for name,d in m['files'].items():
   b=z.read(name)
   ck(len(b)==d['size'],'size mismatch '+name)
   ck(hashlib.sha256(b).hexdigest()==d['sha256'],'SHA mismatch '+name)
   ck(not name.lower().endswith(('.jar','.class','.dat','.idx','.zip','.ttf','.otf')),'private binary in public-safe evidence '+name)
  wirehashes=[];worlds=[]
  for i in (1,2):
   prefix=f'evidence/fresh{i}/'
   receipt=json.loads(z.read(prefix+'receipt.json'));wire=z.read(prefix+'received_wire.bin')
   ck(receipt['source']=='actual-localhost-wire-ISAAC','not from local socket')
   ck(receipt['map_ready'] is True and receipt['error'] is None,'world not ready')
   ck(len(receipt['object_interactions'])==1,'outbound count mismatch')
   ck(len(receipt['acknowledged_objects'])==1,'reply count mismatch')
   x=receipt['object_interactions'][0];ack=receipt['acknowledged_objects'][0]
   ck((x['opcode'],x['length'],x['object_id'])==(132,6,114),'Cook packet mismatch')
   ck((x['world_x'],x['world_y'])==(3362,4769),'world position mismatch')
   ck((ack['requested_opcode'],ack['response_opcode'],ack['object_id'])==(132,253,114),'ack mismatch')
   ck(ack['wire_offset']==x['offset'],'ack offset mismatch')
   ck(ack['text']=='Object 114: isolated test interaction.','reply is not isolated mock')
   ck(len(wire)==52 and x['offset']+7<=len(wire),'wire payload length mismatch')
   ck(hashlib.sha256(wire).hexdigest()==receipt['wire_sha256'],'actual wire SHA mismatch')
   wirehashes.append(receipt['wire_sha256'])
   timeline=json.loads(z.read(prefix+'timeline.json'))
   ck(timeline['status']=='PASS','core test reported failure')
   events=[e['event'] for e in timeline['events']]
   for marker in ('pinned_jar_verified','client_ui_loaded','robot_completed','legacy_osrs_region_selected','mapready_and_object_spawn','actual_cook_receipt','cook_packet_and_reply_verified'):
    ck(marker in events,'missing timeline event '+marker)
   ck(events.index('legacy_osrs_region_selected')<events.index('mapready_and_object_spawn')<events.index('actual_cook_receipt'),'wrong interaction order')
   ck('failure' not in events,'timeline recorded error')
   outer=z.read(prefix+'outer.log').decode(errors='replace')
   ck('R285_BOUND_ISOLATED_OSRS_COOK_GUI_PASS' in outer,'inner GUI did not attest Cook')
   ck('R285_SESSION_TERMINATED status=PASS' in outer,'inner did not close cleanly')
   wrapper=z.read(prefix+'wrapper.log').decode()
   ck('R295_ALL_SEVEN_INPUTS_AND_SOURCE_OVERLAYS_PINNED' in wrapper,'owner inputs not SHA admitted')
   ck('R268_PRIVATE_TEST_HOME_STAGED files=10772' in wrapper,'cache staging absent')
   ck('R295_R295_FRESH_ARCHIVE_STAGE_PASS files=10772' in wrapper,'R295 JAR not staged')
   ck('R295_R295_FRESH_GUI_COOK_PASS' not in wrapper,'outer wrapper unexpectedly marked pass')
   client=z.read(prefix+'client.log').decode(errors='replace')
   ck('[Regions] Loaded region ID: 13386 (field1134)' in client,'no real region 13386')
   server=z.read(prefix+'server.log').decode(errors='replace')
   ck('R276_SERVER_ACTUAL_OBJECT132_RECEIVED' in server,'server never received action')
   ck('object=114 xy=3362,4769' in server,'unexpected object interaction')
   robot=z.read(prefix+'robot.log').decode(errors='replace')
   ck('R285_ACTUAL_OSRS_COOK_OPTION_CLICKED' in robot,'robot Cook click missing')
   for name in ('R285_osrs_world.png','R285_Cook_context.png','R285_after_Cook.png'):
    data=z.read(prefix+name)
    ck(data.startswith(b'\x89PNG\r\n\x1a\n'),'not screenshot PNG')
    img=Image.open(io.BytesIO(data)).convert('RGB')
    ck(img.size==(1400,900),'unexpected render dimensions')
    crop=img.crop((136,185,640,520));flat=crop.getdata()
    filled=sum(max(rgb)>30 for rgb in flat)/(crop.width*crop.height)
    ck(filled>.95,'empty game viewport')
   worlds.append(z.read(prefix+'R285_osrs_world.png'))
  ck(wirehashes[0]!=wirehashes[1],'socket traces are not independent')
  ck(worlds[0]!=worlds[1],'screenshots not independent')
 print(f'R295_TWO_REAL_GUI_INNER_RECEIPTS_PASS checks={count} inner=2 outer=TIMEOUT_NOT_ACCEPTED windows=NOT_TESTED',flush=True)
 return count

if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('usage: R295CoreGUIEvidenceVerifier.py PRIVATE_EVIDENCE.zip')
 verify(sys.argv[1])

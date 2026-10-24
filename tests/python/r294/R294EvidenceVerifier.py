#!/usr/bin/env python3
"""Read-only, source-free R294 two *fresh* R293 GUI session + failure-path evidence verifier."""
import hashlib,io,json,sys,zipfile
from PIL import Image
JAR='0d0eedae92efe709b2d6eb49b1fc4432db174a6e68a7f06fd4fc2736d0f6cee9'

def verify(path):
 checks=0
 def ck(ok,description):
  nonlocal checks
  if not ok:raise AssertionError('R294_EVIDENCE_FAILED: '+description)
  checks+=1
 with zipfile.ZipFile(path) as z:
  ck(z.testzip() is None,'archive CRC')
  meta=json.loads(z.read('MANIFEST.json'))
  ck(meta['milestone']=='R294' and meta['production_source_changes']==0,'milestone/scope')
  ck(meta['compiled_client_jar_sha256']==JAR,'wrong source-built binary')
  ck(meta['native_windows_gui']=='NOT_TESTED' and meta['original_online_server']=='NOT_TESTED','do not claim Windows/live server')
  ck(not meta['private_binaries_in_package'],'no reconstructed private client in evidence')
  ck(meta['fresh_home_replays']==2 and meta['both_fresh_wrapper_exit_zero'] is True,'overclaimed replay reproducibility')
  ck(set(z.namelist())==set(meta['files'])|{'MANIFEST.json'},'unlisted extra file')
  for n,entry in sorted(meta['files'].items()):
   blob=z.read(n)
   ck(len(blob)==entry['size'],'file size '+n)
   ck(hashlib.sha256(blob).hexdigest()==entry['sha256'],'entry SHA '+n)
   ck(not n.lower().endswith(('.class','.jar','.ttf','.otf','.dat','.idx','.zip')),'private binary/cache leaked '+n)
  hashes=[]
  for idx in (1,2):
   base=f'evidence/fresh{idx}/'
   r=json.loads(z.read(base+'receipt.json'));wire=z.read(base+'received_wire.bin')
   ck(r['source']=='actual-localhost-wire-ISAAC','source receipt not live socket')
   ck(r['map_ready'] and r['error'] is None,'mapready/socket parser')
   ck(len(r['object_interactions'])==1 and len(r['acknowledged_objects'])==1,'one Cook and response')
   o=r['object_interactions'][0];a=r['acknowledged_objects'][0]
   ck((o['opcode'],o['length'],o['object_id'],o['world_x'],o['world_y'])==(132,6,114,3362,4769),'invalid Cook action')
   ck((a['object_id'],a['requested_opcode'],a['response_opcode'],a['wire_offset'])==(114,132,253,o['offset']),'missing matched response')
   ck(a['text']=='Object 114: isolated test interaction.','response not synthetic')
   ck(len(wire)==r['wire_bytes'] and o['offset']+7<=len(wire),'wire size/offset mismatch')
   ck(hashlib.sha256(wire).hexdigest()==r['wire_sha256'],'wire hash mismatch')
   ck(r['session_s']>6,'not post-login action')
   client=z.read(base+'client.log').decode(errors='replace')
   for line in ('[Region] Stand in region: 13386','[Region] Region group: white_portal','[Regions] Loaded region ID: 13386 (field1134)'):
    ck(line in client,'real compiled client bank '+line)
   srv=z.read(base+'server.log').decode()
   ck('R276_LIVE_MAPREADY121_WIRE_RECEIVED' in srv,'mapready listener witness missing')
   ck('R276_LIVE_OBJECT_SPAWN_SENT_POST_MAPREADY' in srv,'real model spawn ordering')
   ck('R276_SERVER_ACTUAL_OBJECT132_RECEIVED' in srv and 'object=114 xy=3362,4769' in srv,'server action not received')
   robot=z.read(base+'robot.log').decode()
   for k in ('R285_ACTUAL_OSRS_COOK_CONTEXT_MENU_CAPTURED','R285_ACTUAL_OSRS_COOK_OPTION_CLICKED','R285_ROBOT_CLICK_AND_ATOMIC_SCREENSHOTS_PASS'):
    ck(k in robot,'real AWT GUI click '+k)
   timeline=json.loads(z.read(base+'timeline.json'))
   ck(timeline['status']=='PASS','runner status')
   events=timeline['events'];labels=[e['event'] for e in events]
   for k in ('pinned_jar_verified','client_ui_loaded','robot_completed','legacy_osrs_region_selected','mapready_and_object_spawn','model_settle_started','actual_cook_receipt','cook_packet_and_reply_verified'):
    ck(k in labels,'missing bounded process stage '+k)
   ck('failure' not in labels,'runner contains failure event')
   ck(labels.index('legacy_osrs_region_selected')<labels.index('mapready_and_object_spawn')<labels.index('model_settle_started')<labels.index('actual_cook_receipt'),'invalid stage order')
   for child in ('R285_client.log','R285_server.log'):
    ck(any(e['event']=='child_cleaned' and e.get('name')==child and e.get('code') is not None for e in events),'unreaped child '+child)
   wrapper=z.read(base+'fresh_wrapper.log').decode()
   ck('R294_ALL_FIVE_OWNER_AND_R293_SHA256_PASS' in wrapper,'all five exact source archives not checked')
   ck('R268_PRIVATE_TEST_HOME_STAGED files=10772' in wrapper,'fresh cache staging missing')
   ck('R294_R293_FRESH_ARCHIVE_STAGE_PASS files=10772' in wrapper,'GUI recompiled in new home')
   ck('R294_R293_FRESH_GUI_COOK_PASS' in wrapper,'full wrapper did not accept Cook')
   outer=z.read(base+'outer.log').decode(errors='replace')
   ck('R285_BOUND_ISOLATED_OSRS_COOK_GUI_PASS' in outer and 'R285_SESSION_TERMINATED status=PASS' in outer,'child test completion missing')
   for name in ('R285_osrs_world.png','R285_Cook_context.png','R285_after_Cook.png','R285_after_login.png'):
    raw=z.read(base+name)
    ck(raw[:8]==b'\x89PNG\r\n\x1a\n','not a real GUI PNG '+name)
    im=Image.open(io.BytesIO(raw)).convert('RGB')
    ck(im.size==(1400,900),'Xvfb screen size '+name)
    view=im.crop((136,185,640,520))
    ratio=sum(max(rgb)>30 for rgb in view.getdata())/(view.width*view.height)
    ck(ratio>.95,'world not genuinely populated '+name)
   hashes.append(r['wire_sha256'])
  ck(z.read('evidence/fresh1/R285_osrs_world.png')!=z.read('evidence/fresh2/R285_osrs_world.png'),'two distinct rendered screenshots')
  ck(hashes[0]!=hashes[1],'separate sessions did not produce distinct ciphertext')
  bad=z.read('evidence/negative_hash_preflight.log').decode()
  ck('R294_PINNED_PRIVATE_INPUT_REFUSED r278' in bad,'input tampering refusal not tested')
  exist=z.read('evidence/negative_existing_destination.log').decode()
  ck('R294_UNSAFE_EXISTING_OR_MISSING_OUTPUT' in exist,'existing output refusal not tested')
  ck('REFUSED_NO_WRITES_PASS' in z.read('evidence/negative_test_summary.log').decode(),'negative test write barrier absent')
 print(f'R294_TWO_FRESH_R293_GUI_REPLAYS_EVIDENCE_PASS checks={checks} fresh=2 object114=Cook opcode132=6 reply253=2 region=13386 bank=field1134 negative_guards=2')
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: python R294EvidenceVerifier.py R294_PRIVATE_EVIDENCE.zip')
 verify(sys.argv[1])

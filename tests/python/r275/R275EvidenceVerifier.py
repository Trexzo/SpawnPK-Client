#!/usr/bin/env python3
"""Independent R275 source-free archive evidence verification."""
import hashlib,json,struct,sys,zipfile
def check_file(path):
 n=0
 def ck(ok,label):
  nonlocal n
  if not ok:raise AssertionError(label)
  n+=1
 with zipfile.ZipFile(path) as z:
  ck(z.testzip() is None,'CRC')
  m=json.loads(z.read('MANIFEST.json'))
  ck(m['milestone']=='R275','milestone')
  ck(set(z.namelist())==set(m['files'])|{'MANIFEST.json'},'file set')
  for name,entry in m['files'].items():
   b=z.read(name)
   ck(len(b)==entry['bytes'],'length '+name)
   ck(hashlib.sha256(b).hexdigest()==entry['sha256'],'sha256 '+name)
  log=z.read('logs/R275_FRESH_INPUT_OFFLINE_49_PASS.log').decode(errors='replace')
  ck('R275_ACTUAL_PENDING_OBJECT_PROMOTION_PASS checks=37' in log,'real pending scene')
  ck('R275_INCOMING_OBJECT60_LENGTH_AND_151_TILE_PASS checks=12' in log,'nested 151')
  ck('R275_ALL_OFFLINE_PASS real_compiled_client=37 synthetic_framing=12 total=49' in log,'49-check combined test')
  ck('R274_FULL_REBUILT_CLIENT_ALL_SELECTED_REGRESSIONS_PASS suites=8' in z.read('logs/R274_JAR_316_COMPATIBILITY_PASS.log').decode(),'R274 prior baseline')
  hashes=[]
  for i in (1,2):
   root=f'evidence/replay{i}/'
   r=json.loads(z.read(root+'server_receipt.json'))
   wire=z.read(root+'outbound_wire.bin')
   run=z.read(root+'run.log').decode()
   ck(r['error'] is None and r['map_ready'],'loopback packet failure')
   ck(r['session_s']>=6,'too short')
   ck(r['wire_bytes']==len(wire),'wire byte count')
   ck(r['wire_sha256']==hashlib.sha256(wire).hexdigest(),'wire hash mismatch')
   ck(len(r['object_interactions'])==len(r['acknowledged_objects'])==1,'action pair absent')
   act=r['object_interactions'][0];reply=r['acknowledged_objects'][0]
   ck((act['opcode'],act['object_id'],act['world_x'],act['world_y'],act['offset'])==(132,104,3202,3201,42),'wrong object packet')
   ck(act['length']==6,'wrong packet length')
   ck(reply['wire_offset']==act['offset'],'server reply not correlated')
   ck(reply['requested_opcode']==132 and reply['response_opcode']==253,'response framing')
   ck(reply['text']=='Chest: The lid creaks open.','synthetic chat response')
   ck('R275_GUI_CHEST_SEARCH_LOCALHOST_OPCODE132_PASS' in run,'client GUI interaction')
   ck('R275_AWT_RIGHT_CLICK_MENU_SNAPSHOT' in run and 'R275_AWT_SEARCH_MENU_OPTION_CLICKED' in run,'AWT menu selection')
   for name in ('chest_menu.png','chest_reply.png'):
    b=z.read(root+name)
    ck(b[:8]==b'\x89PNG\r\n\x1a\n','PNG signature')
    ck(struct.unpack('>II',b[16:24])==(1400,900),'screen dimensions')
   hashes.append(r['wire_sha256'])
  ck(hashes[0]!=hashes[1],'two identical wire captures')
 print(f'R275_EVIDENCE_ARCHIVE_PASS checks={n} replays=2 object132=2 ack253=2')
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: python R275EvidenceVerifier.py R275_EVIDENCE.zip')
 check_file(sys.argv[1])

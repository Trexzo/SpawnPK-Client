#!/usr/bin/env python3
"""Source-free R284 local-Cook evidence validation; no game source or credentials."""
import hashlib,io,json,sys,zipfile
from PIL import Image
EXPECTED_JAR='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'

def verify(path):
 checks=0
 def ck(ok,what):
  nonlocal checks
  if not ok:raise AssertionError('R284_EVIDENCE_FAIL '+what)
  checks+=1
 with zipfile.ZipFile(path) as z:
  ck(z.testzip() is None,'ZIP CRC')
  m=json.loads(z.read('MANIFEST.json'))
  ck(m['milestone']=='R284' and m['production_source_changes']==0,'scope/milestone mismatch')
  ck(m['client_jar_sha256']==EXPECTED_JAR,'wrong R278 source-built class JAR')
  ck(m['verified_gui_replays']==2 and m['experimental_one_command_runner_passed'] is False,'overstated replay acceptance')
  ck(set(z.namelist())==set(m['files'])|{'MANIFEST.json'},'unlisted ZIP content')
  for name,meta in m['files'].items():
   data=z.read(name)
   ck(len(data)==meta['size'],'size '+name)
   ck(hashlib.sha256(data).hexdigest()==meta['sha256'],'SHA '+name)
   ck(not name.lower().endswith(('.jar','.class','.dat','.idx','.ttf','.otf')),'private asset in archive '+name)
  direct=z.read('evidence/R283_35_CHECK_REGRESSION_PASS.log').decode()
  ck('R283_AUTHENTIC_REGION_BANK_SELECTOR_PASS checks=35' in direct,'R283 original Java selector checks missing')
  ck('R283_CLEAN_OWNER_INPUT_REGION_SELECTOR_PASS checks=35' in direct,'R283 clean runner missing')
  hashes=[]
  for i in (1,2):
   root=f'evidence/replay{i}/'
   receipt=json.loads(z.read(root+'r276_object_action_receipt.json'))
   wire=z.read(root+'r276_object_action_wire.bin')
   ck(receipt['source']=='actual-localhost-wire-ISAAC','not an independently parsed wire capture')
   ck(receipt['error'] is None and receipt['map_ready'] is True,'missing mapready or protocol error')
   ck(len(receipt['object_interactions'])==1 and len(receipt['acknowledged_objects'])==1,'not exactly one Cook and response')
   pkt=receipt['object_interactions'][0];ack=receipt['acknowledged_objects'][0]
   ck((pkt['opcode'],pkt['length'],pkt['object_id'])==(132,6,114),'wrong Cook wire packet')
   ck((pkt['world_x'],pkt['world_y'],pkt['offset'])==(3362,4769,44),'wrong Cook target/offset')
   ck((ack['object_id'],ack['requested_opcode'],ack['response_opcode'],ack['wire_offset'])==(114,132,253,44),'response pairing drift')
   ck(ack['text']=='Object 114: isolated test interaction.','reply must be clearly synthetic')
   ck(receipt['wire_bytes']==len(wire)==51,'wire is not the original 51 received bytes')
   ck(hashlib.sha256(wire).hexdigest()==receipt['wire_sha256'],'wire ciphertext hash mismatch')
   ck(receipt['session_s']>6,'short incomplete receipt')
   c=z.read(root+'osrs_client.log').decode(errors='replace')
   ck('[Region] Stand in region: 13386' in c,'selected region mismatch')
   ck('[Region] Region group: white_portal' in c,'region group mismatch')
   ck('[Regions] Loaded region ID: 13386 (field1134)' in c,'not real OSRS bank')
   server=z.read(root+'osrs_server.log').decode(errors='replace')
   ck('R276_LIVE_MAPREADY121_WIRE_RECEIVED' in server,'listener map ready not confirmed')
   ck('R276_SERVER_ACTUAL_OBJECT132_RECEIVED offset=44 object=114 xy=3362,4769' in server,'listener Cook not decoded')
   log=z.read(root+'client_inbound.log').decode(errors='replace')
   ck('C>S | OUT | 121 | 0 |' in log,'real client mapready missing')
   ck('S>C | PACKET | 60 | 22 |' in log,'real mixed object update missing')
   ck('C>S | OUT | 132 | 6 |' in log,'real client outbound Cook absent')
   ck('S>C | PACKET | 253 | 39 |' in log,'synthetic chat packet absent')
   for screenshot in ('R284_osrs_world.png','R284_Cook_context.png','R284_after_Cook.png'):
    img=Image.open(io.BytesIO(z.read(root+screenshot))).convert('RGB')
    ck(img.size==(1400,900),'screen dimensions '+screenshot)
    viewport=img.crop((136,185,640,520))
    nonblack=sum(max(pixel)>30 for pixel in viewport.getdata())/(viewport.width*viewport.height)
    ck(nonblack>.95,'scene black '+screenshot)
   hashes.append(receipt['wire_sha256'])
  ck(hashes[0]!=hashes[1],'nonindependent session ciphertext')
  robot=z.read('evidence/replay2/robot.log').decode()
  ck('EXIT=0' in robot,'fresh test robot failed')
  ck('R284_COOK_CONTEXT_MENU_OPENED' in robot and 'R284_ACTUAL_COOK_FIRST_OPTION_CLICKED' in robot,'AWT Cook selection absent')
  print(f'R284_REAL_OSRS_GUI_COOK_LOOPBACK_EVIDENCE_PASS checks={checks} replays=2 region=13386 bank=field1134 Cook_object=114 packet132=6 received=2 synthetic_reply253=2')
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: python tests/R284EvidenceVerifier.py R284_EVIDENCE.zip')
 verify(sys.argv[1])

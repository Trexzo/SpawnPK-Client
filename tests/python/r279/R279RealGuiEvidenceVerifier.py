#!/usr/bin/env python3
"""Read-only source-free evidence verification of actual R278 GUI object actions."""
import hashlib,io,json,struct,sys,zipfile
from PIL import Image
checks=0
def ck(ok,why):
 global checks
 if not ok:raise AssertionError('R279_EVIDENCE_FAIL '+why)
 checks+=1

def verify(path):
 global checks
 with zipfile.ZipFile(path) as z:
  ck(z.testzip() is None,'ZIP CRC')
  manifest=json.loads(z.read('MANIFEST.json'))
  ck(manifest['milestone']=='R279' and manifest['production_source_changes']==0,'wrong milestone/scope')
  ck(set(z.namelist())==set(manifest['files'])|{'MANIFEST.json'},'missing/unexpected entry')
  ck(manifest['r278_jar_sha256']=='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd','not the patched real-client binary')
  for name,entry in manifest['files'].items():
   data=z.read(name)
   ck(len(data)==entry['bytes'],'incorrect entry size '+name)
   ck(hashlib.sha256(data).hexdigest()==entry['sha256'],'incorrect entry SHA '+name)
   ck(not name.endswith(('.jar','.class','.dat','.idx')),'private production asset included '+name)
  receipts=[]
  for index in (1,2):
   base=f'evidence/replay{index}/'
   receipt=json.loads(z.read(base+'server_receipt.json'))
   wire=z.read(base+'received_ciphertext.bin')
   ck(receipt['source']=='actual-localhost-wire-ISAAC','not a real decoded socket')
   ck(receipt['error'] is None and receipt['map_ready'] is True,'login/mapready failed')
   ck(len(wire)==receipt['wire_bytes']>=50,'wrong outbound wire size')
   ck(hashlib.sha256(wire).hexdigest()==receipt['wire_sha256'],'socket bytes mismatch')
   ck(len(receipt['object_interactions'])==2,'two object actions not received')
   ck(len(receipt['acknowledged_objects'])==2,'two replies not transmitted')
   req=receipt['object_interactions'];replies=receipt['acknowledged_objects']
   ck([o['object_id'] for o in req]==[152,104],'wrong object action order')
   ck([o['opcode'] for o in req]==[132,132],'object action opcode drift')
   ck([o['length'] for o in req]==[6,6],'object action framing drift')
   ck([(o['world_x'],o['world_y']) for o in req]==[(3201,3202),(3202,3201)],'wrong selected tiles')
   ck(req[0]['offset']<req[1]['offset']<len(wire),'invalid raw packet offsets')
   ck([o['object_id'] for o in replies]==[152,104],'response pairing drift')
   ck([o['wire_offset'] for o in replies]==[o['offset'] for o in req],'response offset mismatch')
   ck(all(o['requested_opcode']==132 and o['response_opcode']==253 for o in replies),'source-compatible response not sent')
   ck(all(o['text'].startswith('Object ') and 'isolated test interaction' in o['text'] for o in replies),'not synthetic-only messages')
   runner=z.read(base+'runner.log').decode('utf-8','replace')
   ck('R279_TWO_REAL_R278_GUI_FRAME_PASS' in runner,'no rendered-gui gate')
   ck('R279_SOURCE_BUILT_GUI_TWO_DIFFERENT_OBJECTS_WIRE_PASS' in runner,'two-action GUI acceptance missing')
   capture=(base+'client_packet_capture.log')
   if capture in z.namelist():
    log=z.read(capture).decode('utf-8','replace')
    ck(log.count('C>S | OUT | 132 | 6 |')>=2,'two real client packet captures missing')
    ck(log.count('S>C | PACKET | 253 |')>=2,'two responses missing in client capture')
    ck('S>C | PACKET | 60 | 22 |' in log,'mixed four-object inbound packet missing')
    ck('C>S | OUT | 121 | 0 |' in log,'source-built map-ready packet missing')
   for frame in ('before.png','compost_menu.png','chest_menu.png'):
    b=z.read(base+frame)
    ck(b[:8]==b'\x89PNG\r\n\x1a\n','invalid PNG '+frame)
    im=Image.open(io.BytesIO(b)).convert('RGB')
    ck(im.size==(1400,900),'unexpected Xvfb size')
    if frame=='before.png':
     crop=im.crop((136,185,640,520));ratio=sum(max(pixel)>30 for pixel in crop.getdata())/(crop.width*crop.height)
     ck(ratio>.95,'GUI world not genuinely rendered')
   receipts.append(receipt['wire_sha256'])
  ck(len(set(receipts))==2,'two independent sessions share exact ciphertext')
  for file in ('evidence/cooking_range_menu.png','evidence/compost_heap_menu.png'):
   im=Image.open(io.BytesIO(z.read(file)))
   ck(im.size==(1400,900),'wrong object menu screenshot dimensions')
 print(f'R279_REAL_R278_GUI_TWO_OBJECTS_ARCHIVE_PASS checks={checks} replays=2 objects=152,104 opcodes=132,132 responses=253,253')
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: python R279RealGuiEvidenceVerifier.py <evidence.zip>')
 verify(sys.argv[1])

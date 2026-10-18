#!/usr/bin/env python3
"""Stdlib-only verifier for published, private-client-free R271 evidence ZIP."""
import hashlib,json,struct,sys,zipfile

def main(archive):
 n=0
 def check(ok,why):
  nonlocal n
  if not ok:raise AssertionError('R271_ARCHIVE_VERIFIER_FAIL: '+why)
  n+=1
 with zipfile.ZipFile(archive) as z:
  check(z.testzip() is None,'ZIP CRC')
  m=json.loads(z.read('MANIFEST.json'))
  check(m.get('milestone')=='R271' and m.get('production_changes')==0,'wrong artifact/mutation')
  for name,e in m['archive_entries'].items():
   data=z.read(name)
   check(len(data)==e['bytes'],'entry bytes mismatch '+name)
   check(hashlib.sha256(data).hexdigest()==e['sha256'],'entry SHA mismatch '+name)
  r=json.loads(z.read('evidence/replay3/server_report.json'))
  w=z.read('evidence/replay3/client_postlogin_wire.bin')
  check(r['outbound_wire_bytes']==len(w),'wire byte size')
  check(r['outbound_sha256']==hashlib.sha256(w).hexdigest(),'wire checksum')
  check(r['login']['accepted'] is True,'mock login')
  check(r.get('error') is None and not r.get('peer_closed'),'unexpected socket stop')
  check(r['session_s']>=45,'sustained session')
  check(r['heartbeat_count']>=15,'heartbeat count')
  decoded=r['decoded_client_stream']
  check(decoded['map_ready'] is True,'wire mapready121')
  check(decoded['error'] is None,'unframed later packet')
  check(decoded['stop_offset']==len(w),'ISAAC parser unconsumed data')
  check(any(p['opcode']==77 for p in decoded['packets']),'variable-length 77 not decoded')
  walks=decoded['walk_packets'];ack=r['acknowledged_walks']
  check(len(walks)==4 and len(ack)==4,'walks/acks count')
  client=z.read('evidence/replay3/client.log').decode('utf-8','replace')
  runner=z.read('evidence/replay3/run.log').decode('utf-8','replace')
  check('R271_VISIBLE_SCENE_GATE_PASS' in runner,'render gate')
  check('R271_REAL_CLICK_SERVER_ACK_PASS' in runner,'live GUI acceptance')
  check(runner.count('R271_ACTUAL_AWT_CLICK')==4,'four AWT GUI clicks')
  expected=[(46,52),(44,53),(46,63),(45,67)]
  for i,(move,reply) in enumerate(zip(walks,ack)):
   check(move['opcode']==164,'wrong movement opcode')
   check(move['declared_size']==move['length']-1,'bad variable-byte walk framing')
   check(reply['wire_offset']==move['offset'],'request/response wire pair')
   coords=tuple(reply['local_target']);check(coords==expected[i],'unexpected authoritative local target')
   check(move['route']['target_x']-3152==coords[0] and move['route']['target_y']-3152==coords[1],'server ack wrong target')
   check(f'R265_SELF_MASK_AFTER mask=16 appearance=true position={coords[0]},{coords[1]} packetCaret=68' in client,'client did not accept ack')
   check('R270_REAL_VIEWPORT_MOUSE_CLICK' in z.read(f'evidence/replay3/walk_{i+1}.log').decode(),'AWT Robot click not run')
  for i in (1,2,3):
   run=z.read(f'evidence/replay{i}/run.log').decode('utf-8','replace')
   check('R271_VISIBLE_SCENE_GATE_PASS' in run,'previous replay no render gate')
   check(run.count('R271_ACTUAL_AWT_CLICK')==4,'previous replay lacks four clicks')
   for phase in ('before','after'):
    png=z.read(f'evidence/replay{i}/{phase}.png')
    check(png[:8]==b'\x89PNG\r\n\x1a\n','invalid screenshot PNG')
    check(struct.unpack('>II',png[16:24])==(1400,900),'wrong Xvfb dimensions')
  check('R270_ALL_OFFLINE_ASSERTIONS_PASS java=23 framing=23 total=46' in z.read('evidence/R270_COMPATIBILITY_LINUX_PASS.log').decode(),'R270 compatibility not tested')
 print(f'R271_ARCHIVED_REAL_AWT_WALK_EVIDENCE_PASS checks={n} walks=4 acks=4 full_wire=yes')
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: R271ArchivedWalkEvidenceRegression.py R271_EVIDENCE.zip')
 main(sys.argv[1])

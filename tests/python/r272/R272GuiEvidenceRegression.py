#!/usr/bin/env python3
"""Independent standard-library archive and authenticated loopback receipt verifier.
Only tests evidence; never executes a game client or accesses private cache.
"""
import hashlib,json,struct,sys,zipfile
EXPECTED_TEXT='Man: Welcome to the isolated local session!'

def verify(path):
 checks=0
 def ck(condition,label):
  nonlocal checks
  if not condition:raise AssertionError('R272 evidence regression: '+label)
  checks+=1
 with zipfile.ZipFile(path) as z:
  ck(z.testzip() is None,'ZIP entry CRC')
  meta=json.loads(z.read('MANIFEST.json'))
  ck(meta['milestone']=='R272','unexpected milestone')
  ck(meta['contains_private_game_binaries'] is False,'privacy guard')
  names={entry.filename for entry in z.infolist()}
  ck(names=={'MANIFEST.json',*meta['files']},'unexpected/missing archive contents')
  for name,record in sorted(meta['files'].items()):
   blob=z.read(name)
   ck(len(blob)==record['bytes'],'length '+name)
   ck(hashlib.sha256(blob).hexdigest()==record['sha256'],'hash '+name)
  for i in (1,2):
   base=f'evidence/replay{i}/'
   data=json.loads(z.read(base+'r272_server_report.json'))
   raw=z.read(base+'r272_client_wire.bin')
   cap=z.read(base+'capture/inbound.log').decode('utf-8','replace')
   run=z.read(base+'npc_full_run.log').decode('utf-8','replace')
   context=z.read(base+'npc_context_menu.png')
   after=z.read(base+'npc_render_followup.png')
   ck(data['mode']=='isolated-test-only' and data['bind']=='127.0.0.1:43594','not localhost test')
   ck(data['login']['accepted'] is True,'failed synthetic login')
   ck(data.get('error') is None and not data.get('peer_closed'),'socket failure')
   ck(data['session_s']>=34,'session duration too short')
   ck(data['heartbeat_count']>=12,'too few source-backed heartbeat frames')
   ck(data['outbound_wire_bytes']==len(raw),'wire size inconsistency')
   ck(data['outbound_sha256']==hashlib.sha256(raw).hexdigest(),'real socket receipt checksum')
   stream=data['decoded_client_stream']
   ck(stream['error'] is None and stream['stop_offset']==len(raw),'not all ISAAC frames consumed')
   ck(stream['map_ready'] is True,'outbound opcode121 missing')
   ck(len(stream['npc_interactions'])==1,'NPC menu packet count')
   pkt=stream['npc_interactions'][0]
   ck(pkt['opcode']==155 and pkt['length']==2 and pkt['npc_slot']==47,'NPC talk packet mismatch')
   ck(len(data['acknowledged_npc'])==1,'synthetic response count')
   reply=data['acknowledged_npc'][0]
   ck(reply['wire_offset']==pkt['offset'],'request/reply offset mismatch')
   ck(reply['npc_slot']==47 and reply['requested_opcode']==155 and reply['response_opcode']==253,'wrong source compatible reply')
   ck(reply['text']==EXPECTED_TEXT,'unexpected dialogue response')
   ck(any(e['opcode']==65 and e['len']==7 for e in data['inbound']),'source-backed NPC spawn not sent')
   ck(any(e['opcode']==253 and e['len']==len((EXPECTED_TEXT+'\n').encode('latin-1')) for e in data['inbound']),'chat response not transmitted')
   ck(' | S>C | NPC_SYNC | 65 | 7 |' in cap,'client did not capture NPC spawn')
   ck(' | C>S | OUT | 98 |' in cap and ' | C>S | OUT | 155 | 2 | 2F 00' in cap,'client did not emit genuine menu action')
   ck(' | S>C | PACKET | 253 |' in cap,'client did not capture chat response')
   ck('R272_NPC_GUI_FRAME_VIEWPORT_NONBLACK=' in run,'render gate missing')
   ck('R272_CONTEXT_MENU_SNAPSHOT_CAPTURED' in run and 'R272_REAL_AWT_TALK_TO_MENU_SELECTION' in run,'real AWT clicks missing')
   ck('R272_SERVER_REPORT=' in run,'server evidence not correlated')
   ck(context[:8]==b'\x89PNG\r\n\x1a\n' and after[:8]==b'\x89PNG\r\n\x1a\n','invalid PNG')
   ck(struct.unpack('>II',context[16:24])==(1400,900),'wrong screenshot dimensions')
   ck(struct.unpack('>II',after[16:24])==(1400,900),'wrong response screenshot dimensions')
   ck(hashlib.sha256(context).digest()!=hashlib.sha256(after).digest(),'no visual change after real menu selection')
   ck(z.read(base+'right_click.log').decode().count('R272_ACTUAL_NPC_CONTEXT_RIGHT_CLICK')==1,'right-click was not generated')
   ck(z.read(base+'npc_talk_click.log').decode().count('R272_REAL_AWT_NPC_MENU_LEFT_CLICK')==1,'talk-to selection was not generated')
  compat=z.read('evidence/R272_OFFLINE_PASS.log').decode('utf-8')
  ck('R272_ALL_OFFLINE_PASS java_menu=64 java_spawn_to_menu=19 framing=22 total=105' in compat,'offline tests missing')
 print('R272_NPC_GUI_ARCHIVE_PASS checks='+str(checks)+' replays=2 npc65=2 talk155=2 reply253=2 mapready=2')
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('Usage: python R272GuiEvidenceRegression.py R272_EVIDENCE.zip')
 verify(sys.argv[1])

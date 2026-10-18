#!/usr/bin/env python3
"""Independent source-free R280 GUI, source-captured C>S and S>C packet evidence check.

  This cannot re-authenticate ISAAC without private ephemeral session keys. It
  correlates original client packet capture with independently produced mock
  listener reports and SHA-pinned received ciphertext from TWO real GUI runs.
"""
import hashlib,io,json,re,sys,zipfile
from PIL import Image

def verify(path):
    checks=0
    def ck(ok,why):
        nonlocal checks
        if not ok:raise AssertionError('R280_EVIDENCE_FAIL '+why)
        checks+=1
    with zipfile.ZipFile(path) as z:
        ck(z.testzip() is None,'ZIP CRC')
        m=json.loads(z.read('MANIFEST.json'))
        ck(m['milestone']=='R280' and m['production_source_changes']==0,'wrong milestone/scope')
        ck(m['source_built_client_jar_sha256']=='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd','wrong rebuilt binary')
        ck(set(z.namelist())==set(m['files'])|{'MANIFEST.json'},'manifest does not list exact ZIP contents')
        for name,meta in sorted(m['files'].items()):
            data=z.read(name)
            ck(len(data)==meta['bytes'],'wrong size: '+name)
            ck(hashlib.sha256(data).hexdigest()==meta['sha256'],'wrong SHA256: '+name)
            ck(not name.endswith(('.jar','.class','.dat','.idx','.zip')),'private executable/cache bytes included: '+name)
        capture_hashes=[]
        for run in (1,2):
            root=f'evidence/replay{run}/'
            action=json.loads(z.read(root+'object_receipt.json'))
            walk=json.loads(z.read(root+'walk_receipt.json'))
            early=z.read(root+'object_wire_ciphertext.bin')
            full=z.read(root+'walk_wire_ciphertext.bin')
            ck(action['source']=='actual-localhost-wire-ISAAC','object receipt not from real socket')
            ck(action['map_ready'] is True and action['error'] is None,'object action session error')
            ck(action['wire_bytes']==len(early)==63,'initial received wire length mismatch')
            ck(hashlib.sha256(early).hexdigest()==action['wire_sha256'],'early ciphertext hash')
            ck(len(full)==walk['full_wire_bytes']==74,'full walk receipt wire length')
            ck(full.startswith(early),'later walk bytes do not extend genuine early object stream')
            ck(hashlib.sha256(full).hexdigest()==walk['wire_sha256'],'final ciphertext hash')
            ck(walk['map_ready'] and walk['parser_error'] is None,'map ready or framing failed')
            ck(walk['object_ids']==[152,104],'object action order drift')
            ck(len(action['object_interactions'])==len(action['acknowledged_objects'])==2,'missing paired objects')
            for i,(obj_id,coords,off) in enumerate(((152,(3201,3202),47),(104,(3202,3201),56))):
                packet=action['object_interactions'][i]
                response=action['acknowledged_objects'][i]
                ck(packet['opcode']==132 and packet['length']==6,'real GUI object opcode or declared length')
                ck(packet['object_id']==obj_id and (packet['world_x'],packet['world_y'])==coords,'incorrect original scene object')
                ck(packet['offset']==response['wire_offset']==off,'ISAAC opcode not at expected captured offset')
                ck(response['requested_opcode']==132 and response['response_opcode']==253 and response['object_id']==obj_id,'synthetic reply unpaired')
            w=walk['walk']
            ck(w['wire_offset']==65 and w['local_target']==[46,51],'walk packet or authoritative target drift')
            ck(w['at']>action['session_s'],'walk precedes GUI object menu actions')
            ck(action['object_interactions'][1]['offset']<w['wire_offset']<len(full),'walk ordering invalid')
            log=z.read(root+'client_packet_capture.log').decode('utf-8','replace')
            ck(log.count('C>S | OUT | 132 | 6 |')==2,'real client did not emit exactly two object132 packets')
            ck(log.count('C>S | OUT | 164 | 8 |')==1,'real client did not emit exactly one walk164')
            ck('C>S | OUT | 121 | 0 |' in log,'client map-ready frame not present')
            ck('S>C | PACKET | 60 | 22 |' in log,'four authentic object spawns not delivered')
            ck(log.count('S>C | PACKET | 253 |')==2,'two fake chat responses missing from client capture')
            ck('S>C | PLAYER_SYNC | 81 | 68 |' in log,'server-authoritative movement not accepted by client packet decoder')
            runner=z.read(root+'runner.log').decode()
            ck('R280_GUI_RENDERED_PASS' in runner,'initial real world gate missing')
            ck('R280_GUI_TWO_OBJECT132_AND_PLAYER_WALK164_SERVER_ACK_PASS' in runner,'one-session actual wire acceptance missing')
            ck('R280_AFTER_CLICK_RENDERED_FRAME_PASS' in runner and 'R280_SESSION_GUI_CLICK_WIRE_ACCEPTANCE_PASS' in runner,'post-walk scene verification missing')
            robot=z.read(root+'robot.log').decode()
            ck('R280_OBJECT_SEARCH_COMPOST_CLICK_SENT' in robot and 'R280_OBJECT_SEARCH_CHEST_CLICK_SENT' in robot,'genuine object AWT clicks missing')
            ck('R280_REAL_VIEWPORT_WALK_CLICK_SENT x=310 y=315' in robot,'genuine walk AWT click missing')
            ck('R280_GUI_TWO_OBJECTS_AND_WALK_ROBOT_DONE' in robot,'full GUI click sequence did not finish')
            for screenshot in ('before.png','compost_menu.png','chest_menu.png','after_walk.png'):
                im=Image.open(io.BytesIO(z.read(root+screenshot))).convert('RGB')
                ck(im.size==(1400,900),'screen resolution mismatch '+screenshot)
                region=im.crop((136,185,640,520))
                ratio=sum(max(px)>30 for px in region.getdata())/(region.width*region.height)
                ck(ratio>.95,'real viewport not rendered '+screenshot)
            capture_hashes.append(walk['wire_sha256'])
        ck(capture_hashes[0]!=capture_hashes[1],'independent replays have identical ciphertext')
        fresh=z.read('evidence/replay2/fresh_owner_input_runner.log').decode()
        ck('R268_PRIVATE_TEST_HOME_STAGED files=10772' in fresh,'archive-to-clean-home stage not confirmed')
        ck('R280_FRESH_ARCHIVE_GUI_TWO_OBJECTS_AND_REAL_WALK_PASS' in fresh,'fresh wrapper acceptance not present')
        ck('R280_OWNER_PRIVATE_HASHES_PASS_R278_SOURCE_REBUILT_JAR' in fresh,'input hash-guard proof not found')
        print(f'R280_REAL_PATCHED_GUI_OBJECTS_AND_WALK_EVIDENCE_PASS checks={checks} two_genuine_sessions=true objects=152,104 walk164_ack81=46,51 fresh_stage=10772')
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python R280EvidenceVerifier.py <R280_evidence.zip>')
    verify(sys.argv[1])

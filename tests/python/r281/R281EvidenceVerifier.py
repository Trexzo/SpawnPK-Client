#!/usr/bin/env python3
"""Independent evidence verification; no private binary, cache, or live connection."""
import hashlib,io,json,sys,zipfile
from PIL import Image

def verify(path):
    checks=0
    def ck(value,description):
        nonlocal checks
        if not value:raise AssertionError('R281_EVIDENCE_FAILED: '+description)
        checks+=1
    with zipfile.ZipFile(path) as z:
        ck(z.testzip() is None,'ZIP CRC')
        manifest=json.loads(z.read('MANIFEST.json'))
        ck(manifest.get('milestone')=='R281' and manifest.get('production_source_changes')==0,'wrong milestone or production change')
        ck(manifest['source_built_jar_sha256']=='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd','wrong real source-built client')
        ck(set(z.namelist())==set(manifest['files'])|{'MANIFEST.json'},'unlisted/unexpected file')
        for name,meta in manifest['files'].items():
            blob=z.read(name)
            ck(len(blob)==meta['bytes'],'size mismatch '+name)
            ck(hashlib.sha256(blob).hexdigest()==meta['sha256'],'SHA mismatch '+name)
            ck(not name.lower().endswith(('.jar','.class','.idx','.dat','.zip')),'private binaries/cache distributed '+name)
        ck('R281_REAL_OBJECT_ACTION_VARIANTS_PASS checks=28' in z.read('logs/real_object_identity.log').decode(),'real object definition regression absent')
        ck('id=4172 name=Cooking range' in z.read('logs/real_object_identity.log').decode(),'Examine-only same-name variant absent')
        wire_hashes=[]
        for i in (1,2):
            root=f'evidence/replay{i}/'
            obj=json.loads(z.read(root+'object_receipt.json'))
            walk=json.loads(z.read(root+'walk_ack.json'))
            old=z.read(root+'object_wire.bin')
            full=z.read(root+'full_wire.bin')
            ck(obj['source']=='actual-localhost-wire-ISAAC','receipt source not actual loopback')
            ck(obj.get('error') is None and obj['map_ready'],'object socket packet error')
            ck(len(obj['object_interactions'])==1 and len(obj['acknowledged_objects'])==1,'one cave click/reply missing')
            a=obj['object_interactions'][0];b=obj['acknowledged_objects'][0]
            ck(a['opcode']==132 and a['length']==6 and a['object_id']==2,'not genuine Cave Entrance action')
            ck((a['world_x'],a['world_y'])==(3201,3202),'not original cave action target')
            ck(a['offset']==52 and b['wire_offset']==52,'incorrect ISAAC frame offset')
            ck(b['object_id']==2 and b['requested_opcode']==132 and b['response_opcode']==253,'invalid simulated server reply')
            ck(b['text']=='Object 2: isolated test interaction.','response not explicitly synthetic')
            ck(obj['wire_bytes']==len(old)==59,'object receipt length mismatch')
            ck(hashlib.sha256(old).hexdigest()==obj['wire_sha256'],'object ciphertext checksum mismatch')
            ck(len(full)==walk['full_wire_bytes']==69,'complete post-walk cipher length mismatch')
            ck(full.startswith(old),'walk packet not extension of cave action stream')
            ck(hashlib.sha256(full).hexdigest()==walk['wire_sha256'],'full post-login cipher checksum mismatch')
            ck(walk['map_ready'] is True and walk['parser_error'] is None,'walk parser not clean')
            ck(walk['object_ids']==[2],'walk request lacked prior cave action')
            ck(walk['walk']['wire_offset']==60 and walk['walk']['local_target']==[46,51],'wrong real client walk/server position')
            ck(walk['walk']['at']>b['at'],'walk precedes cave action')
            r=z.read(root+'runner.log').decode('utf-8','replace')
            ck('R281_REAL_RENDERED_SCENE_PASS=' in r,'no rendered world gate')
            ck('R281_REAL_CAVE_ENTER132_RECEIVED' in r,'no cave object receipt')
            ck('R281_REAL_CAVE_ENTER_AND_WALK164_ACK_PASS' in r,'no second walking operation')
            ck('R281_COMPLETE_REAL_GUI_PASS' in r,'not completed real GUI acceptance')
            clicks=z.read(root+'robot.log').decode('utf-8','replace')
            ck('R281_REAL_CAVE_ENTER_FIRST_OPTION_SELECTED' in clicks and 'R281_REAL_WALK_AFTER_CAVE_CLICK_SENT' in clicks,'AWT robot did not perform two clicks')
            ck('R281_CAVE_ROBOT_DONE' in clicks,'Robot did not finish')
            srv=z.read(root+'server.log').decode('utf-8','replace')
            ck('R276_SERVER_ACTUAL_OBJECT132_RECEIVED offset=52 object=2 xy=3201,3202' in srv,'server did not decode cave packet')
            ck('R280_RECEIVED_REAL_164_AND_SENT_AUTHORITATIVE_81_ACK' in srv,'server did not respond to walk')
            for shot in ('cave_context.png','after_enter.png','after_walk.png'):
                image=Image.open(io.BytesIO(z.read(root+shot))).convert('RGB')
                ck(image.size==(1400,900),'unexpected source GUI resolution')
                cropped=image.crop((136,185,640,520))
                nonblack=sum(max(rgb)>30 for rgb in cropped.getdata())/(cropped.width*cropped.height)
                ck(nonblack>.95,'scene not rendered in real screenshot '+shot)
            wire_hashes.append(walk['wire_sha256'])
        ck(wire_hashes[0]!=wire_hashes[1],'two different sessions must have unique ISAAC ciphertext')
        cap=z.read('evidence/replay2/client_packet_capture.log').decode('utf-8','replace')
        ck('C>S | OUT | 121 | 0 |' in cap,'client original map-ready packet missing')
        ck('C>S | OUT | 132 | 6 |' in cap,'client original cave packet capture missing')
        ck('C>S | OUT | 164 | 8 |' in cap,'client original walking packet capture missing')
        ck('S>C | PACKET | 253 |' in cap,'client original synthetic chat packet absent')
        ck('S>C | PLAYER_SYNC | 81 | 68 |' in cap,'client server-authoritative movement packet absent')
        clean=z.read('evidence/replay2/runner.log').decode('utf-8','replace')
        ck('R281_ORIGINAL_PRIVATE_INPUT_HASHES_PASS_AND_JAVA11_ROBOTS_COMPILED' in clean,'fresh owner archive guards not confirmed')
        ck('R281_FRESH_OWNER_ARCHIVE_GUI_CAVE_AND_WALK_PASS' in clean,'fresh exact-private-input replay did not complete')
        for snap in ('range_old_overlap_montage.png','range_relocated_montage.png'):
            image=Image.open(io.BytesIO(z.read('evidence/cooking_range_investigation/'+snap)))
            ck(image.size[0]>=1100,'bad Cooking range diagnostic montage')
    print(f'R281_AUTHENTIC_CAVE_ENTER_WALK_GUI_EVIDENCE_PASS checks={checks} runs=2 object_id=2 object_opcode=132 walk_opcode=164 response=253 walk_ack=81 cooking_range_gui=UNVERIFIED')
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python R281EvidenceVerifier.py R281_EVIDENCE.zip')
    verify(sys.argv[1])

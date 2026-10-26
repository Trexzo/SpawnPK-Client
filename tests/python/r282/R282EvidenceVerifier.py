#!/usr/bin/env python3
"""Read-only source-free R282 archive verifier, no external game input needed."""
import hashlib,io,json,re,sys,zipfile
from PIL import Image

def verify(filename):
    count=0
    def ck(ok,message):
        nonlocal count
        if not ok:raise AssertionError('R282_EVIDENCE_FAIL '+message)
        count+=1
    with zipfile.ZipFile(filename) as z:
        ck(z.testzip() is None,'bad ZIP CRC')
        manifest=json.loads(z.read('MANIFEST.json'))
        ck(manifest['milestone']=='R282' and manifest['production_changes']==0,'scope was misrepresented')
        ck(manifest['source_built_jar_sha256']=='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd','unpinned source JAR')
        ck(set(z.namelist())==set(manifest['entries'])|{'MANIFEST.json'},'manifest entry mismatch')
        for name,entry in manifest['entries'].items():
            value=z.read(name)
            ck(len(value)==entry['size'],'size '+name)
            ck(hashlib.sha256(value).hexdigest()==entry['sha256'],'checksum '+name)
            ck(not name.endswith(('.class','.jar','.idx','.dat')),'private binary leaked '+name)
        log=z.read('evidence/definition_banks.log').decode()
        ck('R282_ACTUAL_CLIENT_OBJECT_BANK_ISOLATION_PASS checks=78' in log,'real bank tests absent')
        for mode,action in [('R281_INITIAL_CONFIG_LOAD','Cook'),('REAL_GUI_STANDARD_REGION','null'),('LEGACY_OSRS_REGION','Cook'),('OSRS_CONFIG_REGION','Cook'),('RESTORED_STANDARD_REGION','null')]:
            pattern=r'R282_BANK_VERIFIED phase='+mode+r' mode=\w+ id114_model=5274 action='+action
            ck(re.search(pattern,log) is not None,'wrong bank/action '+mode)
        legacy=z.read('evidence/actual_client_selected_id114.log').decode().strip()
        for field in ['R282_SCENE_PICK id=114','xy=51,49','sceneHash=10','pickedName=Cooking range','pickedActions=null','mode=field1133','override=false','cached=false','pickedModel=[5274]','rawActions=null']:
            ck(field in legacy,'live client pick evidence absent '+field)
        older=z.read('evidence/R278_compatibility.log').decode()
        ck('R278_CLEAN_INPUT_ALL_SUITES_PASS java759 packet38 total797' in older,'prior suite not rerun')
        ck('R278_AUTHORITY_FULL_REAL_CLIENT_PASS checks=254' in older,'real scene authority test not recorded')
        ck('R277_MIXED_MODEL_FOOTPRINT_PASS checks=189' in older,'real rotated model fixture not recorded')
        screenshot=Image.open(io.BytesIO(z.read('evidence/Cooking_range_standard_menu.png'))).convert('RGB')
        ck(screenshot.size==(1400,900),'actual GUI dimensions')
        region=screenshot.crop((136,185,640,520))
        ratio=sum(max(rgb)>30 for rgb in region.getdata())/(region.width*region.height)
        ck(ratio>.95,'not a rendered real GUI')
        runner=z.read('evidence/GUI_round1.log').decode()
        ck('R282_DIAGNOSTIC_REAL_MENU_SWEEP_PASS' in runner,'completed GUI round absent')
        ck('R281_REAL_RENDERED_SCENE_PASS=' in runner,'live rendered viewport gate absent')
        print(f'R282_BANK_AND_GUI_EVIDENCE_PASS checks={count} real_jar_bank=78 clean_prior=797 id114_mode=field1133 cook_not_present=true')
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python R282EvidenceVerifier.py R282_SOURCE_FREE_EVIDENCE.zip')
    verify(sys.argv[1])

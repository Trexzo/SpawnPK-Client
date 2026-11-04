"""R357: SHA-pinned, byte-exact reversible v309 Java readability pass.

Requires the owner-private R356 full source ZIP. Never commits Java/JAR/cache.
Names are inferred source descriptions, NOT original-v309 identity/parity.
"""
from __future__ import annotations
import argparse, hashlib, json, re, stat
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

INPUT_SHA="e0fd993155ff4842ff35afa10e9dc77d47832e707b70f3dbac23427b9f423aa7"
INPUT_MANIFEST="PRIVATE_R356_READABILITY_MANIFEST.json"
OUTPUT_MANIFEST="PRIVATE_R357_READABILITY_MANIFEST.json"
COUNT=1277

TYPES=[
 ("rs/ui/overlay/infobox/Class101.java","Class101","InfoBoxImageSizingMode","232977f6db30de7f5a4f97b20da29ee0baaa46a730819c72db3e1b744670e34b"),
 ("rs/graphics/login/Class68.java","Class68","LoginScreenView","01e9d164b17b030e7edc12af745fb27975d1d1aa0d554e954fc3d865b0387b13"),
 ("rs/graphics/preview/support/Class56.java","Class56","TextureDebugSection","bf58c089d5a795ea7a34ef3ae7267ec1d8725023e0fe140a1a0788dd6eeb2dec"),
 ("rs/graphics/overlay/actor/Class67.java","Class67","ModelInspectorOverlayBase","4590171fa80445475ae832acb50143401c505832920d227c8ba56af1c2018367"),
 ("rs/graphics/overlay/npcmarker/Class63.java","Class63","NpcMarkerSpriteOffset","ff77e4206749f7f2836b3d84514d32091e684ed8051d26eb484a7bad9d8c7e40"),
]
FIELDS=[
 ("rs/ui/overlay/infobox/InfoBox.java","field5485","imageSizingMode"),
 ("rs/graphics/login/LoginScreen.java","field2052","currentView"),
 ("rs/graphics/overlay/actor/ModelInspectorOverlayBase.java","field2489","inspectedModel"),
 ("rs/graphics/overlay/actor/ModelInspectorOverlayBase.java","field2490","inspectedEntity"),
 ("rs/graphics/overlay/npcmarker/NpcMarkerSpriteOffset.java","field2263","spriteIndex"),
 ("rs/graphics/overlay/npcmarker/NpcMarkerSpriteOffset.java","field2264","offsetX"),
 ("rs/graphics/overlay/npcmarker/NpcMarkerSpriteOffset.java","field2265","offsetY"),
 ("rs/graphics/overlay/npcmarker/NpcMarkerSpriteOffset.java","field2266","heightOffset"),
 ("rs/graphics/overlay/npcmarker/NpcMarkerSpriteOffset.java","field2267","ownerOverlay"),
]
METHODS=[
 ("rs/ui/overlay/infobox/InfoBox.java","method423","getImageSizingMode"),
 ("rs/ui/overlay/infobox/InfoBox.java","method889","setImageSizingMode"),
 ("rs/graphics/login/LoginScreen.java","method3354","setCurrentView"),
 ("rs/graphics/overlay/actor/ModelInspectorOverlayBase.java","method3464","setInspectedModel"),
 ("rs/graphics/overlay/actor/ModelInspectorOverlayBase.java","method1612","setInspectedEntity"),
]
# Expected exact lexical symbol occurrence counts by original R356 source path.
EXPECTED={
 "Class101":{"rs/plugins/infoboxes/InfoBoxPlugin.java":2,"rs/scriptpacket/handler/InfoBoxScriptPacket.java":3,"rs/ui/overlay/infobox/Class101.java":4,"rs/ui/overlay/infobox/InfoBox.java":4,"rs/ui/overlay/infobox/InfoBoxManager.java":1},
 "Class68":{"rs/Client.java":2,"rs/graphics/login/Class68.java":4,"rs/graphics/login/LoginScreen.java":7},
 "Class56":{"rs/graphics/preview/support/Class56.java":4,"rs/graphics/preview/support/TextureDebugLoader.java":5},
 "Class67":{"rs/graphics/overlay/actor/Class67.java":1,"rs/graphics/overlay/core/OverlayManager.java":4,"rs/graphics/overlay/recolor/RecolorInspectorOverlay.java":2},
 "Class63":{"rs/graphics/overlay/npcmarker/Class63.java":2,"rs/graphics/overlay/npcmarker/NpcMarkerOverlay.java":3},
 "field5485":{"rs/ui/overlay/infobox/InfoBox.java":3},
 "field2052":{"rs/graphics/login/LoginScreen.java":7},
 "field2489":{"rs/graphics/overlay/actor/Class67.java":2,"rs/graphics/overlay/recolor/ItemRecolorOverlay.java":3,"rs/graphics/overlay/recolor/ObjectRecolorOverlay.java":3,"rs/graphics/overlay/recolor/RecolorInspectorOverlay.java":6},
 "field2490":{"rs/graphics/overlay/actor/Class67.java":2,"rs/graphics/overlay/recolor/ItemRecolorOverlay.java":3,"rs/graphics/overlay/recolor/NpcRecolorOverlay.java":2,"rs/graphics/overlay/recolor/ObjectRecolorOverlay.java":3},
 "field2263":{"rs/graphics/overlay/npcmarker/Class63.java":2,"rs/graphics/overlay/npcmarker/NpcMarkerOverlay.java":1},
 "field2264":{"rs/graphics/overlay/npcmarker/Class63.java":2,"rs/graphics/overlay/npcmarker/NpcMarkerOverlay.java":1},
 "field2265":{"rs/graphics/overlay/npcmarker/Class63.java":2,"rs/graphics/overlay/npcmarker/NpcMarkerOverlay.java":1},
 "field2266":{"rs/graphics/overlay/npcmarker/Class63.java":2,"rs/graphics/overlay/npcmarker/NpcMarkerOverlay.java":1},
 "field2267":{"rs/graphics/overlay/npcmarker/Class63.java":2},
 "method423":{"rs/ui/overlay/infobox/InfoBox.java":1,"rs/ui/overlay/infobox/InfoBoxManager.java":1},
 "method889":{"rs/plugins/infoboxes/InfoBoxPlugin.java":1,"rs/scriptpacket/handler/InfoBoxScriptPacket.java":2,"rs/ui/overlay/infobox/InfoBox.java":1},
 "method3354":{"rs/Client.java":1,"rs/graphics/login/LoginScreen.java":1},
 "method3464":{"rs/graphics/overlay/actor/Class67.java":1,"rs/graphics/overlay/core/OverlayManager.java":1},
 "method1612":{"rs/graphics/overlay/actor/Class67.java":1,"rs/graphics/overlay/core/OverlayManager.java":1},
}

class Refused(ValueError): pass
def sha(data): return hashlib.sha256(data).hexdigest()
def hash_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda:f.read(1<<20),b""):h.update(part)
    return h.hexdigest()

def read_source_zip(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or hash_file(path)!=INPUT_SHA:
        raise Refused("PRIVATE_R356_SHA_MISMATCH")
    with ZipFile(path) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        if (len(infos)!=COUNT+1 or len(names)!=len(set(names)) or
            len(names)!=len(set(n.casefold() for n in names)) or
            INPUT_MANIFEST not in names):
            raise Refused("ZIP_MEMBER_SET_CHANGED")
        m=json.loads(z.read(INPUT_MANIFEST))
        pinned=m.get("source_sha256")
        if m.get("source_count")!=COUNT or not isinstance(pinned,dict) or len(pinned)!=COUNT:
            raise Refused("SOURCE_MANIFEST_INVALID")
        sources={};total=0
        for item in infos:
            n=item.filename
            if n==INPUT_MANIFEST:continue
            parts=n.split("/")
            if (not n.startswith("source/") or not n.endswith(".java") or
                "\\" in n or any(s in ("",".","..") for s in parts) or
                item.is_dir() or stat.S_IFMT(item.external_attr>>16)==stat.S_IFLNK or
                item.flag_bits&1 or item.file_size>4_000_000):
                raise Refused("UNSAFE_JAVA_ENTRY")
            total+=item.file_size
            if total>24_000_000:raise Refused("PRIVATE_SOURCE_SIZE_BUDGET")
            raw=z.read(item);relative=n[7:]
            if len(raw)!=item.file_size or sha(raw)!=pinned.get(relative):
                raise Refused("SOURCE_SHA_DRIFT")
            raw.decode("utf-8")
            sources[relative]=raw
        if set(sources)!=set(pinned):raise Refused("SOURCE_FILE_SET_DRIFT")
        return sources

def replace_words(text,old,new):
    regex=re.compile(r"\b"+re.escape(old)+r"\b")
    result=[];previous=0;pos=0;locations=[]
    for match in regex.finditer(text):
        prefix=text[previous:match.start()]
        result.append(prefix);pos+=len(prefix);locations.append(pos)
        result.append(new);pos+=len(new);previous=match.end()
    result.append(text[previous:])
    return "".join(result),locations

def undo_word_positions(text,old,new,locations):
    for location in reversed(locations):
        if text[location:location+len(new)]!=new:
            raise Refused("INVERSE_POSITION_DRIFT")
        text=text[:location]+old+text[location+len(new):]
    return text

def transform(original, *, types=TYPES,fields=FIELDS,methods=METHODS,
              expected=EXPECTED,expected_count=COUNT,require_owner_hash=True):
    if len(original)!=expected_count:raise Refused("WRONG_SOURCE_COUNT")
    rewritten=dict(original);witness=[]
    for kind,plan in (("type",types),("field",fields),("method",methods)):
        for data in plan:
            owner,old,new=data[:3];new_owner=None
            if owner not in rewritten:raise Refused("MISSING_OWNER_"+old)
            if kind=="type":
                if require_owner_hash and sha(rewritten[owner])!=data[3]:
                    raise Refused("ORIGINAL_OWNER_SHA_CHANGED_"+old)
                if not re.search(r"\b(?:class|enum|interface)\s+"+old+r"\b",rewritten[owner].decode("utf-8")):
                    raise Refused("DECLARATION_MISSING_"+old)
                new_owner=owner[:-len(old)-5]+new+".java"
                if new_owner in rewritten:raise Refused("RENAMED_CLASS_COLLISION")
            term=re.compile(r"\b"+re.escape(old)+r"\b")
            found={path:len(term.findall(raw.decode("utf-8")))
                   for path,raw in rewritten.items()
                   if term.search(raw.decode("utf-8"))}
            required=expected.get(old)
            if not required:raise Refused("UNPINNED_SYMBOL_"+old)
            if kind!="type":
                remapped={}
                for p,count in required.items():
                    for old_path,old_name,new_name,_ in types:
                        if p==old_path:p=old_path[:-len(old_name)-5]+new_name+".java"
                    remapped[p]=count
                required=remapped
            if found!=required:raise Refused("REFERENCE_SCOPE_OR_COUNT_DRIFT_"+old)
            edited={}
            for p in found:
                text,positions=replace_words(rewritten[p].decode("utf-8"),old,new)
                rewritten[p]=text.encode("utf-8")
                edited[new_owner if new_owner and p==owner else p]=positions
            if new_owner:rewritten[new_owner]=rewritten.pop(owner)
            witness.append((kind,old,new,owner,new_owner,edited))
    if len(rewritten)!=len(original):raise Refused("CHANGED_COMPILATION_UNIT_COUNT")
    reversed_sources=dict(rewritten)
    for kind,old,new,owner,new_owner,edited in reversed(witness):
        for p,positions in edited.items():
            reversed_sources[p]=undo_word_positions(
                reversed_sources[p].decode("utf-8"),old,new,positions).encode("utf-8")
        if new_owner:reversed_sources[owner]=reversed_sources.pop(new_owner)
    if reversed_sources!=original:raise Refused("INVERSE_NOT_BYTE_EXACT")
    return rewritten,witness

def stage(input_zip,output_zip):
    dest=Path(output_zip)
    if dest.exists() or dest.is_symlink():raise Refused("NEVER_OVERWRITE_PRIVATE_SOURCE")
    result,witness=transform(read_source_zip(input_zip))
    edits=sum(sum(len(v) for v in item[-1].values()) for item in witness)
    if edits!=108:raise Refused("TOTAL_SYMBOL_REWRITE_DRIFT")
    report={
      "status":"R357_PRIVATE_READABLE_CANDIDATE",
      "source_count":COUNT,"class_renames":len(TYPES),
      "field_renames":len(FIELDS),"method_renames":len(METHODS),
      "identifier_edits":edits,
      "exact_inverse_restores_all_source_bytes":True,
      "original_v309_jar_parity":"NOT_TESTED",
      "names":"INFERRED_CANDIDATES",
      "source_milestone_publishable":False,
      "r356_source_archive_sha256":INPUT_SHA,
      "source_sha256":{p:sha(raw) for p,raw in sorted(result.items())},
    }
    with ZipFile(dest,"w",ZIP_DEFLATED,compresslevel=9) as z:
        for path,raw in sorted(result.items()):
            z.writestr("source/"+path,raw)
        z.writestr(OUTPUT_MANIFEST,json.dumps(report,indent=2,sort_keys=True)+"\n")
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r356-private-source",type=Path,required=True)
    p.add_argument("--new-private-source",type=Path,required=True)
    args=p.parse_args(argv)
    try:result=stage(args.r356_private_source,args.new_private_source)
    except (Refused,OSError,ValueError,UnicodeError,BadZipFile) as exc:
        print(json.dumps({"status":"R357_REFUSED","reason":str(exc)}));return 2
    print(json.dumps({k:v for k,v in result.items() if k!="source_sha256"},
                     indent=2,sort_keys=True))
    return 0
if __name__=="__main__":raise SystemExit(main())

"""R355 private R354→R355 full-source deobfuscation, no game/network execution.

Five source-grounded type names and nine fields are lexical *candidates*.
All original R354 private source bytes are hash-pinned; the result is exactly
reversible even if a new name already appears in a source string literal.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

INPUT_SHA = "e515f96d753a8e0458c21b7a4ebf16c080411ea3ddbf85d184022497bfffd768"
INPUT_MANIFEST = "PRIVATE_R354_READABLE_PASS3_MANIFEST.json"
COUNT = 1277
# (owner path, inferred readable class name, original owner SHA, allowed references)
TYPES = (
 ("rs/ui/outline/Class102.java","OutlinePixelBlockPool",
  "fbafa340c155c0eada3c70b479ece9d9eefab238154b620bf0c58a48de8d1daa",
  {"rs/ui/outline/Class102.java":1,"rs/ui/outline/SimpleClientOutline.java":2}),
 ("rs/ui/outline/Class103.java","OutlineKernelOffset",
  "1a39306a06a918ddbdc719e54215b5f153115644e26202b9e673cb29d177833e",
  {"rs/ui/outline/Class103.java":4,"rs/ui/outline/SimpleClientOutline.java":22}),
 ("rs/ui/outline/Class104.java","OutlineWeightedSample",
  "e4e95c7d2e9be049d58a87891bc225f778a11eb0d814557d52f31f79e939fccf",
  {"rs/ui/outline/Class104.java":5,"rs/ui/outline/SimpleClientOutline.java":15}),
 ("rs/plugins/npcindicators/Class276.java","HighlightedNpcBuilder",
  "2a004196b82de1872cc009a3f4d4ed58d297054ec544e34e1c5d81eb1ab9be45",
  {"rs/plugins/npcindicators/Class276.java":16,"rs/plugins/npcindicators/HighlightedNpc.java":2}),
 ("rs/scriptpacket/handler/Class264.java","NpcHeadIconOverridePacketHandler",
  "4ec724a9e428463091e57caa4a7b42fe51e72963dcd3b73969f91eece9948443",
  {"rs/Client.java":4,"rs/scriptpacket/ScriptPacketRegistry.java":2,
   "rs/scriptpacket/handler/Class264.java":1}),
)
# (post-type-renamed owner, obfuscated member, proposed name, owner count)
FIELDS = (
 ("rs/ui/outline/OutlinePixelBlockPool.java","field5559","packedCoordinates",5),
 ("rs/ui/outline/OutlinePixelBlockPool.java","field5560","freeBlockIndices",6),
 ("rs/ui/outline/OutlinePixelBlockPool.java","field5561","freeBlockCount",5),
 ("rs/ui/outline/OutlineKernelOffset.java","field5562","offsetX",3),
 ("rs/ui/outline/OutlineKernelOffset.java","field5563","offsetY",3),
 ("rs/ui/outline/OutlineWeightedSample.java","field5564","radialDistance",3),
 ("rs/ui/outline/OutlineWeightedSample.java","field5565","pixelOffset",3),
 ("rs/ui/outline/OutlineWeightedSample.java","field5566","alphaWeight",3),
 ("rs/scriptpacket/handler/NpcHeadIconOverridePacketHandler.java",
  "field4118","npcHeadIconOverrides",3),
)

class Refused(ValueError):
    pass

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_verified(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise Refused("INPUT_NOT_REGULAR")
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda:source.read(1<<20),b""):
            h.update(block)
    if h.hexdigest()!=INPUT_SHA:
        raise Refused("INPUT_ARCHIVE_SHA_WRONG")
    with ZipFile(path) as z:
        info=z.infolist()
        names=[i.filename for i in info]
        if (len(info)!=COUNT+1 or len(names)!=len(set(names)) or
            len(names)!=len(set(n.casefold() for n in names)) or
            INPUT_MANIFEST not in names):
            raise Refused("INVALID_ARCHIVE_MEMBER_SET")
        manifest=json.loads(z.read(INPUT_MANIFEST))
        pins=manifest.get("source_sha256_after")
        if (manifest.get("input_source_count")!=COUNT or
            not isinstance(pins,dict) or len(pins)!=COUNT):
            raise Refused("INVALID_SOURCE_MANIFEST")
        source_map={}
        total=0
        for entry in info:
            name=entry.filename
            if name==INPUT_MANIFEST:
                continue
            if (not name.startswith("source/") or not name.endswith(".java") or
                name.startswith("/") or "\\" in name or ".." in name.split("/") or
                entry.is_dir() or stat.S_IFMT(entry.external_attr>>16)==stat.S_IFLNK or
                entry.flag_bits & 1 or entry.file_size>4_000_000):
                raise Refused("UNSAFE_ARCHIVE_SOURCE")
            total+=entry.file_size
            if total>24_000_000:
                raise Refused("SOURCE_BUDGET_EXCEEDED")
            raw=z.read(entry)
            if len(raw)!=entry.file_size or sha(raw)!=pins.get(name[7:]):
                raise Refused("SOURCE_HASH_CHANGED")
            raw.decode("utf-8")
            source_map[name[7:]]=raw
        if len(source_map)!=COUNT or set(source_map)!=set(pins):
            raise Refused("INCOMPLETE_SOURCE_TREE")
        return source_map

def substitute(text,old,new):
    """Record positions in the *output*, for exact inverse of only edited words."""
    expr=re.compile(r"\b"+re.escape(old)+r"\b")
    chunks=[];last=0;offset=0;positions=[]
    for match in expr.finditer(text):
        head=text[last:match.start()]
        chunks.append(head);offset+=len(head)
        positions.append(offset)
        chunks.append(new);offset+=len(new);last=match.end()
    chunks.append(text[last:])
    return "".join(chunks),positions

def inverse_at_positions(text,positions,new,old):
    for i in reversed(positions):
        if text[i:i+len(new)]!=new:
            raise Refused("REVERSE_POSITION_CHANGED")
        text=text[:i]+old+text[i+len(new):]
    return text

def transform(original):
    if len(original)!=COUNT:
        raise Refused("SOURCE_COUNT_CHANGED")
    current=dict(original);history=[]
    for owner,new,expected_sha,allowed in TYPES:
        old=Path(owner).stem
        if owner not in current or sha(current[owner])!=expected_sha:
            raise Refused("CLASS_SHA_MISMATCH_"+old)
        if not re.search(r"\bclass "+old+r"\b",current[owner].decode("utf-8")):
            raise Refused("DECLARATION_MISSING_"+old)
        dest=owner[:-len(old)-5]+new+".java"
        if dest in current:
            raise Refused("RENAMED_OWNER_ALREADY_EXISTS")
        found={p:len(re.findall(r"\b"+old+r"\b",raw.decode("utf-8")))
               for p,raw in current.items()}
        found={p:n for p,n in found.items() if n}
        if found!=allowed:
            raise Refused("UNEXPECTED_CLASS_REFERENCES_"+old)
        edits=[]
        for path in allowed:
            edited,positions=substitute(current[path].decode("utf-8"),old,new)
            current[path]=edited.encode("utf-8")
            edits.append((dest if path==owner else path,positions))
        current[dest]=current.pop(owner)
        history.append((old,new,owner,dest,edits,"type"))
    for owner,old,new,expected_count in FIELDS:
        if owner not in current:
            raise Refused("RENAMED_FIELD_OWNER_MISSING")
        allowed={owner:expected_count}
        if old=="field4118":
            allowed={"rs/Client.java":3,owner:3}
        found={p:len(re.findall(r"\b"+old+r"\b",raw.decode("utf-8")))
               for p,raw in current.items()}
        found={p:n for p,n in found.items() if n}
        if found!=allowed:
            raise Refused("UNEXPECTED_FIELD_REFERENCES_"+old)
        edits=[]
        for path in allowed:
            edited,positions=substitute(current[path].decode("utf-8"),old,new)
            current[path]=edited.encode("utf-8")
            edits.append((path,positions))
        history.append((old,new,None,None,edits,"field"))
    if len(current)!=len(original):
        raise Refused("RENAME_CHANGED_SOURCE_COUNT")
    reverse=dict(current)
    for old,new,owner,dest,edits,kind in reversed(history):
        for path,positions in edits:
            reverse[path]=inverse_at_positions(
                reverse[path].decode("utf-8"),positions,new,old).encode("utf-8")
        if kind=="type":
            reverse[owner]=reverse.pop(dest)
    if reverse!=original:
        raise Refused("EXACT_REVERSE_SOURCE_DRIFT")
    return current,history

def create_private_zip(source,output):
    output=Path(output)
    if output.exists() or output.is_symlink():
        raise Refused("OUTPUT_MUST_BE_NEW")
    current,history=transform(read_verified(source))
    witnesses=[{"old":old,"new":new,"kind":kind,
                "occurrences":sum(len(positions) for _,positions in edits)}
               for old,new,_,_,edits,kind in history]
    manifest={
        "status":"R355_COMPLETE_SOURCE_READABLE_CANDIDATE",
        "original_input_source_zip_sha256":INPUT_SHA,
        "source_count":COUNT,
        "class_renames":len(TYPES),"field_renames":len(FIELDS),
        "identifiers_rewritten":sum(w["occurrences"] for w in witnesses),
        "exact_inverse_restores_all_1277_source_bytes":True,
        "inferred_names_only":True,"original_jar_parity":"NOT_TESTED",
        "source_milestone_publishable":False,
        "source_sha256_after":{p:sha(raw) for p,raw in sorted(current.items())},
        "rename_witness":witnesses,
    }
    with ZipFile(output,"w",ZIP_DEFLATED,compresslevel=9) as z:
        for path,raw in sorted(current.items()):
            z.writestr("source/"+path,raw)
        z.writestr("PRIVATE_R355_READABILITY_MANIFEST.json",
                   json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r354-private-source",required=True,type=Path)
    parser.add_argument("--new-private-source",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        report=create_private_zip(args.r354_private_source,args.new_private_source)
    except (Refused,OSError,ValueError,UnicodeError,BadZipFile) as e:
        print(json.dumps({"status":"R355_SOURCE_REFUSED","reason":str(e)}))
        return 2
    print(json.dumps({k:v for k,v in report.items()
                      if k not in ("source_sha256_after","rename_witness")},
                     sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

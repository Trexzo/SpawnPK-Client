"""R356: owner-private v309 full-tree readability pass 5.

Seven class, thirteen field and thirteen method names are inferred from the
recovered Java, not claimed to be original author names or original-JAR parity.
No game execution, live traffic, production files or Java source in public CI.
"""
from __future__ import annotations
import argparse, hashlib, json, re, stat
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, BadZipFile

INPUT_SHA="7b58b0cc0292aa1a573ff2d1b940eb92fbbb0c7676b9cfdb4931b6824d00ad2c"
INPUT_MANIFEST="PRIVATE_R355_READABILITY_MANIFEST.json"
OUTPUT_MANIFEST="PRIVATE_R356_READABILITY_MANIFEST.json"
SOURCE_COUNT=1277
# Owner, old name, inferred name, exact R355 owner SHA, expected global uses.
CLASSES=[
("rs/util/Class74.java","Class74","ItemIconCacheLoader","27cc0c1aab86749266d483589963bb5c61f423e655b03ef09df8671d33aadc3c",3),
("rs/util/Class75.java","Class75","SpriteIconCacheLoader","13326bd6e0ad3d297de09cc96474f0ae5204ead06c09d9079a5618776d2d6eb7",3),
("rs/util/Class76.java","Class76","ItemIconCacheKey","aa165bf7530692e0961ab8d771c5ac86247f331d854d730a9d4628b50dea70e2",15),
("rs/util/Class77.java","Class77","SpriteIconCacheKey","234eec0826be0f6c6cdc86c54b69b4b8f7b4064948895034b25d6d63020e84ca",13),
("rs/plugins/devtools/Class272.java","Class272","DevToolsWidgetDisplay","d773a17fef1c3e33a2377e0ceae1577d40dceb82356de4f813ff9cec900045b3",11),
("rs/plugins/notifications/Class275.java","Class275","NotificationSoundMode","0fa7e5e4db382ee614202d87d53e1d33aacba153388cb2912978ddaab237f641",12),
("rs/util/Class82.java","Class82","MacOSUiSupport","05221977731d90479beed3b75a6d230e65478da2538029046618036ac86bc3de",8)]
# Post-class-rename declaring owner, original member, readable candidate, uses.
FIELDS=[
("rs/util/ItemIconCacheLoader.java","field5592","iconManager",3),
("rs/util/SpriteIconCacheLoader.java","field5593","iconManager",3),
("rs/util/ItemIconCacheKey.java","field5594","itemId",4),
("rs/util/ItemIconCacheKey.java","field5595","itemQuantity",4),
("rs/util/ItemIconCacheKey.java","field5596","iconSize",4),
("rs/util/SpriteIconCacheKey.java","field5597","spriteDirectory",4),
("rs/util/SpriteIconCacheKey.java","field5598","iconSize",4),
("rs/plugins/devtools/DevToolsWidgetDisplay.java","field4347","labelText",3),
("rs/plugins/devtools/DevToolsWidgetDisplay.java","field4348","screenX",3),
("rs/plugins/devtools/DevToolsWidgetDisplay.java","field4349","screenY",3),
("rs/plugins/devtools/DevToolsWidgetDisplay.java","field4350","widgetType",3),
("rs/plugins/notifications/NotificationSoundMode.java","field4521","displayLabel",4),
("rs/util/MacOSUiSupport.java","field5622","LOG",4)]
METHODS=[
("rs/util/ItemIconCacheKey.java","method1432","getItemId",5),
("rs/util/ItemIconCacheKey.java","method591","getItemQuantity",5),
("rs/util/ItemIconCacheKey.java","method3498","getIconSize",5),
("rs/util/SpriteIconCacheKey.java","method3262","getSpriteDirectory",5),
("rs/util/SpriteIconCacheKey.java","method1912","getIconSize",5),
("rs/plugins/devtools/DevToolsWidgetDisplay.java","method667","getLabelText",6),
("rs/plugins/devtools/DevToolsWidgetDisplay.java","method198","getScreenX",11),
("rs/plugins/devtools/DevToolsWidgetDisplay.java","method2910","getScreenY",11),
("rs/plugins/devtools/DevToolsWidgetDisplay.java","method484","getWidgetType",6),
("rs/plugins/notifications/NotificationSoundMode.java","method2027","getDisplayLabel",1),
("rs/util/MacOSUiSupport.java","method1577","enableNativeFullscreen",2),
("rs/util/MacOSUiSupport.java","method3539","requestUserAttention",2),
("rs/util/MacOSUiSupport.java","method512","requestForeground",3)]

class Refused(ValueError):pass

def sha(data):return hashlib.sha256(data).hexdigest()

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def read_input(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or file_sha(path)!=INPUT_SHA:
        raise Refused("R355_INPUT_SHA_INVALID")
    with ZipFile(path) as z:
        members=z.infolist()
        names=[i.filename for i in members]
        if (len(members)!=SOURCE_COUNT+1 or len(set(names))!=len(names) or
            len(set(n.casefold() for n in names))!=len(names) or
            INPUT_MANIFEST not in names):
            raise Refused("R355_ZIP_FILE_SET_INVALID")
        manifest=json.loads(z.read(INPUT_MANIFEST))
        pins=manifest.get("source_sha256_after")
        if (manifest.get("source_count")!=SOURCE_COUNT or
            not isinstance(pins,dict) or len(pins)!=SOURCE_COUNT):
            raise Refused("R355_SOURCE_PINS_INVALID")
        sources={};budget=0
        for i in members:
            name=i.filename
            if name==INPUT_MANIFEST:continue
            parts=name.split("/")
            if (not name.startswith("source/") or not name.endswith(".java") or
                name.startswith("/") or "\\" in name or
                any(p in ("",".","..") for p in parts) or
                i.is_dir() or stat.S_IFMT(i.external_attr>>16)==stat.S_IFLNK or
                i.flag_bits&1 or i.file_size>4_000_000):
                raise Refused("UNSAFE_SOURCE_MEMBER")
            budget+=i.file_size
            if budget>24_000_000:raise Refused("SOURCE_BUDGET_EXCEEDED")
            raw=z.read(i);relative=name[7:]
            if len(raw)!=i.file_size or sha(raw)!=pins.get(relative):
                raise Refused("SOURCE_BYTES_NOT_PINNED")
            raw.decode("utf-8")
            sources[relative]=raw
        if len(sources)!=SOURCE_COUNT or set(sources)!=set(pins):
            raise Refused("PRIVATE_TREE_INCOMPLETE")
        return sources

def replace(text,old,new):
    expression=re.compile(r"\b"+re.escape(old)+r"\b")
    parts=[];previous=0;out_pos=0;positions=[]
    for match in expression.finditer(text):
        unchanged=text[previous:match.start()]
        parts.append(unchanged);out_pos+=len(unchanged)
        positions.append(out_pos);parts.append(new)
        out_pos+=len(new);previous=match.end()
    parts.append(text[previous:])
    return "".join(parts),positions

def reverse(text,positions,old,new):
    for pos in reversed(positions):
        if text[pos:pos+len(new)]!=new:raise Refused("REVERSE_POSITION_DRIFT")
        text=text[:pos]+old+text[pos+len(new):]
    return text

def transform(original, *, expected_count=SOURCE_COUNT,
              classes=CLASSES,fields=FIELDS,methods=METHODS):
    if len(original)!=expected_count:raise Refused("SOURCE_COUNT_DRIFT")
    current=dict(original);steps=[]
    specs=[("type",p) for p in classes]+[("field",p) for p in fields]+[("method",p) for p in methods]
    for kind,spec in specs:
        owner,old,new=spec[:3]
        if owner not in current:raise Refused("OWNER_MISSING_"+old)
        new_owner=None
        if kind=="type":
            expected_sha,expected_uses=spec[3:]
            if sha(current[owner])!=expected_sha:raise Refused("OWNER_SHA_CHANGED_"+old)
            if not re.search(r"\b(?:class|interface|enum)\s+"+old+r"\b",
                             current[owner].decode("utf-8")):
                raise Refused("DECLARATION_MISSING_"+old)
            new_owner=owner.rsplit("/",1)[0]+"/"+new+".java"
            if new_owner in current:raise Refused("OWNER_COLLISION_"+old)
        else:expected_uses=spec[3]
        token=re.compile(r"\b"+re.escape(old)+r"\b")
        occurrences={p:len(token.findall(raw.decode("utf-8")))
                     for p,raw in current.items() if token.search(raw.decode("utf-8"))}
        if sum(occurrences.values())!=expected_uses or not occurrences or
            (kind!="type" and owner not in occurrences):
            raise Refused("REFERENCE_COUNT_OR_OWNER_DRIFT_"+old)
        edits={}
        for p in occurrences:
            changed,positions=replace(current[p].decode("utf-8"),old,new)
            current[p]=changed.encode("utf-8")
            edits[new_owner if new_owner and p==owner else p]=positions
        if new_owner:current[new_owner]=current.pop(owner)
        steps.append((kind,old,new,owner,new_owner,edits))
    restored=dict(current)
    for kind,old,new,owner,new_owner,edits in reversed(steps):
        for p,positions in edits.items():
            restored[p]=reverse(restored[p].decode("utf-8"),
                                positions,old,new).encode("utf-8")
        if new_owner:restored[owner]=restored.pop(new_owner)
    if restored!=original:raise Refused("REVERSE_NOT_BYTE_EXACT")
    return current,steps

def produce(source_path,output_path):
    output_path=Path(output_path)
    if output_path.exists() or output_path.is_symlink():
        raise Refused("OUTPUT_ALREADY_EXISTS")
    result,steps=transform(read_input(source_path))
    occurrence_count=sum(sum(len(pos) for pos in x[-1].values()) for x in steps)
    if len(result)!=SOURCE_COUNT or occurrence_count!=178:
        raise Refused("TOTAL_SOURCE_RENAME_WITNESS_CHANGED")
    report={"status":"R356_SOURCE_READABILITY_CANDIDATE",
        "source_count":SOURCE_COUNT,
        "class_renames":7,"field_renames":13,"method_renames":13,
        "identifier_occurrences":occurrence_count,
        "all_r355_source_bytes_restored_by_inverse":True,
        "names":"INFERRED_CANDIDATES",
        "original_client_bytecode_parity":"NOT_TESTED",
        "full_source_clean_build":"NOT_PERFORMED_BY_THIS_TOOL",
        "publishable_source":False,
        "r355_archive_sha256":INPUT_SHA,
        "source_sha256":{p:sha(raw) for p,raw in sorted(result.items())}}
    with ZipFile(output_path,"w",ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(result.items()):
            z.writestr("source/"+name,raw)
        z.writestr(OUTPUT_MANIFEST,json.dumps(report,indent=2,sort_keys=True)+"\n")
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r355-private-source",type=Path,required=True)
    parser.add_argument("--new-private-source",type=Path,required=True)
    args=parser.parse_args(argv)
    try:report=produce(args.r355_private_source,args.new_private_source)
    except (Refused,OSError,ValueError,UnicodeError,BadZipFile) as error:
        print(json.dumps({"status":"R356_REFUSED","reason":str(error)}));return 2
    print(json.dumps({k:v for k,v in report.items() if k!="source_sha256"},sort_keys=True))
    return 0

if __name__=="__main__":raise SystemExit(main())

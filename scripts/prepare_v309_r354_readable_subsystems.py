"""R354: five source-grounded readable types, seven fields, one cache method.

Owner-private R353 ZIP input. The 1,277 Java files are SHA-pinned through the
exact archive hash; client source is not committed to the public repository.
All identifiers are inferred names, not original author/JVM symbol authority.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED

INPUT_SHA = "3d9daeb81c1367edc7a2e843a71638d22835bd485bc2d4c09eb0aa43d01b5f22"
COUNT = 1277
# old name, new inferred name, original declaring source path (or None),
# allowed occurrences by source path AT THE POINT OF THIS RENAME,
# required source-code witnesses (declaration or method body).
RENAMES = (
 ("Class87","EventBusSubscriber","rs/eventbus/Class87.java",
   {"rs/eventbus/Class87.java":7,"rs/eventbus/EventBus.java":14},
   ("EventBus.Subscriber","getPriority()","getMethod()")),
 ("Class49","IndexedCacheFileReader","rs/cache/osrs/util/Class49.java",
   {"rs/cache/osrs/util/Class49.java":2,
    "rs/cache/osrs/util/OsrsMapDependencyScanner.java":8},
   ("RandomAccessFile","IndexStore","GZIPInputStream")),
 ("Class47","MapDependencyRecord","rs/cache/osrs/util/Class47.java",
   {"rs/cache/osrs/util/Class47.java":2,
    "rs/cache/osrs/util/OsrsMapDependencyScanner.java":20},
   ("final int field370","final String field371","final String field372")),
 ("Class48","LandscapePlacementVisitor","rs/cache/osrs/util/Class48.java",
   {"rs/cache/osrs/util/Class48.java":1,
    "rs/cache/osrs/util/OsrsMapDependencyScanner.java":1},
   ("void accept(int var1, int var2, int var3, int var4)",)),
 ("Class50","ConfigElementDescriptor","rs/config/Class50.java",
   {"rs/config/Class50.java":1,"rs/config/ConfigItemDescriptor.java":1,
    "rs/config/ConfigSectionDescriptor.java":1,
    "rs/plugins/configs/ConfigPanel.java":3},
   ("String key()","String name()","int position()")),
 ("field370","dependencyObjectId",None,
   {"rs/cache/osrs/util/MapDependencyRecord.java":2,
    "rs/cache/osrs/util/OsrsMapDependencyScanner.java":1},()),
 ("field371","dependencyReference",None,
   {"rs/cache/osrs/util/MapDependencyRecord.java":2,
    "rs/cache/osrs/util/OsrsMapDependencyScanner.java":2},()),
 ("field372","dependencyStatus",None,
   {"rs/cache/osrs/util/MapDependencyRecord.java":2,
    "rs/cache/osrs/util/OsrsMapDependencyScanner.java":1},()),
 ("field373","dataFile",None,
   {"rs/cache/osrs/util/IndexedCacheFileReader.java":4},()),
 ("field374","cacheDirectory",None,
   {"rs/cache/osrs/util/IndexedCacheFileReader.java":3},()),
 ("field375","cacheBaseName",None,
   {"rs/cache/osrs/util/IndexedCacheFileReader.java":3},()),
 ("field376","indexFiles",None,
   {"rs/cache/osrs/util/IndexedCacheFileReader.java":5},()),
 ("method2942","readIndexedFile",None,
   {"rs/cache/osrs/util/IndexedCacheFileReader.java":1,
    "rs/cache/osrs/util/OsrsMapDependencyScanner.java":5},
   ("byte[] method2942(int var1, int var2, boolean var3)",)),
)

OWNER_SHA = {
 "rs/eventbus/Class87.java":
  "7e4051913d8fa43cb92e5bbdfcd2e39df42eba7eb0c7b0a0ec88a4a0570f086b",
 "rs/cache/osrs/util/Class49.java":
  "849167abb136cfad92cf00fae44bb814191ecdf6dfd5cf50c9937abbe09ed95d",
 "rs/cache/osrs/util/Class47.java":
  "ab031a3fd7c2aefdf0c7ba804c9ae2fb2f766f153931e8d01250e2d8f6ac0368",
 "rs/cache/osrs/util/Class48.java":
  "bf23af760cf9ea8b6290f58eda46a6e27f3d7231ba7306dfaddf28a46366422a",
 "rs/config/Class50.java":
  "d15e5c7dfe1b9574bd8357aebb038398f4e28a9fbf47d701b1d842ffc8731691",
}

class SourceRefused(ValueError):
    pass

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def verified_input(path:Path):
    if path.is_symlink() or not path.is_file():
        raise SourceRefused("PRIVATE_SOURCE_ZIP_MISSING")
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            digest.update(block)
    if digest.hexdigest()!=INPUT_SHA:
        raise SourceRefused("R353_SOURCE_ZIP_SHA_MISMATCH")
    with ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)!=COUNT+1:
            raise SourceRefused("ZIP_MEMBER_COUNT_WRONG")
        names=[i.filename for i in infos]
        if (len(set(names))!=len(names) or
            len({n.casefold() for n in names})!=len(names)):
            raise SourceRefused("DUPLICATE_OR_WINDOWS_CASEFOLD_MEMBER")
        original={}
        total=0
        for item in infos:
            n=item.filename
            if n=="PRIVATE_R353_READABILITY_REBUILD_MANIFEST.json":
                continue
            if (not n.startswith("source/") or not n.endswith(".java") or
                n.startswith("/") or "\\" in n or ".." in n.split("/") or
                item.is_dir() or stat.S_IFMT(item.external_attr>>16)==stat.S_IFLNK):
                raise SourceRefused("UNSAFE_PRIVATE_JAVA_ENTRY")
            if item.file_size>4_000_000 or item.flag_bits&1:
                raise SourceRefused("OVERSIZED_OR_ENCRYPTED_SOURCE_ENTRY")
            total+=item.file_size
            if total>24_000_000:raise SourceRefused("SOURCE_BUDGET_EXCEEDED")
            raw=z.read(item)
            if len(raw)!=item.file_size:raise SourceRefused("PARTIAL_SOURCE_ENTRY")
            raw.decode("utf-8")
            original[n[7:]]=raw
        if len(original)!=COUNT:
            raise SourceRefused("JAVA_FILE_COUNT_MISMATCH")
        for name,digest in OWNER_SHA.items():
            if name not in original or sha(original[name])!=digest:
                raise SourceRefused("DECLARING_OWNER_SHA_CHANGED_"+name)
        return original

def transform(original:dict[str,bytes],*,strict:bool=True):
    if len(original)!=(COUNT if strict else len(original)):
        raise SourceRefused("INPUT_SOURCE_COUNT_CHANGED")
    current=dict(original)
    records=[]
    for old,new,owner,expected,witnesses in RENAMES:
        if owner:
            if owner not in current:
                raise SourceRefused("MISSING_OWNER_"+old)
            new_path=owner.rsplit("/",1)[0]+"/"+new+".java"
            if new_path in current:
                raise SourceRefused("TARGET_OWNER_ALREADY_EXISTS_"+old)
            text=current[owner].decode("utf-8")
            if any(w not in text for w in witnesses):
                raise SourceRefused("OWNER_BEHAVIOR_SHAPE_CHANGED_"+old)
        elif witnesses:
            if any(w not in current["rs/cache/osrs/util/IndexedCacheFileReader.java"].decode("utf-8")
                   for w in witnesses):
                raise SourceRefused("CACHE_READER_METHOD_SHAPE_CHANGED")
        else:
            new_path=None
        token=re.compile(r"\b"+re.escape(old)+r"\b")
        hits={name:len(token.findall(data.decode("utf-8")))
              for name,data in current.items()
              if token.search(data.decode("utf-8"))}
        if strict and hits!=expected:
            raise SourceRefused("UNEXPECTED_SYMBOL_OCCURRENCE_"+old)
        # Even non-strict tests must supply only explicit allowed files.
        if not set(hits).issubset(set(expected)):
            raise SourceRefused("UNEXPECTED_REFERENCE_OWNER_"+old)
        if not hits:raise SourceRefused("MISSING_SYMBOL_"+old)
        for name in hits:
            current[name]=token.sub(new,current[name].decode("utf-8")).encode("utf-8")
        if owner:
            current[new_path]=current.pop(owner)
        records.append({
            "old":old,"new":new,"owner":owner,
            "new_owner":new_path if owner else None,
            "references":hits,"identifier_occurrences":sum(hits.values())
        })
    if len(current)!=len(original):
        raise SourceRefused("SOURCE_COUNT_CHANGED")
    # Reverse only the exact witnessed files; global reversal could alter
    # unrelated pre-existing semantic identifiers such as "dataFile".
    backward=dict(current)
    for item in reversed(records):
        token=re.compile(r"\b"+re.escape(item["new"])+r"\b")
        for path in item["references"]:
            path_now=(item["new_owner"] if item["owner"]==path else path)
            data=backward[path_now].decode("utf-8")
            backward[path_now]=token.sub(item["old"],data).encode("utf-8")
        if item["owner"]:
            backward[item["owner"]]=backward.pop(item["new_owner"])
    if backward!=original:
        raise SourceRefused("REVERSE_TRANSFORM_BYTE_DRIFT")
    return current,records

def create_private_zip(source:Path,output:Path):
    if output.exists() or output.is_symlink():
        raise SourceRefused("REFUSE_TO_OVERWRITE_PRIVATE_OUTPUT")
    original=verified_input(source)
    transformed,records=transform(original)
    metadata={
        "status":"R354_PRIVATE_V309_READABLE_SOURCE_CANDIDATE",
        "base_r353_zip_sha256":INPUT_SHA,
        "source_count":COUNT,
        "symbol_changes":sum(r["identifier_occurrences"] for r in records),
        "renamed_source_owners":sum(bool(r["owner"]) for r in records),
        "exact_inverse_all_1277_sources":True,
        "semantic_names":"INFERRED_NOT_ORIGINAL_AUTHORITY",
        "clean_source_rebuild":"NOT_PERFORMED_BY_THIS_TOOL",
        "original_v309_jar_parity":"NOT_TESTED",
        "source_sha256":{n:sha(data) for n,data in sorted(transformed.items())},
        "renames":records,
    }
    with ZipFile(output,"w",ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(transformed.items()):
            z.writestr("source/"+name,data)
        z.writestr("PRIVATE_R354_READABLE_PASS3_MANIFEST.json",
                   json.dumps(metadata,indent=2,sort_keys=True)+"\n")
    return metadata

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r353-private-source-zip",required=True,type=Path)
    parser.add_argument("--new-private-source-zip",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        result=create_private_zip(args.r353_private_source_zip,args.new_private_source_zip)
    except (SourceRefused,OSError,UnicodeError,BadZipFile,ValueError) as error:
        print(json.dumps({"status":"R354_REFUSED","reason":str(error)}))
        return 2
    print(json.dumps({k:v for k,v in result.items() if k not in
        ("source_sha256","renames")},sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

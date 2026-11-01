"""R353 — reversible readability names for three R315 script-packet handlers.

This tool operates on the private R352 source candidate only. The names are
inferred from the original recovered Java/packet dispatch, NOT claimed to be
original author identifiers or exact-JAR semantic authority.

Private client Java is never uploaded to public GitHub/hosted CI.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED_COUNT = 1277
EXPECTED_BASE_SHA = "e46a213ba949dc0a2f420a040b5c9d38451c0923e3ea39917a5d2eb3c9b2fa28"
REGISTRY = "rs/scriptpacket/ScriptPacketRegistry.java"
DEBUG = "rs/debug/UiPacketDecoder.java"

# Existing source shapes and exact registration opcodes are both checked.
RENAMES = (
    ("Class261", "ClientStateScriptPacketHandler", 32, (
        "Client.field678", "WidgetComponent", "handlePacket()", "readPacketUnsignedByte()"
    ), 2, 3),
    ("Class262", "NpcStateResetScriptPacketHandler", 21, (
        "this.client.npcs", ".clear()", "handlePacket()", "readPacketShort()"
    ), 2, 3),
    ("Class263", "GrandExchangeScriptPacketHandler", 14, (
        "GrandExchangeWidget", "WidgetComponent", "handlePacket()", "readPacketString()"
    ), 3, 5),
)

class CandidateRefused(ValueError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def rewrite(sources: dict[str, bytes], *,
            expected_count=EXPECTED_COUNT,
            expected_stats=True):
    if not isinstance(sources, dict) or len(sources)!=expected_count:
        raise CandidateRefused("WRONG_SOURCE_FILE_SET")
    if REGISTRY not in sources or DEBUG not in sources:
        raise CandidateRefused("REGISTRY_OR_DIAGNOSTIC_SOURCE_MISSING")
    dest=dict(sources)
    observations=[]
    for old,new,opcode,required,expected_files,expected_uses in RENAMES:
        old_path=f"rs/scriptpacket/handler/{old}.java"
        new_path=f"rs/scriptpacket/handler/{new}.java"
        if old_path not in dest or new_path in dest:
            raise CandidateRefused("HANDLER_MISSING_OR_ALREADY_RENAMED_"+old)
        owner=dest[old_path].decode("utf-8")
        if (f"public class {old} extends AbstractScriptPacketHandler" not in owner
                or any(s not in owner for s in required)):
            raise CandidateRefused("ORIGINAL_HANDLER_SOURCE_SHAPE_CHANGED_"+old)
        registry=dest[REGISTRY].decode("utf-8")
        if (f"import rs.scriptpacket.handler.{old};" not in registry
                or f"registerPacketHandler({opcode}, {old}.class);" not in registry):
            raise CandidateRefused("PACKET_OPCODE_OR_HANDLER_DISPATCH_CHANGED_"+old)
        token=re.compile(r"\b"+re.escape(old)+r"\b")
        changed=[]
        for path,data in sorted(dest.items()):
            text=data.decode("utf-8")
            count=len(token.findall(text))
            if not count:continue
            # Deny unrelated equal-number classes, imports or reflection strings.
            allowed={old_path,REGISTRY}
            if old=="Class263":allowed.add(DEBUG)
            if path not in allowed:
                raise CandidateRefused("UNEXPECTED_CLASS_REFERENCE_"+old)
            dest[path]=token.sub(new,text).encode("utf-8")
            changed.append({"path":path,"identifiers":count})
        if expected_stats and (len(changed)!=expected_files or
                               sum(x["identifiers"] for x in changed)!=expected_uses):
            raise CandidateRefused("SOURCE_REFERENCE_COUNTS_CHANGED_"+old)
        dest[new_path]=dest.pop(old_path)
        if any(token.search(b.decode("utf-8")) for b in dest.values()):
            raise CandidateRefused("OLD_CLASS_IDENTIFIER_REMAINS_"+old)
        observations.append({
            "from":f"rs.scriptpacket.handler.{old}",
            "to":f"rs.scriptpacket.handler.{new}",
            "packet_opcode":opcode,
            "changed_references":changed,
            "name_authority":"INFERRED_CANDIDATE_ONLY",
        })
    if len(dest)!=expected_count:
        raise CandidateRefused("RENAME_CHANGED_SOURCE_COUNT")
    # Inverse transform must recover every exact input path and byte.
    backward=dict(dest)
    for old,new,_,_,_,_ in reversed(RENAMES):
        old_path=f"rs/scriptpacket/handler/{old}.java"
        new_path=f"rs/scriptpacket/handler/{new}.java"
        if new_path not in backward:raise CandidateRefused("MISSING_REVERSE_OWNER")
        token=re.compile(r"\b"+re.escape(new)+r"\b")
        for path,data in list(backward.items()):
            backward[path]=token.sub(old,data.decode("utf-8")).encode("utf-8")
        backward[old_path]=backward.pop(new_path)
    if backward!=sources:
        raise CandidateRefused("RENAME_NOT_EXACTLY_REVERSIBLE")
    return dest,observations

def read_r352_stage(stage):
    stage=Path(stage)
    manifest_path=stage/"PRIVATE_R315_SOURCE_CANDIDATE.json"
    if stage.is_symlink() or not manifest_path.is_file():
        raise CandidateRefused("R352_PRIVATE_INPUT_MISSING")
    report=json.loads(manifest_path.read_text("utf-8"))
    files=report.get("source_file_sha256")
    if (report.get("base_archive_sha256")!=EXPECTED_BASE_SHA
            or report.get("source_count")!=EXPECTED_COUNT
            or report.get("mode")!="readable"
            or report.get("source_milestone_publishable") is not False
            or not isinstance(files,dict)
            or len(files)!=EXPECTED_COUNT):
        raise CandidateRefused("R352_PRIVATE_SOURCE_PROVENANCE_NOT_PINNED")
    sources={}
    for rel,expected_hash in sorted(files.items()):
        if (not isinstance(rel,str) or not rel.endswith(".java")
                or "\\" in rel or rel.startswith("/")
                or ".." in rel.split("/") or rel in sources):
            raise CandidateRefused("UNSAFE_PRIVATE_SOURCE_PATH")
        path=stage/"source"/rel
        if path.is_symlink() or not path.is_file():
            raise CandidateRefused("PRIVATE_SOURCE_NOT_REGULAR")
        data=path.read_bytes()
        if sha(data)!=expected_hash:
            raise CandidateRefused("PRIVATE_SOURCE_SHA_MISMATCH")
        sources[rel]=data
    return sources

def stage_candidate(stage,new_output):
    output=Path(new_output)
    if output.exists() or output.is_symlink():
        raise CandidateRefused("OUTPUT_MUST_NOT_ALREADY_EXIST")
    original=read_r352_stage(stage)
    modified,observations=rewrite(original)
    output.mkdir(parents=True,exist_ok=False)
    for rel,data in sorted(modified.items()):
        f=output/"source"/rel
        f.parent.mkdir(parents=True,exist_ok=True)
        f.write_bytes(data)
    report={
        "status":"R353_COMPLETE_READABLE_CANDIDATE_STAGED",
        "java_sources":len(modified),
        "class_renames":observations,
        "exact_reverse_restores_r352_source":True,
        "source_file_sha256":{rel:sha(data) for rel,data in sorted(modified.items())},
        "full_clean_build":"NOT_RUN_BY_THIS_COMMAND",
        "original_client_jar_semantic_parity":"NOT_TESTED",
        "source_milestone_publishable":False,
    }
    (output/"PRIVATE_R353_SOURCE_CANDIDATE.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r352-private-stage",type=Path,required=True)
    parser.add_argument("--new-private-output",type=Path,required=True)
    args=parser.parse_args()
    try:
        report=stage_candidate(args.r352_private_stage,args.new_private_output)
    except (CandidateRefused,OSError,UnicodeError,ValueError) as e:
        print(json.dumps({"status":"R353_REFUSED","reason":str(e)}))
        return 2
    print(json.dumps({k:v for k,v in report.items() if k!="source_file_sha256"},
                     indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

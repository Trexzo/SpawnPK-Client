"""R227: all original v309 Packet methods from the REAL readable Packet.java.

Exact SHA-pinned private original-v309 JAR + genuine readable source tree;
10 auditable Java compiler-shape rewrites across 10 methods, plus the
correct Integer type for temporary Configuration.field1313 declaration,
reproduce EVERY original rs/x/e method from readable rs/io/Packet.java.

A single isolated 27-source Java9 build matches 81/81 original Packet
method bodies, all 2,296 JVM operations and original byte offsets, opcodes,
constant operands, branch addresses, max-stack and locals. Exactly 30
symbolic original->readable aliases, SHA-pinned together and per method.
The actual Packet.java is NEVER changed in the user's source tree, no
original game code is executed, and full-client compilation is not claimed.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_v309_real_packet_base_closure_r226 import (
    build_real_packet_closure,
    compare_packet_base_jvm,
    verify_superclass_abi,
    EXPECTED_ALL_METHODS as BASE_METHODS,
    EXPECTED_ORIGINAL_INSTRUCTIONS as BASE_OPS,
    ORIGINAL_JAR_SHA256,
    SOURCE_ZIP_SHA256,
    R221_EVIDENCE_ZIP_SHA256,
    ORIGINAL_CLASS_SHA256 as BASE_ORIGINAL_SHA,
    READABLE_OWNER as BASE_OWNER,
    R226RealPacketClosureError,
    REAL_EMITTED_CLASSES,
    FINAL_SOURCE_OWNERS,
)
from .private_v309_spellbook_real_dependencies_r222 import (
    R221_CLASS_SHA256,R222_REAL_WIDGET_CLASS_SHA256,
    file_sha,read_unique,
)
from .private_v309_gambling_widget_original_code_r224 import (
    NORMALIZED_CLASS_SHA256 as GAMBLING_SHA256,
)
from .private_v309_gambling_callback_original_code_r225 import (
    NORMALIZED_169_CLASS_SHA256 as HUD_CALLBACK_SHA256,
    READABLE_168_CLASS_SHA256 as PACKET_CALLBACK_SHA256,
)

ORIGINAL_OWNER="rs/x/e"
READABLE_OWNER="rs/io/Packet"
ORIGINAL_CLASS_SHA256="b605d053ed38f602f90ac6bd2ff58de7149a55b44a9e88ee123802e4606a1fa2"
ORIGINAL_READABLE_JAVA_SHA256="df4791701d6820b5ce41388be75d40364b2e8e20f08771d854e5fd62b9cf5030"
NORMALIZED_JAVA_SHA256="16b77aa3c024bc93babc77213ab9ca825883a89478851c79a5c5d1a4c26ecc77"
NORMALIZED_CLASS_SHA256="a47cc0aa2665fe2b8dfde80baeed5f3bc5db860bc7105cd97e0e0db2acc72597"
ORIGINAL_METHODS=81
ORIGINAL_INSTRUCTIONS=2296
EXPECTED_SYMBOL_ALIASES=30
EXPECTED_SYMBOLIC_ALIAS_SHA="d1b08d2f65323413b0bd330ed9b7c020b7c1aa131dd562bf398add6b012899d9"
EXPECTED_METHOD_LEDGER_SHA="bafb9dd66f4971c6dbe03eea27bf147e47bda63a6c9727a8a903ae43d0e303db"
COMPILER_NORMALIZED_METHOD_COUNT=10

# Exact source excerpts, counts and static type rewrites. These changes
# affect ONLY a private temporary compiler copy; the original readable
# Packet.java source hash remains independently pinned.
SOURCE_REWRITES=(
    ("return var1 + var2;",
     "var1 += var2;\n      return var1;",2,1),
    ("return var1 < 128 ? this.readUnsignedByte() : this.method3348() - 32768;",
     "if (var1 < 128) {\n         return this.readUnsignedByte();\n      }\n      return this.method3348() - 32768;",1,1),
    ("public int method2073() {\n      return this.caret;",
     "public int method2073() {\n      int var1 = this.caret;\n      return var1;",1,1),
    ("return var1 < 128 ? this.readUnsignedByte() - 64 : this.method3348() - 49152;",
     "if (var1 < 128) {\n            return this.readUnsignedByte() - 64;\n         }\n         return this.method3348() - 49152;",2,2),
    ("return var1 < 128 ? this.readUnsignedByte() - 64 : this.method332() - 49152;",
     "if (var1 < 128) {\n         return this.readUnsignedByte() - 64;\n      }\n      return this.method332() - 49152;",1,1),
    ("var1 += -65535;","var1 = -65535 + var1;",2,2),
    ("this.caret = this.caret + var1.length();",
     "this.caret += var1.length();",1,1),
    ("byte[] var5 = var3.toByteArray();",
     "BigInteger var4 = var3;\n      byte[] var5 = var4.toByteArray();",1,1),
)

class R227OriginalReadablePacketError(ValueError):
    pass


def need(ok,reason):
    if not ok:raise R227OriginalReadablePacketError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize_packet_java(source, *, raw_pin=ORIGINAL_READABLE_JAVA_SHA256,
                          normalized_pin=NORMALIZED_JAVA_SHA256):
    need(type(source) is str and sha(source.encode("utf-8"))==raw_pin,
         "R227_EXACT_EXISTING_PACKET_JAVA_SOURCE_PIN_REQUIRED")
    normalized=source
    for old,new,expected_occurrences,replacements in SOURCE_REWRITES:
        need(normalized.count(old)==expected_occurrences and
             new not in normalized and replacements>=1,
             "R227_PACKET_SOURCE_COMPILER_REWRITE_ANCHOR_CHANGED")
        normalized=normalized.replace(old,new,replacements)
    need(sha(normalized.encode("utf-8"))==normalized_pin,
         "R227_EXACT_EIGHT_APPROVED_COMPILER_REWRITE_GROUPS_ONLY")
    return normalized


def parse_complete_javap(text):
    lines=text.splitlines()
    methods=[]
    for i,line in enumerate(lines):
        if line.strip()!="Code:":continue
        header=lines[i-1].strip()
        need(header and all(header!=x[0] for x in methods),
             "R227_DUPLICATE_OR_MISSING_JVM_METHOD_ID")
        instr=[]
        for line in lines[i+1:]:
            match=re.match(r"^\s*(\d+):\s+(\w+)(.*)$",line)
            if not match:break
            operand=match.group(3).strip()
            if "//" in operand:operand=operand.split("//",1)[1].strip()
            instr.append((int(match.group(1)),match.group(2),operand))
        need(instr and len(set(x[0] for x in instr))==len(instr),
             "R227_INVALID_JVM_METHOD_INSTRUCTION_STREAM")
        methods.append((header,instr))
    return methods


def compare_complete_original_packet(original_javap,rebuilt_javap, *,
                                     expected_method_count=ORIGINAL_METHODS,
                                     expected_ops=ORIGINAL_INSTRUCTIONS,
                                     alias_sha=EXPECTED_SYMBOLIC_ALIAS_SHA,
                                     ledger_sha=EXPECTED_METHOD_LEDGER_SHA):
    old=parse_complete_javap(original_javap)
    new=parse_complete_javap(rebuilt_javap)
    need(len(old)==len(new)==expected_method_count,
         "R227_ALL_81_PACKET_METHODS_MUST_BE_PRESENT")
    need(sum(len(x) for _,x in old)==sum(len(x) for _,x in new)==expected_ops,
         "R227_EXACT_2296_ORIGINAL_JVM_INSTRUCTIONS_REQUIRED")
    all_aliases={}
    ledger=[]
    for (oldheader,oldcode),(newheader,newcode) in zip(old,new):
        need(len(oldcode)==len(newcode),
             "R227_METHOD_JVM_INSTRUCTION_COUNT_DRIFT")
        local_aliases={}
        for a,b in zip(oldcode,newcode):
            need(a[:2]==b[:2],
                 "R227_ORIGINAL_PACKET_OPCODE_OR_BYTE_OFFSET_DRIFT")
            if a[2]!=b[2]:
                need(a[2].startswith((
                    "Field ","Method ","InterfaceMethod ","class ","InvokeDynamic "))
                     and b[2].startswith((
                    "Field ","Method ","InterfaceMethod ","class ","InvokeDynamic ")),
                     "R227_NON_SYMBOLIC_OPERAND_OR_BRANCH_CHANGED")
                need((a[2] not in all_aliases or all_aliases[a[2]]==b[2])
                     and (a[2] not in local_aliases or
                          local_aliases[a[2]]==b[2]),
                     "R227_ORIGINAL_SYMBOL_HAS_CONFLICTING_RENAME")
                local_aliases[a[2]]=b[2]
                all_aliases[a[2]]=b[2]
        ledger.append((oldheader,newheader,len(oldcode),
                       sha(json.dumps(local_aliases,sort_keys=True,
                                      separators=(",",":")).encode()),
                       len(local_aliases)))
    need(len(all_aliases)==EXPECTED_SYMBOL_ALIASES and
         sha(json.dumps(all_aliases,sort_keys=True,
                        separators=(",",":")).encode())==alias_sha,
         "R227_ALL_30_ORIGINAL_PACKET_SYMBOL_ALIASES_REQUIRED")
    need(sha(json.dumps(ledger,separators=(",",":")).encode())==ledger_sha,
         "R227_ALL_81_ORIGINAL_METHOD_IDENTITIES_AND_ALIASES_CHANGED")
    return {
        "original_packet_method_Code_bodies_verified":len(ledger),
        "original_packet_JVM_instructions_verified":expected_ops,
        "original_offsets_opcodes_literal_constants_branches_all_match":True,
        "unique_original_to_readable_symbolic_aliases":len(all_aliases),
        "per_method_symbolic_identity_ledger_SHA256":ledger_sha,
        "methods":ledger,
    }


def verify_packet_class_metadata(original,rebuilt):
    a=parse_class(original)
    b=parse_class(rebuilt)
    need(a.name==ORIGINAL_OWNER and b.name==READABLE_OWNER and
         a.super_name=="rs/a" and b.super_name=="rs/DualNode" and
         len(a.fields)==len(b.fields)==11 and
         len(a.methods)==len(b.methods)==ORIGINAL_METHODS and
         a.major==b.major==53 and
         len(a.interfaces)==len(b.interfaces)==0,
         "R227_ORIGINAL_PACKET_JVM_CLASS_MEMBER_HEADER_CHANGED")
    pa=profile_class_field_accesses(original)
    pb=profile_class_field_accesses(rebuilt)
    for i,(x,y) in enumerate(zip(pa["methods"],pb["methods"])):
        need(x["access"]==y["access"] and
             x["code_length"]==y["code_length"] and
             x["max_stack"]==y["max_stack"] and
             x["max_locals"]==y["max_locals"] and
             x["exception_handlers"]==y["exception_handlers"] and
             x["stackmap_table_present"]==y["stackmap_table_present"],
             "R227_PACKET_ORIGINAL_METHOD_CODE_METADATA_DRIFT_"+str(i))
    return True


def verify_private_normalized_packet(original_jar,source_tree_zip,
                                     r221_evidence_zip):
    try:
        sources,old_base,reference_spell=build_real_packet_closure(
            original_jar,source_tree_zip,r221_evidence_zip)
    except R226RealPacketClosureError as exc:
        raise R227OriginalReadablePacketError(
            "R227_REAL_SOURCE_BASELINE_SHA_PIN_OR_CLOSURE_FAILED") from exc
    need(sha(sources["rs/io/Packet.java"].encode())==
         ORIGINAL_READABLE_JAVA_SHA256,
         "R227_ORIGINAL_DECOMPILED_PACKET_SOURCE_CHANGED")
    sources["rs/io/Packet.java"]=normalize_packet_java(
        sources["rs/io/Packet.java"])
    cfg="rs/Configuration.java"
    need(sources[cfg].count("public static int field1313;")==1,
         "R227_COMPILER_ONLY_CONFIGURATION_FIELD_ABI_CHANGED")
    sources[cfg]=sources[cfg].replace(
        "public static int field1313;",
        "public static Integer field1313;",1)
    with ZipFile(original_jar) as jar:
        original=read_unique(jar,"rs/x/e.class",150000)
    need(sha(original)==ORIGINAL_CLASS_SHA256,
         "R227_ORIGINAL_RS_X_E_CLASS_PIN_FAILED")
    javac=shutil.which("javac");javap=shutil.which("javap")
    need(bool(javac and javap),"R227_JDK_JAVA9_COMPILER_AND_DISASSEMBLER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r227-packet-java9-") as td:
        root=Path(td);out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        env={k:v for k,v in os.environ.items()
             if k not in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                          "JDK_JAVA_OPTIONS","_JAVA_OPTIONS")}
        paths=[]
        for name,body in sources.items():
            path=root/"source"/name
            need(not path.exists(),"R227_DUPLICATE_JAVA_SOURCE_OWNER")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(body,encoding="utf-8")
            paths.append(str(path))
        try:
            compiled=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none","-implicit:none",
                 "-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(out),*paths],cwd=root,env=env,
                stdin=subprocess.DEVNULL,capture_output=True,timeout=180)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R227OriginalReadablePacketError(
                "R227_SOURCE_ONLY_JDK9_COMPILER_ABORTED") from exc
        files={p.relative_to(out).as_posix():p.read_bytes()
               for p in out.rglob("*.class")}
        need(compiled.returncode==0 and
             set(files)=={x[:-5]+".class" for x in sources} and
             len(files)==FINAL_SOURCE_OWNERS,
             "R227_ALL_27_JAVA9_SOURCE_OWNERS_MUST_COMPILE")
        need(sha(files["rs/io/Packet.class"])==NORMALIZED_CLASS_SHA256,
             "R227_NORMALIZED_PACKET_BINARY_SHA_NOT_MATCH")
        for owner,pin in {
            "rs/interfaces/widgets/Class179.class":R221_CLASS_SHA256,
            "rs/interfaces/widgets/Widget.class":R222_REAL_WIDGET_CLASS_SHA256,
            "rs/interfaces/widgets/Class170.class":GAMBLING_SHA256,
            "rs/interfaces/widgets/Class168.class":PACKET_CALLBACK_SHA256,
            "rs/interfaces/widgets/Class169.class":HUD_CALLBACK_SHA256,
            "rs/scriptpacket/Class260.class":
                REAL_EMITTED_CLASSES["rs/scriptpacket/Class260.class"],
        }.items():
            need(sha(files[owner])==pin,
                 "R227_PREVIOUS_ORIGINAL_ACCEPTED_CLASS_CHANGED_"+owner)
        need(files["rs/interfaces/widgets/Class179.class"]==
             reference_spell,
             "R227_ORIGINAL_SPELLBOOK_WHOLE_CLASS_NOT_IDENTICAL")
        def disasm(cp,owner):
            try:
                return subprocess.run(
                    [javap,"-p","-c","-classpath",str(cp),owner],
                    cwd=root,env=env,capture_output=True,text=True,
                    timeout=90,check=True).stdout
            except (OSError,subprocess.SubprocessError) as exc:
                raise R227OriginalReadablePacketError(
                    "R227_ORIGINAL_OR_READABLE_CLASS_JAVAP_FAILED") from exc
        before=disasm(original_jar,"rs.x.e")
        after=disasm(out,"rs.io.Packet")
        base_before=disasm(original_jar,"rs.q.a.a.a")
        base_after=disasm(out,"rs.scriptpacket.Class260")
    verify_packet_class_metadata(original,files["rs/io/Packet.class"])
    base_proof=compare_packet_base_jvm(base_before,base_after)
    verify_superclass_abi(old_base,files[BASE_OWNER+".class"])
    need(base_proof["original_concrete_JVM_instructions_verified"]==BASE_OPS,
         "R227_BASE_CLASS_JVM_OPERATIONS_CHANGED")
    packet_proof=compare_complete_original_packet(before,after)
    need(all(file_sha(path)==pin for path,pin in (
        (original_jar,ORIGINAL_JAR_SHA256),
        (source_tree_zip,SOURCE_ZIP_SHA256),
        (r221_evidence_zip,R221_EVIDENCE_ZIP_SHA256))),
        "R227_PRIVATE_ARTIFACTS_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_original_packet_all_81_methods_readable_source_r227",
        **packet_proof,
        "normalized_private_Packet_java_SHA256":NORMALIZED_JAVA_SHA256,
        "whole_emitted_Packet_class_SHA256":NORMALIZED_CLASS_SHA256,
        "original_obfuscated_Packet_class_SHA256":ORIGINAL_CLASS_SHA256,
        "compiler_expression_normalizations":COMPILER_NORMALIZED_METHOD_COUNT,
        "corrected_compiler_only_Configuration_field1313_Integer":True,
        "original_packet_superclass_52_JVM_instructions_preserved":True,
        "accepted_Spellbook_4314_JVM_instructions_preserved":True,
        "accepted_gambling_widget_and_callbacks_binary_unchanged":True,
        "actual_genuine_decompiled_source_owners":16,
        "compiler_only_nonoriginal_dependency_sources":11,
        "source_only_java9_compiled_classes":FINAL_SOURCE_OWNERS,
        "whole_original_client_compiled":False,
        "original_game_code_executed":False,
        "original_obfuscated_classfile_byte_identity_claimed":False,
        "source_redistribution_authorized":False,
    }

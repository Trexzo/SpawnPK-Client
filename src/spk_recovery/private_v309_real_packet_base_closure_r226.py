"""R226: replace SIX temporary v309 source dependencies with actual Java.

SHA-pinned private source-only JDK9 compile of R225 Class179/Class170/168/169
plus REAL Class260, Packet, Node, DualNode, NodeDeque, Class257 sources.
Original rs/q/a/a/a -> readable Class260: 13 declarations, all 12 concrete
JVM method bodies (52 instructions) compared against actual original JAR.
The still-temporary 11 declarations are explicitly NOT recovered gameplay.
No original JAR / original-derived Java source is committed to public CI.
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

from .classfile import parse_class
from .private_v309_spellbook_real_dependencies_r222 import (
    ORIGINAL_JAR_SHA256,SOURCE_ZIP_SHA256,R221_EVIDENCE_ZIP_SHA256,
    R221_CLASS_SHA256,R222_REAL_WIDGET_CLASS_SHA256,REPLACEMENTS,
    read_unique,read_fake_template_ast,integrate_actual_readable_dependencies,
    file_sha,
)
from .private_v309_gambling_source_closure_r223 import (
    ADDITIONAL_REAL,SOURCE_ROOT,augment_fake_only_sources,
)
from .private_v309_gambling_widget_original_code_r224 import (
    normalize_exact_gambling_source,NORMALIZED_CLASS_SHA256 as GAMBLE_SHA,
)
from .private_v309_gambling_callback_original_code_r225 import (
    normalize_original_readable_overlay_java,
    NORMALIZED_169_CLASS_SHA256 as OVERLAY_SHA,
    READABLE_168_CLASS_SHA256 as PACKET_CALLBACK_SHA,
)

ORIGINAL_OWNER="rs/q/a/a/a"
READABLE_OWNER="rs/scriptpacket/Class260"
ORIGINAL_CLASS_SHA256="2bc61b580ec34dc8fde828b288f37dc9fef86637d830dc411b43d85b9f0e61bf"
REAL_JAVA={
    "rs/scriptpacket/Class260.java":"35c830443eceb92a3402ea2ab034bb50c613ed6543f91d86fe27d9322c9dd94e",
    "rs/io/Packet.java":"df4791701d6820b5ce41388be75d40364b2e8e20f08771d854e5fd62b9cf5030",
    "rs/Node.java":"dc62405cff406ef20c7c6bc1a33947a6b414246e47e5419fa4609c4ea76ee7b6",
    "rs/DualNode.java":"b7c63f2949f5fe7be716974d20a8bf96531b7814dd209de5ea822f15abfdfb0c",
    "rs/NodeDeque.java":"791f595d70e3c1500a190ece947a06c291ae30877fe6e2dca40fc2b7c0608dfd",
    "rs/network/Class257.java":"b41c145718684053a0820a4af0a45d7bc1e028b0167953e963cafa0fabe6b568",
}
REAL_EMITTED_CLASSES={
    "rs/scriptpacket/Class260.class":"4032c94e90c9258a5094128e80c0648d8728128f8932a7b288f2b066e228b299",
    "rs/io/Packet.class":"db27e7c735aa81b99af68b95aded101ba02038ca0929253cc955131",
    "rs/Node.class":"13baea62565030d208fa4b0099c0b1ef59ce42dff3726482e526d986e1379714",
    "rs/DualNode.class":"67a6bb447c50502ed8b3e4bbbfcd6b0e7043c4272d457add02803ec33849339d",
    "rs/NodeDeque.class":"29970eec2ed333aceb9820a080f86b1521a19477548b2aecbd115a866c412010",
    "rs/network/Class257.class":"f6916551f70bfe801582e85478d24872e544fb99081033550b92be3686d020fb",
}
GAMBLE_CLASS_SHA="4dddfefb8f688118c2b433ff0afd9c3834018b337ec8a6c255ad0b33b3e01aeb"
BASELINE_SOURCE_OWNERS=18
FINAL_SOURCE_OWNERS=27
GENUINE_READABLE_SOURCE_OWNERS=16  # includes accepted normalized Class179
NONORIGINAL_COMPILER_DECLARATIONS=11
EXPECTED_CONCRETE_METHODS=12
EXPECTED_ALL_METHODS=13
EXPECTED_ORIGINAL_INSTRUCTIONS=52
EXPECTED_ALIAS_SHA256="7a7282370e2b2e795675e5f7585dd474fff6d086d3b18a5c5b2e096d61e98973"

CONCRETE_METHODS=(
    ("public rs.q.a.a.a();","public rs.scriptpacket.Class260();",3),
    ("public void configure(com.google.inject.Binder);","public void configure(com.google.inject.Binder);",1),
    ("public void a(rs.x.e);","public void setPacket(rs.io.Packet);",4),
    ("public void a(rs.Client);","public void setClient(rs.Client);",4),
    ("public int c();","public int method777();",4),
    ("public long d();","public long method3412();",4),
    ("public int e();","public int method2463();",4),
    ("public int f();","public int method1462();",4),
    ("public int a(int);","public int method3631(int);",13),
    ("public int g();","public int method442();",4),
    ("public java.lang.String h();","public java.lang.String method2632();",4),
    ("public final com.google.inject.Injector i();",
     "public final com.google.inject.Injector method2909();",3),
)
ABSTRACT_METHOD=(
    ("a","()V"),("handlePacket","()V"),
)
# These are original->readable constant-pool references, not guesses.
ALIASES={
    "Field b:Lrs/x/e;":"Field packet:Lrs/io/Packet;",
    "Field c:Lrs/Client;":"Field client:Lrs/Client;",
    "Method rs/x/e.A:()I":"Method rs/io/Packet.method3348:()I",
    "Method rs/x/e.E:()J":"Method rs/io/Packet.method1875:()J",
    "Method rs/x/e.y:()I":"Method rs/io/Packet.readUnsignedByte:()I",
    "Method a:(I)I":"Method method3631:(I)I",
    "Method rs/x/e.J:()V":"Method rs/io/Packet.method3628:()V",
    "Method rs/x/e.k:(I)I":"Method rs/io/Packet.getBits:(I)I",
    "Method rs/x/e.K:()V":"Method rs/io/Packet.method480:()V",
    "Method rs/x/e.D:()I":"Method rs/io/Packet.method1287:()I",
    "Method rs/x/e.F:()Ljava/lang/String;":
        "Method rs/io/Packet.method814:()Ljava/lang/String;",
    "Field a:Lcom/google/inject/Injector;":
        "Field field4122:Lcom/google/inject/Injector;",
}
# Only 11 compiler-only owners remain after replacing Class260; three Guice
# interfaces and three supporting types are NEW, explicitly nonoriginal.
TEMPORARY_JAVA={
    "com/google/inject/Binder.java":
        "package com.google.inject; public interface Binder {}",
    "com/google/inject/Injector.java":
        "package com.google.inject; public interface Injector {}",
    "com/google/inject/Module.java":
        "package com.google.inject; public interface Module {void configure(Binder b);}",
    "rs/pkg48/Class307.java":
        "package rs.pkg48; public class Class307 {public static void method2446(String s){} }",
}


class R226RealPacketClosureError(ValueError):
    pass


def need(condition,why):
    if not condition:
        raise R226RealPacketClosureError(why)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_code(text,method_header):
    lines=text.splitlines()
    matches=[i for i,line in enumerate(lines) if line.strip()==method_header]
    need(len(matches)==1,"R226_JVM_METHOD_HEADER_NOT_UNIQUE")
    idx=matches[0]+1
    need(idx<len(lines) and lines[idx].strip()=="Code:",
         "R226_EXPECTED_CONCRETE_METHOD_CODE")
    result=[]
    for line in lines[idx+1:]:
        m=re.match(r"^\s*(\d+):\s+(\w+)(.*)$",line)
        if not m:break
        operand=m.group(3).strip()
        if "//" in operand:operand=operand.split("//",1)[1].strip()
        result.append((int(m.group(1)),m.group(2),operand))
    need(bool(result) and len({r[0] for r in result})==len(result),
         "R226_EMPTY_OR_DUPLICATED_JVM_INSTRUCTIONS")
    return result


def compare_packet_base_jvm(original_javap,readable_javap, *,
                            method_rows=CONCRETE_METHODS,
                            aliases=ALIASES,
                            expected_total=EXPECTED_ORIGINAL_INSTRUCTIONS):
    need(len(method_rows)==EXPECTED_CONCRETE_METHODS and
         sum(x[2] for x in method_rows)==EXPECTED_ORIGINAL_INSTRUCTIONS,
         "R226_TWELVE_ORIGINAL_METHOD_INVENTORY_CHANGED")
    mapping={}
    methods=[]
    for old,new,count in method_rows:
        a=parse_code(original_javap,old)
        b=parse_code(readable_javap,new)
        need(len(a)==len(b)==count,"R226_METHOD_INSTRUCTION_COUNT_CHANGED")
        for x,y in zip(a,b):
            need(x[:2]==y[:2] and
                 aliases.get(x[2],x[2])==y[2],
                 "R226_ORIGINAL_PACKET_BASE_OPCODE_OFFSET_OPERAND_DRIFT")
            if x[2]!=y[2]:
                need(x[2] in aliases and
                     x[2] not in mapping or
                     (x[2] in mapping and mapping[x[2]]==y[2]),
                     "R226_UNMAPPED_OR_CONFLICTING_FIELD_METHOD_ALIAS")
                mapping[x[2]]=y[2]
        methods.append({"original":old,"readable":new,"instructions":count})
    need(len(mapping)==len(aliases) and mapping==aliases and
         sha(json.dumps(mapping,sort_keys=True,
                        separators=(",",":")).encode())==
         EXPECTED_ALIAS_SHA256 and
         sum(x["instructions"] for x in methods)==expected_total,
         "R226_ORIGINAL_PACKET_CLASS_ALL_MEMBER_ALIAS_PINS_REQUIRED")
    return {
        "original_concrete_method_bodies_verified":len(method_rows),
        "original_concrete_JVM_instructions_verified":expected_total,
        "original_JVM_offsets_opcodes_and_operands_match":True,
        "explicit_member_aliases_verified":len(mapping),
        "methods":methods,
    }


def verify_superclass_abi(original_class,readable_class):
    a=parse_class(original_class)
    b=parse_class(readable_class)
    need(a.name==ORIGINAL_OWNER and b.name==READABLE_OWNER and
         a.super_name==b.super_name=="java/lang/Object" and
         a.major==b.major==53 and
         a.interfaces==b.interfaces==["com/google/inject/Module"] and
         len(a.fields)==len(b.fields)==3 and
         len(a.methods)==len(b.methods)==EXPECTED_ALL_METHODS,
         "R226_ORIGINAL_PACKET_BASE_CLASS_HEADER_OR_ABI_DRIFT")
    field_names=(
        (("a","Lcom/google/inject/Injector;"),
         ("field4122","Lcom/google/inject/Injector;")),
        (("b","Lrs/x/e;"),("packet","Lrs/io/Packet;")),
        (("c","Lrs/Client;"),("client","Lrs/Client;")),
    )
    need(all((x["name"],x["descriptor"],x["access"])==
             (n,d,y["access"]) and
             (y["name"],y["descriptor"])==(mapped,md)
             for x,y,((n,d),(mapped,md)) in
             zip(a.fields,b.fields,field_names)),
         "R226_ORIGINAL_THREE_INSTANCE_FIELD_ABI_DRIFT")
    old=[m for m in a.methods if
         (m["name"],m["descriptor"])==ABSTRACT_METHOD[0]]
    new=[m for m in b.methods if
         (m["name"],m["descriptor"])==ABSTRACT_METHOD[1]]
    need(len(old)==len(new)==1 and
         old[0]["access"]==new[0]["access"] and
         (old[0]["access"]&0x0400)!=0,
         "R226_ORIGINAL_ABSTRACT_PACKET_CALLBACK_ABI_CHANGED")
    return True


def build_real_packet_closure(original_jar,source_tree_zip,r221_evidence_zip):
    need(all(file_sha(path)==pin for path,pin in (
        (original_jar,ORIGINAL_JAR_SHA256),
        (source_tree_zip,SOURCE_ZIP_SHA256),
        (r221_evidence_zip,R221_EVIDENCE_ZIP_SHA256))),
        "R226_THREE_PINNED_PRIVATE_INPUT_ARTIFACTS_REQUIRED")
    with ZipFile(original_jar) as jar:
        original_class=read_unique(jar,ORIGINAL_OWNER+".class",100000)
    need(sha(original_class)==ORIGINAL_CLASS_SHA256,
         "R226_ORIGINAL_PACKET_SUPERCLASS_SHA_CHANGED")
    with ZipFile(source_tree_zip) as tree:
        all_reals={**{f"rs/interfaces/widgets/{key}.java":value
                       for key,value in REPLACEMENTS.items()},
                   **ADDITIONAL_REAL,**REAL_JAVA}
        real_sources={}
        for owner,pin in all_reals.items():
            blob=read_unique(tree,SOURCE_ROOT+owner,1000000)
            need(sha(blob)==pin,"R226_REAL_EXISTING_JAVA_HASH_CHANGED_"+owner)
            real_sources[owner]=blob.decode("utf-8")
    with ZipFile(r221_evidence_zip) as evidence:
        template=read_unique(evidence,
            "scripts/source-only-recompile-unified-class.py",30000)
        normalized=read_unique(evidence,
            "private/normalized-readable-Class179.java",100000)
        reference=read_unique(evidence,
            "private/compiled-readable-Class179.class",100000)
    need(sha(reference)==R221_CLASS_SHA256,
         "R226_PREVIOUS_ACCEPTED_SPELLBOOK_BINARY_SHA_CHANGED")
    four={simple:real_sources[f"rs/interfaces/widgets/{simple}.java"]
          for simple in REPLACEMENTS}
    sources=integrate_actual_readable_dependencies(
        read_fake_template_ast(template),four)
    sources["rs/interfaces/widgets/Class179.java"]=normalized.decode("utf-8")
    sources=augment_fake_only_sources(
        sources,{k:real_sources[k] for k in ADDITIONAL_REAL})
    for cls in ("Class170","Class169"):
        owner=f"rs/interfaces/widgets/{cls}.java"
        sources[owner]=(
            normalize_exact_gambling_source(sources[owner]) if cls=="Class170"
            else normalize_original_readable_overlay_java(sources[owner]))
    for owner in REAL_JAVA:
        sources[owner]=real_sources[owner]
    sources.update(TEMPORARY_JAVA)
    # Packet needs four additional *signatures*, never original behavior.
    cfg="rs/Configuration.java"
    need(sources[cfg].count(
        "public static rs.pkg39.Class53 screenMode;")==1,
         "R226_TEMPORARY_CONFIGURATION_SIGNATURE_DRIFT")
    sources[cfg]=sources[cfg].replace(
        "public static rs.pkg39.Class53 screenMode;",
        "public static int field1313; public static rs.pkg39.Class53 screenMode;",
        1)
    need(len(sources)==FINAL_SOURCE_OWNERS and
         len(REAL_JAVA)==6 and
         len(REPLACEMENTS)+len(ADDITIONAL_REAL)+len(REAL_JAVA)+1==
             GENUINE_READABLE_SOURCE_OWNERS and
         len(sources)-GENUINE_READABLE_SOURCE_OWNERS==
             NONORIGINAL_COMPILER_DECLARATIONS,
         "R226_REAL_VS_TEMPORARY_SOURCE_PARTITION_CHANGED")
    return sources,original_class,reference


def verify_pinned_packet_closure(original_jar,source_tree_zip,r221_evidence_zip):
    sources,original_class,original_spellbook=build_real_packet_closure(
        original_jar,source_tree_zip,r221_evidence_zip)
    javac=shutil.which("javac");javap=shutil.which("javap")
    need(bool(javac and javap),"R226_JDK_JAVAC_AND_JAVAP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r226-real-packet-") as tmp:
        root=Path(tmp);out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        paths=[]
        for owner,java in sources.items():
            dest=root/"src"/owner
            need(not dest.exists(),"R226_JAVA_OWNER_NOT_UNIQUE")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(java,encoding="utf-8")
            paths.append(str(dest))
        env={k:v for k,v in os.environ.items()
             if k not in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                           "JDK_JAVA_OPTIONS","_JAVA_OPTIONS")}
        try:
            proc=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=180,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R226RealPacketClosureError("R226_JAVAC_ABORTED") from exc
        emitted={p.relative_to(out).as_posix():p.read_bytes()
                 for p in out.rglob("*.class")}
        need(proc.returncode==0 and
             set(emitted)=={name[:-5]+".class" for name in sources},
             "R226_ALL_27_JAVA9_SOURCES_MUST_COMPILE")
        for owner,pin in {
            "rs/interfaces/widgets/Class179.class":R221_CLASS_SHA256,
            "rs/interfaces/widgets/Widget.class":R222_REAL_WIDGET_CLASS_SHA256,
            "rs/interfaces/widgets/Class170.class":GAMBLE_CLASS_SHA,
            "rs/interfaces/widgets/Class168.class":PACKET_CALLBACK_SHA,
            "rs/interfaces/widgets/Class169.class":OVERLAY_SHA,
            **REAL_EMITTED_CLASSES,
        }.items():
            need(sha(emitted[owner])==pin,
                 "R226_ACCEPTED_OR_ACTUAL_JAVA_CLASS_SHA_DRIFT_"+owner)
        need(emitted["rs/interfaces/widgets/Class179.class"]==
             original_spellbook,
             "R226_4314_ORIGINAL_SPELLBOOK_JVM_CODE_CHANGED")
        readable_base=emitted[READABLE_OWNER+".class"]
        def disasm(cp,owner):
            try:
                return subprocess.run(
                    [javap,"-p","-c","-classpath",str(cp),owner],
                    cwd=root,env=env,capture_output=True,text=True,
                    check=True,timeout=70).stdout
            except (OSError,subprocess.SubprocessError) as exc:
                raise R226RealPacketClosureError(
                    "R226_CLASSFILE_DISASSEMBLY_FAILED") from exc
        original_javap=disasm(original_jar,"rs.q.a.a.a")
        readable_javap=disasm(out,"rs.scriptpacket.Class260")
    verify_superclass_abi(original_class,readable_base)
    proof=compare_packet_base_jvm(original_javap,readable_javap)
    need(all(file_sha(path)==pin for path,pin in (
        (original_jar,ORIGINAL_JAR_SHA256),
        (source_tree_zip,SOURCE_ZIP_SHA256),
        (r221_evidence_zip,R221_EVIDENCE_ZIP_SHA256))),
        "R226_PINNED_ARTIFACTS_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_original_packet_base_and_real_packet_node_source_closure_r226",
        **proof,
        "original_abstract_callback_declarations_matched":1,
        "original_packet_superclass_total_methods":EXPECTED_ALL_METHODS,
        "actual_original_decompiled_readable_java_owners":
            GENUINE_READABLE_SOURCE_OWNERS,
        "clearly_nonoriginal_compiler_declarations":
            NONORIGINAL_COMPILER_DECLARATIONS,
        "source_only_javac_release":9,
        "compiled_java_source_and_classfile_count":FINAL_SOURCE_OWNERS,
        "compiler_errors":0,
        "Class179_original_4314_JVM_method_proof_unchanged":True,
        "Class170_Class168_Class169_original_code_evidence_preserved":True,
        "original_full_Packet_JVM_parity_verified_here":False,
        "original_client_code_executed":False,
        "whole_original_v309_client_compiles":False,
        "source_redistribution_authorized":False,
    }

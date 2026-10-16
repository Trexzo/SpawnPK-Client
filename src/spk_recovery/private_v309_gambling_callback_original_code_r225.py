"""R225: recover the REAL v309 gambling packet + HUD callback JVM Code.

Original rs/n/c/W.class -> existing readable Class168.java (VERBATIM).
Original rs/n/c/X.class -> existing readable Class169.java (one explicitly
tracked, behavior-equivalent early return compiler-shape change).

Source-only Java 9 rebuild of the complete R223/R224 18-owner candidate
must preserve the accepted Class179 / Widget / Class170 binaries exactly.
The two new callbacks' original Code is matched instruction by instruction.
No game code is ever executed; fake build declarations are NOT recovered.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .private_v309_spellbook_real_dependencies_r222 import (
    ORIGINAL_JAR_SHA256, SOURCE_ZIP_SHA256, R221_EVIDENCE_ZIP_SHA256,
    R221_CLASS_SHA256, R222_REAL_WIDGET_CLASS_SHA256,
    REPLACEMENTS, read_unique,read_fake_template_ast,
    integrate_actual_readable_dependencies,file_sha,
)
from .private_v309_gambling_source_closure_r223 import (
    ADDITIONAL_REAL,SOURCE_ROOT,augment_fake_only_sources,
)
from .private_v309_gambling_widget_original_code_r224 import (
    normalize_exact_gambling_source,
    NORMALIZED_CLASS_SHA256 as R224_GAMBLING_WIDGET_SHA256,
    decode_javap_method,
)

READABLE_168_SHA256=(
    "28a814fd331abe90eb2711929d4edc84c184d7a41bc8fcf90b13117b5ec20103"
)
READABLE_169_SHA256=(
    "591e74de23e0824070636a8ff4a5197e347e5b495f2fe2698b880f05b664d996"
)
NORMALIZED_169_SOURCE_SHA256=(
    "285d42d5c59f442057c354635ef95ee05e2d32d1f01debae0c82b7e44c73bce8"
)
NORMALIZED_169_CLASS_SHA256=(
    "cae4619b7ffc5c653f38c22277ae0b6a3c5309f962033aabb2a200da74c16592"
)
READABLE_168_CLASS_SHA256=(
    "0604158afc9475bdae752a0e2df7fd64483b2208dd7c571f709239416779db02"
)
ORIGINAL_168_CLASS_SHA256=(
    "a4dfe82736a05630859290ed16361af359b8bc0b45c9f3441d15b56fde105dbd"
)
ORIGINAL_169_CLASS_SHA256=(
    "74e96c4c84103eb7f8fecdc06cec69077d85d87b38d5cc9f82696ec1cb9b4859"
)
EARLY_GUARD_BEFORE="      if (var2 == Class69.field2525) {"
EARLY_GUARD_AFTER="      if (var2 != Class69.field2525) return;"
TRAILER_BEFORE=(
    "      }\n   }\n\n   @Override\n   public void method904()"
)
TRAILER_AFTER=(
    "   }\n\n   @Override\n   public void method904()"
)
SYMBOL_PREFIXES=("Field ","Method ","InterfaceMethod ","class ","InvokeDynamic ")

# Exact original header, readable header, original name + JVM descriptor,
# readable name + descriptor, original instruction count, member-alias SHA.
PACKET_METHODS=(
    ("rs.n.c.W();","rs.interfaces.widgets.Class168();",
     "<init>","()V","<init>","()V",3,
     "2addf1c8ffbf6c8e452ced23ab6660a6cc6e73a4877029248d5e3f84f0f7e377"),
    ("public void a();","public void handlePacket();",
     "a","()V","handlePacket","()V",17,
     "632f0fbe433fddf7c048faaff16db5319cf15124eb84593d3baf12083937967b"),
)
OVERLAY_METHODS=(
    ("rs.n.c.X();","rs.interfaces.widgets.Class169();",
     "<init>","()V","<init>","()V",3,
     "16f602143cdfa99b2cf7ee5f09a925b5f00ec282ea27ccf6ee2383020bfd42a5"),
    ("public void b();","public void method1484();",
     "b","()V","method1484","()V",1,
     "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"),
    ("public boolean a(rs.Client);","public boolean method3175(rs.Client);",
     "a","(Lrs/Client;)Z","method3175","(Lrs/Client;)Z",9,
     "145305340e304ff736822daee237537f8ad1972ca51bcc33c20f1b3d73abdd4a"),
    ("public void b(rs.Client, rs.l.e.f$a);",
     "public void method1640(rs.Client, rs.graphics.hud.Class69);",
     "b","(Lrs/Client;Lrs/l/e/f$a;)V",
     "method1640","(Lrs/Client;Lrs/graphics/hud/Class69;)V",98,
     "31216caf9592b0d6f36af7363ba97212e21f438fcdab115f29f7292f88018415"),
    ("public void c();","public void method904();",
     "c","()V","method904","()V",1,
     "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"),
)
PACKET_ALIAS_SHA256=(
    "47855c9a98f09ec1f784651d00ac05ce64c02bbb9d0e28a62397377a0e2bdf85"
)
OVERLAY_ALIAS_SHA256=(
    "d737df220db4bd4485e1b91149a82e5d83883a7d9d8a855b97b2dbd37a6329fe"
)


class R225OriginalCallbacksError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R225OriginalCallbacksError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize_original_readable_overlay_java(source, *,
          original_sha=READABLE_169_SHA256,
          normalized_sha=NORMALIZED_169_SOURCE_SHA256):
    """One predicate inversion + early return, and its matching closing brace."""
    need(type(source) is str and sha(source.encode("utf-8"))==original_sha,
         "R225_ACTUAL_UNCHANGED_CLASS169_SOURCE_PIN_REQUIRED")
    need(source.count(EARLY_GUARD_BEFORE)==1 and
         source.count(TRAILER_BEFORE)==1 and
         EARLY_GUARD_AFTER not in source,
         "R225_CLASS169_EXACT_GUARD_SOURCE_SHAPE_MISSING")
    result=source.replace(EARLY_GUARD_BEFORE,EARLY_GUARD_AFTER,1)
    result=result.replace(TRAILER_BEFORE,TRAILER_AFTER,1)
    need(sha(result.encode("utf-8"))==normalized_sha,
         "R225_ONLY_APPROVED_EARLY_RETURN_NORMALIZATION")
    return result


def compare_callback_jvm_code(original_javap,readable_javap, *,
                              methods,
                              original_total,alias_count,alias_sha):
    need(len(methods)>0 and sum(x[6] for x in methods)==original_total,
         "R225_EXACT_ORIGINAL_CALLBACK_METHOD_INVENTORY_REQUIRED")
    collective={}
    results=[]
    for oh,rh,on,od,rn,rd,nops,pin in methods:
        old=decode_javap_method(original_javap,oh)
        new=decode_javap_method(readable_javap,rh)
        need(len(old)==len(new)==nops,
             "R225_ORIGINAL_METHOD_OP_COUNT_MISMATCH_"+on)
        aliases={}
        for left,right in zip(old,new):
            need(left[:2]==right[:2],
                 "R225_ORIGINAL_OFFSET_OR_OPCODE_CHANGED_"+on)
            if left[2]!=right[2]:
                need(left[2].startswith(SYMBOL_PREFIXES) and
                     right[2].startswith(SYMBOL_PREFIXES),
                     "R225_ORIGINAL_JVM_NON_SYMBOLIC_OPERAND_CHANGED_"+on)
                need(left[2] not in aliases or aliases[left[2]]==right[2],
                     "R225_INCONSISTENT_ORIGINAL_SYMBOLIC_RENAME_"+on)
                aliases[left[2]]=right[2]
        need(sha(json.dumps(aliases,sort_keys=True,
                           separators=(",",":")).encode())==pin,
             "R225_PER_ORIGINAL_METHOD_SYMBOLIC_ALIASES_CHANGED_"+on)
        for before,after in aliases.items():
            need(before not in collective or collective[before]==after,
                 "R225_TWO_METHODS_RENAME_ONE_SYMBOL_DIFFERENTLY")
            collective[before]=after
        need(old[-1][1]==new[-1][1]
             and old[-1][1] in ("return","ireturn"),
             "R225_ORIGINAL_CALLBACK_RETURN_OPCODE_CHANGED")
        results.append({
            "original_method":on+od,
            "readable_method":rn+rd,
            "original_JVM_instructions_matched":nops,
            "distinct_original_to_readable_symbols":len(aliases),
        })
    need(len(collective)==alias_count and
         sha(json.dumps(collective,sort_keys=True,
                        separators=(",",":")).encode())==alias_sha,
         "R225_COMPLETE_ORIGINAL_CALLBACK_SYMBOL_MAPPING_CHANGED")
    return {
        "method_count":len(results),
        "instruction_count":sum(x["original_JVM_instructions_matched"]
                                for x in results),
        "symbolic_alias_count":len(collective),
        "all_branch_offsets_and_constants_identical":True,
        "methods":results,
    }


def verify_private_original_gambling_callbacks(original_jar,source_zip,
                                               r221_zip):
    need(file_sha(original_jar)==ORIGINAL_JAR_SHA256 and
         file_sha(source_zip)==SOURCE_ZIP_SHA256 and
         file_sha(r221_zip)==R221_EVIDENCE_ZIP_SHA256,
         "R225_ALL_THREE_PRIVATE_JAR_ZIP_SOURCE_PINS_REQUIRED")
    with ZipFile(original_jar) as jar:
        w=read_unique(jar,"rs/n/c/W.class",30000)
        x=read_unique(jar,"rs/n/c/X.class",30000)
    need(sha(w)==ORIGINAL_168_CLASS_SHA256 and
         sha(x)==ORIGINAL_169_CLASS_SHA256,
         "R225_ORIGINAL_PACKET_OR_HUD_CALLBACK_CLASS_SHA_CHANGED")
    with ZipFile(source_zip) as tree:
        four={}
        for owner,pin in REPLACEMENTS.items():
            data=read_unique(tree,SOURCE_ROOT+"rs/interfaces/widgets/"+
                             owner+".java",200000)
            need(sha(data)==pin,
                 "R225_R222_REAL_JAVA_SOURCE_CHANGED_"+owner)
            four[owner]=data.decode("utf-8")
        five={}
        for relative,pin in ADDITIONAL_REAL.items():
            data=read_unique(tree,SOURCE_ROOT+relative,200000)
            need(sha(data)==pin,
                 "R225_R223_REAL_JAVA_SOURCE_CHANGED_"+relative)
            five[relative]=data.decode("utf-8")
    with ZipFile(r221_zip) as proof:
        template=read_unique(proof,
            "scripts/source-only-recompile-unified-class.py",30000)
        source179=read_unique(proof,
            "private/normalized-readable-Class179.java",150000)
        compiled179=read_unique(proof,
            "private/compiled-readable-Class179.class",200000)
    need(sha(compiled179)==R221_CLASS_SHA256,
         "R225_R221_ORIGINAL_VERIFIED_CLASS_HASH_CHANGED")
    sources=integrate_actual_readable_dependencies(
        read_fake_template_ast(template),four)
    sources["rs/interfaces/widgets/Class179.java"]=source179.decode("utf-8")
    sources=augment_fake_only_sources(sources,five)
    sources["rs/interfaces/widgets/Class170.java"]=(
        normalize_exact_gambling_source(
            sources["rs/interfaces/widgets/Class170.java"]))
    sources["rs/interfaces/widgets/Class169.java"]=(
        normalize_original_readable_overlay_java(
            sources["rs/interfaces/widgets/Class169.java"]))
    javac=shutil.which("javac");javap=shutil.which("javap")
    need(bool(javac and javap),"R225_SOURCE_ONLY_JAVA9_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r225-callback-") as td:
        root=Path(td);empty=root/"empty";out=root/"classes"
        empty.mkdir();out.mkdir();paths=[]
        for relative,java in sources.items():
            dest=root/"src"/relative
            need(not dest.exists(),"R225_DUPLICATE_SOURCE_OWNER")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(java,encoding="utf-8")
            paths.append(str(dest))
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):env.pop(key,None)
        try:
            result=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,capture_output=True,timeout=150,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R225OriginalCallbacksError(
                "R225_SOURCE_ONLY_JAVA9_COMPILER_ABORTED") from exc
        emitted={str(p.relative_to(out)) for p in out.rglob("*.class")}
        need(result.returncode==0 and len(sources)==18 and
             emitted=={x[:-5]+".class" for x in sources},
             "R225_WHOLE_CALLBACK_SOURCE_SET_JAVAC_FAILED")
        def binary(owner):
            return (out/(owner+".class")).read_bytes()
        packet=binary("rs/interfaces/widgets/Class168")
        overlay=binary("rs/interfaces/widgets/Class169")
        gambling=binary("rs/interfaces/widgets/Class170")
        spell=binary("rs/interfaces/widgets/Class179")
        widget=binary("rs/interfaces/widgets/Widget")
        need(sha(packet)==READABLE_168_CLASS_SHA256 and
             sha(overlay)==NORMALIZED_169_CLASS_SHA256 and
             sha(gambling)==R224_GAMBLING_WIDGET_SHA256 and
             spell==compiled179 and
             sha(widget)==R222_REAL_WIDGET_CLASS_SHA256,
             "R225_SOURCE_REBUILD_CHANGED_ACCEPTED_DEPENDENT_CLASS_BYTES")
        def disassemble(cp,owner):
            try:
                return subprocess.run([
                    javap,"-p","-c","-classpath",str(cp),owner],
                    cwd=root,env=env,capture_output=True,text=True,
                    timeout=60,check=True).stdout
            except (OSError,subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as exc:
                raise R225OriginalCallbacksError(
                    "R225_ORIGINAL_OR_READABLE_JAVAP_FAILED") from exc
        before_w=disassemble(original_jar,"rs.n.c.W")
        after_w=disassemble(out,"rs.interfaces.widgets.Class168")
        before_x=disassemble(original_jar,"rs.n.c.X")
        after_x=disassemble(out,"rs.interfaces.widgets.Class169")
    for original_binary,rebuilt_binary,methods in (
        (w,packet,PACKET_METHODS),
        (x,overlay,OVERLAY_METHODS),
    ):
        a=profile_class_field_accesses(original_binary)
        b=profile_class_field_accesses(rebuilt_binary)
        def find(profile,name,desc):
            rows=[m for m in profile["methods"]
                  if (m["name"],m["descriptor"])==(name,desc)]
            need(len(rows)==1,"R225_REAL_METHOD_OWNER_NOT_UNIQUE")
            return rows[0]
        for _,_,on,od,rn,rd,count,_ in methods:
            p=find(a,on,od);q=find(b,rn,rd)
            need(p["access"]==q["access"] and
                 p["code_length"]==q["code_length"] and
                 p["max_stack"]==q["max_stack"] and
                 p["max_locals"]==q["max_locals"] and
                 p["exception_handlers"]==q["exception_handlers"] and
                 p["stackmap_table_present"]==q["stackmap_table_present"],
                 "R225_ORIGINAL_CALLBACK_JVM_CODE_METADATA_CHANGED_"+on)
    pw=compare_callback_jvm_code(
        before_w,after_w,methods=PACKET_METHODS,
        original_total=20,alias_count=4,alias_sha=PACKET_ALIAS_SHA256)
    px=compare_callback_jvm_code(
        before_x,after_x,methods=OVERLAY_METHODS,
        original_total=112,alias_count=13,alias_sha=OVERLAY_ALIAS_SHA256)
    need(file_sha(original_jar)==ORIGINAL_JAR_SHA256 and
         file_sha(source_zip)==SOURCE_ZIP_SHA256 and
         file_sha(r221_zip)==R221_EVIDENCE_ZIP_SHA256,
         "R225_PRIVATE_FILES_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_real_gambling_packet_hud_callbacks_source_r225",
        "original_packet_owner":"rs/n/c/W",
        "original_hud_owner":"rs/n/c/X",
        "packet":pw,"hud":px,
        "total_original_callbacks_methods_verified":7,
        "total_original_callbacks_JVM_instructions_verified":132,
        "additional_R224_original_gambling_widget_instructions_preserved":954,
        "preserved_original_semantic_spellbook_JVM_instructions":4314,
        "Class179_byte_identical_to_R221":True,
        "Class170_original_JVM_Code_preserved":True,
        "two_verbatim_and_one_compiler_normalized_real_Java_sources":True,
        "temporary_nonoriginal_dependency_source_count":8,
        "java_source_owners_compiled":18,
        "original_client_game_code_executed":False,
        "entire_client_compiled":False,
        "redistribution_rights_verified":False,
    }

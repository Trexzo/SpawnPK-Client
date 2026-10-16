"""R224: original v309 gambling widget ALL six method Code bodies.

A complete, locally rebuilt readable Class170.java corresponds to ORIGINAL
rs/n/c/V.class. Exactly TWO source compiler-shape normalizations change
expanded array stores into semantically equivalent -= / += expressions.
No original game method is executed. Original-derived source and binary
remain private; hosted tests use separately authored fixtures.

The full R223 source-only dependency build is replayed with the normalized
genuine Class170 method source and all 18 compiled Java owners. The
independently R221-verified Class179.class MUST remain byte-for-byte equal.
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
from .private_v309_spellbook_real_dependencies_r222 import (
    ORIGINAL_JAR_SHA256, SOURCE_ZIP_SHA256,
    R221_EVIDENCE_ZIP_SHA256, R221_CLASS_SHA256,
    R222_REAL_WIDGET_CLASS_SHA256, REPLACEMENTS,
    integrate_actual_readable_dependencies,
    read_unique, read_fake_template_ast, file_sha,
)
from .private_v309_gambling_source_closure_r223 import (
    ADDITIONAL_REAL, SOURCE_ROOT, augment_fake_only_sources,
)

ORIGINAL_OWNER="rs/n/c/V"
READABLE_OWNER="rs/interfaces/widgets/Class170"
ORIGINAL_CLASS_SHA256=(
    "51c5f49ff23619c5417a248788b15f66da5f1db5760e09835aa7aae6d6245686"
)
REAL_JAVA_SHA256=(
    "73a2f01084e9abd1c86c9d6cad95cb35ce58873f0f45a771b79c36e2bad54b42"
)
NORMALIZED_JAVA_SHA256=(
    "33def70a97c84201b14b501b8785068703bb04431f1d622eb66d0a6d96cb2d93"
)
NORMALIZED_CLASS_SHA256=(
    "4dddfefb8f688118c2b433ff0afd9c3834018b337ec8a6c255ad0b33b3e01aeb"
)
GLOBAL_ALIAS_SHA256=(
    "55eb560ebb8c6910ce588015d7517e01ccfda15344d168b588b1442cde276abf"
)
METHODS=(
    ("public rs.n.c.V(rs.l.K[]);",
     "public rs.interfaces.widgets.Class170(rs.graphics.HitsplatFont[]);",
     "<init>", "([Lrs/l/K;)V","<init>",
     "([Lrs/graphics/HitsplatFont;)V",4,
     "1c5f629d4f842c62434516fb803e0c31f03caef33589461ec47503e0f7075814"),
    ("public void a();","public void register();",
     "a","()V","register","()V",5,
     "6d4e7a2875b2e95d014ba6c5cf0dd217d6354d2771f1e41270695a5ce587d2a6"),
    ("public void h();","public void method1306();",
     "h","()V","method1306","()V",607,
     "14d80fbbc36099cadd2274c77ba291ca2c8a5edef9e5161945f488b865048c37"),
    ("public void i();","public void method268();",
     "i","()V","method268","()V",223,
     "da3b023156bae3bc010ef86d783c02f49806babfbc0c1e21fc2c530f0b79b0aa"),
    ("private rs.n.e m(int);",
     "private rs.interfaces.WidgetComponent method701(int);",
     "m","(I)Lrs/n/e;","method701",
     "(I)Lrs/interfaces/WidgetComponent;",102,
     "66d5159a58499ad6b27f23f85dd824df60cbda2c660670570046d875d81531e2"),
    ("static {};","static {};",
     "<clinit>","()V","<clinit>","()V",13,
     "734d81eaf8a45d31bd895dae6d21d3f820f126f3f9a11b0e7bd889ee2e4df83f"),
)
BEFORE_AFTER=(
    ("var1.childY[var6] = var1.childY[var6] - 9;",
     "var1.childY[var6] -= 9;"),
    ("var1.childY[var6] = var1.childY[var6] + 13;",
     "var1.childY[var6] += 13;"),
)
SYMBOL_PREFIXES=("Field ","Method ","InterfaceMethod ","class ","InvokeDynamic ")


class R224GamblingWidgetParityError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R224GamblingWidgetParityError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize_exact_gambling_source(source, *,
                                    source_sha=REAL_JAVA_SHA256,
                                    normalized_sha=NORMALIZED_JAVA_SHA256):
    need(type(source) is str and sha(source.encode("utf-8"))==source_sha,
         "R224_EXACT_UNMODIFIED_REAL_JAVA_REQUIRED")
    candidate=source
    for original,rewritten in BEFORE_AFTER:
        need(candidate.count(original)==1 and
             rewritten not in candidate,
             "R224_COMPOUND_ARRAY_ASSIGNMENT_ANCHOR_DRIFT")
        candidate=candidate.replace(original,rewritten,1)
    need(sha(candidate.encode("utf-8"))==normalized_sha,
         "R224_EXACT_TWO_BEHAVIOR_PRESERVING_EDITS_ONLY")
    return candidate


def decode_javap_method(disassembly,header):
    lines=disassembly.splitlines()
    indexes=[i for i,x in enumerate(lines) if x.strip()==header]
    need(len(indexes)==1,"R224_MISSING_OR_DUPLICATED_METHOD_HEADER")
    start=indexes[0]+1
    need(start<len(lines) and lines[start].strip()=="Code:",
         "R224_MISSING_JVM_CODE_ATTRIBUTE")
    rows=[]
    for line in lines[start+1:]:
        m=re.match(r"^\s+(\d+):\s+(\w+)(.*)$",line)
        if not m:break
        operand=m.group(3).strip()
        if "//" in operand:operand=operand.split("//",1)[1].strip()
        rows.append((int(m.group(1)),m.group(2),operand))
    need(bool(rows) and len({x[0] for x in rows})==len(rows),
         "R224_JVM_CODE_DECODE_EMPTY_OR_DUPLICATED")
    return rows


def verify_original_class170_code(original_javap, rebuilt_javap, *,
                                  methods=METHODS,
                                  original_total=954,
                                  global_alias_sha=GLOBAL_ALIAS_SHA256,
                                  expected_alias_count=50):
    need(len(methods)==6 and sum(row[6] for row in methods)==original_total,
         "R224_EXACT_SIX_JVM_METHOD_INVENTORY_REQUIRED")
    all_aliases={}
    method_report=[]
    for old_header,new_header,old_name,old_desc,new_name,new_desc,nops,pin in methods:
        original=decode_javap_method(original_javap,old_header)
        rebuilt=decode_javap_method(rebuilt_javap,new_header)
        need(len(original)==len(rebuilt)==nops,
             "R224_WRONG_ORIGINAL_METHOD_INSTRUCTION_COUNT_"+old_name)
        aliases={}
        for a,b in zip(original,rebuilt):
            need(a[:2]==b[:2],
                 "R224_ORIGINAL_JVM_OFFSET_OR_OPCODE_CHANGED_"+old_name)
            if a[2]!=b[2]:
                need(a[2].startswith(SYMBOL_PREFIXES) and
                     b[2].startswith(SYMBOL_PREFIXES),
                     "R224_NON_SYMBOLIC_OR_BRANCH_OPERAND_CHANGED_"+old_name)
                need(a[2] not in aliases or aliases[a[2]]==b[2],
                     "R224_INCONSISTENT_METHOD_MEMBER_RENAME_"+old_name)
                aliases[a[2]]=b[2]
        digest=sha(json.dumps(aliases,sort_keys=True,
                              separators=(",",":")).encode())
        need(digest==pin,"R224_METHOD_ALIAS_FINGERPRINT_CHANGED_"+old_name)
        for key,value in aliases.items():
            need(key not in all_aliases or all_aliases[key]==value,
                 "R224_DIFFERENT_METHODS_MAP_SAME_MEMBER_DIFFERENTLY")
            all_aliases[key]=value
        need(original[-1][1]==rebuilt[-1][1] and
             original[-1][1] in ("return","areturn"),
             "R224_ORIGINAL_METHOD_RETURN_CHANGED")
        method_report.append({
            "original_method":old_name+old_desc,
            "readable_method":new_name+new_desc,
            "instructions":nops,
            "distinct_aliases":len(aliases),
            "all_opcodes_offsets_branches_constants_equal":True,
        })
    global_digest=sha(json.dumps(all_aliases,sort_keys=True,
                                 separators=(",",":")).encode())
    need(len(all_aliases)==expected_alias_count and
         global_digest==global_alias_sha,
         "R224_COMPLETE_50_SYMBOLIC_RENAME_TABLE_CHANGED")
    return {
        "schema_version":1,
        "kind":"v309_gambling_widget_all_six_original_method_code_r224",
        "original_owner":ORIGINAL_OWNER,
        "readable_owner":READABLE_OWNER,
        "original_JVM_methods_verified":len(method_report),
        "original_JVM_instructions_verified":sum(x["instructions"]
                                                  for x in method_report),
        "distinct_symbol_aliases_verified":len(all_aliases),
        "all_original_offsets_branches_opcodes_and_constants_equal":True,
        "compiler_shape_source_edits":2,
        "original_game_code_executed":False,
        "complete_client_source_compiled":False,
        "methods":method_report,
    }


def verify_private_original_gambling_widget(original_jar,source_zip,r221_zip):
    """Replay the R223 18-owner source-only build using genuine, pinned Java."""
    need(file_sha(original_jar)==ORIGINAL_JAR_SHA256 and
         file_sha(source_zip)==SOURCE_ZIP_SHA256 and
         file_sha(r221_zip)==R221_EVIDENCE_ZIP_SHA256,
         "R224_THREE_PINNED_PRIVATE_INPUTS_REQUIRED")
    with ZipFile(original_jar) as jar:
        orig=read_unique(jar,ORIGINAL_OWNER+".class",10000)
    need(sha(orig)==ORIGINAL_CLASS_SHA256,
         "R224_ORIGINAL_GAMBLING_CLASS_SHA256_CHANGED")
    with ZipFile(source_zip) as tree:
        base={}
        for owner,pin in REPLACEMENTS.items():
            content=read_unique(tree,SOURCE_ROOT+"rs/interfaces/widgets/"+
                                owner+".java",200000)
            need(sha(content)==pin,"R224_BASE_REAL_SOURCE_DRIFT_"+owner)
            base[owner]=content.decode("utf-8")
        added={}
        for path,pin in ADDITIONAL_REAL.items():
            content=read_unique(tree,SOURCE_ROOT+path,200000)
            need(sha(content)==pin,"R224_R223_REAL_SOURCE_DRIFT_"+path)
            added[path]=content.decode("utf-8")
    with ZipFile(r221_zip) as evidence:
        template=read_unique(evidence,
            "scripts/source-only-recompile-unified-class.py",30000)
        verified_class=read_unique(evidence,
            "private/compiled-readable-Class179.class",200000)
        spell_source=read_unique(evidence,
            "private/normalized-readable-Class179.java",150000)
    need(sha(verified_class)==R221_CLASS_SHA256,
         "R224_R221_VERIFIED_SPELLBOOK_CLASS_CHANGED")
    sources=integrate_actual_readable_dependencies(
        read_fake_template_ast(template),base)
    sources["rs/interfaces/widgets/Class179.java"]=spell_source.decode("utf-8")
    sources=augment_fake_only_sources(sources,added)
    source_key="rs/interfaces/widgets/Class170.java"
    sources[source_key]=normalize_exact_gambling_source(sources[source_key])
    javac=shutil.which("javac");javap=shutil.which("javap")
    need(bool(javac and javap),"R224_JDK_JAVAC_AND_JAVAP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r224-gambling-") as td:
        root=Path(td);out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        paths=[]
        for relative,java in sources.items():
            path=root/"src"/relative
            need(not path.exists(),"R224_DUPLICATE_JAVA_SOURCE")
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(java,encoding="utf-8")
            paths.append(str(path))
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):env.pop(key,None)
        try:
            build=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*paths],
                capture_output=True,timeout=150,cwd=root,env=env,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R224GamblingWidgetParityError(
                "R224_SOURCE_ONLY_JAVA9_BUILD_ABORTED") from exc
        emitted={str(p.relative_to(out)) for p in out.rglob("*.class")}
        need(build.returncode==0 and len(sources)==18 and
             emitted=={x[:-5]+".class" for x in sources},
             "R224_FULL_R223_SOURCE_CLOSURE_JAVA9_FAILED")
        compiled=(out/(READABLE_OWNER+".class")).read_bytes()
        spell=(out/"rs/interfaces/widgets/Class179.class").read_bytes()
        widget=(out/"rs/interfaces/widgets/Widget.class").read_bytes()
        need(sha(compiled)==NORMALIZED_CLASS_SHA256 and
             spell==verified_class and
             sha(widget)==R222_REAL_WIDGET_CLASS_SHA256,
             "R224_GAMBLING_OR_SPELLBOOK_OR_WIDGET_EMITTED_HASH_CHANGED")
        def inspect(cp,owner):
            try:
                return subprocess.run([
                    javap,"-p","-c","-classpath",str(cp),owner],
                    cwd=root,env=env,capture_output=True,text=True,
                    timeout=60,check=True).stdout
            except (OSError,subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as exc:
                raise R224GamblingWidgetParityError(
                    "R224_JAVAP_CLASSFILE_INSPECTION_ABORTED") from exc
        a=inspect(original_jar,"rs.n.c.V")
        b=inspect(out,"rs.interfaces.widgets.Class170")
    before=profile_class_field_accesses(orig)
    after=profile_class_field_accesses(compiled)
    def find(profile,name,desc):
        ms=[x for x in profile["methods"]
            if (x["name"],x["descriptor"])==(name,desc)]
        need(len(ms)==1,"R224_EXACT_CLASS_METHOD_OWNER_NOT_UNIQUE")
        return ms[0]
    for _,_,old,old_desc,new,new_desc,nops,_ in METHODS:
        x=find(before,old,old_desc)
        y=find(after,new,new_desc)
        need(x["access"]==y["access"] and
             x["code_length"]==y["code_length"] and
             x["max_stack"]==y["max_stack"] and
             x["max_locals"]==y["max_locals"] and
             x["exception_handlers"]==y["exception_handlers"] and
             x["stackmap_table_present"]==y["stackmap_table_present"],
             "R224_ORIGINAL_JVM_METHOD_CODE_METADATA_CHANGED_"+old)
    proof=verify_original_class170_code(a,b)
    need(file_sha(original_jar)==ORIGINAL_JAR_SHA256 and
         file_sha(source_zip)==SOURCE_ZIP_SHA256 and
         file_sha(r221_zip)==R221_EVIDENCE_ZIP_SHA256,
         "R224_PRIVATE_INPUT_CHANGED_DURING_VERIFICATION")
    return {
        **proof,
        "original_class_sha256":ORIGINAL_CLASS_SHA256,
        "unmodified_real_source_sha256":REAL_JAVA_SHA256,
        "normalized_real_source_sha256":NORMALIZED_JAVA_SHA256,
        "source_built_Class170_sha256":NORMALIZED_CLASS_SHA256,
        "source_built_Class179_sha256":R221_CLASS_SHA256,
        "source_only_java_release":9,
        "total_source_owners_compiled":18,
        "temporary_nonoriginal_signature_owners":8,
        "original_spellbook_14_method_Code_preserved":True,
        "original_gambling_six_method_Code_verified":True,
        "source_redistribution_rights_verified":False,
    }

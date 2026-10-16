"""R221: whole v309 spellbook Class179 single-class JVM Code verifier.

Unlike R212-R219 (individual methods), R221 checks ONE emitted
Class179.class containing all 14 methods against SHA-pinned original
rs/n/c/ap.class. Original client code is NEVER executed. Only acceptable
instruction encoding change: ldc -> ldc_w, with exact operand values;
branch targets must resolve to the same instruction INDEX, not the same
byte offset. Every resolved original->readable symbol mapping is
fingerprinted and source-dependent.

The normalized Java source and compiled class are SHA pinned. Compiler-
only helper source is not accepted as original, whole-client compilation
is NOT claimed. The actual source-only javac build and provenance are
separately preserved in a private acceptance report.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

ORIGINAL_JAR_SHA256="ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
ORIGINAL_OWNER_SHA256="b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
NORMALIZED_REAL_SOURCE_SHA256="e274c0f12c36baeaa129920d5e259897a292b65a1138fc386f1413f00ff60406"
ONE_EMITTED_CLASS_SHA256="b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e"

# header original / header readable / original JVM ops /
# ldc widened / sha256 of all accepted per-method renamed symbols
METHODS=(
 ("public static void h();","public static void method1966();",10,0,"c29bc71626d2926ce1c4d0d1e395380bdc395d0234c69bd3f4ed8e65c4f241ef"),
 ("public static void i();","public static void method3153();",62,0,"8d100c46b7854f579e97a703ce717c4a1ee7d0785d2821aa91bea8f369f75901"),
 ("public static void j();","public static void method236();",19,0,"504e88113d9f8744fe6bc8fc82cda5f5120f963cb14beecc35541cc00d2e25db"),
 ("public static void a(rs.n.c.ap$c);","public static void method2689(rs.interfaces.widgets.Class178);",243,0,"a7de3252557f43b328325dc8d2d925e688d648026c401f8d570712dbde8a5b0e"),
 ("public rs.n.c.ap(rs.l.K[]);","public rs.interfaces.widgets.Class179(rs.graphics.HitsplatFont[]);",4,0,"1c5f629d4f842c62434516fb803e0c31f03caef33589461ec47503e0f7075814"),
 ("public void a();","public void register();",438,0,"c5208f52477762f4cf219eece66a757bd60949cc774510d32d28b5fc372a9e57"),
 ("public static void m(int);","public static void method640(int);",76,0,"f3bc09e42a9a9fe8fe8e3ee5e75a2fd615737478a815ac11206131b4efba0def"),
 ("public static void k();","public static void method1241();",43,3,"0bee5d15e2894694300aea80e2cabeced459fe3be264de5dae863cb4d56af387"),
 ("public void l();","public void method1592();",160,35,"4de2968505153daeb46c44753705462915bd8a0b5c99b6115641e67b51eec835"),
 ("public void m();","public void method2352();",1580,24,"458cdae2b202c9ad8c2d1930f4117f6a8d460058c6ecaac749a3b10eaf857422"),
 ("public void n();","public void method3532();",419,26,"2359b62bd9728cf457d16f1f84700caccce10fe6ddcca64177335e016cd5cf6b"),
 ("public void o();","public void method892();",760,90,"ab863c2ec0611355af31266de4918db70952b04dac8d51da0f920b03137acaeb"),
 ("public void p();","public void method1712();",487,0,"1cf53f91a9e8f611f7db442eb177bdfd90c621ff6ab68ab48dcf4d521810d86b"),
 ("static {};","static {};",13,0,"9f83ac257dada6fd2f01e2d04f0ac71adbb4d90b461d7a3764b085990a34b9c7"),
)
BRANCHES=frozenset((
 "ifeq","ifne","iflt","ifge","ifgt","ifle","if_icmpeq","if_icmpne",
 "if_icmplt","if_icmpge","if_icmpgt","if_icmple","if_acmpeq",
 "if_acmpne","ifnull","ifnonnull","goto","goto_w","jsr","jsr_w",
))
SYMBOL_PREFIXES=("Field ","Method ","InterfaceMethod ","class ","InvokeDynamic ")


class R221SingleClassParityError(ValueError):
    pass


def require(ok,message):
    if not ok:
        raise R221SingleClassParityError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_method(text,header):
    tag=header+"\n    Code:\n"
    require(text.count(tag)==1,"R221_METHOD_NOT_UNIQUE_"+header)
    body=text.split(tag,1)[1]
    result=[]
    for line in body.splitlines():
        m=re.match(r"^\s+(\d+):\s+(\w+)(.*)$",line)
        if not m:
            break
        operand=m.group(3).strip()
        if "//" in operand:
            operand=operand.split("//",1)[1].strip()
        result.append((int(m.group(1)),m.group(2),operand))
    require(bool(result) and
            len(set(x[0] for x in result))==len(result),
            "R221_INVALID_DECODED_INSTRUCTION_STREAM")
    return result


def verify_unified_disassembly(old_text,new_text, *,
                               expected=METHODS):
    require(len(expected)==14 and
            sum(x[2] for x in expected)==4314 and
            sum(x[3] for x in expected)==178,
            "R221_PINNED_COMPLETE_CLASS_INVENTORY_CHANGED")
    entries=[]
    for before,after,count,allowed_wide,expected_alias_sha in expected:
        old=parse_method(old_text,before)
        new=parse_method(new_text,after)
        require(len(old)==len(new)==count,
                "R221_METHOD_INSTRUCTION_COUNT_CHANGED")
        oldpos={x[0]:i for i,x in enumerate(old)}
        newpos={x[0]:i for i,x in enumerate(new)}
        aliases={}
        widened=0
        branches=0
        for i,(a,b) in enumerate(zip(old,new)):
            off,opcode,operand=a
            newoff,newopcode,newoperand=b
            if opcode!=newopcode:
                require(opcode=="ldc" and newopcode=="ldc_w",
                        "R221_UNSUPPORTED_JVM_OPCODE_SUBSTITUTION")
                widened+=1
            require(newoff-off==widened-(1 if opcode=="ldc" and
                newopcode=="ldc_w" else 0),
                "R221_UNEXPECTED_JVM_CODE_OFFSET_CHANGE")
            if opcode in BRANCHES:
                require(operand.isdecimal() and newoperand.isdecimal(),
                        "R221_MALFORMED_BRANCH_DESTINATION")
                prior=int(operand)
                next_=int(newoperand)
                require(prior in oldpos and next_ in newpos and
                        oldpos[prior]==newpos[next_],
                        "R221_BRANCH_DESTINATION_INSTRUCTION_CHANGED")
                branches+=1
            elif operand!=newoperand:
                require(operand.startswith(SYMBOL_PREFIXES)
                        and newoperand.startswith(SYMBOL_PREFIXES),
                        "R221_NON_SYMBOLIC_JVM_OPERAND_CHANGED")
                require(operand not in aliases or
                        aliases[operand]==newoperand,
                        "R221_ONE_TO_MANY_OWNER_MEMBER_ALIAS")
                aliases[operand]=newoperand
        require(widened==allowed_wide,
                "R221_LDC_WIDENING_COUNT_CHANGED")
        digest=sha(json.dumps(aliases,sort_keys=True,
                              separators=(",",":")).encode())
        require(digest==expected_alias_sha,
                "R221_EXPLICIT_ORIGINAL_TO_READABLE_ALIAS_SHA_CHANGED")
        require(old[-1][1]=="return" and new[-1][1]=="return",
                "R221_METHOD_RETURN_INSTRUCTION_CHANGED")
        entries.append({
            "original":before,"readable":after,
            "matched_instructions":count,
            "ldc_to_ldc_w":widened,
            "verified_branch_targets":branches,
            "member_aliases":len(aliases),
        })
    return {
        "schema_version":1,
        "kind":"v309_real_one_class_fourteen_original_method_code_r221",
        "verified_original_JVM_methods":len(entries),
        "verified_original_JVM_instructions":sum(
            x["matched_instructions"] for x in entries),
        "allowlisted_ldc_to_ldc_w_encoding_changes":sum(
            x["ldc_to_ldc_w"] for x in entries),
        "single_emitted_readable_class_code_verified":True,
        "all_branch_target_instruction_indices_verified":True,
        "whole_v309_client_compiled":False,
        "original_game_code_executed":False,
        "original_binary_classfile_identity_proven":False,
        "compiler_only_nonoriginal_helpers_used_for_build":True,
        "methods":entries,
    }


def verify_private_unified_class(original_jar,normalized_java,rebuilt_class):
    """No original code is loaded by JVM; javap only inspects class metadata."""
    original_jar=Path(original_jar)
    normalized_java=Path(normalized_java)
    rebuilt_class=Path(rebuilt_class)
    require(original_jar.is_file() and normalized_java.is_file() and
            rebuilt_class.is_file(),
            "R221_ALL_PINNED_PRIVATE_FILES_REQUIRED")
    require(sha(original_jar.read_bytes())==ORIGINAL_JAR_SHA256 and
            sha(normalized_java.read_bytes())==NORMALIZED_REAL_SOURCE_SHA256 and
            sha(rebuilt_class.read_bytes())==ONE_EMITTED_CLASS_SHA256,
            "R221_PINNED_ORIGINAL_AND_UNIFIED_SOURCE_CLASS_SHA_REQUIRED")
    with ZipFile(original_jar) as jar:
        require(jar.namelist().count("rs/n/c/ap.class")==1,
                "R221_ORIGINAL_PARENT_CLASS_ENTRY_NOT_UNIQUE")
        require(sha(jar.read("rs/n/c/ap.class"))==ORIGINAL_OWNER_SHA256,
                "R221_ORIGINAL_CLASSFILE_FINGERPRINT_CHANGED")
    javap=shutil.which("javap")
    require(javap is not None,"R221_JDK_JAVAP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r221-class-") as td:
        out=Path(td)/"classes/rs/interfaces/widgets/Class179.class"
        out.parent.mkdir(parents=True)
        out.write_bytes(rebuilt_class.read_bytes())
        def inspect(cp,owner):
            try:
                p=subprocess.run(
                    [javap,"-p","-c","-classpath",str(cp),owner],
                    capture_output=True,text=True,timeout=90,check=True)
                return p.stdout
            except (subprocess.SubprocessError,OSError) as exc:
                raise R221SingleClassParityError(
                    "R221_UNIFIED_CLASS_JAVAP_FAILED") from exc
        original=inspect(original_jar,"rs.n.c.ap")
        rebuilt=inspect(Path(td)/"classes","rs.interfaces.widgets.Class179")
    return verify_unified_disassembly(original,rebuilt)

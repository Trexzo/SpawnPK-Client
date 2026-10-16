"""R217: real original v309 lunar and ancient spellbook layout source Code.

Proves original rs/n/c/ap.p() and n() against the EXISTING private
rs/interfaces/widgets/Class179.java methods method1712() and method3532().
The lunar source is verbatim; the ancient source has exactly two pinned,
arithmetic-equivalent compiler-shape adjustments before compilation.

Acceptance is ALL 487+419 JVM instructions, exact offsets, branches,
literal operands, nine/three explicit owner ABI renames, method attributes,
SHA-pinned original binary and pre-existing readable Java source.
No client code is executed and helper declarations are compiler-only.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_v309_readable_spellbook_long_filter_r214 import (
    compare_full_original_readable_code,
    R214OriginalReadableFilterError,
)

ORIGINAL_CLASS_SHA256="b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
SOURCE_TREE_SHA256="cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
READABLE_JAVA_SHA256="8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
SOURCE_PATH="recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
METHOD_DETAILS={
    "method1712":{
        "original":"p", "operations":487,"last_offset":1050,
        "source_sha256":"9a430b012fa327bdb563f1bf75e51409105b52ed279b801f2ffbe951d9c04f25",
        "compiled_sha256":"9a430b012fa327bdb563f1bf75e51409105b52ed279b801f2ffbe951d9c04f25",
        "aliases":{
            "Method d:(I)Lrs/n/e;":"Method createPanelWidget:(I)Lrs/interfaces/WidgetComponent;",
            "Method rs/n/e.k:(I)V":"Method rs/interfaces/WidgetComponent.allocateChildren:(I)V",
            "Method b:(IIIILrs/n/e;)V":"Method setChildOf:(IIIILrs/interfaces/WidgetComponent;)V",
        },
    },
    "method3532":{
        "original":"n", "operations":419,"last_offset":778,
        "source_sha256":"5c8eb43b2f81559ee70f0ef7fd16fac55be8cb9ae1e36b921f611670f70f1b54",
        "compiled_sha256":"72651ccaeba1dc34c6c9fc362420e535fc33a8894afbd9ff63c34c85534579ed",
        "aliases":{
            "Method d:(I)Lrs/n/e;":"Method createPanelWidget:(I)Lrs/interfaces/WidgetComponent;",
            "Method b:(IILjava/lang/String;Ljava/lang/String;)Lrs/n/e;":"Method createSpriteTextWidget:(IILjava/lang/String;Ljava/lang/String;)Lrs/interfaces/WidgetComponent;",
            "Field H:[Lrs/n/e;":"Field widgetTable:[Lrs/interfaces/WidgetComponent;",
            "Field rs/n/e.ab:I":"Field rs/interfaces/WidgetComponent.mouseOverLayer:I",
            "Field a:[Lrs/l/K;":"Field fonts:[Lrs/graphics/HitsplatFont;",
            "Method c:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/l/K;III)V":"Method createThreeRequirementMagicSpellAlt:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/graphics/HitsplatFont;III)V",
            "Method rs/n/e.k:(I)V":"Method rs/interfaces/WidgetComponent.allocateChildren:(I)V",
            "Method rs/n/e.b:(IIII)V":"Method rs/interfaces/WidgetComponent.setChild:(IIII)V",
        },
    },
}
NONORIGINAL_COMPILER_DECLARATIONS={
    "rs/interfaces/widgets/Widget.java":(
        "package rs.interfaces.widgets;\n"
        "import rs.interfaces.WidgetComponent;\n"
        "import rs.graphics.HitsplatFont;\n"
        "public class Widget extends WidgetComponent {\n"
        " protected HitsplatFont[] fonts;\n"
        " public static void setChildOf(int a,int b,int c,int d,WidgetComponent w){}\n"
        " public static WidgetComponent createPanelWidget(int i){return null;}\n"
        " public static WidgetComponent createSpriteTextWidget(int a,int b,String c,String d){return null;}\n"
        " public static void createThreeRequirementMagicSpellAlt("
        "int a,int b,int c,int d,int e,int f,int g,int h,int i,int j,"
        "String k,String l,HitsplatFont[] m,int n,int o,int p){}\n"
        "}\n"
    ),
    "rs/interfaces/WidgetComponent.java":(
        "package rs.interfaces;\n"
        "public class WidgetComponent {\n"
        " public static WidgetComponent[] widgetTable;\n"
        " public int mouseOverLayer;\n"
        " public void allocateChildren(int n){}\n"
        " public void setChild(int a,int b,int c,int d){}\n"
        "}\n"
    ),
    "rs/graphics/HitsplatFont.java":"package rs.graphics;public class HitsplatFont {}\n",
}


class R217ReadableLayoutError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R217ReadableLayoutError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def extract_existing_method(source,name):
    need(name in METHOD_DETAILS,"R217_ONLY_TWO_PINNED_REAL_METHODS")
    matches=list(re.finditer(
        r"(?m)^\s*public\s+void\s+"+re.escape(name)+r"\s*\(\s*\)\s*\{",
        source))
    need(len(matches)==1,"R217_EXISTING_METHOD_OWNER_NOT_UNIQUE")
    start=matches[0].start()
    pos=source.index("{",start)+1
    depth=1
    while depth and pos<len(source):
        if source[pos]=="{":depth+=1
        elif source[pos]=="}":depth-=1
        pos+=1
    need(depth==0 and pos-start<11000,"R217_EXISTING_SOURCE_BRACE_DRIFT")
    return source[start:pos]


def normalize_ancient_compiler_shape(original_source, *, pin=True):
    """Exactly two equivalent += rewrites; nothing else may change."""
    if pin:
        need(digest(original_source.encode())==
             METHOD_DETAILS["method3532"]["source_sha256"],
             "R217_REAL_READABLE_ANCIENT_SOURCE_DIGEST_CHANGED")
    substitutions=(
        ("var8 = var6 + 4;","var8 += 4;"),
        ("var9 = var7 + 2;","var9 += 2;"),
    )
    result=original_source
    for before,after in substitutions:
        need(result.count(before)==1 and after not in result,
             "R217_EXACT_ANCIENT_COMPILER_SHAPE_REQUIRED")
        result=result.replace(before,after,1)
    if pin:
        need(digest(result.encode())==
             METHOD_DETAILS["method3532"]["compiled_sha256"],
             "R217_NORMALIZED_ANCIENT_JAVA_DIGEST_CHANGED")
    return result


def audit_layout_methods(original_javap,readable_javap, *,
                         details=METHOD_DETAILS):
    proofs={}
    for readable,expected in sorted(details.items()):
        oldname=expected["original"]
        try:
            result=compare_full_original_readable_code(
                original_javap,readable_javap,
                original_title="public void "+oldname+"();",
                readable_title="public void "+readable+"();",
                aliases=expected["aliases"],
                expected_instructions=expected["operations"],
                expected_last_offset=expected["last_offset"])
        except R214OriginalReadableFilterError as exc:
            raise R217ReadableLayoutError(
                "R217_SOURCE_ORIGINAL_JVM_CODE_PARITY_FAILED_"+readable) from exc
        proofs[oldname+"()"]={
            "readable_name":readable,
            "matched_original_jvm_instructions":
                result["original_decoded_jvm_instructions"],
            "last_offset":expected["last_offset"],
            "aliases_exercised":
                result["actual_distinct_renamed_member_or_type_symbols"],
            "all_original_offsets_branches_and_operands_match":True,
        }
    need(sum(x["matched_original_jvm_instructions"] for x in
             proofs.values())==906,"R217_ORIGINAL_JVM_TOTAL_906_DRIFT")
    return proofs


def verify_pinned_real_readable_layouts(original_jar,private_source_zip, *,
                                        jar_sha256=CANONICAL_V309,
                                        class_sha256=ORIGINAL_CLASS_SHA256,
                                        source_zip_sha256=SOURCE_TREE_SHA256,
                                        readable_sha256=READABLE_JAVA_SHA256):
    need(file_digest(original_jar)==jar_sha256 and
         file_digest(private_source_zip)==source_zip_sha256,
         "R217_EXACT_V309_PRIVATE_BINARY_AND_READABLE_TREE_REQUIRED")
    with ZipFile(original_jar) as jar:
        need(jar.namelist().count("rs/n/c/ap.class")==1,
             "R217_ORIGINAL_CLASS_NOT_UNIQUE")
        original=jar.read("rs/n/c/ap.class")
    need(digest(original)==class_sha256,
         "R217_ORIGINAL_BINARY_CLASS_SHA_DRIFT")
    with ZipFile(private_source_zip) as z:
        need(z.namelist().count(SOURCE_PATH)==1,
             "R217_READABLE_JAVA_SOURCE_NOT_UNIQUE")
        readable=z.read(SOURCE_PATH)
    need(digest(readable)==readable_sha256,
         "R217_PRIVATE_READABLE_DONOR_JAVA_SHA_DRIFT")
    java=readable.decode("utf-8")
    lunar=extract_existing_method(java,"method1712")
    ancient=extract_existing_method(java,"method3532")
    need(digest(lunar.encode())==METHOD_DETAILS["method1712"]["source_sha256"],
         "R217_VERBATIM_LUNAR_JAVA_SHA_DRIFT")
    ancient_fixed=normalize_ancient_compiler_shape(ancient)
    partial=(
        "package rs.interfaces.widgets;\n"
        "import rs.interfaces.WidgetComponent;\n"
        "import rs.graphics.HitsplatFont;\n"
        "public class Class179 extends Widget {\n"
        +lunar+"\n"+ancient_fixed+"\n}\n"
    )
    javac=shutil.which("javac")
    javap=shutil.which("javap")
    need(javac and javap,"R217_JDK9_JAVAC_JAVAP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r217-") as td:
        root=Path(td)
        files={"rs/interfaces/widgets/Class179.java":partial,
               **NONORIGINAL_COMPILER_DECLARATIONS}
        paths=[]
        for name,source in files.items():
            dest=root/"sources"/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(source,encoding="utf-8")
            paths.append(str(dest))
        output=root/"classes"
        empty=root/"empty"
        output.mkdir();empty.mkdir()
        env={k:v for k,v in os.environ.items() if k not in
             ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS")}
        try:
            compiled=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(output),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=100,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R217ReadableLayoutError("R217_SOURCE_ONLY_COMPILE_ABORT") from exc
        emitted={p.relative_to(output).as_posix()
                 for p in output.rglob("*.class")}
        need(compiled.returncode==0 and
             emitted=={name[:-5]+".class" for name in files},
             "R217_EXPECTED_COMPILED_OWNERS_OR_JAVAC_FAILED")
        rebuilt=(output/"rs/interfaces/widgets/Class179.class").read_bytes()
        def javap_text(cp,owner):
            try:
                return subprocess.run([javap,"-p","-c",
                    "-classpath",str(cp),owner],
                    cwd=root,env=env,capture_output=True,text=True,
                    timeout=45,check=True).stdout
            except (OSError,subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as exc:
                raise R217ReadableLayoutError("R217_JAVAP_FAILED") from exc
        before=javap_text(original_jar,"rs.n.c.ap")
        after=javap_text(output,"rs.interfaces.widgets.Class179")
    old_profile=profile_class_field_accesses(original)
    new_profile=profile_class_field_accesses(rebuilt)
    for readable,expected in METHOD_DETAILS.items():
        def select(profile,name):
            found=[m for m in profile["methods"]
                if (m["name"],m["descriptor"])==(name,"()V")]
            need(len(found)==1,"R217_SELECTED_JVM_METHOD_NOT_UNIQUE")
            return found[0]
        old=select(old_profile,expected["original"])
        new=select(new_profile,readable)
        need(old["access"]==new["access"] and
             old["code_length"]==new["code_length"]==
             expected["last_offset"]+1 and
             old["max_stack"]==new["max_stack"] and
             old["max_locals"]==new["max_locals"] and
             old["exception_handlers"]==new["exception_handlers"] and
             old["stackmap_table_present"]==new["stackmap_table_present"],
             "R217_JVM_CODE_LIMITS_OR_ATTRIBUTES_DIFFER")
    matched=audit_layout_methods(before,after)
    need(file_digest(original_jar)==jar_sha256 and
         file_digest(private_source_zip)==source_zip_sha256,
         "R217_PRIVATE_INPUT_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_original_lunar_and_ancient_from_existing_readable_java_r217",
        "selected_original_methods":2,
        "original_jvm_instructions_matched":906,
        "methods":matched,
        "lunar_original_readable_java_unchanged":True,
        "ancient_readable_java_normalizations":[
            "var8 = var6 + 4 => var8 += 4",
            "var9 = var7 + 2 => var9 += 2",
        ],
        "temporary_nonoriginal_signature_helpers":len(
            NONORIGINAL_COMPILER_DECLARATIONS),
        "private_source_classfiles_executed":False,
        "whole_original_spellbook_parent_compiled":False,
        "full_original_client_compiled":False,
        "original_binary_byte_identity_proven":False,
        "redistribution_authorized":False,
    }

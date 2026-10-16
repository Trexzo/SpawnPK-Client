"""R218 — verify the original v309 760-op lunar-spell definitions Code.

Uses the real preexisting readable Class179.method892() Java **unchanged**.
Compiles it from source with only TWO explicit compiler-only helper
declarations and an unverified no-op signature for method1712; no original
client classfiles on source/compiler classpath and no game method execution.

Each of 760 JVM instructions, 1644 Code bytes, offsets, branch constants
and EIGHT explicit original-to-readable member/type names must match the
SHA-pinned original rs/n/c/ap.o(). Not a whole-parent source build.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import os
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
UNMODIFIED_METHOD_SHA256="aecd4c7af25cff1dd4b2f04a7dbdd39f89b7fe215b2d941588f80fe82d512c6d"
ORIGINAL_METHOD_TITLE="public void o();"
READABLE_METHOD_TITLE="public void method892();"
ORIGINAL_INSTRUCTIONS=760
LAST_OFFSET=1643
ALIASES={
    "Method p:()V":"Method method1712:()V",
    "Method d:()V":"Method createLunarHomeTeleportButton:()V",
    "Method b:(IILjava/lang/String;)V":"Method createLunarRuneOverlay:(IILjava/lang/String;)V",
    "Field a:[Lrs/l/K;":"Field fonts:[Lrs/graphics/HitsplatFont;",
    "Method b:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/l/K;III)V":"Method createThreeRequirementLunarSpell:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/graphics/HitsplatFont;III)V",
    "Method b:(IIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/l/K;III)V":"Method createTwoRequirementLunarSpell:(IIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/graphics/HitsplatFont;III)V",
    "Method d:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/l/K;III)V":"Method createThreeRequirementLunarSpellAlt:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/graphics/HitsplatFont;III)V",
    "Method e:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/l/K;III)V":"Method createThreeRequirementLunarSpellOffset:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/graphics/HitsplatFont;III)V",
}
# Original/evidence boundary: source-only signatures, never recovered
# implementations. method1712() is deliberately a no-op declaration for
# this isolated o() proof and must not be counted as verified here.
COMPILER_ONLY_HELPERS={
    "rs/interfaces/widgets/Widget.java":(
        "package rs.interfaces.widgets;\n"
        "import rs.graphics.HitsplatFont;\n"
        "public class Widget {\n"
        " protected HitsplatFont[] fonts;\n"
        " public static void createLunarHomeTeleportButton(){}\n"
        " public static void createLunarRuneOverlay(int a,int b,String c){}\n"
        " public static void createThreeRequirementLunarSpell("
        "int a,int b,int c,int d,int e,int f,int g,int h,int i,int j,"
        "String k,String l,HitsplatFont[] m,int n,int o,int p){}\n"
        " public static void createThreeRequirementLunarSpellAlt("
        "int a,int b,int c,int d,int e,int f,int g,int h,int i,int j,"
        "String k,String l,HitsplatFont[] m,int n,int o,int p){}\n"
        " public static void createThreeRequirementLunarSpellOffset("
        "int a,int b,int c,int d,int e,int f,int g,int h,int i,int j,"
        "String k,String l,HitsplatFont[] m,int n,int o,int p){}\n"
        " public static void createTwoRequirementLunarSpell("
        "int a,int b,int c,int d,int e,int f,int g,String h,String i,"
        "HitsplatFont[] j,int k,int l,int m){}\n"
        "}\n"
    ),
    "rs/graphics/HitsplatFont.java":"package rs.graphics;public class HitsplatFont {}\n",
}


class R218ReadableLunarSpellError(ValueError):
    pass


def need(ok,message):
    if not ok:
        raise R218ReadableLunarSpellError(message)


def file_sha(path):
    hasher=sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            hasher.update(block)
    return hasher.hexdigest()


def extract_real_lunar_spells_method(source,name="method892"):
    matches=list(re.finditer(
        r"(?m)^\s*public\s+void\s+"+re.escape(name)+r"\s*\(\s*\)\s*\{",
        source))
    need(len(matches)==1,"R218_EXISTING_READABLE_METHOD_NOT_UNIQUE")
    start=matches[0].start()
    pos=source.index("{",start)+1
    depth=1
    while depth and pos<len(source):
        if source[pos]=="{":depth+=1
        elif source[pos]=="}":depth-=1
        pos+=1
    need(depth==0 and pos-start<12000,
         "R218_REAL_METHOD_UNBALANCED_OR_OVERSIZED")
    return source[start:pos]


def audit_original_lunar_spells(original_javap,rebuilt_javap, *,
                               original_title=ORIGINAL_METHOD_TITLE,
                               readable_title=READABLE_METHOD_TITLE,
                               aliases=ALIASES,
                               expected_instructions=ORIGINAL_INSTRUCTIONS,
                               expected_last_offset=LAST_OFFSET):
    try:
        result=compare_full_original_readable_code(
            original_javap,rebuilt_javap,
            original_title=original_title,
            readable_title=readable_title,
            aliases=aliases,
            expected_instructions=expected_instructions,
            expected_last_offset=expected_last_offset)
    except R214OriginalReadableFilterError as exc:
        raise R218ReadableLunarSpellError(
            "R218_ORIGINAL_LUNAR_SPELL_JVM_CODE_MISMATCH") from exc
    return {
        "selected_original_method":"rs/n/c/ap.o()V",
        "actual_readable_java_method":"Class179.method892()V",
        "matched_original_jvm_instructions":result[
            "original_decoded_jvm_instructions"],
        "exact_offsets_opcodes_operands_and_branch_targets":True,
        "distinct_original_to_readable_aliases_exercised":result[
            "actual_distinct_renamed_member_or_type_symbols"],
        "existing_readable_method_source_edited":False,
        "unselected_original_parent_methods_verified":False,
        "original_game_code_executed":False,
    }


def verify_pinned_real_readable_lunar_spells(original_jar,source_zip, *,
                                            jar_sha256=CANONICAL_V309,
                                            original_class_sha256=ORIGINAL_CLASS_SHA256,
                                            source_zip_sha256=SOURCE_TREE_SHA256,
                                            donor_sha256=READABLE_JAVA_SHA256):
    need(file_sha(original_jar)==jar_sha256 and
         file_sha(source_zip)==source_zip_sha256,
         "R218_ORIGINAL_BIN_AND_READABLE_TREE_SHA_REQUIRED")
    with ZipFile(original_jar) as jar:
        need(jar.namelist().count("rs/n/c/ap.class")==1,
             "R218_PINNED_JVM_OWNER_NOT_UNIQUE")
        old=jar.read("rs/n/c/ap.class")
    need(sha256(old).hexdigest()==original_class_sha256,
         "R218_ORIGINAL_JVM_CLASS_SHA_CHANGED")
    with ZipFile(source_zip) as archive:
        need(archive.namelist().count(SOURCE_PATH)==1,
             "R218_READABLE_JAVA_OWNER_NOT_UNIQUE")
        real=archive.read(SOURCE_PATH)
    need(sha256(real).hexdigest()==donor_sha256,
         "R218_DECOMPILED_JAVA_SOURCE_SHA_CHANGED")
    method=extract_real_lunar_spells_method(real.decode("utf-8"))
    need(sha256(method.encode()).hexdigest()==UNMODIFIED_METHOD_SHA256,
         "R218_ORIGINAL_EXISTING_LUNAR_METHOD_SOURCE_CHANGED")
    partial=(
        "package rs.interfaces.widgets;\n"
        "import rs.graphics.HitsplatFont;\n"
        "public class Class179 extends Widget {\n"
        +method+"\n"
        " public void method1712(){}\n"
        "}\n"
    )
    javac=shutil.which("javac")
    javap=shutil.which("javap")
    need(javac is not None and javap is not None,
         "R218_JAVA9_JAVAC_JAVAP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r218-") as td:
        root=Path(td)
        files={"rs/interfaces/widgets/Class179.java":partial,
               **COMPILER_ONLY_HELPERS}
        paths=[]
        for path,body in files.items():
            dest=root/"source"/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(body)
            paths.append(str(dest))
        out=root/"classes"
        empty=root/"empty"
        out.mkdir();empty.mkdir()
        env={k:v for k,v in os.environ.items() if k not in
             ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS")}
        try:
            compiled=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=100,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R218ReadableLunarSpellError(
                "R218_SOURCE_ONLY_JAVA_COMPILER_ABORT") from exc
        classes={x.relative_to(out).as_posix()
                 for x in out.rglob("*.class")}
        need(compiled.returncode==0 and
             classes=={x[:-5]+".class" for x in files},
             "R218_UNEXPECTED_COMPILER_OUTPUT_OR_JAVAC_FAILURE")
        built=(out/"rs/interfaces/widgets/Class179.class").read_bytes()
        def disasm(cp,cls):
            try:
                return subprocess.run(
                    [javap,"-p","-c","-classpath",str(cp),cls],
                    cwd=root,env=env,capture_output=True,text=True,
                    timeout=45,check=True).stdout
            except (OSError,subprocess.TimeoutExpired,
                    subprocess.CalledProcessError) as exc:
                raise R218ReadableLunarSpellError(
                    "R218_JAVAP_DISASSEMBLY_ABORTED") from exc
        a=disasm(original_jar,"rs.n.c.ap")
        b=disasm(out,"rs.interfaces.widgets.Class179")
    old_profile=profile_class_field_accesses(old)
    new_profile=profile_class_field_accesses(built)
    def unique(profile,name):
        result=[x for x in profile["methods"]
                if (x["name"],x["descriptor"])==(name,"()V")]
        need(len(result)==1,"R218_ORIGINAL_OR_READABLE_JVM_METHOD_ABSENT")
        return result[0]
    before=unique(old_profile,"o")
    after=unique(new_profile,"method892")
    need(before["access"]==after["access"] and
         before["code_length"]==after["code_length"]==LAST_OFFSET+1 and
         before["max_stack"]==after["max_stack"] and
         before["max_locals"]==after["max_locals"] and
         before["exception_handlers"]==after["exception_handlers"] and
         before["stackmap_table_present"]==after["stackmap_table_present"],
         "R218_JVM_CODE_ATTRIBUTE_LIMITS_CHANGED")
    parity=audit_original_lunar_spells(a,b)
    need(file_sha(original_jar)==jar_sha256 and
         file_sha(source_zip)==source_zip_sha256,
         "R218_PRIVATE_INPUT_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_original_readable_lunar_spells_source_R218",
        **parity,
        "original_class_sha256":original_class_sha256,
        "exact_readable_method_source_sha256":UNMODIFIED_METHOD_SHA256,
        "original_code_length_bytes":LAST_OFFSET+1,
        "nonoriginal_source_only_helpers":len(COMPILER_ONLY_HELPERS),
        "fake_method1712_implementation_accepted":False,
        "original_full_class_abi_recovered":False,
        "entire_v309_client_compiles":False,
        "original_binary_class_identity_proven":False,
        "redistribution_authorized":False,
    }

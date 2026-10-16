"""R216: real decompiled Class179.method1592 -> original rs/n/c/ap.l().

The existing readable Java method is copied VERBATIM from the exact
SHA-pinned private recovered-source tree. Source-only Java9 rebuild must
match all 160 original JVM operations, offsets and 9 explicit resolved
symbol aliases. Temporary dependency signatures are NOT original source.
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
TREE_SHA256="cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
DONOR_SHA256="8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
METHOD_SHA256="a15930f11270b2817890d51e00672a3a54d4e42697cb89cdd168bc767cf68114"
DONOR_ENTRY="recovered-source/v309/src/rs/interfaces/widgets/Class179.java"

ALIASES={
    "Method d:(I)Lrs/n/e;":"Method createPanelWidget:(I)Lrs/interfaces/WidgetComponent;",
    "Method rs/n/e.k:(I)V":"Method rs/interfaces/WidgetComponent.allocateChildren:(I)V",
    "Method a:(ILjava/lang/String;Ljava/lang/String;)V":"Method createDirectSpriteTextButton:(ILjava/lang/String;Ljava/lang/String;)V",
    "Field a:[Lrs/l/K;":"Field fonts:[Lrs/graphics/HitsplatFont;",
    "Method a:(ILjava/lang/String;[Lrs/l/K;II)V":"Method createOverlayTextOptionWidget:(ILjava/lang/String;[Lrs/graphics/HitsplatFont;II)V",
    "Method h:(ILjava/lang/String;)V":"Method createFullScreenDirectSprite:(ILjava/lang/String;)V",
    "Method c:(IILjava/lang/String;)V":"Method createFullScreenSprite:(IILjava/lang/String;)V",
    "Method a:(ILjava/lang/String;Ljava/lang/String;[Lrs/l/K;IIZZI)V":"Method createOptionText:(ILjava/lang/String;Ljava/lang/String;[Lrs/graphics/HitsplatFont;IIZZI)V",
    "Method rs/n/e.b:(IIII)V":"Method rs/interfaces/WidgetComponent.setChild:(IIII)V",
}
# All seven builder calls not returning a usable object MUST have void
# return types. Giving them invented object return types creates spurious
# POP operations (160 original instructions vs 172 invented ones).
NONORIGINAL_HELPERS={
    "rs/graphics/HitsplatFont.java":"package rs.graphics;public class HitsplatFont{}",
    "rs/interfaces/WidgetComponent.java":(
        "package rs.interfaces;import rs.graphics.HitsplatFont;"
        "public class WidgetComponent{"
        "public void allocateChildren(int a){}"
        "public void setChild(int a,int b,int c,int d){}"
        "public static WidgetComponent createPanelWidget(int a){return null;}"
        "public static void createDirectSpriteTextButton(int a,String b,String c){}"
        "public static void createOverlayTextOptionWidget(int a,String b,HitsplatFont[] c,int d,int e){}"
        "public static void createFullScreenDirectSprite(int a,String b){}"
        "public static void createFullScreenSprite(int a,int b,String c){}"
        "public static void createOptionText(int a,String b,String c,HitsplatFont[] d,int e,int f,boolean g,boolean h,int i){}"
        "}"
    ),
    "rs/interfaces/widgets/Widget.java":(
        "package rs.interfaces.widgets;"
        "import rs.graphics.HitsplatFont;"
        "import rs.interfaces.WidgetComponent;"
        "public class Widget extends WidgetComponent{"
        "protected HitsplatFont[] fonts;public Widget(){}"
        "}"
    ),
}


class R216ReadablePanelError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R216ReadablePanelError(reason)


def file_digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def extract_panel_method(source,name="method1592"):
    matches=list(re.finditer(
        r"(?m)^\s*public\s+void\s+"+re.escape(name)+r"\s*\(\s*\)\s*\{",
        source))
    need(len(matches)==1,"R216_EXACT_READABLE_METHOD_REQUIRED")
    start=matches[0].start()
    i=source.index("{",start)+1
    depth=1
    while depth and i<len(source):
        if source[i]=="{":depth+=1
        elif source[i]=="}":depth-=1
        i+=1
    need(depth==0 and i-start<8000,"R216_INVALID_SOURCE_BODY")
    return source[start:i]


def audit_panel_code(original_disassembly,readable_disassembly, *,
                     original_title="public void l();",
                     readable_title="public void method1592();",
                     aliases=ALIASES,expected_instructions=160,
                     expected_last_offset=314):
    try:
        result=compare_full_original_readable_code(
            original_disassembly,readable_disassembly,
            original_title=original_title,readable_title=readable_title,
            aliases=aliases,expected_instructions=expected_instructions,
            expected_last_offset=expected_last_offset)
    except R214OriginalReadableFilterError as exc:
        raise R216ReadablePanelError("R216_ORIGINAL_CODE_NOT_EQUAL") from exc
    return {
        "original_readable_methods_compared":1,
        "original_jvm_instructions_matched":result["original_decoded_jvm_instructions"],
        "matched_old_new_symbols":result["actual_distinct_renamed_member_or_type_symbols"],
        "all_original_code_offsets_branches_equal":True,
        "donor_java_method_modified":False,
        "game_executed":False,
    }


def verify_private_original_panel(original_jar,source_tree, *,
                                  jar_sha256=CANONICAL_V309,
                                  source_sha256=TREE_SHA256,
                                  donor_sha256=DONOR_SHA256,
                                  original_class_sha256=ORIGINAL_CLASS_SHA256):
    need(file_digest(original_jar)==jar_sha256 and
         file_digest(source_tree)==source_sha256,
         "R216_EXACT_PRIVATE_ORIGINAL_AND_SOURCE_SHA_REQUIRED")
    with ZipFile(original_jar) as z:
        need(z.namelist().count("rs/n/c/ap.class")==1,
             "R216_ORIGINAL_CLASS_DUPLICATE")
        original=z.read("rs/n/c/ap.class")
    need(sha256(original).hexdigest()==original_class_sha256,
         "R216_ORIGINAL_CLASS_SHA_CHANGED")
    with ZipFile(source_tree) as z:
        need(z.namelist().count(DONOR_ENTRY)==1,
             "R216_READABLE_JAVA_NOT_UNIQUE")
        source=z.read(DONOR_ENTRY)
    need(sha256(source).hexdigest()==donor_sha256,
         "R216_DONOR_JAVA_SHA_CHANGED")
    method=extract_panel_method(source.decode("utf-8"))
    need(sha256(method.encode()).hexdigest()==METHOD_SHA256,
         "R216_EXISTING_VERBATIM_METHOD_SOURCE_CHANGED")
    partial=(
        "package rs.interfaces.widgets;\n"
        "import rs.graphics.HitsplatFont;\n"
        "import rs.interfaces.WidgetComponent;\n"
        "public class Class179 extends Widget {\n"+method+"\n}\n"
    )
    javac=shutil.which("javac")
    javap=shutil.which("javap")
    need(javac and javap,"R216_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r216-") as td:
        root=Path(td)
        files={"rs/interfaces/widgets/Class179.java":partial,**NONORIGINAL_HELPERS}
        args=[]
        for name,body in files.items():
            dest=root/"src"/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(body)
            args.append(str(dest))
        out=root/"out";empty=root/"empty"
        out.mkdir();empty.mkdir()
        env={k:v for k,v in os.environ.items() if k not in
             ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS")}
        try:
            done=subprocess.run(
                [javac,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*args],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=75,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R216ReadablePanelError("R216_JAVA_COMPILER_ABORTED") from exc
        output={p.relative_to(out).as_posix() for p in out.rglob("*.class")}
        need(done.returncode==0 and
             output=={x[:-5]+".class" for x in files},
             "R216_SOURCE_BUILD_OR_CLASS_SET_FAILED")
        rebuilt=(out/"rs/interfaces/widgets/Class179.class").read_bytes()
        def disasm(cp,cls):
            try:
                return subprocess.run([javap,"-p","-c",
                    "-classpath",str(cp),cls],
                    cwd=root,env=env,capture_output=True,text=True,
                    timeout=40,check=True).stdout
            except (OSError,subprocess.TimeoutExpired,
                    subprocess.CalledProcessError) as exc:
                raise R216ReadablePanelError("R216_JAVAP_FAILED") from exc
        original_javap=disasm(original_jar,"rs.n.c.ap")
        readable_javap=disasm(out,"rs.interfaces.widgets.Class179")
    old=profile_class_field_accesses(original)
    new=profile_class_field_accesses(rebuilt)
    def find(profile,name):
        entries=[x for x in profile["methods"]
                 if (x["name"],x["descriptor"])==(name,"()V")]
        need(len(entries)==1,"R216_JVM_METHOD_NOT_UNIQUE")
        return entries[0]
    a=find(old,"l");b=find(new,"method1592")
    need(a["access"]==b["access"] and
         a["code_length"]==b["code_length"]==315 and
         a["max_stack"]==b["max_stack"] and
         a["max_locals"]==b["max_locals"] and
         a["exception_handlers"]==b["exception_handlers"] and
         a["stackmap_table_present"]==b["stackmap_table_present"],
         "R216_JVM_CODE_LENGTH_OR_LIMIT_CHANGED")
    report=audit_panel_code(original_javap,readable_javap)
    need(file_digest(original_jar)==jar_sha256 and
         file_digest(source_tree)==source_sha256,
         "R216_PRIVATE_EVIDENCE_CHANGED_DURING_PROOF")
    return {
        "schema_version":1,
        "kind":"v309_spellbook_readable_panel_original_source_R216",
        **report,
        "unchanged_source_method_sha256":METHOD_SHA256,
        "real_decompiled_source_compiled":True,
        "compiler_only_helper_classes":len(NONORIGINAL_HELPERS),
        "original_binary_classfile_identity":False,
        "full_original_spellbook_parent_verified":False,
        "whole_v309_client_compiles":False,
        "redistribution_authorized":False,
    }

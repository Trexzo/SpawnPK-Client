"""R219: final two original v309 spellbook Code methods from REAL readable Java.

Original rs/n/c/ap.a() and m() are independently rebuilt from verbatim
existing Class179.register() and method2352(). Verifier requires all
438+1580 original JVM operations and exact byte offsets/branches/operands,
using 21+23 explicit original-to-readable symbolic ABI aliases.

No game code executes. The partial classes compile against source-only
temporary NONORIGINAL declarations that cannot be counted as recovered
original source; this does NOT prove a single compiled 14-method class,
original classfile byte identity, or the whole client build.
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
TREE_SHA256="cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
DONOR_SHA256="8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
DONOR_PATH="recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
METHODS={
    "register":{
        "original":"a",
        "ops":438,"last":1030,
        "source_sha":"d9ae9d22316b6780946ae471b051a2cbe8634194353cb3881681acdb11e80279",
        "aliases":{
            "Field f:Ljava/util/List;":"Field field3648:Ljava/util/List;",
            "Field rs/n/c/ap$a.a:Lrs/n/c/ap$a;":"Field rs/interfaces/widgets/Class176.field3590:Lrs/interfaces/widgets/Class176;",
            "Field rs/n/c/ap$a.b:Lrs/n/c/ap$a;":"Field rs/interfaces/widgets/Class176.field3591:Lrs/interfaces/widgets/Class176;",
            "Method l:()V":"Method method1592:()V",
            "Method m:()V":"Method method2352:()V",
            "Method n:()V":"Method method3532:()V",
            "Method o:()V":"Method method892:()V",
            "Method j:()V":"Method method236:()V",
            "class rs/l/F":"class rs/graphics/Sprite",
            'Method rs/l/F."<init>":(Ljava/lang/String;)V':'Method rs/graphics/Sprite."<init>":(Ljava/lang/String;)V',
            "Field bJ:Lrs/l/F;":"Field field3649:Lrs/graphics/Sprite;",
            "Field bK:Lrs/l/F;":"Field field3650:Lrs/graphics/Sprite;",
            "Field bL:Lrs/l/F;":"Field field3651:Lrs/graphics/Sprite;",
            "Field bO:Lrs/l/F;":"Field field3654:Lrs/graphics/Sprite;",
            "Field bP:Lrs/l/F;":"Field field3655:Lrs/graphics/Sprite;",
            "Field bM:Lrs/l/F;":"Field field3652:Lrs/graphics/Sprite;",
            "Field bN:Lrs/l/F;":"Field field3653:Lrs/graphics/Sprite;",
            "Field rs/n/e.H:[Lrs/n/e;":"Field rs/interfaces/WidgetComponent.widgetTable:[Lrs/interfaces/WidgetComponent;",
            "Field rs/n/e.aG:Lrs/l/F;":"Field rs/interfaces/WidgetComponent.hoverSprite:Lrs/graphics/Sprite;",
            "Field rs/n/e.E:Lrs/l/F;":"Field rs/interfaces/WidgetComponent.sprite:Lrs/graphics/Sprite;",
            "Field rs/n/e.at:Ljava/lang/String;":"Field rs/interfaces/WidgetComponent.field3951:Ljava/lang/String;",
        },
    },
    "method2352":{
        "original":"m",
        "ops":1580,"last":2726,
        "source_sha":"3b51bad51c32fa622aab39fbc694e3804080b03ec634207c7702e85b7f6dce31",
        "aliases":{
            "Method j:(I)Lrs/n/e;":"Method createContainerWidget:(I)Lrs/interfaces/WidgetComponent;",
            "Field H:[Lrs/n/e;":"Field widgetTable:[Lrs/interfaces/WidgetComponent;",
            "Field rs/n/e.aH:I":"Field rs/interfaces/WidgetComponent.scrollHeight:I",
            "Field rs/n/e.aR:I":"Field rs/interfaces/WidgetComponent.height:I",
            "Field rs/n/e.P:I":"Field rs/interfaces/WidgetComponent.width:I",
            "Field rs/n/e.al:[I":"Field rs/interfaces/WidgetComponent.children:[I",
            "Field rs/n/e.am:[I":"Field rs/interfaces/WidgetComponent.childX:[I",
            "Field rs/n/e.bc:[I":"Field rs/interfaces/WidgetComponent.childY:[I",
            "Method rs/n/e.k:(I)V":"Method rs/interfaces/WidgetComponent.allocateChildren:(I)V",
            "Method rs/n/e.b:(IIII)V":"Method rs/interfaces/WidgetComponent.setChild:(IIII)V",
            "Method b:(IILjava/lang/String;Ljava/lang/String;)Lrs/n/e;":"Method createSpriteTextWidget:(IILjava/lang/String;Ljava/lang/String;)Lrs/interfaces/WidgetComponent;",
            "Field a:[Lrs/l/K;":"Field fonts:[Lrs/graphics/HitsplatFont;",
            "Method a:(IIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/l/K;III)V":"Method createTwoRequirementMagicSpell:(IIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/graphics/HitsplatFont;III)V",
            "Field rs/n/e.H:[Lrs/n/e;":"Field rs/interfaces/WidgetComponent.widgetTable:[Lrs/interfaces/WidgetComponent;",
            "Field rs/n/e.X:[[I":"Field rs/interfaces/WidgetComponent.scripts:[[I",
            "Method a:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/l/K;III)V":"Method createThreeRequirementMagicSpell:(IIIIIIIIIILjava/lang/String;Ljava/lang/String;[Lrs/graphics/HitsplatFont;III)V",
            "Field rs/n/e.ab:I":"Field rs/interfaces/WidgetComponent.mouseOverLayer:I",
            "Method a:(ILjava/lang/String;Ljava/lang/String;)V":"Method createDirectSpriteTextButton:(ILjava/lang/String;Ljava/lang/String;)V",
            "Method a:(ILjava/lang/String;[Lrs/l/K;II)V":"Method createOverlayTextOptionWidget:(ILjava/lang/String;[Lrs/graphics/HitsplatFont;II)V",
            "Field rs/n/e.aQ:Z":"Field rs/interfaces/WidgetComponent.hidden:Z",
            "Method a:(ILjava/lang/String;[Lrs/l/K;IIZZ)V":"Method createText:(ILjava/lang/String;[Lrs/graphics/HitsplatFont;IIZZ)V",
            "Field g:[I":"Field field3643:[I",
            "Field bI:[I":"Field field3644:[I",
        },
    },
}
REGISTER_FAKE_DEPENDENCIES={
    "rs/interfaces/widgets/Widget.java":
        "package rs.interfaces.widgets;public class Widget {}",
    "rs/interfaces/widgets/Class176.java":
        "package rs.interfaces.widgets;public enum Class176 {COMBAT,TELEPORT;"
        "public static final Class176 field3590=COMBAT,field3591=TELEPORT;}",
    "rs/graphics/Sprite.java":
        "package rs.graphics;public class Sprite {public Sprite(String p){} }",
    "rs/interfaces/WidgetComponent.java":
        "package rs.interfaces;import rs.graphics.Sprite;"
        "public class WidgetComponent{"
        "public static WidgetComponent[] widgetTable;"
        "public Sprite sprite,hoverSprite;public String field3951;}",
}
CLASSIC_FAKE_DEPENDENCIES={
    "rs/graphics/HitsplatFont.java":
        "package rs.graphics;public class HitsplatFont {}",
    "rs/interfaces/WidgetComponent.java":
        "package rs.interfaces;public class WidgetComponent{"
        "public static WidgetComponent[] widgetTable;"
        "public int scrollHeight,height,width,mouseOverLayer;"
        "public boolean hidden;"
        "public int[] children,childX,childY;"
        "public int[][] scripts;"
        "public void allocateChildren(int n){}"
        "public void setChild(int a,int b,int c,int d){} }",
    "rs/interfaces/widgets/Widget.java":
        "package rs.interfaces.widgets;"
        "import rs.graphics.HitsplatFont;"
        "import rs.interfaces.WidgetComponent;"
        "public class Widget extends WidgetComponent{"
        "protected HitsplatFont[] fonts;"
        "public static WidgetComponent createContainerWidget(int i){return null;}"
        "public static WidgetComponent createSpriteTextWidget(int a,int b,String c,String d){return null;}"
        "public static void createTwoRequirementMagicSpell("
        "int a,int b,int c,int d,int e,int f,int g,String h,String i,"
        "HitsplatFont[] j,int k,int l,int m){}"
        "public static void createThreeRequirementMagicSpell("
        "int a,int b,int c,int d,int e,int f,int g,int h,int i,int j,"
        "String k,String l,HitsplatFont[] m,int n,int o,int p){}"
        "public static void createDirectSpriteTextButton(int a,String b,String c){}"
        "public static void createOverlayTextOptionWidget("
        "int a,String b,HitsplatFont[] c,int d,int e){}"
        "public static void createText(int a,String b,HitsplatFont[] c,"
        "int d,int e,boolean f,boolean g){}"
        "}",
}


class R219OriginalReadableMethodsError(ValueError):
    pass


def need(ok,why):
    if not ok:
        raise R219OriginalReadableMethodsError(why)


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1048576),b""):
            h.update(chunk)
    return h.hexdigest()


def extract_existing_method(source,name):
    need(name in METHODS,"R219_SELECTED_SOURCE_NAME_NOT_ALLOWED")
    hits=list(re.finditer(
        r"(?m)^\s*public\s+void\s+"+re.escape(name)+r"\s*\(\s*\)\s*\{",
        source))
    need(len(hits)==1,"R219_EXACT_SOURCE_METHOD_IDENTITY_NOT_UNIQUE")
    start=hits[0].start()
    index=source.index("{",start)+1
    level=1
    while level and index<len(source):
        if source[index]=="{":level+=1
        elif source[index]=="}":level-=1
        index+=1
    need(level==0 and index-start<11000,
         "R219_EXISTING_JAVA_SOURCE_BRACE_STRUCTURE_CHANGED")
    return source[start:index]


def audit_real_method_pair(original_javap,rebuilt_javap, *,
                           selected_method,expected=METHODS):
    need(selected_method in expected,"R219_SELECTED_METHOD_NOT_PINNED")
    item=expected[selected_method]
    try:
        result=compare_full_original_readable_code(
            original_javap,rebuilt_javap,
            original_title="public void "+item["original"]+"();",
            readable_title="public void "+selected_method+"();",
            aliases=item["aliases"],
            expected_instructions=item["ops"],
            expected_last_offset=item["last"])
    except R214OriginalReadableFilterError as exc:
        raise R219OriginalReadableMethodsError(
            "R219_ORIGINAL_AND_READABLE_METHOD_CODE_NOT_EQUAL_"+selected_method
        ) from exc
    return {
        "selected_original_method":item["original"]+"()V",
        "existing_readable_method":selected_method+"()V",
        "original_jvm_instructions_verified":
            result["original_decoded_jvm_instructions"],
        "original_jvm_last_byte_offset":item["last"],
        "all_instruction_offsets_branches_and_symbolic_operands_match":True,
        "original_to_readable_aliases_exercised":
            result["actual_distinct_renamed_member_or_type_symbols"],
        "actual_existing_readable_java_source_modified":False,
    }


def verify_pinned_final_two_parent_methods(original_jar,source_tree_zip, *,
                                          jar_sha256=CANONICAL_V309,
                                          original_class_sha256=ORIGINAL_CLASS_SHA256,
                                          source_zip_sha256=TREE_SHA256,
                                          readable_sha256=DONOR_SHA256):
    need(file_sha(original_jar)==jar_sha256 and
         file_sha(source_tree_zip)==source_zip_sha256,
         "R219_EXACT_PRIVATE_V309_BINARY_AND_READABLE_TREE_REQUIRED")
    with ZipFile(original_jar) as original:
        need(original.namelist().count("rs/n/c/ap.class")==1,
             "R219_ORIGINAL_PARENT_BINARY_OWNER_NOT_UNIQUE")
        old=original.read("rs/n/c/ap.class")
    need(hashlib.sha256(old).hexdigest()==original_class_sha256,
         "R219_ORIGINAL_SPELLBOOK_CLASS_SHA_CHANGED")
    with ZipFile(source_tree_zip) as private_tree:
        need(private_tree.namelist().count(DONOR_PATH)==1,
             "R219_READABLE_CLASS179_JAVA_NOT_UNIQUE")
        donor=private_tree.read(DONOR_PATH)
    need(hashlib.sha256(donor).hexdigest()==readable_sha256,
         "R219_REAL_EXISTING_DECOMPILED_JAVA_SHA_CHANGED")
    java=donor.decode("utf-8")
    javac=shutil.which("javac")
    javap=shutil.which("javap")
    need(javac is not None and javap is not None,
         "R219_SOURCE_ONLY_JDK9_TOOLS_REQUIRED")
    old_profile=profile_class_field_accesses(old)
    proofs={}
    for name,item in METHODS.items():
        method=extract_existing_method(java,name)
        need(hashlib.sha256(method.encode()).hexdigest()==item["source_sha"],
             "R219_EXISTING_SOURCE_METHOD_BODY_CHANGED_"+name)
        if name=="register":
            partial=(
                "package rs.interfaces.widgets;\n"
                "import java.util.*;\n"
                "import rs.graphics.Sprite;\n"
                "import rs.interfaces.WidgetComponent;\n"
                "public class Class179 extends Widget {\n"
                "public static final List<Class176> field3648=new ArrayList<>();\n"
                "private static Sprite field3649,field3650,field3651,"
                "field3652,field3653,field3654,field3655;\n"
                "public void method1592(){}\n"
                "public void method2352(){}\n"
                "public void method3532(){}\n"
                "public void method892(){}\n"
                "public static void method236(){}\n"
                +method+"\n}\n")
            helpers=REGISTER_FAKE_DEPENDENCIES
        else:
            partial=(
                "package rs.interfaces.widgets;\n"
                "import java.util.*;\n"
                "import rs.interfaces.WidgetComponent;\n"
                "import rs.graphics.HitsplatFont;\n"
                "public class Class179 extends Widget {\n"
                "public static int[] field3643,field3644;\n"
                +method+"\n}\n")
            helpers=CLASSIC_FAKE_DEPENDENCIES
        with tempfile.TemporaryDirectory(prefix="spk-r219-"+name+"-") as td:
            root=Path(td)
            files={"rs/interfaces/widgets/Class179.java":partial,**helpers}
            paths=[]
            for relative,text in files.items():
                target=root/"src"/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(text,encoding="utf-8")
                paths.append(str(target))
            out=root/"classes";empty=root/"empty"
            out.mkdir();empty.mkdir()
            env={k:v for k,v in os.environ.items() if k not in
                 ("CLASSPATH","JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS")}
            try:
                result=subprocess.run([
                    javac,"--release","9","-g:none","-proc:none",
                    "-implicit:none","-classpath",str(empty),
                    "-sourcepath",str(empty),"-d",str(out),*paths],
                    cwd=root,env=env,stdin=subprocess.DEVNULL,
                    capture_output=True,timeout=110,check=False)
            except (OSError,subprocess.TimeoutExpired) as exc:
                raise R219OriginalReadableMethodsError(
                    "R219_JAVAC_SOURCE_BUILD_ABORTED") from exc
            emitted={p.relative_to(out).as_posix()
                     for p in out.rglob("*.class")}
            need(result.returncode==0 and
                 emitted=={p[:-5]+".class" for p in files},
                 "R219_SOURCE_ONLY_CLASS_INVENTORY_OR_COMPILER_FAILURE")
            rebuilt=(out/"rs/interfaces/widgets/Class179.class").read_bytes()
            def disasm(cp,owner):
                try:
                    return subprocess.run(
                        [javap,"-p","-c","-classpath",str(cp),owner],
                        cwd=root,env=env,capture_output=True,
                        text=True,timeout=50,check=True).stdout
                except (OSError,subprocess.TimeoutExpired,
                        subprocess.CalledProcessError) as exc:
                    raise R219OriginalReadableMethodsError(
                        "R219_JAVAP_DISASSEMBLY_FAILED") from exc
            original_javap=disasm(original_jar,"rs.n.c.ap")
            candidate_javap=disasm(out,"rs.interfaces.widgets.Class179")
        new_profile=profile_class_field_accesses(rebuilt)
        def get(profile,method_id):
            members=[x for x in profile["methods"]
                     if (x["name"],x["descriptor"])==(method_id,"()V")]
            need(len(members)==1,"R219_SELECTED_JVM_METHOD_BODY_ABSENT")
            return members[0]
        left=get(old_profile,item["original"])
        right=get(new_profile,name)
        need(left["access"]==right["access"] and
             left["code_length"]==right["code_length"]==item["last"]+1 and
             left["max_stack"]==right["max_stack"] and
             left["max_locals"]==right["max_locals"] and
             left["exception_handlers"]==right["exception_handlers"] and
             left["stackmap_table_present"]==right["stackmap_table_present"],
             "R219_ORIGINAL_JVM_CODE_ATTRIBUTE_LIMIT_CHANGED")
        proofs[name]=audit_real_method_pair(
            original_javap,candidate_javap,selected_method=name)
    need(sum(x["original_jvm_instructions_verified"] for x in
             proofs.values())==2018,
         "R219_FINAL_TWO_ORIGINAL_JVM_INSTRUCTION_TOTAL_DRIFT")
    need(file_sha(original_jar)==jar_sha256 and
         file_sha(source_tree_zip)==source_zip_sha256,
         "R219_PRIVATE_SOURCE_OR_BINARY_CHANGED_DURING_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"v309_last_two_original_spellbook_methods_from_readable_java_r219",
        "actual_selected_parent_methods":2,
        "matched_original_jvm_instructions":2018,
        "methods":proofs,
        "all_fourteen_original_parent_method_bodies_separately_verified_cumulative":True,
        "cumulative_original_parent_jvm_instructions_from_R212_through_R219":4314,
        "register_and_classic_source_bodies_unchanged":True,
        "isolated_java_release":9,
        "original_client_game_code_executed":False,
        "temporary_compiler_only_helper_implementations_accepted":False,
        "all_fourteen_methods_compiled_together_as_one_class":False,
        "whole_original_client_compiles":False,
        "original_classfile_binary_identity_proven":False,
        "source_redistribution_authorized":False,
    }

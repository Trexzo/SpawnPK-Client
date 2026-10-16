"""R223: compile five more REAL v309 readable source owners, not dummy code.

Build the complete, R221-original-Code-accepted Class179.java with actual
Widget, three widget enums, Class170 gambling widget, Class168 packet
callback, Class169 overlay callback, and actual Class69/Class53 enums.

All nine actual readable dependency inputs are independently SHA pinned.
Only EIGHT dependency owners are still compiler-only, including TWO newly
identified abstract APIs: scriptpacket.Class260 and graphics.hud.Overlay.
The extra four inherited widget builder signatures are placed ONLY on the
already-fake WidgetComponent, never on actual original-derived Widget.java.

Original proprietary sources/JAR are private inputs. No game Java runs.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .private_v309_spellbook_real_dependencies_r222 import (
    ORIGINAL_JAR_SHA256, SOURCE_ZIP_SHA256, R221_EVIDENCE_ZIP_SHA256,
    R221_NORMALIZED_JAVA_SHA256, R221_CLASS_SHA256,
    R222_REAL_WIDGET_CLASS_SHA256,
    REPLACEMENTS as R222_REALS,
    read_unique,read_fake_template_ast,integrate_actual_readable_dependencies,
    file_sha,
)
from .private_v309_unified_spellbook_class_r221 import verify_private_unified_class
from .private_v309_readable_widget_source_parity_r210 import audit_readable_widget_classfiles

ADDITIONAL_REAL={
    "rs/interfaces/widgets/Class170.java":
       "73a2f01084e9abd1c86c9d6cad95cb35ce58873f0f45a771b79c36e2bad54b42",
    "rs/interfaces/widgets/Class168.java":
       "28a814fd331abe90eb2711929d4edc84c184d7a41bc8fcf90b13117b5ec20103",
    "rs/interfaces/widgets/Class169.java":
       "591e74de23e0824070636a8ff4a5197e347e5b495f2fe2698b880f05b664d996",
    "rs/graphics/hud/Class69.java":
       "fdcbbc45cdb74b792037b9ca93019ebc8ab21e929ce1f21391d717a409396cde",
    "rs/pkg39/Class53.java":
       "22126d408186bd402e87619d4774daffde2b2955dead0ec73bd44abc9bdc4596",
}
ALL_REAL_COUNT=9
NONORIGINAL_SUPPORT_COUNT=8
EXPECTED_JAVA_OWNERS=18
CL170_CLASS_SHA256="f7ac42cca5d8c44aa827edaf947b1698724d4151a84a4fef9ee2a5097469f917"
CL168_CLASS_SHA256="0604158afc9475bdae752a0e2df7fd64483b2208dd7c571f709239416779db02"
CL169_CLASS_SHA256="0f3f82bb7ffb5f4c91c67798e54851e989d32356d5f8dfa55a88d5725d9fe776"
SOURCE_ROOT="recovered-source/v309/src/"

# The following prototypes are NOT restored game logic. They exist only
# to compile genuine Class168 + Class169 source that calls these APIs.
TEMPORARY_API_CLASSES={
    "rs/scriptpacket/Class260.java":(
        "package rs.scriptpacket;"
        "public abstract class Class260 {"
        "protected int method2463(){return 0;}"
        "public abstract void handlePacket();}"
    ),
    "rs/graphics/hud/Overlay.java":(
        "package rs.graphics.hud;"
        "import rs.Client;"
        "public abstract class Overlay {"
        "public abstract void method1484();"
        "public abstract boolean method3175(Client c);"
        "public abstract void method1640(Client c,Class69 x);"
        "public abstract void method904();}"
    ),
}
# Newly encountered Class170 inherited calls; declaration-only prototypes
# on a fake WidgetComponent class. These are never inserted in actual Widget.
TEMPORARY_WIDGET_BUILDERS=(
    " public static void createArchiveSpriteButton(int a,int b,int c,"
    "int d,int e,String f,int g,int h,String i){}\n"
    " public static void createSizedTextChildContainer(int a,int b,"
    "String c,int d,int e,int f){}\n"
    " public static void createTextOptionWidget(int a,String b,"
    "rs.graphics.HitsplatFont[] c,int d,int e,boolean f){}\n"
    " public static void createZeroWidthTextOption(int a,String b,"
    "rs.graphics.HitsplatFont[] c,int d,int e,boolean f){}\n"
)


class R223ReadableDependencyClosureError(ValueError):
    pass


def need(ok,code):
    if not ok:
        raise R223ReadableDependencyClosureError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def augment_fake_only_sources(r222_sources,real_five):
    """Strict source provenance: never edit any existing REAL java bytes."""
    need(isinstance(r222_sources,dict)
         and len(r222_sources)==12
         and set(real_five)==set(ADDITIONAL_REAL),
         "R223_R222_BASE_AND_FIVE_REAL_DEPENDENCIES_REQUIRED")
    result=dict(r222_sources)
    for owner,content in real_five.items():
        need(type(content) is str
             and sha(content.encode("utf-8"))==ADDITIONAL_REAL[owner],
             "R223_NEW_REAL_SOURCE_DIGEST_CHANGED_"+owner)
        if owner=="rs/interfaces/widgets/Class170.java":
            need(owner in result,"R223_FAKE_CLASS170_MISSING_FROM_R222")
        else:
            need(owner not in result,"R223_DUPLICATE_REAL_OWNER_"+owner)
        result[owner]=content
    for owner,source in TEMPORARY_API_CLASSES.items():
        need(owner not in result,"R223_FAKE_API_MUST_BE_NEW_"+owner)
        result[owner]=source

    # Only mutate precisely known FAKE sources and use fail-closed matches.
    parent_key="rs/interfaces/WidgetComponent.java"
    parent=result[parent_key]
    need(parent.count(" public void setChild(int a,int b,int c,int d){}")==1
         and parent.count(" public int scrollHeight,height,width,mouseOverLayer;")==1
         and parent.endswith(" }"),
         "R223_FAKE_WIDGET_COMPONENT_SIGNATURE_DRIFT")
    parent=parent.replace(
        " public int scrollHeight,height,width,mouseOverLayer;",
        " public int scrollHeight,height,width,mouseOverLayer,scrollbarId,"
        "id,type,invSpritePadX,invSpritePadY;"
        " public String[] actions;"
        " public int[] itemModelIds,stackSizes,itemIds,itemColors;"
        " public boolean field3946;",1)
    parent=parent.replace(
        " public void setChild(int a,int b,int c,int d){}",
        " public void setChild(int a,int b,int c,int d){}"
        " public rs.interfaces.WidgetComponent initItemNames(){return this;}"
        " public static rs.graphics.Sprite getSprite(int id,String s)"
        "{return null;}",1)
    pos=parent.rfind(" }")
    result[parent_key]=parent[:pos]+TEMPORARY_WIDGET_BUILDERS+parent[pos:]

    sprite=result["rs/graphics/Sprite.java"]
    need(sprite.count("public Sprite(String p){}")==1,
         "R223_FAKE_SPRITE_SIGNATURE_DRIFT")
    result["rs/graphics/Sprite.java"]=sprite.replace(
        "public Sprite(String p){}",
        "public Sprite(String p){} public void method1192(int x,int y){}",1)

    font=result["rs/graphics/HitsplatFont.java"]
    need(font.count("public class HitsplatFont {}")==1,
         "R223_FAKE_FONT_SIGNATURE_DRIFT")
    result["rs/graphics/HitsplatFont.java"]=font.replace(
        "public class HitsplatFont {}",
        "public class HitsplatFont {"
        "public void method1156(String s,int x,int y,int color,int alpha){} }",1)

    client=result["rs/Client.java"]
    need(client.count("public static int[] tabInterfaceIds;")==1,
         "R223_FAKE_CLIENT_SIGNATURE_DRIFT")
    result["rs/Client.java"]=client.replace(
        "public static int[] tabInterfaceIds;",
        "public static int[] tabInterfaceIds;"
        "public static int rootInterfaceId,screenWidth,screenHeight;"
        "public static rs.graphics.HitsplatFont field1004;",1)

    conf=result["rs/Configuration.java"]
    need(conf.count("public static void saveSettings(){}")==1,
         "R223_FAKE_CONFIGURATION_SIGNATURE_DRIFT")
    result["rs/Configuration.java"]=conf.replace(
        "public static void saveSettings(){}",
        "public static rs.pkg39.Class53 screenMode;"
        "public static void saveSettings(){}",1)

    need(len(result)==EXPECTED_JAVA_OWNERS and
         sum(x in result for x in ADDITIONAL_REAL)==5 and
         sum(x in result for x in TEMPORARY_API_CLASSES)==2,
         "R223_EXPECTED_18_SOURCE_OWNER_CLOSURE_FAILED")
    return result


def verify_private_r223_source_closure(original_jar,source_zip,r221_zip):
    need(file_sha(original_jar)==ORIGINAL_JAR_SHA256
         and file_sha(source_zip)==SOURCE_ZIP_SHA256
         and file_sha(r221_zip)==R221_EVIDENCE_ZIP_SHA256,
         "R223_THREE_EXACT_PRIVATE_INPUT_DIGESTS_REQUIRED")
    with ZipFile(original_jar) as jar:
        original_widget=read_unique(jar,"rs/n/c.class",30000)
    with ZipFile(source_zip) as archive:
        four={}
        for name,digest in R222_REALS.items():
            data=read_unique(archive,SOURCE_ROOT+
                "rs/interfaces/widgets/"+name+".java",200000)
            need(sha(data)==digest,"R223_R222_REAL_SOURCE_CHANGED_"+name)
            four[name]=data.decode("utf-8")
        five={}
        for path,digest in ADDITIONAL_REAL.items():
            data=read_unique(archive,SOURCE_ROOT+path,200000)
            need(sha(data)==digest,"R223_ADDITIONAL_REAL_SOURCE_CHANGED_"+path)
            five[path]=data.decode("utf-8")
    with ZipFile(r221_zip) as archive:
        script=read_unique(archive,
             "scripts/source-only-recompile-unified-class.py",25000)
        candidate=read_unique(archive,
             "private/normalized-readable-Class179.java",100000)
        expected_class=read_unique(archive,
             "private/compiled-readable-Class179.class",100000)
    need(sha(candidate)==R221_NORMALIZED_JAVA_SHA256
         and sha(expected_class)==R221_CLASS_SHA256,
         "R223_R221_VERIFIED_CLASS_AND_JAVA_DRIFT")
    base=integrate_actual_readable_dependencies(
        read_fake_template_ast(script),four)
    base["rs/interfaces/widgets/Class179.java"]=candidate.decode("utf-8")
    sources=augment_fake_only_sources(base,five)

    javac=shutil.which("javac")
    need(javac is not None,"R223_JDK_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r223-real-") as td:
        root=Path(td);src=root/"src";out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        inputs=[]
        for relative,text in sources.items():
            dest=src/relative
            need(not dest.exists(),"R223_DUPLICATED_JAVA_SOURCE_OWNER")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(text,encoding="utf-8")
            inputs.append(str(dest))
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            proc=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*inputs],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=150,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R223ReadableDependencyClosureError(
                "R223_ACTUAL_JAVA9_SOURCE_BUILD_ABORTED") from exc
        emitted={f.relative_to(out).as_posix()
                 for f in out.rglob("*.class")}
        need(proc.returncode==0 and
             emitted=={n[:-5]+".class" for n in sources},
             "R223_ACTUAL_SOURCES_FAILED_OR_EXTRA_CLASS_EMITTED")
        def built(name):
            return (out/name).read_bytes()
        class179=built("rs/interfaces/widgets/Class179.class")
        widget=built("rs/interfaces/widgets/Widget.class")
        need(class179==expected_class and
             sha(class179)==R221_CLASS_SHA256,
             "R223_ORIGINAL_VERIFIED_SPELLBOOK_BINARY_CHANGED")
        need(sha(widget)==R222_REAL_WIDGET_CLASS_SHA256,
             "R223_VERIFIED_READABLE_WIDGET_BINARY_CHANGED")
        for owner,pin in (
            ("Class170",CL170_CLASS_SHA256),
            ("Class168",CL168_CLASS_SHA256),
            ("Class169",CL169_CLASS_SHA256),
        ):
            need(sha(built("rs/interfaces/widgets/"+owner+".class"))==pin,
                 "R223_ORIGINAL_DECOMPILED_DEPENDENCY_BUILD_DRIFT_"+owner)
    proof=audit_readable_widget_classfiles(original_widget,widget)
    need(proof["matched_original_decoded_jvm_instructions"]==11,
         "R223_REAL_WIDGET_ORIGINAL_CODE_PROOF_LOST")
    with tempfile.TemporaryDirectory(prefix="spk-r223-replay-") as tmp:
        source=Path(tmp)/"Class179.java"
        output=Path(tmp)/"Class179.class"
        source.write_bytes(candidate);output.write_bytes(class179)
        check=verify_private_unified_class(original_jar,source,output)
    need(check["verified_original_JVM_methods"]==14 and
         check["verified_original_JVM_instructions"]==4314,
         "R223_FULL_ORIGINAL_CLASS_CODE_PROOF_LOST")
    need(file_sha(original_jar)==ORIGINAL_JAR_SHA256
         and file_sha(source_zip)==SOURCE_ZIP_SHA256
         and file_sha(r221_zip)==R221_EVIDENCE_ZIP_SHA256,
         "R223_PRIVATE_INPUT_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_real_gambling_widget_callback_and_mode_source_r223",
        "real_readable_dependency_classes":ALL_REAL_COUNT,
        "additional_real_source_classes":list(ADDITIONAL_REAL),
        "compiler_only_dependency_declarations":NONORIGINAL_SUPPORT_COUNT,
        "java_source_class_owners_compiled":EXPECTED_JAVA_OWNERS,
        "java_release":9,
        "actual_local_source_javac_errors":0,
        "Class179_sha256":R221_CLASS_SHA256,
        "Class179_byte_identical_to_R221":True,
        "verified_original_spellbook_JVM_methods":14,
        "verified_original_spellbook_JVM_instructions":4314,
        "Widget_original_JVM_instructions":11,
        "new_dependent_classes_original_JVM_code_verified":False,
        "whole_client_compiles":False,
        "game_code_executed":False,
        "fake_declarations_counted_as_original":False,
        "source_redistribution_authorized":False,
    }

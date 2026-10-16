"""R213 — additional v309 original spellbook Code from readable Java.

Original rs/n/c/ap.m(int) and k() have exact Java counterparts in the
preexisting decompiled Class179.java: method640(int), method1241().
Extract those two method bodies unchanged from the SHA-pinned source tree,
compile in an isolated Java9 partial class with FAKE dependency signatures,
then prove all 76+43 original JVM instructions, exact branch/offset/operand
semantics under EXPLICIT original->readable symbolic mapping.

Partial source compilation does not prove the remaining 9 parent methods,
full-class superclass/field ABI or runnable client. No original code runs.
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

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .bytecode_profile import profile_class_field_accesses
from .source_method_parity import _normalized_instructions
from .private_v309_readable_spellbook_three_methods_r212 import (
    map_instruction_symbolic,
)

ORIGINAL_OWNER="rs/n/c/ap"
READABLE_OWNER="rs/interfaces/widgets/Class179"
ORIGINAL_JAR_SHA256=CANONICAL_V309
ORIGINAL_CLASS_SHA256=(
    "b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
)
SOURCE_TREE_SHA256=(
    "cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
)
SOURCE_ENTRY=(
    "recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
)
SOURCE_SHA256=(
    "8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
)
METHODS=(
    ("m","(I)V","method640",76,
     "754eca1686ff2ad99b1da0fadf82bf5f117ba88e25136bd7911d8ff1a280b1dd"),
    ("k","()V","method1241",43,
     "a91a1399ed71d332f6c0952ba3c6c92ffc8d65122c9c777f18e28211546c70ce"),
)
TOTAL_ORIGINAL_JVM_INSTRUCTIONS=119

ALIASES={
    # Original parent instance/static UI data
    ("rs/n/c/ap","bQ","I"):
        (READABLE_OWNER,"field3656","I"),
    ("rs/n/c/ap","e","Z"):
        (READABLE_OWNER,"field3647","Z"),
    ("rs/n/c/ap","f","Ljava/util/List;"):
        (READABLE_OWNER,"field3648","Ljava/util/List;"),
    # Tab changes and original names for source methods
    ("rs/Client","eT","[I"):
        ("rs/Client","tabInterfaceIds","[I"),
    ("rs/n/c/ap","k","()V"):
        (READABLE_OWNER,"method1241","()V"),
    ("rs/n/c/ap","j","()V"):
        (READABLE_OWNER,"method236","()V"),
    ("rs/f/a","d","()V"):
        ("rs/Configuration","saveSettings","()V"),
    # Three original spellbook categories and decompiled enum aliases
    ("rs/n/c/ap$a","a","Lrs/n/c/ap$a;"):
        ("rs/interfaces/widgets/Class176","field3590",
         "Lrs/interfaces/widgets/Class176;"),
    ("rs/n/c/ap$a","b","Lrs/n/c/ap$a;"):
        ("rs/interfaces/widgets/Class176","field3591",
         "Lrs/interfaces/widgets/Class176;"),
    ("rs/n/c/ap$a","c","Lrs/n/c/ap$a;"):
        ("rs/interfaces/widgets/Class176","field3592",
         "Lrs/interfaces/widgets/Class176;"),
    # Original sprite toggle resources
    ("rs/n/c/V","f","Lrs/l/F;"):
        ("rs/interfaces/widgets/Class170","field3533",
         "Lrs/graphics/Sprite;"),
    ("rs/n/c/V","g","Lrs/l/F;"):
        ("rs/interfaces/widgets/Class170","field3534",
         "Lrs/graphics/Sprite;"),
    ("rs/n/e","H","[Lrs/n/e;"):
        ("rs/interfaces/WidgetComponent","widgetTable",
         "[Lrs/interfaces/WidgetComponent;"),
    ("rs/n/e","E","Lrs/l/F;"):
        ("rs/interfaces/WidgetComponent","sprite",
         "Lrs/graphics/Sprite;"),
    # Unchanged Java collection methods are explicitly included.
    ("java/util/List","contains","(Ljava/lang/Object;)Z"):
        ("java/util/List","contains","(Ljava/lang/Object;)Z"),
    ("java/util/List","remove","(Ljava/lang/Object;)Z"):
        ("java/util/List","remove","(Ljava/lang/Object;)Z"),
    ("java/util/List","add","(Ljava/lang/Object;)Z"):
        ("java/util/List","add","(Ljava/lang/Object;)Z"),
}
NONORIGINAL_SOURCE_DECLARATIONS={
    "rs/Client.java":(
        "package rs;\n"
        "public class Client {public static int[] tabInterfaceIds;}\n"
    ),
    "rs/Configuration.java":(
        "package rs;\n"
        "public class Configuration {public static void saveSettings(){}}\n"
    ),
    "rs/graphics/Sprite.java":(
        "package rs.graphics;\n"
        "public class Sprite {}\n"
    ),
    "rs/interfaces/WidgetComponent.java":(
        "package rs.interfaces;\n"
        "import rs.graphics.Sprite;\n"
        "public class WidgetComponent {\n"
        " public static WidgetComponent[] widgetTable;\n"
        " public Sprite sprite;\n"
        "}\n"
    ),
    "rs/interfaces/widgets/Class170.java":(
        "package rs.interfaces.widgets;\n"
        "import rs.graphics.Sprite;\n"
        "public class Class170 {\n"
        " public static Sprite field3533,field3534;\n"
        "}\n"
    ),
    "rs/interfaces/widgets/Class176.java":(
        "package rs.interfaces.widgets;\n"
        "public enum Class176 {\n"
        " COMBAT, TELEPORT, UTILITY;\n"
        " public static final Class176 field3590=COMBAT;\n"
        " public static final Class176 field3591=TELEPORT;\n"
        " public static final Class176 field3592=UTILITY;\n"
        "}\n"
    ),
}


class R213ReadableSpellbookCodeError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R213ReadableSpellbookCodeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda:stream.read(1048576),b""):
            h.update(data)
    return h.hexdigest()


def extract_pinned_source_method(source,name):
    names=list(re.finditer(
        r"(?m)^\s*public\s+static\s+void\s+"+
        re.escape(name)+r"\s*\((?P<params>[^)]*)\)\s*\{",
        source))
    need(len(names)==1,
         "R213_REAL_DONOR_METHOD_SIGNATURE_NOT_UNIQUE")
    first=names[0].start()
    cursor=source.index("{",first)+1
    depth=1
    while depth and cursor<len(source):
        if source[cursor]=="{": depth+=1
        elif source[cursor]=="}":depth-=1
        cursor+=1
    need(depth==0 and cursor-first<=2000,
         "R213_UNBALANCED_OR_EXCESSIVE_JAVA_METHOD")
    return source[first:cursor]


def _method(profile,name,descriptor):
    values=[x for x in profile["methods"]
            if (x["name"],x["descriptor"])==(name,descriptor)]
    need(len(values)==1 and values[0]["code_length"] is not None,
         "R213_JVM_METHOD_BODY_NOT_UNIQUE")
    return values[0]


def audit_two_readable_methods(
        original_class,candidate_class, *,
        method_pairs=METHODS,member_aliases=ALIASES,
        expected_total=TOTAL_ORIGINAL_JVM_INSTRUCTIONS):
    original=profile_class_field_accesses(original_class)
    candidate=profile_class_field_accesses(candidate_class)
    need(len(method_pairs)==2 and
         len({x[0:2] for x in method_pairs})==2,
         "R213_EXACT_TWO_SELECTED_JVM_METHODS_REQUIRED")
    compared=0
    summary=[]
    for old,descriptor,new,count,_ in method_pairs:
        a=_method(original,old,descriptor)
        b=_method(candidate,new,descriptor)
        need(a["access"]==b["access"] and
             a["max_stack"]==b["max_stack"] and
             a["max_locals"]==b["max_locals"] and
             a["code_length"]==b["code_length"] and
             a["exception_handlers"]==b["exception_handlers"] and
             a["stackmap_table_present"]==b["stackmap_table_present"],
             "R213_METHOD_ACCESS_LIMIT_OR_HANDLER_DIFFERS")
        before=_normalized_instructions(original,a)
        after=_normalized_instructions(candidate,b)
        mapped=[
            map_instruction_symbolic(x,aliases=member_aliases)
            for x in before
        ]
        need(len(before)==count and mapped==after,
             "R213_READABLE_METHOD_CODE_OR_SYMBOLIC_OPERAND_DRIFT")
        compared+=len(before)
        summary.append({
            "original_method":old+descriptor,
            "readable_method":new+descriptor,
            "original_jvm_instructions_matched":count,
            "original_code_offsets_and_branches_match":True,
        })
    need(compared==expected_total,
         "R213_ORIGINAL_119_INSTRUCTION_TOTAL_CHANGED")
    return {
        "schema_version":1,
        "kind":"v309_existing_readable_spellbook_toggle_methods_r213",
        "selected_original_method_count":2,
        "original_jvm_instructions_matched":compared,
        "methods":summary,
        "readable_source_semantic_code_parity_verified":True,
        "other_twelve_parent_methods_code_verified":False,
        "original_parent_full_class_header_verified":False,
        "original_game_code_executed":False,
        "whole_original_client_compiles":False,
    }


def verify_pinned_two_readable_original_spellbook_methods(
        original_jar,source_tree_zip, *,
        original_jar_sha256=CANONICAL_V309,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        source_zip_sha256=SOURCE_TREE_SHA256,
        source_sha256=SOURCE_SHA256):
    need(file_sha(original_jar)==original_jar_sha256
         and file_sha(source_tree_zip)==source_zip_sha256,
         "R213_PRIVATE_BINARY_AND_SOURCE_TREE_SHA_MISMATCH")
    with ZipFile(original_jar) as jar:
        path=ORIGINAL_OWNER+".class"
        need(jar.namelist().count(path)==1,
             "R213_ORIGINAL_CLASSFILE_ENTRY_NOT_UNIQUE")
        old=jar.read(path)
    need(sha(old)==original_class_sha256,
         "R213_ORIGINAL_PARENT_CLASS_SHA_CHANGED")
    with ZipFile(source_tree_zip) as tree:
        need(tree.namelist().count(SOURCE_ENTRY)==1,
             "R213_PRIVATE_SOURCE_JAVA_ENTRY_NOT_UNIQUE")
        readable=tree.read(SOURCE_ENTRY)
    need(sha(readable)==source_sha256,
         "R213_ORIGINAL_READABLE_DONOR_SHA_CHANGED")
    source=readable.decode("utf-8")
    java_parts=[]
    for oldname,descriptor,name,count,pin in METHODS:
        body=extract_pinned_source_method(source,name)
        need(sha(body.encode("utf-8"))==pin,
             "R213_PINNED_VERBATIM_METHOD_SOURCE_CHANGED")
        java_parts.append(body)
    class_source=(
        "package rs.interfaces.widgets;\n"
        "import java.util.*;\n"
        "import rs.Configuration;\n"
        "import rs.Client;\n"
        "import rs.interfaces.WidgetComponent;\n"
        "public class Class179 {\n"
        " public static int field3656;\n"
        " public static boolean field3647;\n"
        " public static final List<Class176> field3648=new ArrayList<>();\n"
        +"\n".join(java_parts)+"\n"
        " public static void method236(){}\n"
        "}\n"
    )
    javac=shutil.which("javac")
    need(javac is not None,"R213_JDK9_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r213-source-") as tmp:
        root=Path(tmp)
        inputs={READABLE_OWNER+".java":class_source,
                **NONORIGINAL_SOURCE_DECLARATIONS}
        paths=[]
        for relative,body in inputs.items():
            file=root/"src"/relative
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(body,encoding="utf-8")
            paths.append(str(file))
        empty=root/"empty";out=root/"classes"
        empty.mkdir();out.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            built=subprocess.run(
                [javac,"--release","9","-g:none",
                 "-proc:none","-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=120,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R213ReadableSpellbookCodeError(
                "R213_ORIGINAL_READABLE_SOURCE_BUILD_ABORTED") from exc
        emitted={file.relative_to(out).as_posix()
                 for file in out.rglob("*.class")}
        expected={p[:-5]+".class" for p in inputs}
        need(built.returncode==0 and emitted==expected,
             "R213_READABLE_METHOD_BUILD_OR_CLASS_SET_CHANGED")
        candidate=(out/(READABLE_OWNER+".class")).read_bytes()
    result=audit_two_readable_methods(old,candidate)
    need(file_sha(original_jar)==original_jar_sha256
         and file_sha(source_tree_zip)==source_zip_sha256,
         "R213_PRIVATE_SOURCE_OR_BINARY_CHANGED_DURING_REPLAY")
    return {
        **result,
        "original_class_sha256":original_class_sha256,
        "readable_original_source_sha256":source_sha256,
        "original_method_source_mutation_count":0,
        "compiler_only_dependency_source_owners":6,
        "fake_dependency_source_integrated_into_client_tree":False,
        "all_five_R212_R213_selected_original_Code_methods_cumulative":
            5,
        "all_five_R212_R213_original_JVM_instructions_cumulative":
            210,
        "private_original_code_published":False,
    }

"""R215: existing readable Class179 constructor and static initializer JVM Code.

Recompile the actual unchanged Class179(HitsplatFont[]) constructor and
the five actual original-decompiled static field INITIALIZER DECLARATIONS
from the SHA-pinned Class179.java, then match all 4 + 13 original JVM
instructions/offsets against original v309 rs/n/c/ap class after only six
explicit owner/field aliases. Do not execute any client class or accept
the temporary compiler-only superclass as recovered original Java.
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

ORIGINAL_JAR_SHA256=CANONICAL_V309
ORIGINAL_PARENT_CLASS_SHA256=(
    "b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
)
PRIVATE_TREE_SHA256=(
    "cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
)
DONOR_JAVA_PATH=(
    "recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
)
DONOR_JAVA_SHA256=(
    "8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
)
DONOR_CONSTRUCTOR_SHA256=(
    "b7ad88602f8d1608ae741e31564fecd55f63988858e9935975ee5551e61a5852"
)
DECLARATION_FIELD_NAMES=(
    "field3645","field3646","field3647","field3648","field3656"
)
EXACT_EXPECTED_INITIALIZER_SOURCE_VALUES=(
    ("field3645","int","0"),
    ("field3646","boolean","true"),
    ("field3647","boolean","true"),
    ("field3648","List<Class176>","new ArrayList()"),
    ("field3656","int","-1"),
)
CONSTRUCTOR_ALIASES={
    'Method rs/n/c."<init>":([Lrs/l/K;)V':
    'Method rs/interfaces/widgets/Widget."<init>":([Lrs/graphics/HitsplatFont;)V',
}
INITIALIZER_ALIASES={
    "Field c:I":"Field field3645:I",
    "Field d:Z":"Field field3646:Z",
    "Field e:Z":"Field field3647:Z",
    "Field f:Ljava/util/List;":"Field field3648:Ljava/util/List;",
    "Field bQ:I":"Field field3656:I",
}
ORIGINAL_CONSTRUCTOR_TITLE="public rs.n.c.ap(rs.l.K[]);"
READABLE_CONSTRUCTOR_TITLE=(
    "public rs.interfaces.widgets.Class179(rs.graphics.HitsplatFont[]);"
)
INITIALIZER_TITLE="static {};"
NONORIGINAL_SIGNATURE_HELPERS={
    "rs/interfaces/widgets/Widget.java":(
        "package rs.interfaces.widgets;\n"
        "import rs.graphics.HitsplatFont;\n"
        "public class Widget { public Widget(HitsplatFont[] fonts){} }\n"
    ),
    "rs/graphics/HitsplatFont.java":(
        "package rs.graphics; public class HitsplatFont {}\n"
    ),
    "rs/interfaces/widgets/Class176.java":(
        "package rs.interfaces.widgets; public enum Class176 {COMBAT;}\n"
    ),
}


class R215OriginalReadableInitializerError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R215OriginalReadableInitializerError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def extract_exact_readable_constructor(source, *,
                                       name="Class179",parameter="HitsplatFont"):
    pattern=(
        r"(?m)^\s*public\s+"+re.escape(name)+
        r"\s*\("+re.escape(parameter)+
        r"\[\]\s+var1\)\s*\{"
    )
    matches=list(re.finditer(pattern,source))
    need(len(matches)==1,"R215_ACTUAL_READABLE_CONSTRUCTOR_NOT_UNIQUE")
    begin=matches[0].start()
    end=source.index("{",begin)+1
    depth=1
    while depth and end<len(source):
        if source[end]=="{":depth+=1
        elif source[end]=="}":depth-=1
        end+=1
    need(depth==0 and end-begin<=150,
         "R215_CONSTRUCTOR_EXTRACT_UNBOUNDED")
    return source[begin:end]


def extract_original_static_initializer_declarations(source, *,
           entries=EXACT_EXPECTED_INITIALIZER_SOURCE_VALUES):
    lines=[]
    for field,typename,value in entries:
        escaped_type=re.escape(typename).replace(r"\<","<").replace(r"\>",">")
        needle=(r"(?m)^\s*(?:public|private)\s+static\s+"
                r"(?:final\s+)?"+escaped_type+r"\s+"+
                re.escape(field)+r"\s*=\s*"+
                re.escape(value)+r"\s*;")
        matches=list(re.finditer(needle,source))
        need(len(matches)==1,
             "R215_PINNED_STATIC_FIELD_INITIALIZER_NOT_UNIQUE_"+field)
        lines.append(matches[0].group().strip())
    need(len(lines)==len(entries),
         "R215_NOT_ALL_FIVE_ACTUAL_DONOR_FIELD_INITIALIZERS_FOUND")
    return tuple(lines)


def audit_constructor_and_initializer(original_javap,rebuilt_javap, *,
                                      constructor_aliases=CONSTRUCTOR_ALIASES,
                                      initializer_aliases=INITIALIZER_ALIASES):
    try:
        constructor=compare_full_original_readable_code(
            original_javap,rebuilt_javap,
            original_title=ORIGINAL_CONSTRUCTOR_TITLE,
            readable_title=READABLE_CONSTRUCTOR_TITLE,
            aliases=constructor_aliases,
            expected_instructions=4,
            expected_last_offset=5)
        initializer=compare_full_original_readable_code(
            original_javap,rebuilt_javap,
            original_title=INITIALIZER_TITLE,
            readable_title=INITIALIZER_TITLE,
            aliases=initializer_aliases,
            expected_instructions=13,
            expected_last_offset=26)
    except R214OriginalReadableFilterError as exc:
        raise R215OriginalReadableInitializerError(
            "R215_SOURCE_ONLY_CONSTRUCTOR_OR_CLINIT_JVM_CODE_DIFFER") from exc
    return {
        "original_constructor_jvm_instructions_matched":
            constructor["original_decoded_jvm_instructions"],
        "original_static_initializer_jvm_instructions_matched":
            initializer["original_decoded_jvm_instructions"],
        "total_original_jvm_instructions_matched":17,
        "constructor_method_owner_and_supertype_explicitly_mapped":True,
        "five_original_runtime_default_assignments_matched":True,
        "all_jvm_offsets_and_branch_targets_match":True,
        "full_original_spelled_class_abi_accepted":False,
    }


def verify_pinned_original_readable_constructor_clinit(
        original_jar,private_source_zip, *,
        original_jar_sha256=ORIGINAL_JAR_SHA256,
        original_class_sha256=ORIGINAL_PARENT_CLASS_SHA256,
        source_tree_sha256=PRIVATE_TREE_SHA256,
        readable_source_sha256=DONOR_JAVA_SHA256):
    need(file_sha(original_jar)==original_jar_sha256 and
         file_sha(private_source_zip)==source_tree_sha256,
         "R215_PRIVATE_JAR_OR_READABLE_SOURCE_TREE_SHA_CHANGED")
    with ZipFile(original_jar) as jar:
        name="rs/n/c/ap.class"
        need(jar.namelist().count(name)==1,
             "R215_ORIGINAL_CLASS_NOT_UNIQUE")
        original_bytes=jar.read(name)
    need(digest(original_bytes)==original_class_sha256,
         "R215_ORIGINAL_CLASSFILE_DIGEST_CHANGED")
    with ZipFile(private_source_zip) as tree:
        need(tree.namelist().count(DONOR_JAVA_PATH)==1,
             "R215_READABLE_DONOR_JAVA_NOT_UNIQUE")
        donor=tree.read(DONOR_JAVA_PATH)
    need(digest(donor)==readable_source_sha256,
         "R215_READABLE_DONOR_JAVA_SHA_CHANGED")
    source=donor.decode("utf-8")
    constructor=extract_exact_readable_constructor(source)
    need(digest(constructor.encode("utf-8"))==DONOR_CONSTRUCTOR_SHA256,
         "R215_UNCHANGED_ACTUAL_READABLE_CONSTRUCTOR_SHA_CHANGED")
    declarations=extract_original_static_initializer_declarations(source)
    partial=(
        "package rs.interfaces.widgets;\n"
        "import java.util.*;\n"
        "import rs.graphics.HitsplatFont;\n"
        "public class Class179 extends Widget {\n"
        +"\n".join(declarations)+"\n"+constructor+"\n}\n"
    )
    javac=shutil.which("javac");javap=shutil.which("javap")
    need(javac is not None and javap is not None,
         "R215_JDK9_JAVAC_JAVAP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r215-read-init-") as tmp:
        root=Path(tmp)
        files={
            "rs/interfaces/widgets/Class179.java":partial,
            **NONORIGINAL_SIGNATURE_HELPERS,
        }
        paths=[]
        for filename,body in files.items():
            dest=root/"src"/filename
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(body,encoding="utf-8")
            paths.append(str(dest))
        output=root/"classes";empty=root/"empty"
        output.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            compiled=subprocess.run(
                [javac,"--release","9","-g:none",
                 "-proc:none","-implicit:none",
                 "-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(output),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=75,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R215OriginalReadableInitializerError(
                "R215_JAVA_SOURCE_ONLY_COMPILATION_ABORTED") from exc
        emitted={f.relative_to(output).as_posix()
                 for f in output.rglob("*.class")}
        need(compiled.returncode==0 and
             emitted=={f[:-5]+".class" for f in files},
             "R215_ONLY_READABLE_OWNER_AND_FAKE_HELPER_CLASS_OUTPUTS")
        rebuilt_bytes=(output/"rs/interfaces/widgets/Class179.class").read_bytes()
        def disasm(cp,owner):
            try:
                return subprocess.run(
                    [javap,"-p","-c","-classpath",str(cp),owner],
                    capture_output=True,text=True,check=True,
                    cwd=root,env=env,timeout=40).stdout
            except (OSError,subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as exc:
                raise R215OriginalReadableInitializerError(
                    "R215_JAVAP_FAILURE") from exc
        original_text=disasm(original_jar,"rs.n.c.ap")
        new_text=disasm(output,"rs.interfaces.widgets.Class179")
    def one(profile,name,signature):
        members=[m for m in profile["methods"]
                 if (m["name"],m["descriptor"])==(name,signature)]
        need(len(members)==1,"R215_EXPECTED_METHOD_NOT_UNIQUE")
        return members[0]
    original=profile_class_field_accesses(original_bytes)
    candidate=profile_class_field_accesses(rebuilt_bytes)
    for key_before,key_after,length in (
        (("<init>","([Lrs/l/K;)V"),
         ("<init>","([Lrs/graphics/HitsplatFont;)V"),6),
        (("<clinit>","()V"),("<clinit>","()V"),27),
    ):
        a=one(original,*key_before);b=one(candidate,*key_after)
        need(a["access"]==b["access"] and
             a["code_length"]==b["code_length"]==length and
             a["max_stack"]==b["max_stack"] and
             a["max_locals"]==b["max_locals"] and
             a["exception_handlers"]==b["exception_handlers"] and
             a["stackmap_table_present"]==b["stackmap_table_present"],
             "R215_SELECTED_JVM_CODE_ATTRIBUTE_LIMIT_MISMATCH")
    report=audit_constructor_and_initializer(original_text,new_text)
    need(file_sha(original_jar)==original_jar_sha256 and
         file_sha(private_source_zip)==source_tree_sha256,
         "R215_ORIGINAL_OR_DONOR_JAVA_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_existing_readable_Class179_constructor_initializer_r215",
        **report,
        "source_compilation_java_release":9,
        "original_full_binary_classfile_sha256":original_class_sha256,
        "original_real_readable_Class179_java_sha256":
            readable_source_sha256,
        "original_donor_constructor_sha256":DONOR_CONSTRUCTOR_SHA256,
        "original_initializer_field_names":list(DECLARATION_FIELD_NAMES),
        "original_source_declarations_verbatim":True,
        "fake_dependency_helper_owners":len(NONORIGINAL_SIGNATURE_HELPERS),
        "all_selected_Java_bodies_executed":False,
        "original_game_client_executed":False,
        "remaining_original_parent_JVM_methods_unverified_here":12,
        "entire_original_v309_client_compiles":False,
        "source_redistribution_authorized":False,
    }

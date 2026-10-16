"""R212 — actually compile ORIGINAL-DECOMPILED Class179 method bodies.

Original v309 rs/n/c/ap.h/i/j method Code can be recovered without
duplicating or inventing their implementations: the exact existing
Class179.java source contains corresponding method1966/method3153/method236
bodies. Recompile those unchanged bodies with separately declared ONLY
support signatures, then prove EVERY JVM instruction and offset after an
explicit field/member/owner identity map.

This is a THREE-METHOD PARTIAL SOURCE PROOF. The temporary partial Java
class does not reproduce the original full rs/n/c/ap class ABI, 14 methods,
superclass or runtime. No synthetic helpers are accepted as recovered code.
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
from .source_method_parity import _normalized_instructions

ORIGINAL_OWNER="rs/n/c/ap"
READABLE_OWNER="rs/interfaces/widgets/Class179"
JAR_SHA256=CANONICAL_V309
ORIGINAL_CLASS_SHA256=(
    "b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
)
PRIVATE_SOURCE_TREE_SHA256=(
    "cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
)
SOURCE_PATH=(
    "recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
)
SOURCE_SHA256=(
    "8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
)
THREE_METHODS=(
    ("h","method1966",10,
     "3dfd9ee3a6df082885818958cba7eeaa4844061a7ae736fe8370c9ca8b2c5219"),
    ("i","method3153",62,
     "a1c398fa3ed9b467d7303f81595425658574dc97288102ecb9fd536c04459ad6"),
    ("j","method236",19,
     "b6f0954b935b9f6de4f774de664fc5fc399e18c38a7eac49a92af19dde47165d"),
)
EXPECTED_TOTAL_ORIGINAL_JVM_INSTRUCTIONS=91

MEMBER_ALIASES={
    # original static widget class
    ("rs/n/c/ap","d","Z"):
        ("rs/interfaces/widgets/Class179","field3646","Z"),
    ("rs/n/c/ap","g","[I"):
        ("rs/interfaces/widgets/Class179","field3643","[I"),
    ("rs/n/c/ap","bI","[I"):
        ("rs/interfaces/widgets/Class179","field3644","[I"),
    # original interface/widget storage
    ("rs/n/e","H","[Lrs/n/e;"):
        ("rs/interfaces/WidgetComponent","widgetTable",
         "[Lrs/interfaces/WidgetComponent;"),
    ("rs/n/e","am","[I"):
        ("rs/interfaces/WidgetComponent","childX","[I"),
    ("rs/n/e","bc","[I"):
        ("rs/interfaces/WidgetComponent","childY","[I"),
    # original method/call identities
    ("rs/n/c/ap","j","()V"):
        ("rs/interfaces/widgets/Class179","method236","()V"),
    ("rs/n/c/ap","i","()V"):
        ("rs/interfaces/widgets/Class179","method3153","()V"),
    ("rs/f/a","d","()V"):
        ("rs/Configuration","saveSettings","()V"),
    ("rs/n/c/ap$c","values","()[Lrs/n/c/ap$c;"):
        ("rs/interfaces/widgets/Class178","values",
         "()[Lrs/interfaces/widgets/Class178;"),
    ("rs/n/c/ap","a","(Lrs/n/c/ap$c;)V"):
        ("rs/interfaces/widgets/Class179","method2689",
         "(Lrs/interfaces/widgets/Class178;)V"),
}
DECLARATION_ONLY_SUPPORT={
    "rs/interfaces/widgets/Class178.java":(
        "package rs.interfaces.widgets;\n"
        "public enum Class178 {ONE,TWO,THREE;}\n"
    ),
    "rs/interfaces/WidgetComponent.java":(
        "package rs.interfaces;\n"
        "public class WidgetComponent {\n"
        "  public static WidgetComponent[] widgetTable;\n"
        "  public int[] childX,childY;\n"
        "}\n"
    ),
    "rs/Configuration.java":(
        "package rs;\n"
        "public class Configuration {\n"
        "  public static void saveSettings(){}\n"
        "}\n"
    ),
}


class R212ReadableSpellbookCodeError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R212ReadableSpellbookCodeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda:stream.read(1048576),b""):
            h.update(part)
    return h.hexdigest()


def extract_original_donor_method(source,method):
    """Read exact donor source method body with fail-closed brace matching.

    The three pinned methods contain no unbalanced braces in Java string or
    comment literals. Whole-file SHA and method-body SHA are both required
    for acceptance. No AST mutation, rewriting or decompilation occurs.
    """
    matches=list(re.finditer(
        r"(?m)^\s*public\s+static\s+void\s+"+
            re.escape(method)+r"\s*\(\s*\)\s*\{",
        source))
    need(len(matches)==1,
         "R212_PINNED_SOURCE_METHOD_SIGNATURE_NOT_UNIQUE")
    start=matches[0].start()
    begin=source.index("{",matches[0].start())
    depth=1
    end=begin+1
    while depth and end<len(source):
        if source[end]=="{":
            depth+=1
        elif source[end]=="}":
            depth-=1
        end+=1
    need(depth==0 and end-start<=3000,
         "R212_UNBOUNDED_READABLE_SOURCE_METHOD")
    return source[start:end]


def map_instruction_symbolic(row, *, aliases=MEMBER_ALIASES):
    result=dict(row)
    opcode=result.get("opcode")
    if opcode in ("0xb2","0xb3","0xb4","0xb5",
                  "0xb6","0xb7","0xb8","0xb9"):
        key=(result.get("owner"),result.get("name"),
             result.get("descriptor"))
        if key in aliases:
            owner,name,descriptor=aliases[key]
            result["owner"]=owner
            result["name"]=name
            result["descriptor"]=descriptor
        elif result.get("owner") not in (
                "java/util/Arrays",):
            raise R212ReadableSpellbookCodeError(
                "R212_ORIGINAL_UNMAPPED_SYMBOLIC_REFERENCE")
    return result


def _method(profile,name):
    matches=[m for m in profile["methods"]
             if (m["name"],m["descriptor"])==(name,"()V")]
    need(len(matches)==1 and matches[0]["code_length"] is not None,
         "R212_SELECTED_METHOD_JVM_CODE_MISSING")
    return matches[0]


def audit_three_readable_method_code(
        original_class,candidate_class, *,
        method_pairs=THREE_METHODS,
        member_aliases=MEMBER_ALIASES,
        expected_total=EXPECTED_TOTAL_ORIGINAL_JVM_INSTRUCTIONS):
    """Compare full Code (not just opcode count) under only listed aliases."""
    old=profile_class_field_accesses(original_class)
    new=profile_class_field_accesses(candidate_class)
    need(len(method_pairs)==3 and
         len({p[0] for p in method_pairs})==3 and
         len({p[1] for p in method_pairs})==3,
         "R212_THREE_UNIQUE_METHOD_IDENTITIES_REQUIRED")
    compared=0
    checks=[]
    for original,readable,nops,_ in method_pairs:
        a=_method(old,original)
        b=_method(new,readable)
        need(a["access"]==b["access"] and
             a["code_length"]==b["code_length"] and
             a["max_stack"]==b["max_stack"] and
             a["max_locals"]==b["max_locals"] and
             a["exception_handlers"]==b["exception_handlers"] and
             a["stackmap_table_present"]==
                 b["stackmap_table_present"],
             "R212_ORIGINAL_SELECTED_CODE_LIMITS_OR_HANDLER_DIFF")
        before=_normalized_instructions(old,a)
        after=_normalized_instructions(new,b)
        converted=[
            map_instruction_symbolic(x,aliases=member_aliases)
            for x in before]
        need(len(before)==nops and converted==after,
             "R212_ORIGINAL_READABLE_METHOD_JVM_CODE_NOT_IDENTICAL")
        compared+=len(before)
        checks.append({
            "original":original,
            "readable":readable,
            "full_original_method_instructions_matched":nops,
            "bytecode_offsets_and_branches_equal":True,
        })
    need(compared==expected_total,
         "R212_PINNED_THREE_METHOD_INSTRUCTION_COUNT_DRIFT")
    return {
        "schema_version":1,
        "kind":"v309_existing_Class179_three_method_original_semantic_code_r212",
        "selected_original_methods":3,
        "matched_original_jvm_instructions":compared,
        "method_audits":checks,
        "all_original_method_code_under_named_aliases_equal":True,
        "unselected_spellbook_parent_methods_code_verified":False,
        "full_original_spellbook_parent_abi_verified":False,
        "source_only_java9":True,
        "original_client_game_code_executed":False,
        "full_client_compiles":False,
    }


def verify_pinned_three_original_readable_spellbook_methods(
        original_jar,private_recovered_source_zip, *,
        original_jar_sha256=JAR_SHA256,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        source_tree_sha256=PRIVATE_SOURCE_TREE_SHA256,
        donor_java_sha256=SOURCE_SHA256):
    """Source-only build of 3 ACTUAL donor methods with fake declarations.

    The real Class179 code is extracted byte-for-byte as-is. The remaining
    11 original methods, class superclass and full field set are NOT
    compiled, so no such class-level claim is made.
    """
    need(file_digest(original_jar)==original_jar_sha256
         and file_digest(private_recovered_source_zip)==source_tree_sha256,
         "R212_PINNED_ORIGINAL_JAR_AND_PRIVATE_SOURCE_ZIP_REQUIRED")
    with ZipFile(original_jar) as jar:
        path=ORIGINAL_OWNER+".class"
        need(jar.namelist().count(path)==1,
             "R212_ORIGINAL_CLASS_NOT_UNIQUE")
        original=jar.read(path)
    need(digest(original)==original_class_sha256,
         "R212_ORIGINAL_CLASSFILE_SHA_CHANGED")
    with ZipFile(private_recovered_source_zip) as sources:
        need(sources.namelist().count(SOURCE_PATH)==1,
             "R212_PINNED_DONOR_JAVA_NOT_UNIQUE")
        source=sources.read(SOURCE_PATH)
    need(digest(source)==donor_java_sha256,
         "R212_PINNED_DONOR_JAVA_SHA_CHANGED")
    content=source.decode("utf-8")
    pieces=[]
    for original,readable,expected,sha in THREE_METHODS:
        body=extract_original_donor_method(content,readable)
        need(digest(body.encode("utf-8"))==sha,
             "R212_EXACT_REAL_DONOR_METHOD_BODY_SHA_CHANGED")
        pieces.append(body)
    partial=(
        "package rs.interfaces.widgets;\n"
        "import java.util.Arrays;\n"
        "import rs.interfaces.WidgetComponent;\n"
        "import rs.Configuration;\n"
        "public class Class179 {\n"
        "  private static int[] field3643,field3644;\n"
        "  public static boolean field3646;\n"
        +"\n".join(pieces)+"\n"
        "  public static void method2689(Class178 mode){}\n"
        "}\n"
    )
    javac=shutil.which("javac")
    need(javac is not None,"R212_JDK9_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r212-source-") as tmp:
        root=Path(tmp)
        sources={READABLE_OWNER+".java":partial,
                 **DECLARATION_ONLY_SUPPORT}
        paths=[]
        for rel,body in sources.items():
            target=root/"src"/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(body,encoding="utf-8")
            paths.append(str(target))
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            process=subprocess.run(
                [javac,"--release","9","-g:none",
                 "-proc:none","-implicit:none",
                 "-classpath",str(empty),"-sourcepath",str(empty),
                 "-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R212ReadableSpellbookCodeError(
                "R212_READABLE_SOURCE_JAVAC_ABORTED") from exc
        emitted={p.relative_to(out).as_posix()
                 for p in out.rglob("*.class")}
        required={x[:-5]+".class" for x in sources}
        need(process.returncode==0 and emitted==required,
             "R212_ORIGINAL_DECOMPILED_PARTIAL_SOURCE_ONLY_BUILD_FAILED")
        compiled=(out/(READABLE_OWNER+".class")).read_bytes()
    report=audit_three_readable_method_code(original,compiled)
    need(file_digest(original_jar)==original_jar_sha256
         and file_digest(private_recovered_source_zip)==source_tree_sha256,
         "R212_ORIGINAL_OR_READABLE_JAVA_SOURCE_CHANGED_DURING_REPLAY")
    return {
        **report,
        "original_class_sha256":original_class_sha256,
        "real_existing_readable_class179_source_sha256":donor_java_sha256,
        "compiler_only_support_declarations":3,
        "full_source_owner_java_rebuilt":False,
        "fake_support_classes_accepted_as_original":False,
        "private_original_source_published":False,
    }

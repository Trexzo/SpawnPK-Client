"""R222 — real readable Widget + three real enum owners in ONE Java9 build.

R221 built one complete Class179 with eleven NONORIGINAL compiler-only
dependency declarations. This verifier replaces FOUR of those owners with
the EXACT SHA-pinned preexisting readable Java files, *without* changing
any accepted Class179 source or code. The remaining seven declarations
stay explicitly separate; 7 is not zero and not a full-client source build.

Private inputs: original client JAR, R203 recovered-source ZIP, R220-R221
unified private evidence ZIP. No private Java/JAR is committed to GitHub.
"""
from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .private_v309_unified_spellbook_class_r221 import (
    verify_private_unified_class,
)
from .private_v309_readable_widget_source_parity_r210 import (
    audit_readable_widget_classfiles,
)

ORIGINAL_JAR_SHA256="ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
ORIGINAL_WIDGET_SHA256="65b1517e3630da9dcc79b8e53c28fa1622c000ff0825b33880ca3262d4d2b2a0"
SOURCE_ZIP_SHA256="cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
R221_EVIDENCE_ZIP_SHA256="4e39cdbf11e2ff5191778228a30da0208538f1cae93ff0730ea97dbd3d289658"
R221_TEMPLATE_SHA256="7044c78ee98639c59a1fc5085b8e087cf6cf6ac2c9e550a9f532969c617ac2df"
R221_NORMALIZED_JAVA_SHA256="e274c0f12c36baeaa129920d5e259897a292b65a1138fc386f1413f00ff60406"
R221_CLASS_SHA256="b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e"
R222_REAL_WIDGET_CLASS_SHA256="80764ebe0d17d04f3b040cf0c0319c5397994fd6ef662cad04647bea752752e6"
JAVA_ROOT="recovered-source/v309/src/"
SOURCE_ROOT="rs/interfaces/widgets/"
REPLACEMENTS={
    "Widget":"b3f77f45537ce65772e066f4bd27b9c3df99ca767479b5704927fb51df60985a",
    "Class176":"316e4d1ca79fb0b773c160370c0899c13bc8e1ffe888c6663537cb4f5181bcc2",
    "Class177":"b9e52f622c580e87a21e8dfecba7aee2e9764bf53341bdc3042c86f9adbdddf6",
    "Class178":"ac73c8215e875b5d605ba76920b18c59297197f77eeb5d0dc3cfbad6aaf6be35",
}
ORIGINAL_SUPPORT_OWNERS=11
REMAINING_COMPILER_ONLY_OWNERS=7


class R222DependencyClosureError(ValueError):
    pass


def need(ok,why):
    if not ok:
        raise R222DependencyClosureError(why)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda:f.read(1048576),b""):
            h.update(data)
    return h.hexdigest()


def read_unique(z,name,limit):
    need(z.namelist().count(name)==1,
         "R222_PINNED_PRIVATE_ZIP_ENTRY_NOT_UNIQUE_"+name)
    meta=z.getinfo(name)
    need(0<meta.file_size<=limit and meta.compress_size<=limit,
         "R222_PRIVATE_ZIP_ENTRY_SIZE_LIMIT_"+name)
    return z.read(name)


def read_fake_template_ast(script):
    """Literal-only extraction. Never execute a script from a private ZIP."""
    tree=ast.parse(script.decode("utf-8"))
    nodes=[
        n.value for n in tree.body
        if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=="H" for t in n.targets)
    ]
    need(len(nodes)==1,"R222_EXACT_ONE_JAVA_HELPER_TEMPLATE_LITERAL_REQUIRED")
    try:
        value=ast.literal_eval(nodes[0])
    except (ValueError,TypeError,SyntaxError,
            RecursionError,MemoryError) as exc:
        raise R222DependencyClosureError(
            "R222_HELPER_TEMPLATE_MUST_BE_LITERAL_DATA") from exc
    need(type(value) is dict and len(value)==ORIGINAL_SUPPORT_OWNERS and
         all(type(k) is str and type(v) is str and
             k.endswith(".java") and len(v)<50000
             for k,v in value.items()),
         "R222_ELEVEN_DECLARATION_ONLY_OWNERS_REQUIRED")
    return value


def integrate_actual_readable_dependencies(template,actual_sources):
    """No edit to actual source; move fake static builder API into fake parent.

    Previously compiler-only Widget had 19 fake static builder declarations.
    Replacing it with REAL Widget.java means that same temporary API must
    be carried by the still-fake WidgetComponent.java base. Those static
    declarations remain temporary, NONORIGINAL and are NOT counted as real.
    """
    need(type(template) is dict and len(template)==ORIGINAL_SUPPORT_OWNERS
         and set(actual_sources)==set(REPLACEMENTS),
         "R222_EXACT_SEVEN_FAKE_FOUR_REAL_OWNER_PARTITION")
    old_widget=template["rs/interfaces/widgets/Widget.java"]
    pos=old_widget.find(
        " public static WidgetComponent createPanelWidget(")
    need(pos>0 and old_widget.endswith(" }"),
         "R222_ORIGINAL_COMPILER_SIGNATURE_TEMPLATE_CHANGED")
    static_builders=old_widget[pos:old_widget.rfind(" }")]
    need(static_builders.count("public static ")==19,
         "R222_NINETEEN_TEMPORARY_BUILDERS_REQUIRED")
    parent_key="rs/interfaces/WidgetComponent.java"
    parent=template[parent_key]
    need(parent.count("import rs.graphics.Sprite;")==1 and
         parent.endswith(" }"),
         "R222_FAKE_PARENT_DECLARATION_TEMPLATE_CHANGED")
    parent=parent.replace(
        "import rs.graphics.Sprite;",
        "import rs.graphics.Sprite; import rs.graphics.HitsplatFont;",
    )
    end=parent.rfind(" }")
    parent=parent[:end]+static_builders+"\n"+parent[end:]
    result=dict(template)
    result[parent_key]=parent
    for owner,text in actual_sources.items():
        key=f"{SOURCE_ROOT}{owner}.java"
        need(key in result and digest(text.encode("utf-8"))==
             REPLACEMENTS[owner],
             "R222_REAL_JAVA_SOURCE_PIN_OR_OWNER_CHANGED_"+owner)
        result[key]=text
    need(len(result)==ORIGINAL_SUPPORT_OWNERS and
         all(len(v)>0 for v in result.values()),
         "R222_SOURCE_CLASS_COUNT_CHANGED")
    return result


def verify_private_real_widget_and_enums(original_jar,source_zip,
                                         r221_evidence_zip):
    need(file_sha(original_jar)==ORIGINAL_JAR_SHA256 and
         file_sha(source_zip)==SOURCE_ZIP_SHA256 and
         file_sha(r221_evidence_zip)==R221_EVIDENCE_ZIP_SHA256,
         "R222_ALL_THREE_PRIVATE_INPUT_ZIP_JAR_SHA256_REQUIRED")
    with ZipFile(original_jar) as jar:
        base=read_unique(jar,"rs/n/c.class",30000)
    need(digest(base)==ORIGINAL_WIDGET_SHA256,
         "R222_ORIGINAL_WIDGET_JVM_BINARY_SHA256_CHANGED")
    with ZipFile(source_zip) as tree:
        reals={}
        for owner,expected in REPLACEMENTS.items():
            data=read_unique(tree,JAVA_ROOT+SOURCE_ROOT+owner+".java",
                             100000)
            need(digest(data)==expected,
                 "R222_PINNED_READABLE_SOURCE_CHANGED_"+owner)
            reals[owner]=data.decode("utf-8")
    with ZipFile(r221_evidence_zip) as zip_:
        script=read_unique(zip_,
            "scripts/source-only-recompile-unified-class.py",25000)
        normalized=read_unique(zip_,
            "private/normalized-readable-Class179.java",100000)
        before=read_unique(zip_,
            "private/compiled-readable-Class179.class",100000)
    need(digest(script)==R221_TEMPLATE_SHA256 and
         digest(normalized)==R221_NORMALIZED_JAVA_SHA256 and
         digest(before)==R221_CLASS_SHA256,
         "R222_R221_PROVEN_SOURCE_TEMPLATE_OR_CLASS_CHANGED")
    candidate=integrate_actual_readable_dependencies(
        read_fake_template_ast(script),reals)
    candidate["rs/interfaces/widgets/Class179.java"]=normalized.decode("utf-8")
    javac=shutil.which("javac")
    need(javac is not None,"R222_JDK9_JAVAC_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r222-real-dependencies-") as td:
        root=Path(td)
        src=root/"src";out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        paths=[]
        for rel,java in candidate.items():
            dest=src/rel
            need(not dest.exists(),"R222_DUPLICATE_COMPILE_INPUT")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(java,encoding="utf-8")
            paths.append(str(dest))
        env=os.environ.copy()
        for name in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                     "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(name,None)
        try:
            proc=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*paths],
                capture_output=True,stdin=subprocess.DEVNULL,
                timeout=120,check=False,cwd=root,env=env)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R222DependencyClosureError(
                "R222_JAVA9_SOURCE_ONLY_COMPILATION_ABORTED") from exc
        expected={x[:-5]+".class" for x in candidate}
        emitted={x.relative_to(out).as_posix()
                 for x in out.rglob("*.class")}
        need(proc.returncode==0 and emitted==expected,
             "R222_REAL_FOUR_DEPENDENCY_SOURCE_BUILD_FAILED")
        target=(out/"rs/interfaces/widgets/Class179.class").read_bytes()
        compiled_widget=(out/"rs/interfaces/widgets/Widget.class").read_bytes()
    need(target==before and digest(target)==R221_CLASS_SHA256,
         "R222_REAL_DEPENDENCIES_CHANGED_R221_ACCEPTED_CLASS_BYTES")
    need(digest(compiled_widget)==R222_REAL_WIDGET_CLASS_SHA256,
         "R222_ORIGINAL_READABLE_WIDGET_JAVA_COMPILER_OUTPUT_CHANGED")
    widget_proof=audit_readable_widget_classfiles(
        base,compiled_widget,
        expected_original_sha256=ORIGINAL_WIDGET_SHA256)
    need(widget_proof["matched_original_decoded_jvm_instructions"]
         if "matched_original_decoded_jvm_instructions" in widget_proof
         else widget_proof["matched_original_decoded_jvm_instructions"]==11,
         "R222_REAL_WIDGET_ORIGINAL_JVM_PARITY_NOT_PROVEN")
    # The one emitted target's bytes equal the R221 independently
    # original-JAR verified candidate, so all 4314 method Code bytes and
    # branch+alias hashes are unchanged. We still replay R221's verifier.
    with tempfile.TemporaryDirectory(prefix="spk-r222-replay-") as tmp:
        java=Path(tmp)/"Class179.java"
        output=Path(tmp)/"Class179.class"
        java.write_bytes(normalized)
        output.write_bytes(target)
        class_proof=verify_private_unified_class(original_jar,java,output)
    need(class_proof["verified_original_JVM_methods"]==14
         and class_proof["verified_original_JVM_instructions"]==4314,
         "R222_R221_PRIVATE_ORIGINAL_CLASS_REPLAY_FAILED")
    return {
        "schema_version":1,
        "kind":"v309_real_readable_widget_and_three_enum_source_closure_r222",
        "single_real_readable_spellbook_java_class_compiled":True,
        "full_14_method_original_JVM_code_preserved":True,
        "original_JVM_instructions_preserved":4314,
        "source_only_real_readable_dependency_owners":sorted(REPLACEMENTS),
        "original_semantic_readable_widget_methods_verified":6,
        "original_semantic_readable_widget_instructions_verified":11,
        "compiler_only_dependency_count_before":ORIGINAL_SUPPORT_OWNERS,
        "compiler_only_dependency_count_after":REMAINING_COMPILER_ONLY_OWNERS,
        "emitted_whole_spellbook_class_sha256":R221_CLASS_SHA256,
        "temporary_helper_builder_declarations":19,
        "client_runtime_executed":False,
        "whole_client_compiled":False,
        "original_binary_class_byte_identity_claimed":False,
        "source_redistribution_authorized":False,
    }

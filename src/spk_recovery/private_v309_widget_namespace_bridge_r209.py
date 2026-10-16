"""R209 — original v309 widget CLASS-vs-PACKAGE collision Java9 gate.

JVM accepts rs/n.class, rs/n/c.class and rs/n/c/ap.class simultaneously;
javac rejects rs.n.c as both a class and package. Use the preexisting,
deterministic R125 mapping to choose legal type aliases and compile a
synthetic counterpart. Never claim that the renamed source .class is the
byte-identical original, or write original-derived Java to public CI.

Two independent proofs:
  1) private pinned v309 JAR/classfile hierarchy + full R125 remap plan;
  2) hosted JDK9 javac negative-original / positive-legalized *invented*
     class/package experiment with exact emitted-owner and superclass audit.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import (
    CANONICAL_V309,
    original_class_inventory,
    plan_client_namespaces,
)

ORIGINAL_WIDGET_BASE = "rs/n/c"
ORIGINAL_SPELLBOOK_CHILD = "rs/n/c/ap"
ORIGINAL_PARENT = "rs/n"
EXPECTED_BASE_SHA256 = (
    "65b1517e3630da9dcc79b8e53c28fa1622c000ff0825b33880ca3262d4d2b2a0"
)
EXPECTED_CHILD_SHA256 = (
    "b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
)


class R209NamespaceBridgeError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise R209NamespaceBridgeError(message)


def _hex(raw):
    return hashlib.sha256(raw).hexdigest()


def _mapped_names(plan, names):
    remaps=plan.get("remaps")
    need(plan.get("identifiers_included") is True and
         isinstance(remaps, list),
         "R209_PRIVATE_R125_CLASS_IDENTITIES_REQUIRED")
    mapping={}
    for item in remaps:
        old=item["old_internal_name"]
        new=item["new_internal_name"]
        need(old not in mapping and old!=new,
             "R209_DUPLICATED_OR_NOOP_R125_REMAP")
        mapping[old]=new
    return {name:mapping.get(name,name) for name in names}


def inspect_widget_legalizer(original_classes, *,
                             planner=plan_client_namespaces,
                             expected_base=ORIGINAL_WIDGET_BASE,
                             expected_child=ORIGINAL_SPELLBOOK_CHILD):
    """Prove target mapping is safe without claiming source is rewritten."""
    need(isinstance(original_classes,set) and
         {expected_base,expected_child}.issubset(original_classes) and
         any(x.startswith(expected_base+"/")
             for x in original_classes),
         "R209_REAL_CLASS_AND_PACKAGE_COLLISION_REQUIRED")
    report=planner(original_classes,include_identifiers=True)
    targets=_mapped_names(report,original_classes)
    base=targets[expected_base]
    child=targets[expected_child]
    need(base!=expected_base and
         base not in original_classes and
         child!=base and
         report["no_type_package_shadow_after_mapping"] is True and
         report["mapped_paths_unique_after_casefold"] is True and
         report["mapped_package_directories_unique_after_casefold"] is True,
         "R209_WIDGET_BASE_ALIAS_OR_GLOBAL_COLLISIONS_UNRESOLVED")
    need(not any(cls.startswith(base+"/") for cls in targets.values()),
         "R209_MAPPED_BASE_SHADOWS_ANOTHER_PACKAGE")
    need(child.endswith("/"+expected_child.rsplit("/",1)[-1]) or
         child!=expected_child,
         "R209_ORIGINAL_CHILD_LOST_FROM_LEGALIZER")
    return {
        "schema_version":1,
        "kind":"v309_widget_class_package_java_namespace_bridge_r209",
        "input_original_class_count":len(original_classes),
        "original_base_owner":expected_base,
        "original_child_owner":expected_child,
        "legal_java_base_owner":base,
        "legal_java_child_owner":child,
        "private_whole_client_mapping_sha256":
            report["private_mapping_sha256"],
        "class_package_shadow_resolved":True,
        "java_and_casefold_safe":True,
        "source_java_rewritten":False,
        "original_binary_class_name_unchanged":False,
        "renamed_classfile_bytecode_parity_proven":False,
        "full_original_client_compiles":False,
    }


def verify_private_v309_widget_namespace(
        original_jar, *,
        original_sha256=CANONICAL_V309,
        base_sha256=EXPECTED_BASE_SHA256,
        child_sha256=EXPECTED_CHILD_SHA256):
    """Real private binary hierarchy with pinned full-JAR and class hashes."""
    names=original_class_inventory(original_jar,original_sha256)
    with ZipFile(original_jar) as archive:
        expected={
            ORIGINAL_WIDGET_BASE:base_sha256,
            ORIGINAL_SPELLBOOK_CHILD:child_sha256,
        }
        parsed={}
        for owner,digest in expected.items():
            path=owner+".class"
            need(archive.namelist().count(path)==1,
                 "R209_ORIGINAL_CLASS_ENTRY_NOT_UNIQUE")
            raw=archive.read(path)
            need(_hex(raw)==digest,"R209_ORIGINAL_WIDGET_CLASS_SHA_CHANGED")
            parsed[owner]=parse_class(raw)
    need(parsed[ORIGINAL_SPELLBOOK_CHILD].super_name==
         ORIGINAL_WIDGET_BASE and
         parsed[ORIGINAL_WIDGET_BASE].name==ORIGINAL_WIDGET_BASE and
         parsed[ORIGINAL_SPELLBOOK_CHILD].name==
         ORIGINAL_SPELLBOOK_CHILD,
         "R209_ORIGINAL_CHILD_TO_BASE_SUPERCLASS_EDGE_CHANGED")
    report=inspect_widget_legalizer(names)
    report.update({
        "original_full_jar_sha256":original_sha256,
        "original_base_class_sha256":base_sha256,
        "original_child_class_sha256":child_sha256,
        "original_child_superclass_edge_sha_pinned":True,
        "original_source_compiled":False,
        "original_game_code_executed":False,
    })
    return report


def compile_synthetic_widget_alias_pair(*, original_base="toy/widget/Base",
                                        original_child="toy/widget/Base/Child"):
    """JDK9 build proves collision failure and legal alias success.

    Invented source is not associated with any original game Java. The
    check does not run any class. The generated classes are disposable.
    """
    parts=original_base.split("/")
    name=parts[-1]
    package="/".join(parts[:-1])
    need(len(parts)>=3 and
         original_child.startswith(original_base+"/") and
         all(p.isidentifier() for p in original_child.split("/")) and
         all(p.isidentifier() for p in parts) and
         name[0].isupper() and
         shutil.which("javac") is not None,
         "R209_SIMPLE_INVENTED_JAVAC_FIXTURE_NAMES_REQUIRED")
    report=inspect_widget_legalizer(
        {original_base,original_child},
        expected_base=original_base,expected_child=original_child)
    new_base=report["legal_java_base_owner"]
    new_child=report["legal_java_child_owner"]
    need(new_child==original_child and new_base!=original_base,
         "R209_SYNTHETIC_MAPPING_UNEXPECTED_SUBTREE_RENAME")
    pkg=package.replace("/",".")
    child_package=original_base.replace("/",".")
    first=(
        "package "+pkg+";\n"
        "public abstract class "+name+" {\n"
        "  public final int points(){return 7;}\n"
        "}\n"
    )
    old_child=(
        "package "+child_package+";\n"
        "public final class "+original_child.rsplit("/",1)[-1]+
        " extends "+original_base.replace("/",".")+" {\n"
        "  public int score(){return points()+5;}\n"
        "}\n"
    )
    legalized_base=first.replace(
        "class "+name+" {",
        "class "+new_base.rsplit("/",1)[-1]+" {")
    legalized_child=old_child.replace(
        "extends "+original_base.replace("/","."),
        "extends "+new_base.replace("/","."))
    with tempfile.TemporaryDirectory(prefix="spk-r209-jdk9-") as tmp:
        root=Path(tmp)
        empty=root/"empty"
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        def compiled(sources,dir_name):
            src=root/(dir_name+"-src")
            out=root/(dir_name+"-classes")
            out.mkdir()
            paths=[]
            for owner,body in sources:
                filename=src/(owner+".java")
                filename.parent.mkdir(parents=True,exist_ok=True)
                filename.write_text(body,encoding="utf-8")
                paths.append(str(filename))
            p=subprocess.run(
                ["javac","--release","9","-g:none",
                 "-proc:none","-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=60,check=False)
            return p,out
        before,_=compiled([
            (original_base,first),
            (original_child,old_child)],"illegal")
        need(before.returncode!=0,
             "R209_ILLEGAL_UNREWRITTEN_JAVA_CLASS_PACKAGE_COMPILED")
        after,out=compiled([
            (new_base,legalized_base),
            (new_child,legalized_child)],"legal")
        emitted={p.relative_to(out).as_posix() for p in out.rglob("*.class")}
        need(after.returncode==0 and
             emitted=={new_base+".class",new_child+".class"},
             "R209_JDK9_LEGALIZED_SYNTHETIC_PAIR_FAILED_TO_BUILD")
        base_bytes=(out/(new_base+".class")).read_bytes()
        child_bytes=(out/(new_child+".class")).read_bytes()
    rebuilt_base=parse_class(base_bytes)
    rebuilt_child=parse_class(child_bytes)
    need(rebuilt_base.name==new_base and
         rebuilt_child.name==new_child and
         rebuilt_child.super_name==new_base and
         rebuilt_base.major==rebuilt_child.major==53,
         "R209_COMPILED_JVM_SUPERCLASS_NOT_LEGALIZED_ALIAS")
    return {
        **report,
        "original_name_synthetic_javac_failed":True,
        "legalized_name_synthetic_javac_passed":True,
        "legalized_compiled_child_extends_alias":True,
        "independently_compiled_java_major":53,
        "original_proprietary_source_compiled":False,
        "original_v309_binary_byte_identity_proven":False,
        "original_game_code_executed":False,
    }

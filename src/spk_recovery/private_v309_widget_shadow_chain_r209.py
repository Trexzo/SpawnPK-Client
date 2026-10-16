"""R209 additional class/package-shadow chain source compilation proof.

Invented class identities model three REAL v309 namespace depth levels:
  original type rs/n, original type rs/n/c, child owner rs/n/c/ap.
This tests source name legality only. In the real client rs/n/c extends
rs/n/e, NOT rs/n; the invented inheritance chain is deliberately unrelated
and must never be misreported as an original-game class hierarchy.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import plan_client_namespaces
from .private_v309_widget_namespace_bridge_r209 import (
    R209NamespaceBridgeError,
    inspect_widget_legalizer,
)


def need(ok,why):
    if not ok:
        raise R209NamespaceBridgeError(why)


def compile_three_depth_synthetic_chain():
    """Require legal compiler output for two simultaneous JVM type shadows."""
    owners=("toy/Node","toy/Node/Base","toy/Node/Base/Child")
    names=set(owners)
    full=plan_client_namespaces(names,include_identifiers=True)
    remap={x["old_internal_name"]:x["new_internal_name"]
           for x in full["remaps"]}
    after={name:remap.get(name,name) for name in owners}
    need(after[owners[0]]!=owners[0] and
         after[owners[1]]!=owners[1] and
         after[owners[2]]==owners[2] and
         len(set(after.values()))==3 and
         full["no_type_package_shadow_after_mapping"],
         "R209_TWO_NESTED_CLASS_PACKAGE_SHADOWS_NOT_REMAPPED")
    audit=inspect_widget_legalizer(
        names,expected_base=owners[1],expected_child=owners[2])
    need(audit["legal_java_base_owner"]==after[owners[1]],
         "R209_MULTIPLE_SHADOW_PLANNER_NOT_STABLE")

    def source(owner,base=None):
        package,_,name=owner.rpartition("/")
        text="package "+package.replace("/",".")+";\n"
        text+="public class "+name
        if base:
            text+=" extends "+base.replace("/",".")
        return text+" {public int identity(){return 7;}}\n"

    original=[
        (owners[0],source(owners[0])),
        (owners[1],source(owners[1],owners[0])),
        (owners[2],source(owners[2],owners[1])),
    ]
    renamed=[
        (after[owners[0]],source(after[owners[0]])),
        (after[owners[1]],source(after[owners[1]],after[owners[0]])),
        (after[owners[2]],source(after[owners[2]],after[owners[1]])),
    ]
    java=shutil.which("javac")
    need(java is not None,"R209_JDK9_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r209-shadow-chain-") as tmp:
        root=Path(tmp)
        empty=root/"empty"
        empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        def run(inputs,label):
            src=root/(label+"-src")
            out=root/(label+"-out")
            out.mkdir()
            paths=[]
            for owner,body in inputs:
                dest=src/(owner+".java")
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(body,encoding="utf-8")
                paths.append(str(dest))
            proc=subprocess.run(
                [java,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=75,check=False)
            return proc,out
        broken,_=run(original,"illegal")
        need(broken.returncode!=0,
             "R209_ILLEGAL_THREE_DEPTH_CLASS_PACKAGE_SOURCES_BUILT")
        built,out=run(renamed,"legal")
        emitted={f.relative_to(out).as_posix() for f in out.rglob("*.class")}
        need(built.returncode==0 and
             emitted=={x+".class" for x in after.values()},
             "R209_LEGALIZED_THREE_DEPTH_JAVAC_OR_OUTPUT_FAILED")
        classes={
            name:parse_class((out/(name+".class")).read_bytes())
            for name in after.values()
        }
    need(classes[after[owners[0]]].super_name=="java/lang/Object"
         and classes[after[owners[1]]].super_name==after[owners[0]]
         and classes[after[owners[2]]].super_name==after[owners[1]]
         and all(c.major==53 for c in classes.values()),
         "R209_THREE_DEPTH_JVM_SUPERCLASS_LINKAGE_INCORRECT")
    return {
        "schema_version":1,
        "kind":"invented_java9_three_depth_class_package_shadow_r209",
        "original_type_names":list(owners),
        "legal_type_names":[after[n] for n in owners],
        "original_source_compilation_failed":True,
        "source_only_legalized_java9_compilation_passed":True,
        "all_three_emitted_classfile_owners_and_supers_verified":True,
        "two_simultaneous_class_package_shadows_eliminated":True,
        "original_game_class_hierarchy_reproduced":False,
        "original_client_source_compiled":False,
        "original_client_game_code_executed":False,
    }

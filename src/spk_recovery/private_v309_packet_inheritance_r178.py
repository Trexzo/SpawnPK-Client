"""R178: independently compile partial Packet with both original Java parents.

The two parent classes MUST first pass R177's whole-class source proof.
Then the Packet child is recompiled together with them, without ANY
original game binary classpath. Only the 61 independently selected
Packet Code method bodies are verified; other Packet members are not.
"""
import hashlib
import os
from pathlib import Path
from shutil import which
from subprocess import run
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from .private_client_source_ast_census_r126 import sha_file,source_members
from .private_v309_packet_parent_source_r177 import (
    verify_original_packet_parents, OWNERS)
from .private_v309_packet_61_methods_r176 import verify_packet_61, ADDED
from .private_v309_packet_49_methods_r175 import NEW as SIX
from .private_v309_packet_43_methods_r174 import READERS
from .private_v309_packet_34_methods_r173 import WRITERS
from .private_v309_packet_22_methods_r172 import EXTRA
from .bytecode_profile import profile_class_field_accesses
from .classfile import parse_class
from .private_v309_matrix_source_method_parity_r150 import _strict_inspections


def verify_packet_with_original_parents(
        jar, partial_packet_source, parent_sources, *,
        original_sha256,packet_source_sha256,parent_source_sha256,
        class_sha256,parent_class_shas,
        owner="rs/x/e",prior_six_kwargs=None,
        prior_49_count=1183,new_count=311,
        parent_instruction_count=48,
        previous_22_count=309,
        previous_endian_count=360,
        previous_six_count=186,
        previous_final_six_count=212,
        expected_selected_methods=61):
    parents=verify_original_packet_parents(
        jar,parent_sources,original_sha256=original_sha256,
        source_sha256=parent_source_sha256,
        original_class_shas=parent_class_shas,
        expected_methods=4,
        expected_instructions=parent_instruction_count)
    if parents["all_original_parent_method_bodies_matched"]!=4:
        raise ValueError("R178_TWO_PARENTS_NOT_FULLY_PROVEN")
    kw=dict(prior_six_kwargs or {})
    prior=verify_packet_61(
        jar,partial_packet_source,original_sha256=original_sha256,
        source_sha256=packet_source_sha256,
        owner=owner,class_sha256=class_sha256,
        first_six_kwargs=kw,legacy=prior_49_count,
        new_count=new_count,first_six=previous_six_count,
        prior_endian=previous_endian_count,
        prior_twenty_two=previous_22_count,
        prior_six_new_instructions=previous_final_six_count,
        expected_calls=5)
    if prior["selected_packet_method_bodies"]!=expected_selected_methods:
        raise ValueError("R178_PARTIAL_PACKET_SELECTED_JAVA_NOT_PROVEN")
    sources=source_members(partial_packet_source,packet_source_sha256)
    additional=source_members(parent_sources,parent_source_sha256)
    if len(sources)!=1 or sources[0][0]!=owner+".java" or {
        name for name,_ in additional}!={x+".java" for x in OWNERS}:
        raise ValueError("R178_SOURCE_SET_NOT_THREE_ORIGINAL_OWNERS")
    javac=which("javac")
    if not javac:raise ValueError("R178_JDK_REQUIRED")
    with TemporaryDirectory(prefix="spk-r178-") as tmp:
        root=Path(tmp);paths=[]
        for name,data in [*sources,*additional]:
            p=root/"src"/name
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            paths.append(p)
        child=root/"src"/(owner+".java")
        text=child.read_text(encoding="utf-8")
        marker="public class e {"
        if owner!="rs/x/e" or text.count(marker)!=1:
            raise ValueError("R178_UNEXPECTED_PACKET_SOURCE_DECLARATION")
        child.write_text(text.replace(
            marker,"public class e extends rs.a {",1),encoding="utf-8")
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for k in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                  "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):env.pop(k,None)
        result=run([javac,"--release","9","-proc:none","-implicit:none",
                    "-g:none","-classpath",str(empty),
                    "-sourcepath",str(empty),"-d",str(out),
                    *[str(p) for p in paths]],cwd=root,env=env,
                   capture_output=True,timeout=90)
        classes={p.relative_to(out).as_posix()
                 for p in out.rglob("*.class")}
        if result.returncode or classes!={owner+".class",
                                          "rs/a.class","rs/t.class"}:
            raise ValueError("R178_SOURCE_ONLY_THREE_CLASS_COMPILE_FAILED")
        rebuilt=(out/(owner+".class")).read_bytes()
    with ZipFile(jar) as original:
        raw=original.read(owner+".class")
    ocls,bcls=parse_class(raw),parse_class(rebuilt)
    if (ocls.super_name,bcls.super_name)!=("rs/a","rs/a"):
        raise ValueError("R178_ORIGINAL_PACKET_PARENT_NOT_PRESERVED")
    original=profile_class_field_accesses(raw)
    new=profile_class_field_accesses(rebuilt)
    six={(kw.get(k,d),descriptor) for k,d,descriptor in (
        ("signed_short","B","()I"),("raw_int","r","()I"),
        ("float_reader","s","()F"),("alternate_raw_int","p","()I"),
        ("unsigned_short","o","()I"),("unsigned_byte","y","()I"))}
    selected=six|set(EXTRA)|set(WRITERS)|set(READERS)|set(SIX)|set(ADDED)
    compared=_strict_inspections(original,new,selected=sorted(selected))
    if compared["verified_selected_method_count"]!=expected_selected_methods or (
        compared["matched_opcode_count"]!=prior_49_count+new_count
        or not compared["all_selected_core_method_code_equal"]):
        raise ValueError("R178_ORIGINAL_PACKET_METHOD_CODE_CHANGED_BY_INHERITANCE")
    if (sha_file(jar)!=original_sha256 or
        sha_file(partial_packet_source)!=packet_source_sha256 or
        sha_file(parent_sources)!=parent_source_sha256):
        raise ValueError("R178_PRIVATE_INPUTS_CHANGED")
    return {
        "original_java_parent_classes_recovered":2,
        "original_parent_methods":4,
        "original_parent_instructions":parent_instruction_count,
        "packet_selected_methods_matching_original":expected_selected_methods,
        "packet_instructions_matching_original":prior_49_count+new_count,
        "packet_superclass_chain_matches_original":True,
        "original_game_binary_compiler_dependency":False,
        "full_original_packet_accepted":False,
        "canonical_client_source_tree_changed":False,
        "whole_client_build_passed":False,
    }

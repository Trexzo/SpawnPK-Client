"""R203 — real original v309 spellbook filter enum source, no fake runtime.

The original rs/n/c/ap$a class has original enum labels COMBAT/TELEPORT/
UTILITY while JVM field IDs are obfuscated as a/b/c. The private Java9
source preserves enum labels as real Java constants and supplies a/b/c
aliases for original named bytecode references. Six additional alias writes
and three alias fields are explicitly NOT claimed as original classfile
identity. Original method Code is source-only checked symbolically.

Public GitHub contains verification tooling and invented tests, never
original-derived Java, original JAR, or copied game assets.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_client_source_ast_census_r126 import sha_file, source_members
from .private_v309_signlink_nested_enum_r190 import (
    audit_original_direction_enum_java,
)

ORIGINAL_OWNER="rs/n/c/ap$a"
ORIGINAL_CLASS_SHA256=(
    "884186742e7d92489d6634e8cb6d0012ee5e8ba71bcc272c339bed4a8a9ee7df"
)
SOURCE_ZIP_SHA256=(
    "2b362652ac6a89450c080ff3c771cfd1cc7443307603e90225a42d7a464d1558"
)
ORIGINAL_FIELD_MAP={
    "a":"COMBAT","b":"TELEPORT","c":"UTILITY","d":"$VALUES",
}
ORIGINAL_VALUES_HELPER_MAP={"a":"$values"}
ORIGINAL_JVM_METHODS=5
ORIGINAL_INSTRUCTIONS=50
PREVIOUS_1294_TREE_SHA256=(
    "0dfe8e5bd245c6c6b51b562fc310f7730891a3aefaf1e18c97bd10fc6ba6fe39"
)
R203_1295_TREE_SHA256=(
    "cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
)


class R203OriginalSpellbookEnumError(ValueError):
    pass


def need(value,why):
    if not value:
        raise R203OriginalSpellbookEnumError(why)


def verify_pinned_original_spellbook_filter_enum(
        original_jar,original_named_enum_source_zip, *,
        original_jar_sha256=CANONICAL_V309,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        source_zip_sha256=SOURCE_ZIP_SHA256,
        original_owner=ORIGINAL_OWNER,
        original_field_map=ORIGINAL_FIELD_MAP,
        original_values_helper_map=ORIGINAL_VALUES_HELPER_MAP):
    need(sha_file(original_jar)==original_jar_sha256 and
         sha_file(original_named_enum_source_zip)==source_zip_sha256,
         "R203_EXACT_ORIGINAL_BINARY_AND_PRIVATE_JAVA_SOURCE_PINS")
    sources=source_members(
        original_named_enum_source_zip,source_zip_sha256)
    need(len(sources)==1 and
         sources[0][0]==original_owner+".java" and
         0<len(sources[0][1])<25_000,
         "R203_EXACT_ONE_ORIGINAL_NAMED_JAVA_SOURCE_REQUIRED")
    with ZipFile(original_jar) as z:
        name=original_owner+".class"
        need(z.namelist().count(name)==1,
             "R203_ORIGINAL_CLASSFILE_OWNER_NOT_UNIQUE")
        original_bytes=z.read(name)
    need(hashlib.sha256(original_bytes).hexdigest()==original_class_sha256,
         "R203_ORIGINAL_ENUM_CLASS_SHA256_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R203_JDK_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r203-enum-") as td:
        root=Path(td)
        src=root/"src"/sources[0][0]
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_bytes(sources[0][1])
        out=root/"classes"
        empty=root/"empty"
        out.mkdir();empty.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            p=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),str(src)],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,check=False,timeout=90)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R203OriginalSpellbookEnumError(
                "R203_ORIGINAL_ENUM_SOURCE_ONLY_BUILD_ABORTED") from exc
        emitted={f.relative_to(out).as_posix()
                 for f in out.rglob("*.class")}
        need(p.returncode==0 and
             emitted=={original_owner+".class"},
             "R203_ONE_ENUM_ONLY_JAVA9_BUILD_REQUIRED")
        generated=(out/(original_owner+".class")).read_bytes()
    # Underlying R190 verifier compares ALL five methods and the three
    # extra obfuscated alias writes, not just names/field count.
    original=audit_original_direction_enum_java(
        original_bytes,generated,
        original_owner=original_owner,
        original_enum_class_sha256=original_class_sha256,
        original_field_map=original_field_map,
        original_array_method_map=original_values_helper_map)
    need(original["all_five_original_enum_methods_semantically_matched"]
         and original["matched_original_enum_jvm_instructions"]==
             ORIGINAL_INSTRUCTIONS and
         original["java_derived_class_has_three_extra_alias_fields"],
         "R203_NOT_ALL_FIVE_ORIGINAL_JVM_METHODS_MATCH")
    need(sha_file(original_jar)==original_jar_sha256 and
         sha_file(original_named_enum_source_zip)==source_zip_sha256,
         "R203_PRIVATE_BINARY_OR_SOURCE_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_original_spellbook_enum_source_recovery_r203",
        "original_enum_owner":original_owner,
        "original_class_sha256":original_class_sha256,
        "original_method_bodies_semantically_matched":ORIGINAL_JVM_METHODS,
        "original_jvm_instructions_matched":ORIGINAL_INSTRUCTIONS,
        "original_value_labels_in_order":["COMBAT","TELEPORT","UTILITY"],
        "explicit_obfuscated_field_aliases":["a","b","c"],
        "nonoriginal_alias_initializer_instructions":6,
        "full_original_classfile_binary_identity_verified":False,
        "original_innerclasses_attribute_identity_verified":False,
        "original_game_or_enum_runtime_executed":False,
        "original_full_spellbook_filter_parent_recovered":False,
        "whole_original_v309_client_compiles":False,
        "original_source_redistribution_authorized":False,
    }

"""R204: original v309 Spellbook spell-definition + mode enum Java source parity.

Replays only SHA-pinned original classfiles and three original-named *private*
Java source ZIPs. JDK9 source-only compilation has an EMPTY original/external
binary classpath, emits three classfiles and NEVER executes any game code.

The two new Java enums expose obfuscated enum constant field aliases to
preserve original member references AND real Enum.name()/ordinal strings.
These aliases add 44 fields and 88 initializer instructions. They are not
original classfile bytes and do not establish runtime classfile identity.
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
from .private_v309_config_four_enum_source_r197 import (
    audit_config_enum_classfiles,
)

PREVIOUS_OWNER="rs/n/c/ap$a"
PREVIOUS_SOURCE_SHA256=(
    "2b362652ac6a89450c080ff3c771cfd1cc7443307603e90225a42d7a464d1558"
)
SPELL_OWNER="rs/n/c/ap$b"
SPELL_CLASS_SHA256=(
    "d93b66584019f930d6d14cecd69f9611c579300df1031835211cf879cf25fc74"
)
SPELL_SOURCE_SHA256=(
    "4326e992898ddbf2f5a14523b11d4e03dc67a32dd4931b47636a59d7141d45f1"
)
MODE_OWNER="rs/n/c/ap$c"
MODE_CLASS_SHA256=(
    "a4b10c2b2a46602227f2de4c73d1bffde8029a1c354496fa80650c3c0a770c08"
)
MODE_SOURCE_SHA256=(
    "989f83eecd2c817554ff5140be0f6017a918d627d64693030795e338a12046db"
)
ORIGINAL_CLASS_PINS={
    SPELL_OWNER: SPELL_CLASS_SHA256,
    MODE_OWNER: MODE_CLASS_SHA256,
}
SPELL_LABELS=(
    "AIR_STRIKE","CONFUSE","WATER_STRIKE","EARTH_STRIKE","WEAKEN",
    "FIRE_STRIKE","WIND_BOLT","CURSE","WATER_BOLT","EARTH_BOLT",
    "FIRE_BOLT","CRUMBLE_UNDEAD","WIND_BLAST","WATER_BLAST",
    "EARTH_BLAST","FIRE_BLAST","AIR_WAVE","WATER_WAVE","EARTH_WAVE",
    "FIRE_WAVE","SARA_STRIKE","GUTHIX_CLAWS","ZAMMY_FLAMES",
    "CHARGE","STUN","BIND","SNARE","ENTANGLE","TELEBLOCK",
    "AIR_SURGE","WATER_SURGE","EARTH_SURGE","FIRE_SURGE",
    "HOME_TELEPORT","MONEY_TELEPORT","SKILL_TELEPORT",
    "BOSS_TELEPORT","PK_TELEPORT","MINIGAME_TELEPORT",
    "HOUSE_TELEPORT","BOUNTY_TELEPORT",
)
SPELL_FIELDS=tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNO")
MODE_FIELDS=("a","b","c")
MODE_LABELS=("MODERN","LUNAR","ANCIENTS")
SPECS={
    SPELL_OWNER:{
        "constants":tuple(zip(SPELL_FIELDS,SPELL_LABELS)),
        "array_field":"S",
        "array_method":"a",
        "other_fields":("P","Q","R"),
        "method_count":6,
        "original_instruction_count":586,
        "source_derived_synthetic_accessors":(),
    },
    MODE_OWNER:{
        "constants":tuple(zip(MODE_FIELDS,MODE_LABELS)),
        "array_field":"d",
        "array_method":"a",
        "other_fields":(),
        "method_count":5,
        "original_instruction_count":50,
        "source_derived_synthetic_accessors":(),
    },
}


class R204OriginalSpellbookEnumsError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R204OriginalSpellbookEnumsError(reason)


def verify_pinned_original_spellbook_enums(
        original_jar,previous_category_java_zip,
        spell_java_zip,mode_java_zip, *,
        original_jar_sha256=CANONICAL_V309,
        previous_source_sha256=PREVIOUS_SOURCE_SHA256,
        spell_source_sha256=SPELL_SOURCE_SHA256,
        mode_source_sha256=MODE_SOURCE_SHA256,
        original_class_pins=ORIGINAL_CLASS_PINS):
    """Source-only full-method symbolic verification, no game execution."""
    pins=(
        (original_jar,original_jar_sha256),
        (previous_category_java_zip,previous_source_sha256),
        (spell_java_zip,spell_source_sha256),
        (mode_java_zip,mode_source_sha256),
    )
    need(all(sha_file(path)==expected for path,expected in pins),
         "R204_ORIGINAL_BINARY_OR_PRIVATE_SOURCE_SHA256_MISMATCH")
    expected_owners=(PREVIOUS_OWNER,SPELL_OWNER,MODE_OWNER)
    originals={}
    for owner,(path,sha) in zip(expected_owners,pins[1:]):
        members=source_members(path,sha)
        need(len(members)==1 and members[0][0]==owner+".java" and
             0<len(members[0][1])<=20000,
             "R204_ONE_EXACT_ORIGINAL_NAMED_JAVA_SOURCE_PER_ZIP")
        originals[owner]=members[0][1]
    need(set(original_class_pins)=={SPELL_OWNER,MODE_OWNER},
         "R204_EXACTLY_TWO_NEW_ORIGINAL_CLASS_PINS")
    with ZipFile(original_jar) as archive:
        need(all(archive.namelist().count(owner+".class")==1
                 for owner in original_class_pins),
             "R204_ORIGINAL_JVM_CLASSFILES_NOT_UNIQUE")
        original_classes={
            owner:archive.read(owner+".class")
            for owner in original_class_pins
        }
    need(all(hashlib.sha256(original_classes[owner]).hexdigest()==expected
             for owner,expected in original_class_pins.items()),
         "R204_ORIGINAL_SPELLBOOK_JVM_CLASS_SHA256_CHANGED")
    javac=shutil.which("javac")
    need(javac is not None,"R204_JDK_COMPILER_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r204-private-") as temp:
        root=Path(temp)
        source_files=[]
        for owner,body in originals.items():
            out=root/"src"/(owner+".java")
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(body)
            source_files.append(str(out))
        empty=root/"empty"
        classes=root/"classes"
        empty.mkdir()
        classes.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            compiled=subprocess.run([
                javac,"--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(classes),
                *source_files],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,check=False,timeout=120)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R204OriginalSpellbookEnumsError(
                "R204_JAVA9_SOURCE_ONLY_COMPILATION_ABORTED") from exc
        emitted={p.relative_to(classes).as_posix()
                 for p in classes.rglob("*.class")}
        need(compiled.returncode==0 and
             emitted=={owner+".class" for owner in expected_owners},
             "R204_THREE_AND_ONLY_THREE_JAVA_ENUM_OWNERS_MUST_COMPILE")
        rebuilt={
            owner:(classes/(owner+".class")).read_bytes()
            for owner in original_class_pins
        }
    reports=[]
    for owner,config in SPECS.items():
        try:
            proof=audit_config_enum_classfiles(
                original_classes[owner],rebuilt[owner],
                owner=owner,config=config,
                original_sha256=original_class_pins[owner])
        except ValueError as exc:
            raise R204OriginalSpellbookEnumsError(
                "R204_ORIGINAL_ENUM_METHOD_CODE_OR_ALIAS_MISMATCH") from exc
        reports.append(proof)
    need(sum(p["original_jvm_methods_compared"] for p in reports)==11 and
         sum(p["matched_original_semantic_jvm_instructions"]
             for p in reports)==636 and
         sum(p["extra_alias_initializer_instructions"]
             for p in reports)==88,
         "R204_ORIGINAL_METHOD_OR_ALIAS_COUNT_DRIFT")
    need(all(sha_file(path)==expected for path,expected in pins),
         "R204_ORIGINAL_JAVA_OR_BINARY_CHANGED_DURING_VERIFICATION")
    return {
        "schema_version":1,
        "kind":"v309_original_spellbook_two_enum_sources_r204",
        "original_named_java_sources_compiled_in_one_java9_build":3,
        "new_original_class_owners_verified":2,
        "new_original_method_bodies_verified":11,
        "matched_original_semantic_jvm_instructions":636,
        "nonoriginal_enum_alias_fields":44,
        "nonoriginal_alias_initializer_instructions":88,
        "original_client_classfiles_used_as_compiler_dependencies":False,
        "fake_compiler_helper_java_added":False,
        "full_original_spellbook_parent_source_recovered":False,
        "original_complete_classfile_byte_identity":False,
        "original_game_code_executed":False,
        "full_original_v309_client_compiles":False,
        "source_publication_authorized":False,
        "classes":reports,
    }

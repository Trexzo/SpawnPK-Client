"""R204 synthetic Java9 enum verifier regressions. No original client files.

Invented 41-entry spell catalog and three-mode enum are compiled twice:
baseline synthetic JVM owner and source variant exposing obfuscated aliases.
The strict original-semantic comparator must accept only the new aliases
and refuse numeric widget IDs, lookup predicates, constants or alias drift.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_config_four_enum_source_r197 import (
    R197OriginalConfigEnumError,
    audit_config_enum_classfiles,
)
from spk_recovery.private_v309_spellbook_two_enum_source_r204 import (
    SPELL_LABELS,SPELL_FIELDS,MODE_LABELS,MODE_FIELDS,SPECS,
)


class R204UnrelatedSpellbookCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK javac required")
        cls.tmp=TemporaryDirectory(prefix="r204-invented-java-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.owner="invented/M"
        cls.mode_owner="invented/T"
        cls.labels=tuple(f"ITEM_{n}" for n in range(41))
        cls.aliases=tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNO")
        members=",\n".join(
            f"  {label}({1000+n},{n+1},{n%3})"
            for n,label in enumerate(cls.labels))
        cls.header=(
            "package invented;\n"
            "public enum M {\n"
            +members+";\n"
            " public int P;\n"
            " public int Q;\n"
            " public int R;\n"
            " private M(int p,int q,int r){P=p;Q=q;R=r;}\n"
            " public static M a(int id){\n"
            "  for(M entry:values()){\n"
            "    if(entry.P==id)return entry;\n"
            "  }\n"
            "  return null;\n"
            " }\n"
        )
        cls.alias_declarations="".join(
            f" public static final M {alias}={label};\n"
            for alias,label in zip(cls.aliases,cls.labels))
        cls.original_source=cls.header+"}\n"
        cls.aliased_source=cls.header+cls.alias_declarations+"}\n"
        cls.mode_source=(
            "package invented;\n"
            "public enum T {FIRST, SECOND, THIRD;\n"
        )
        cls.mode_aliases=(
            "public static final T a=FIRST;\n"
            "public static final T b=SECOND;\n"
            "public static final T c=THIRD;\n"
        )
        cls.original_class=cls.compile_source(
            "catalog-original","invented/M",cls.original_source)
        cls.aliased_class=cls.compile_source(
            "catalog-aliased","invented/M",cls.aliased_source)
        cls.original_mode=cls.compile_source(
            "mode-original","invented/T",cls.mode_source+"}\n")
        cls.aliased_mode=cls.compile_source(
            "mode-aliased","invented/T",
            cls.mode_source+cls.mode_aliases+"}\n")
        p=profile_class_field_accesses(cls.original_class)
        cls.instruction_total=sum(
            len(m["instructions"]) for m in p["methods"])
        q=profile_class_field_accesses(cls.original_mode)
        cls.mode_instruction_total=sum(
            len(m["instructions"]) for m in q["methods"])
        cls.config={
            "constants":tuple(zip(cls.aliases,cls.labels)),
            "aliases":tuple(zip(cls.aliases,cls.labels)),
            "array_field":"$VALUES",
            "array_method":"$values",
            "other_fields":("P","Q","R"),
            "method_count":6,
            "original_instruction_count":cls.instruction_total,
            "source_derived_synthetic_accessors":(),
        }
        # For native original enum field names, map source-owned original
        # constant names to their own labels, but aliases remain a/b/c.
        cls.config["constants"]=tuple((label,label)
                                       for label in cls.labels)
        cls.mode_config={
            "constants":tuple((m,m)
                              for m in ("FIRST","SECOND","THIRD")),
            "aliases":(("a","FIRST"),("b","SECOND"),("c","THIRD")),
            "array_field":"$VALUES",
            "array_method":"$values",
            "other_fields":(),
            "method_count":5,
            "original_instruction_count":cls.mode_instruction_total,
            "source_derived_synthetic_accessors":(),
        }

    @classmethod
    def compile_source(cls,tag,owner,body):
        root=cls.root/tag
        src=root/"src"/(owner+".java")
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(body,encoding="utf-8")
        out=root/"classes"
        empty=root/"empty"
        out.mkdir()
        empty.mkdir()
        proc=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),str(src)],
            capture_output=True,text=True,timeout=90,check=False)
        if proc.returncode:
            raise AssertionError(
                "invented Java9 enum compilation failed: "+proc.stderr)
        return (out/(owner+".class")).read_bytes()

    def audit_catalog(self,body=None):
        compiled=(self.aliased_class if body is None else
                  self.compile_source("mutation-"+str(hash(body)),
                                      self.owner,body))
        return audit_config_enum_classfiles(
            self.original_class,compiled,owner=self.owner,
            config=self.config,
            original_sha256=hashlib.sha256(self.original_class).hexdigest())

    def test_large_catalog_all_methods_and_extra_aliases(self):
        result=self.audit_catalog()
        self.assertEqual(6,result["original_jvm_methods_compared"])
        self.assertEqual(self.instruction_total,
                         result["matched_original_semantic_jvm_instructions"])
        self.assertEqual(41,result["source_added_alias_fields"])
        self.assertEqual(82,result["extra_alias_initializer_instructions"])
        self.assertFalse(result["original_binary_classfile_identity_claimed"])

    def test_three_mode_enum_and_aliases(self):
        result=audit_config_enum_classfiles(
            self.original_mode,self.aliased_mode,
            owner=self.mode_owner,config=self.mode_config,
            original_sha256=hashlib.sha256(
                self.original_mode).hexdigest())
        self.assertEqual(5,result["original_jvm_methods_compared"])
        self.assertEqual(self.mode_instruction_total,
                         result["matched_original_semantic_jvm_instructions"])
        self.assertEqual(6,result["extra_alias_initializer_instructions"])

    def test_changed_widget_id_rejected(self):
        bad=self.aliased_source.replace("ITEM_0(1000,1,0)",
                                        "ITEM_0(1001,1,0)")
        with self.assertRaises(R197OriginalConfigEnumError):
            self.audit_catalog(bad)

    def test_changed_lookup_branch_rejected(self):
        bad=self.aliased_source.replace("entry.P==id","entry.P!=id")
        with self.assertRaises(R197OriginalConfigEnumError):
            self.audit_catalog(bad)

    def test_changed_alias_assignment_rejected(self):
        bad=self.aliased_source.replace(
            "public static final M a=ITEM_0;",
            "public static final M a=ITEM_1;")
        with self.assertRaises(R197OriginalConfigEnumError):
            self.audit_catalog(bad)

    def test_removed_alias_rejected(self):
        bad=self.aliased_source.replace(
            " public static final M O=ITEM_40;\n","")
        with self.assertRaises(R197OriginalConfigEnumError):
            self.audit_catalog(bad)

    def test_class_hash_guard_rejects_wrong_original(self):
        with self.assertRaises(R197OriginalConfigEnumError):
            audit_config_enum_classfiles(
                self.original_class,self.aliased_class,
                owner=self.owner,config=self.config,
                original_sha256="0"*64)


if __name__=="__main__":
    unittest.main()

"""R190 unrelated synthetic Java9 enum and compiler alias regressions.

NO original game source or JAR is used. We independently compile an invented
three-value Java enum, then a new source variant that exposes three aliases.
The strict verifier must permit only expected alias bytecode and reject
changed literal names, ordinal order, helper calls and omitted aliases.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.private_v309_signlink_nested_enum_r190 import (
    R190NestedDirectionEnumError,
    audit_original_direction_enum_java,
)


class R190SyntheticNestedEnumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("JDK required")
        cls.tmp=TemporaryDirectory(prefix="r190-synthetic-enum-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.old_text=(
            "package invented;\n"
            "enum E { LEFT, RIGHT, NORMAL; }\n"
        )
        cls.new_text=(
            "package invented;\n"
            "enum E {\n"
            " LEFT, RIGHT, NORMAL;\n"
            " public static final E a=LEFT;\n"
            " public static final E b=RIGHT;\n"
            " public static final E c=NORMAL;\n"
            "}\n"
        )
        cls.original=cls.compile_java("old",cls.old_text)
        cls.candidate=cls.compile_java("rebuilt",cls.new_text)

    @classmethod
    def compile_java(cls,dir_name,text):
        root=cls.root/dir_name
        path=root/"src/invented/E.java"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding="utf-8")
        classes=root/"classes"
        empty=root/"empty"
        classes.mkdir();empty.mkdir()
        result=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(classes),str(path)],
            capture_output=True,text=True,check=False,timeout=60)
        if result.returncode:
            raise AssertionError("synthetic Java9 fixture failed: "+
                                 result.stderr)
        return (classes/"invented/E.class").read_bytes()

    def check(self, candidate=None,**changes):
        options={
            "original_owner":"invented/E",
            "original_enum_class_sha256":
                hashlib.sha256(self.original).hexdigest(),
            "original_field_map":{
                "LEFT":"LEFT","RIGHT":"RIGHT",
                "NORMAL":"NORMAL","$VALUES":"$VALUES"},
            "original_array_method_map":{"$values":"$values"},
        }
        options.update(changes)
        return audit_original_direction_enum_java(
            self.original,candidate or self.candidate,**options)

    def test_all_five_original_enum_methods_match(self):
        result=self.check()
        self.assertTrue(result[
            "all_five_original_enum_methods_semantically_matched"])
        self.assertEqual(["LEFT","RIGHT","NORMAL"],
                         result["original_enum_values_in_order"])
        self.assertTrue(result[
            "obfuscated_outer_java_field_aliases_preserved"])
        self.assertFalse(result["original_enum_classfile_byte_identity"])
        self.assertFalse(result[
            "original_innerclasses_attribute_equivalence_verified"])
        self.assertFalse(result["original_game_code_executed"])
        self.assertGreater(result[
            "matched_original_enum_jvm_instructions"],0)

    def test_wrong_alias_assignment_is_rejected(self):
        bad=self.compile_java("wrong-alias",
            self.new_text.replace("a=LEFT;","a=RIGHT;"))
        with self.assertRaises(R190NestedDirectionEnumError):
            self.check(bad)

    def test_enum_value_order_mutation_rejected(self):
        bad=self.compile_java("wrong-order",
            self.new_text.replace(
                "LEFT, RIGHT, NORMAL;","RIGHT, LEFT, NORMAL;"))
        with self.assertRaises(R190NestedDirectionEnumError):
            self.check(bad)

    def test_original_value_label_mutation_rejected(self):
        bad=self.compile_java("wrong-label",
            self.new_text.replace(
                "LEFT, RIGHT, NORMAL;","OTHER, RIGHT, NORMAL;")
            .replace("a=LEFT;","a=OTHER;"))
        with self.assertRaises(R190NestedDirectionEnumError):
            self.check(bad)

    def test_missing_alias_is_rejected(self):
        bad=self.compile_java("missing-alias",
            self.new_text.replace(
                " public static final E c=NORMAL;\n",""))
        with self.assertRaises(R190NestedDirectionEnumError):
            self.check(bad)

    def test_bad_digest_field_mapping_or_owner_fails(self):
        for kw in (
            {"original_enum_class_sha256":"0"*64},
            {"original_owner":"invented/W"},
            {"original_field_map":{
                "LEFT":"RIGHT","RIGHT":"LEFT",
                "NORMAL":"NORMAL","$VALUES":"$VALUES"}},
            {"original_array_method_map":{"$values":"wrong"}},
        ):
            with self.subTest(kw=kw):
                with self.assertRaises(R190NestedDirectionEnumError):
                    self.check(**kw)


if __name__=="__main__":
    unittest.main()

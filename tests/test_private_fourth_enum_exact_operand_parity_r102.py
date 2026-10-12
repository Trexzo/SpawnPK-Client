"""R102: all-nine exact resolved operands on two independently compiled Java9 enums."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_nested_enum_collision_rebind import rebind_classfile
from spk_recovery.private_fourth_enum_exact_operand_parity_r102 import (
    FourthEnumExactOperandError,
    exact_fourth_enum_operands,
    replay_private_fourth_enum_exact_operands,
)


@unittest.skipUnless(shutil.which("javac"), "Java9-compatible javac required")
class OriginalFourthEnumExactOperandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = self.root = Path(self.tmp.name)
        source = root / "src" / "p" / "Owner.java"
        source.parent.mkdir(parents=True)
        source.write_text(
            "package p; public final class Owner {"
            "public enum Placeholder {"
            ' A("One","https://example.invalid"),'
            ' B("Two","https://example.invalid");'
            "private String x,y;"
            "Placeholder(String a,String b){x=a;y=b;}"
            "public String first(){return x;}"
            "public String second(){return y;}"
            "}"
            "public enum Surrogate {"
            ' A("One","https://example.invalid"),'
            ' B("Two","https://example.invalid");'
            "private String x,y;"
            "Surrogate(String a,String b){x=a;y=b;}"
            "public String first(){return x;}"
            "public String second(){return y;}"
            "}"
            "public static String r1(Placeholder e){return e.x;}"
            "public static String r2(Placeholder e){return e.y;}"
            "public static String s1(Surrogate e){return e.x;}"
            "public static String s2(Surrogate e){return e.y;}"
            "}", encoding="utf-8")
        classes = root / "classes"
        classes.mkdir()
        compilation = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(source)],
            capture_output=True, text=True)
        self.assertEqual(compilation.returncode, 0, compilation.stderr)
        self.original = root / "original.jar"
        self.candidate = root / "candidate.jar"
        self.output = root / "aggregate"
        with ZipFile(self.original, "w") as a, ZipFile(self.candidate, "w") as b:
            for f in classes.rglob("*.class"):
                name = f.relative_to(classes).as_posix()
                b.writestr(name, f.read_bytes())
                rewritten, _ = rebind_classfile(
                    f.read_bytes(), "p/Owner", "Placeholder")
                if name == "p/Owner$Placeholder.class":
                    name = "p/Owner$Owner.class"
                a.writestr(name, rewritten)
        self.o = profile_jar_class(self.original, "p/Owner$Owner.class")
        self.c = profile_jar_class(self.candidate, "p/Owner$Surrogate.class")

    @staticmethod
    def digest(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    def run_gate(self, *, original_pin=None, candidate_pin=None):
        return replay_private_fourth_enum_exact_operands(
            self.original, self.candidate, "p/Owner.class", "Surrogate",
            self.output,
            original_sha256=original_pin or self.digest(self.original),
            candidate_sha256=candidate_pin or self.digest(self.candidate),
        )

    def test_real_java9_exact_all_nine_resolved_operand_pairs(self):
        proof = self.run_gate()
        self.assertEqual(proof["original_methods_operand_and_opcode_exact"], 9)
        self.assertEqual(proof["original_instructions_operand_and_opcode_exact"], 62)
        self.assertEqual(proof["permitted_compiler_generated_enum_field_aliases"], 3)
        self.assertEqual(proof["permitted_synthetic_accessor_aliases_by_exact_private_field"], 2)
        self.assertEqual(proof["ordinary_getter_aliases_used"], 0)
        self.assertFalse(proof["four_nested_enums_R95_parity_certified"])
        self.assertTrue((self.output / "fourth-enum-exact-operands.aggregate.json").is_file())

    def test_changed_original_initializer_string_is_not_accepted(self):
        bad = copy.deepcopy(self.c)
        clinit = next(m for m in bad["methods"] if m["name"] == "<clinit>")
        first = next(row for row in clinit["instructions"]
                     if row.get("constant_pool_tag") == 8)
        first["constant"] = "DIFFERENT_ENUM_NAME"
        with self.assertRaisesRegex(FourthEnumExactOperandError,
                                    "EXACT_RESOLVED_OPERAND_MISMATCH"):
            exact_fourth_enum_operands(self.o, bad)

    def test_original_non_generated_getter_name_cannot_be_aliased(self):
        bad = copy.deepcopy(self.c)
        getter = next(m for m in bad["methods"]
                      if m.get("descriptor") == "()Ljava/lang/String;")
        getter["name"] = "unreviewedGetter"
        with self.assertRaisesRegex(FourthEnumExactOperandError,
                                    "NON_GENERATED_ENUM_METHOD_NAME_CHANGED"):
            exact_fourth_enum_operands(self.o, bad)

    def test_two_original_synthetic_accessor_targets_must_keep_order(self):
        bad = copy.deepcopy(self.c)
        indices = [i for i, m in enumerate(bad["methods"])
                   if m.get("access") == 0x1008]
        self.assertEqual(len(indices), 2)
        i, j = indices
        bad["methods"][i], bad["methods"][j] = (
            bad["methods"][j], bad["methods"][i]
        )
        with self.assertRaisesRegex(FourthEnumExactOperandError,
                                    "SYNTHETIC_ACCESSOR_TARGET_ORDER_CHANGED"):
            exact_fourth_enum_operands(self.o, bad)

    def test_changed_private_data_field_identity_is_not_aliased(self):
        bad = copy.deepcopy(self.c)
        field = next(f for f in bad["fields"]
                     if f.get("descriptor") == "Ljava/lang/String;")
        field["name"] = "other_field"
        for m in bad["methods"]:
            for row in m.get("instructions", []):
                if (row.get("owner") == bad["internal_name"]
                        and row.get("name") == "x"):
                    row["name"] = "other_field"
        with self.assertRaisesRegex(FourthEnumExactOperandError,
                                    "NON_GENERATED_FIELD_IDENTITY_CHANGED"):
            exact_fourth_enum_operands(self.o, bad)

    def test_changed_synthetic_accessor_opcode_vetoed(self):
        bad = copy.deepcopy(self.c)
        method = next(m for m in bad["methods"] if m.get("access") == 0x1008)
        method["instructions"][1]["opcode"] = "0xb6"
        with self.assertRaisesRegex(FourthEnumExactOperandError,
                                    "NINE_OPCODE_SHAPES_NOT_ACCEPTED"):
            exact_fourth_enum_operands(self.o, bad)

    def test_unrelated_original_owner_vetoed(self):
        bad = copy.deepcopy(self.c)
        bad["internal_name"] = "q/Other$Surrogate"
        with self.assertRaisesRegex(FourthEnumExactOperandError,
                                    "MUST_SHARE_OUTER_OWNER"):
            exact_fourth_enum_operands(self.o, bad)

    def test_wrong_original_jar_pin_vetoes_before_output(self):
        with self.assertRaisesRegex(FourthEnumExactOperandError,
                                    "COMPLETE_JAR_SHA256_MISMATCH"):
            self.run_gate(original_pin="0" * 64)
        self.assertFalse(self.output.exists())

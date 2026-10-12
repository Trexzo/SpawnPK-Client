"""R100: verify all nine enum method shapes using actual Java 9 source builds."""
from __future__ import annotations
import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_fourth_enum_nine_shape_witness import (
    FourthEnumSourceShapeError, EXPECTED,
    classify, prove_fourth_enum_source_shapes,
)


@unittest.skipUnless(shutil.which("javac"), "Java9-compatible javac required")
class FourthEnumNineSourceShapeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        source = root / "src" / "p" / "Owner.java"
        source.parent.mkdir(parents=True)
        source.write_text(
            "package p; public final class Owner {"
            "public enum Original {"
            ' A("x","y"), B("z","q");'
            "private String x;private String y;"
            "Original(String x,String y){this.x=x;this.y=y;}"
            "public String first(){return x;}"
            "public String second(){return y;}"
            "}"
            "public enum Surrogate {"
            ' A("x","y"), B("z","q");'
            "private String x;private String y;"
            "Surrogate(String x,String y){this.x=x;this.y=y;}"
            "public String first(){return x;}"
            "public String second(){return y;}"
            "}"
            "public static String a(Original e){return e.x;}"
            "public static String b(Original e){return e.y;}"
            "public static String c(Surrogate e){return e.x;}"
            "public static String d(Surrogate e){return e.y;}"
            "}", encoding="utf-8")
        classes = root / "classes"
        classes.mkdir()
        result = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(source)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        jar = root / "fixture.jar"
        with ZipFile(jar, "w") as z:
            for f in classes.rglob("*.class"):
                z.write(f, f.relative_to(classes).as_posix())
        self.original = profile_jar_class(jar, "p/Owner$Original.class")
        self.candidate = profile_jar_class(jar, "p/Owner$Surrogate.class")

    def test_all_nine_compiled_java9_source_opcode_shapes(self):
        result = prove_fourth_enum_source_shapes(
            self.original, self.candidate)
        self.assertEqual(result["original_method_opcode_sequences_compared"], 9)
        self.assertEqual(result["original_private_string_getters_checked"], 2)
        self.assertEqual(result["original_synthetic_accessors_checked"], 2)
        self.assertTrue(result["all_nine_original_jvm_opcode_shapes_matched"])
        self.assertFalse(result["original_constant_literals_and_field_method_operands_proven"])
        self.assertFalse(result["original_four_enums_R95_parity_proven"])
        self.assertFalse(result["whole_original_client_runtime_equivalence_certified"])
        self.assertEqual(len(classify(self.original)), 9)
        self.assertEqual(len(EXPECTED["initializer"]), 19)
        self.assertEqual(len(EXPECTED["constructor"]), 11)

    def test_changed_constructor_opcode_rejected(self):
        bad = copy.deepcopy(self.candidate)
        ctor = next(m for m in bad["methods"] if m["name"] == "<init>")
        ctor["instructions"][-1]["opcode"] = "0xb0"
        with self.assertRaisesRegex(FourthEnumSourceShapeError,
                                    "NINE_OPCODE_SHAPES_CHANGED"):
            prove_fourth_enum_source_shapes(self.original, bad)

    def test_changed_initializer_opcode_rejected(self):
        bad = copy.deepcopy(self.candidate)
        clinit = next(m for m in bad["methods"] if m["name"] == "<clinit>")
        clinit["instructions"][0]["opcode"] = "0x01"
        with self.assertRaisesRegex(FourthEnumSourceShapeError,
                                    "NINE_OPCODE_SHAPES_CHANGED"):
            prove_fourth_enum_source_shapes(self.original, bad)

    def test_changed_string_getter_rejected(self):
        bad = copy.deepcopy(self.candidate)
        getter = next(m for m in bad["methods"]
                      if m.get("descriptor") == "()Ljava/lang/String;")
        getter["instructions"][1]["opcode"] = "0xb6"
        with self.assertRaisesRegex(FourthEnumSourceShapeError,
                                    "GETTER_NOT_THREE_OPS"):
            prove_fourth_enum_source_shapes(self.original, bad)

    def test_missing_synthetic_accessor_rejected(self):
        bad = copy.deepcopy(self.candidate)
        access = next(m for m in bad["methods"]
                      if m.get("access") == 0x1008)
        bad["methods"].remove(access)
        with self.assertRaisesRegex(FourthEnumSourceShapeError,
                                    "R99_ACCESSOR_SHAPE_NOT_ACCEPTED"):
            prove_fourth_enum_source_shapes(self.original, bad)

    def test_unrelated_enclosing_owner_rejected(self):
        bad = copy.deepcopy(self.candidate)
        bad["internal_name"] = "q/Elsewhere$Surrogate"
        with self.assertRaisesRegex(FourthEnumSourceShapeError,
                                    "SAME_OUTER_NOT_PROVEN"):
            prove_fourth_enum_source_shapes(self.original, bad)

    def test_shape_only_does_not_claim_literal_equivalence(self):
        bad = copy.deepcopy(self.candidate)
        # All opcodes remain identical, but constant/literal semantics are
        # deliberately unverified by this bounded shape witness.
        clinit = next(m for m in bad["methods"] if m["name"] == "<clinit>")
        ldc = next(r for r in clinit["instructions"] if r.get("opcode")=="0x12")
        ldc["constant"] = "MUTATED_LITERAL"
        proof = prove_fourth_enum_source_shapes(self.original, bad)
        self.assertFalse(proof["original_constant_literals_and_field_method_operands_proven"])

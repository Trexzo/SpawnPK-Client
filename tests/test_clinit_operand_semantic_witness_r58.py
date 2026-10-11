"""R58: Java9 synthetic normalized original-versus-compiled operands."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.clinit_operand_semantic_witness import (
    ClinitOperandWitnessError, compare_clinit_operand_semantics,
    private_clinit_operand_replay,
)


@unittest.skipUnless(shutil.which("javac"), "javac needed for JVM proof")
class ClinitOperandSemanticTests(unittest.TestCase):
    def _jar(self, root: Path, dirname: str, cls: str, *,
             text: str = "hello", method: str = "base",
             suffix: str = "suffix", swap: bool = False) -> Path:
        files = root / dirname / "source" / "p"
        classes = root / dirname / "classes"
        files.mkdir(parents=True)
        classes.mkdir()
        a = "x" if cls == "A" else "first"
        b = "y" if cls == "A" else "second"
        assignments = (
            f'public static int {a}=3;'
            f'public static int {b}={a};'
            f'public static String label="{text}";'
            f'public static String settings="prefix"+Provider.{method}()+"{suffix}";'
        )
        if swap:
            assignments = (f'public static int {b}=0;'
                           f'public static int {a}=3;'
                           f'public static String label="{text}";'
                           f'public static String settings="prefix"+Provider.{method}()+"{suffix}";')
        (files / (cls + ".java")).write_text(
            "package p; public final class " + cls
            + "{ " + assignments + " }", encoding="utf-8"
        )
        (files / "Provider.java").write_text(
            'package p; public final class Provider {'
            'public static String base(){return "ok";}'
            'public static String alt(){return "ok";} }',
            encoding="utf-8"
        )
        p = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(files / (cls + ".java")),
             str(files / "Provider.java")],
            capture_output=True, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        jar = root / (dirname + ".jar")
        with ZipFile(jar, "w") as z:
            for name in (cls, "Provider"):
                z.write(classes / "p" / (name + ".class"),
                        "p/" + name + ".class")
        return jar

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _aliases():
        return [
            {"original": {"name": a, "descriptor": d},
             "candidate": {"name": b, "descriptor": d}}
            for a, b, d in (
                ("x", "first", "I"),
                ("y", "second", "I"),
                ("label", "label", "Ljava/lang/String;"),
                ("settings", "settings", "Ljava/lang/String;"),
            )
        ]

    @staticmethod
    def _profiles(a: Path, b: Path):
        return profile_jar_class(a, "p/A.class"), profile_jar_class(b, "p/B.class")

    def test_original_candidate_exact_semantic_operands_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self._jar(root, "original", "A")
            b = self._jar(root, "candidate", "B")
            result = compare_clinit_operand_semantics(
                *self._profiles(a, b), self._aliases()
            )
            self.assertTrue(result["same_order_all_static_writes"])
            self.assertTrue(result["identical_normalized_initializer_operand_semantics"])
            self.assertEqual(result["original_owner_static_writes_in_order"], 4)
            self.assertGreaterEqual(result["operand_proof_counts"]["static_field_reference"], 5)
            self.assertEqual(result["operand_proof_counts"]["static_method_reference"], 1)
            self.assertEqual(result["operand_proof_counts"]["indy_bootstrap_recipe"], 1)
            self.assertFalse(result["original_helper_side_effects_and_runtime_execution_equivalent"])

            aliases = root / "field-aliases.private.json"
            aliases.write_text(
                json.dumps({"schema_version": 1, "aliases": self._aliases()}),
                encoding="utf-8"
            )
            out = root / "private"
            report = private_clinit_operand_replay(
                a, "p/A.class", b, "p/B.class", aliases, out,
                original_sha256=self._sha(a),
                candidate_sha256=self._sha(b),
            )
            self.assertTrue(
                (out / "clinit-operand-parity.aggregate.json").is_file()
            )
            self.assertNotIn('"first"', json.dumps(report))
            self.assertNotIn('"prefix"', json.dumps(report))

    def test_only_ldc_width_changes_with_identical_constants_are_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self._jar(root, "original", "A")
            b = self._jar(root, "candidate", "B")
            original, candidate = self._profiles(a, b)
            method = next(m for m in candidate["methods"]
                          if m["name"] == "<clinit>")
            ldc = next(x for x in method["instructions"]
                       if x["opcode"] == "0x12")
            ldc["opcode"] = "0x13"
            result = compare_clinit_operand_semantics(
                original, candidate, self._aliases()
            )
            self.assertEqual(
                result["ldc_to_ldc_w_width_differences_exactly_validated"], 1
            )
            self.assertFalse(result["strict_r56_original_opcode_gate_certified"])
            ldc["constant"] = "different constant"
            with self.assertRaisesRegex(
                ClinitOperandWitnessError,
                "EXACT_JVM_INSTRUCTION_OPERAND_SEMANTICS_MISMATCH",
            ):
                compare_clinit_operand_semantics(
                    original, candidate, self._aliases()
                )

    def test_actual_different_constant_and_bootstrap_recipe_are_vetoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self._jar(root, "original", "A")
            literal = self._jar(root, "literal", "B", text="changed")
            with self.assertRaisesRegex(
                ClinitOperandWitnessError, "OPERAND_SEMANTICS_MISMATCH"
            ):
                compare_clinit_operand_semantics(
                    *self._profiles(a, literal), self._aliases()
                )
            recipe = self._jar(root, "recipe", "B", suffix="different")
            with self.assertRaisesRegex(
                ClinitOperandWitnessError, "OPERAND_SEMANTICS_MISMATCH"
            ):
                compare_clinit_operand_semantics(
                    *self._profiles(a, recipe), self._aliases()
                )

    def test_actual_different_static_method_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self._jar(root, "original", "A")
            b = self._jar(root, "candidate", "B", method="alt")
            with self.assertRaisesRegex(
                ClinitOperandWitnessError, "OPERAND_SEMANTICS_MISMATCH"
            ):
                compare_clinit_operand_semantics(*self._profiles(a, b),
                                                  self._aliases())

    def test_original_candidate_write_order_must_be_equal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self._jar(root, "original", "A")
            b = self._jar(root, "candidate", "B", swap=True)
            with self.assertRaisesRegex(
                ClinitOperandWitnessError, "WRITE_ORDER_DIFFERENT"
            ):
                compare_clinit_operand_semantics(*self._profiles(a, b),
                                                  self._aliases())

    def test_invalid_alias_and_changed_pin_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self._jar(root, "original", "A")
            b = self._jar(root, "candidate", "B")
            aliases = self._aliases()
            with self.assertRaisesRegex(
                ClinitOperandWitnessError, "EXACTLY_COVER_STORES"
            ):
                compare_clinit_operand_semantics(
                    *self._profiles(a, b), aliases[:3]
                )
            bad = root / "private.json"
            bad.write_text(
                json.dumps({"schema_version": 1, "aliases": aliases}),
                encoding="utf-8"
            )
            out = root / "target"
            with self.assertRaisesRegex(
                ClinitOperandWitnessError, "PRIVATE_JVM_OPERAND_REPLAY_UNVERIFIABLE"
            ):
                private_clinit_operand_replay(
                    a, "p/A.class", b, "p/B.class", bad, out,
                    original_sha256="0" * 64, candidate_sha256=self._sha(b)
                )
            self.assertFalse(out.exists())
            out.mkdir()
            keep = out / "keep"
            keep.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(
                ClinitOperandWitnessError, "OUTPUT_ALREADY_EXISTS"
            ):
                private_clinit_operand_replay(
                    a, "p/A.class", b, "p/B.class", bad, out,
                    original_sha256=self._sha(a), candidate_sha256=self._sha(b)
                )
            self.assertEqual(keep.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()

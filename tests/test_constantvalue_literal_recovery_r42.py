"""R42: compiled JVM ConstantValue parity from literal-only private source fragments."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_field_scaffold import (
    FieldDeclarationScaffoldError,
    _exact_constant_literal,
    scaffold_missing_fields,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class JvmConstantLiteralReconstructionTests(unittest.TestCase):
    def _class(self, root: Path, stem: str, members: str) -> Path:
        src = root / stem / "source" / "p"
        dst = root / stem / "classes"
        src.mkdir(parents=True)
        dst.mkdir(parents=True)
        file = src / "A.java"
        file.write_text("package p; public class A {" + members + "}", encoding="utf-8")
        result = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(dst), str(file)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        jar = root / (stem + ".jar")
        with ZipFile(jar, "w") as output:
            output.write(dst / "p" / "A.class", "p/A.class")
        return jar

    def test_emitted_source_compiles_to_identical_constantvalue_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._class(
                root, "original",
                'public static final boolean on=true;'
                'public static final boolean off=false;'
                'public static final int revision=309;'
                'public static final String label="A\\\\B \\"C\\"";'
                'public static int mutable;',
            )
            candidate = self._class(root, "candidate", "public static int mutable;")
            folder = root / "private-emitted-literals"
            report = scaffold_missing_fields(
                original, candidate, folder,
                original_sha256=_hash(original),
                candidate_sha256=_hash(candidate),
                class_entry="p/A.class",
                emit_verified_constants=True,
            )
            self.assertTrue(report["verified_literal_initializer_mode_enabled"])
            self.assertEqual(report["declarations_staged"], 4)
            self.assertEqual(report["verified_literal_initializers_staged"], 4)
            self.assertEqual(report["final_fields_without_constant_value_evidence"], 0)
            self.assertFalse(report["initializer_values_without_constantvalue_invented"])
            private_fragment = (folder / "missing-fields.fragment.txt").read_text()
            for declaration in (
                "public static final boolean on = true;",
                "public static final boolean off = false;",
                "public static final int revision = 309;",
            ):
                self.assertIn(declaration, private_fragment)
            generated = self._class(
                root, "generated",
                private_fragment + "\npublic static int mutable;",
            )
            def fields(jar):
                with ZipFile(jar) as archive:
                    profile = profile_class_field_accesses(
                        archive.read("p/A.class")
                    )
                return {
                    (f["name"], f["descriptor"]):
                        (f["access"], f["signature"], f["constant_value"])
                    for f in profile["fields"]
                }
            self.assertEqual(fields(original), fields(generated))
            self.assertNotIn("revision", json.dumps(report))
            self.assertNotIn("label", json.dumps(report))
            self.assertFalse(report["source_compilation_certified"])
            self.assertFalse(report["canonical_identity_accepted"])

    def test_missing_final_without_constantvalue_never_gets_default(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._class(
                root, "original",
                'public static final int runtimeValue;'
                'static { runtimeValue = Integer.parseInt("7"); }',
            )
            candidate = self._class(root, "candidate", "")
            folder = root / "private"
            report = scaffold_missing_fields(
                original, candidate, folder,
                original_sha256=_hash(original),
                candidate_sha256=_hash(candidate),
                class_entry="p/A.class", emit_verified_constants=True,
            )
            fragment = (folder / "missing-fields.fragment.txt").read_text()
            self.assertIn("public static final int runtimeValue;", fragment)
            self.assertNotIn("runtimeValue =", fragment)
            self.assertEqual(report["final_fields_without_constant_value_evidence"], 1)
            self.assertEqual(report["verified_literal_initializers_staged"], 0)
            self.assertFalse(report["runtime_field_initialization_recovered"])

    def test_literal_mode_opt_in_never_changes_default_declaration_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._class(
                root, "original", "public static final int revision=7;",
            )
            candidate = self._class(root, "candidate", "")
            report = scaffold_missing_fields(
                original, candidate, root / "default",
                original_sha256=_hash(original),
                candidate_sha256=_hash(candidate),
                class_entry="p/A.class",
            )
            self.assertFalse(report["verified_literal_initializer_mode_enabled"])
            self.assertEqual(report["verified_literal_initializers_staged"], 0)
            fragment = (root / "default" / "missing-fields.fragment.txt").read_text()
            self.assertIn("public static final int revision;", fragment)
            self.assertNotIn("revision =", fragment)


class FailClosedLiteralTranslatorTests(unittest.TestCase):
    def test_boolean_and_range_bounds(self):
        self.assertEqual(_exact_constant_literal("Z", 1), "true")
        self.assertEqual(_exact_constant_literal("Z", 0), "false")
        self.assertEqual(_exact_constant_literal("I", -(2**31)), str(-(2**31)))
        self.assertEqual(_exact_constant_literal("J", -(2**63)), "(-9223372036854775807L - 1L)")
        self.assertEqual(_exact_constant_literal("B", -128), "(byte) -128")
        self.assertEqual(_exact_constant_literal("S", 32767), "(short) 32767")
        self.assertEqual(_exact_constant_literal("C", 65535), "(char) 65535")
        for descriptor, value in (
            ("Z", 2), ("Z", True), ("I", 2**31), ("I", 1.2),
            ("J", 2**63), ("B", 128), ("S", -32769), ("C", -1),
        ):
            with self.subTest(descriptor=descriptor, value=value):
                with self.assertRaises(FieldDeclarationScaffoldError):
                    _exact_constant_literal(descriptor, value)

    def test_strings_must_be_exact_printable_ascii(self):
        self.assertEqual(_exact_constant_literal("Ljava/lang/String;", "abc"),
                         '"abc"')
        self.assertEqual(
            _exact_constant_literal("Ljava/lang/String;", 'a"b\\c'),
            '"a\\"b\\\\c"',
        )
        for invalid in ("hello\n", "spécial", "👍", "\x00"):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(
                    FieldDeclarationScaffoldError,
                    "STRING_CONSTANT_NEEDS_MANUAL_LITERAL_ENCODING",
                ):
                    _exact_constant_literal("Ljava/lang/String;", invalid)

    def test_ambiguous_ieee_float_or_reference_literals_are_never_guessed(self):
        for desc, value in (
            ("F", 1.25), ("D", float("nan")),
            ("Ljava/lang/Object;", "text"), ("[I", None),
        ):
            with self.subTest(descriptor=desc):
                with self.assertRaisesRegex(
                    FieldDeclarationScaffoldError,
                    "UNSUPPORTED_EXACT_CONSTANT_LITERAL_TYPE",
                ):
                    _exact_constant_literal(desc, value)


if __name__ == "__main__":
    unittest.main()

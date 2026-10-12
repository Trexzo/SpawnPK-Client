"""R108: real Java9 126-field original-like source and exact 33 ConstantValue."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_owner_field_source_r108 import (
    OriginalOwnerFieldSourceError, build_private_original_owner_fields,
)


@unittest.skipUnless(shutil.which("javac"), "Java9-compatible javac required")
class OriginalOwnerFieldsAndConstantsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "original-private-fixture.jar"
        self.out = self.root / "private-field-source"

    def compile_fixture(self, *, extra_field=False, changed_constant=False,
                        unsafe_string=False, change_major=False):
        source = self.root / "source" / "p" / "Owner.java"
        source.parent.mkdir(parents=True)
        lines = ["package p; public final class Owner {"]
        for i in range(28):
            lines.append(
                "public static final boolean cb" + str(i) +
                " = " + ("true" if i % 2 else "false") + ";")
        for i, value in enumerate((53, 309, 43594, 9)):
            lines.append("public static final int ci" + str(i) +
                         " = " + str(value) + ";")
        sval = '"line\\nunsafe"' if unsafe_string else '"private-test"'
        if changed_constant:
            lines.append("public static final String cs = new String(" +
                         sval + ");")
        else:
            lines.append("public static final String cs = " + sval + ";")
        for i in range(6):
            lines.append("public static final String fr" + str(i) + ";")
        lines.extend(["public static final Integer fi;",
                      "public static final int[] fa;"])
        for i in range(72):
            lines.append("public static boolean nb" + str(i) + ";")
        for i in range(6):
            lines.append("public static int ni" + str(i) + ";")
        for i in range(7):
            lines.append("public static String nr" + str(i) + ";")
        if extra_field:
            lines.append("public static boolean unexpected;")
        lines.append("static {")
        for i in range(6):
            lines.append('fr' + str(i) + ' = new String("x");')
        lines.append("fi = Integer.valueOf(1); fa = new int[1];")
        lines.append("}")
        lines.append("}")
        source.write_text("\n".join(lines), encoding="utf-8")
        classes = self.root / "classes"
        classes.mkdir()
        done = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(source)],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        binary = (classes / "p" / "Owner.class").read_bytes()
        if change_major:
            assert binary[6:8] == (53).to_bytes(2, "big")
            binary = binary[:6] + (52).to_bytes(2, "big") + binary[8:]
        with ZipFile(self.original, "w") as z:
            z.writestr("p/Owner.class", binary)
        return hashlib.sha256(self.original.read_bytes()).hexdigest()

    def gate(self, pin, javac="javac"):
        return build_private_original_owner_fields(
            self.original, "p/Owner.class", self.out,
            original_sha256=pin, javac=javac)

    def test_javac9_exact_original_like_126_fields_and_33_constants(self):
        pin = self.compile_fixture()
        result = self.gate(pin)
        self.assertEqual(result["original_owner_fields_recovered"], 126)
        self.assertEqual(result["original_owner_public_static_fields"], 85)
        self.assertEqual(result["original_owner_public_static_final_fields"], 41)
        self.assertEqual(result["original_owner_ConstantValue_initializers_recovered"], 33)
        self.assertEqual(result["javac9_ConstantValue_field_metadata_exact"], 33)
        self.assertEqual(result["original_final_fields_needing_clinit_assignments"], 8)
        self.assertFalse(result["original_complete_java9_owner_source_compiled"])
        self.assertFalse(result["whole_client_runtime_equivalence_certified"])
        self.assertTrue((self.out / "private-source" / "p" /
                         "Owner.fields.PRIVATE.java.inc").is_file())
        self.assertTrue((self.out / "private-field-constants-java9.class").is_file())
        self.assertEqual(len(list(self.out.iterdir())), 3)

    def test_wrong_original_complete_jar_pin_no_output(self):
        self.compile_fixture()
        with self.assertRaisesRegex(OriginalOwnerFieldSourceError,
                                    "COMPLETE_JAR_SHA256_MISMATCH"):
            self.gate("0" * 64)
        self.assertFalse(self.out.exists())

    def test_changed_original_field_count_fails_closed(self):
        pin = self.compile_fixture(extra_field=True)
        with self.assertRaisesRegex(OriginalOwnerFieldSourceError,
                                    "ORIGINAL_126_FIELDS_REQUIRED"):
            self.gate(pin)
        self.assertFalse(self.out.exists())

    def test_changed_constant_value_count_fails_closed(self):
        pin = self.compile_fixture(changed_constant=True)
        with self.assertRaisesRegex(OriginalOwnerFieldSourceError,
                                    "FIELD_DISTRIBUTION_NOT_EXACT"):
            self.gate(pin)
        self.assertFalse(self.out.exists())

    def test_original_string_with_control_character_rejected(self):
        pin = self.compile_fixture(unsafe_string=True)
        with self.assertRaisesRegex(OriginalOwnerFieldSourceError,
                                    "UNSUPPORTED_ORIGINAL_JAVA9_STRING_CONSTANT"):
            self.gate(pin)
        self.assertFalse(self.out.exists())

    def test_wrong_java_class_major_vetoes(self):
        pin = self.compile_fixture(change_major=True)
        with self.assertRaisesRegex(OriginalOwnerFieldSourceError,
                                    "ORIGINAL_OWNER_NOT_JAVA9"):
            self.gate(pin)
        self.assertFalse(self.out.exists())

    def test_missing_javac_vetoes_without_private_source_promotion(self):
        pin = self.compile_fixture()
        with self.assertRaisesRegex(OriginalOwnerFieldSourceError,
                                    "PRIVATE_JAVAC9_CONSTANT_PROOF_NOT_AVAILABLE"):
            self.gate(pin, javac="nonexistent-r108-javac")
        self.assertFalse(self.out.exists())

    def test_existing_output_directory_is_never_overwritten(self):
        pin = self.compile_fixture()
        self.out.mkdir()
        (self.out / "keep.txt").write_text("private")
        with self.assertRaisesRegex(OriginalOwnerFieldSourceError,
                                    "FRESH_PRIVATE_SOURCE_OUTPUT_REQUIRED"):
            self.gate(pin)
        self.assertEqual((self.out / "keep.txt").read_text(), "private")

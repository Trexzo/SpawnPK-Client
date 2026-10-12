"""R101: private original-derived source emitter, real javac9 positive/negative."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_nested_enum_collision_rebind import rebind_classfile
from spk_recovery.private_original_fourth_enum_source_emitter import (
    OriginalFourthEnumSourceError,
    compile_private_original_enum_source,
)


@unittest.skipUnless(shutil.which("javac"), "Java9-compatible javac required")
class OriginalFourthEnumPrivateEmitterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "original.jar"
        self.out = self.root / "private-original-emission"

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def fixture(self, *, bad_literal=False, drop_fourth=False,
                reverse_accessor_order=False):
        src = self.root / "src" / "p" / "Owner.java"
        src.parent.mkdir(parents=True, exist_ok=True)
        string_literal = '"line\\nunsafe"' if bad_literal else '"https://example.invalid"'
        first_access, second_access = (
            ("b", "a") if reverse_accessor_order else ("a", "b")
        )
        text = (
            "package p; public final class Owner {"
            "public enum Placeholder {"
            ' ALPHA("One",' + string_literal + '),'
            ' BETA("Two",' + string_literal + ');'
            "private String a,b;"
            "Placeholder(String x,String y){a=x;b=y;}"
            "public String first(){return a;}"
            "public String second(){return b;}"
            "}"
            "public enum One{C,D}public enum Two{E,F}"
            "public enum Three{G,H}"
            "public static String x(Placeholder e){return e." + first_access + ";}"
            "public static String y(Placeholder e){return e." + second_access + ";}"
            "}"
        )
        src.write_text(text, encoding="utf-8")
        classes = self.root / "classes"
        classes.mkdir()
        p = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        with ZipFile(self.original, "w") as z:
            for f in classes.rglob("*.class"):
                name = f.relative_to(classes).as_posix()
                if drop_fourth and name == "p/Owner$One.class":
                    continue
                data, _ = rebind_classfile(f.read_bytes(), "p/Owner", "Placeholder")
                if name == "p/Owner$Placeholder.class":
                    name = "p/Owner$Owner.class"
                z.writestr(name, data)
        return self.sha(self.original)

    def replay(self, *, pin, javac="javac"):
        return compile_private_original_enum_source(
            self.original, "p/Owner.class", self.out,
            original_sha256=pin, javac=javac)

    def test_real_java9_private_source_compilation_and_nine_opcode_shapes(self):
        pin = self.fixture()
        proof = self.replay(pin=pin)
        self.assertEqual(proof["original_enum_methods_compiled_and_shapes_matched"], 9)
        self.assertTrue(proof["original_six_initializer_literal_values_preserved"])
        self.assertTrue(proof["original_two_private_string_field_identifiers_preserved"])
        self.assertTrue(proof["original_two_getter_to_field_relations_preserved"])
        self.assertTrue(proof["original_synthetic_accessor_field_order_preserved"])
        self.assertFalse(proof["R95_original_nested_enum_parity_certified"])
        self.assertFalse(proof["whole_client_runtime_equivalence_certified"])
        self.assertTrue((self.out / "private-java9-source-candidate.jar").is_file())
        self.assertTrue(
            (self.out / "private-java-source" / "p" / "Owner.java").is_file())
        with ZipFile(self.out / "private-java9-source-candidate.jar") as z:
            self.assertEqual(
                set(z.namelist()),
                {"p/Owner.class", "p/Owner$ReconstructedEnum.class"})

    def test_original_synthetic_accessor_order_not_field_declaration_order(self):
        # The two original synthetic accessors can read their private fields
        # in the reverse order of the field table; preserve method order.
        pin = self.fixture(reverse_accessor_order=True)
        proof = self.replay(pin=pin)
        self.assertTrue(proof["original_synthetic_accessor_field_order_preserved"])
        self.assertEqual(proof["original_enum_methods_compiled_and_shapes_matched"], 9)

    def test_wrong_original_complete_jar_sha_vetoes_and_no_output(self):
        self.fixture()
        with self.assertRaisesRegex(
            OriginalFourthEnumSourceError, "ORIGINAL_COMPLETE_JAR_SHA256_NOT_PINNED"
        ):
            self.replay(pin="0" * 64)
        self.assertFalse(self.out.exists())

    def test_original_nonprintable_java_literal_rejected(self):
        pin = self.fixture(bad_literal=True)
        with self.assertRaisesRegex(
            OriginalFourthEnumSourceError,
            "UNSUPPORTED_OR_UNSAFE_ORIGINAL_JAVA_STRING_LITERAL",
        ):
            self.replay(pin=pin)
        self.assertFalse(self.out.exists())

    def test_missing_original_fourth_enum_entry_vetoes(self):
        pin = self.fixture(drop_fourth=True)
        with self.assertRaisesRegex(
            OriginalFourthEnumSourceError, "ORIGINAL_FOUR_ENUM_ENTRIES_NOT_EXACT"
        ):
            self.replay(pin=pin)
        self.assertFalse(self.out.exists())

    def test_missing_java9_compiler_vetoes_without_source_output(self):
        pin = self.fixture()
        with self.assertRaisesRegex(
            OriginalFourthEnumSourceError, "PRIVATE_JAVA9_COMPILER_UNAVAILABLE"
        ):
            self.replay(pin=pin, javac="there-is-no-private-javac")
        self.assertFalse(self.out.exists())

    def test_existing_private_output_no_overwrite(self):
        pin = self.fixture()
        self.out.mkdir()
        with self.assertRaisesRegex(
            OriginalFourthEnumSourceError, "FRESH_PRIVATE_SOURCE_OUTPUT_REQUIRED"
        ):
            self.replay(pin=pin)

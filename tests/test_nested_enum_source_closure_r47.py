"""R47 synthetic JVM enum source dependency closure; no SpawnPK classfile."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import warnings
from zipfile import ZipFile

from spk_recovery.nested_enum_source_closure import (
    NestedEnumClosureError, verify_nested_enum_closure,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class NestedEnumClosureTests(unittest.TestCase):
    def _compile(self, root: Path, name: str, text: str) -> Path:
        src = root / name / "source" / "p"
        classes = root / name / "classes"
        src.mkdir(parents=True)
        classes.mkdir(parents=True)
        file = src / "Outer.java"
        file.write_text("package p; " + text, encoding="utf-8")
        result = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(file)],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as z:
            for path in sorted((classes / "p").glob("*.class")):
                z.write(path, "p/" + path.name)
        return jar

    def _pair(self, root: Path):
        original = self._compile(root, "original", (
            "public class Outer {"
            " public enum Color { RED, GREEN }"
            " public enum Size { SMALL, BIG }"
            " public static Color one;"
            " public static Color two;"
            " public static Size size;"
            " public static int count;"
            "}"
        ))
        candidate = self._compile(root, "candidate", "public class Outer {}")
        previous = root / "previous.jar"
        previous.write_bytes(original.read_bytes())
        return original, previous, candidate

    def _run(self, original: Path, previous: Path, candidate: Path,
             *, previous_pin=None):
        return verify_nested_enum_closure(
            original, previous, candidate,
            original_sha256=_sha(original),
            previous_sha256=previous_pin or _sha(previous),
            candidate_sha256=_sha(candidate),
            class_entry="p/Outer.class",
        )

    def test_exact_enum_dependencies_from_missing_fields(self):
        with tempfile.TemporaryDirectory() as d:
            original, previous, candidate = self._pair(Path(d))
            r = self._run(original, previous, candidate)
            self.assertEqual(r["original_missing_field_declarations"], 4)
            self.assertEqual(r["missing_nested_enum_typed_field_declarations"], 3)
            self.assertEqual(r["unique_nested_jvm_enum_types"], 2)
            self.assertEqual(r["byte_identical_nested_enum_type_count"], 2)
            self.assertEqual(r["nested_java_source_name_collision_count"], 0)
            self.assertEqual(sorted(
                x["referencing_missing_original_field_count"]
                for x in r["nested_enum_types"]), [1, 2])
            self.assertTrue(all(x["jvm_enum_flag_present"]
                                for x in r["nested_enum_types"]))
            self.assertTrue(all(not x["source_java_enum_recovered"]
                                for x in r["nested_enum_types"]))
            for key in ("source_equivalence_certified",
                        "source_code_generated",
                        "original_nested_class_bytes_published",
                        "canonical_identity_accepted"):
                self.assertFalse(r[key])
            for name in ("Color", "Size", "one", "two", "Outer",
                         "RED", "GREEN", "SMALL", "BIG"):
                self.assertNotIn(name, str(r))
            self.assertEqual(r, self._run(original, previous, candidate))

    def test_changed_previous_enum_class_hash_detected_without_acceptance(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original, previous, candidate = self._pair(root)
            newer = self._compile(root, "previous-changed", (
                "public class Outer {"
                " public enum Color { RED, GREEN, BLUE }"
                " public enum Size { SMALL, BIG }"
                " public static Color one; public static Color two;"
                " public static Size size; public static int count;"
                "}"
            ))
            r = self._run(original, newer, candidate)
            self.assertEqual(r["unique_nested_jvm_enum_types"], 2)
            self.assertEqual(r["byte_identical_nested_enum_type_count"], 1)
            self.assertFalse(r["source_equivalence_certified"])

    def test_existing_candidate_enum_field_is_not_counted_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original, previous, _ = self._pair(root)
            candidate = self._compile(root, "candidate-more", (
                "public class Outer { public enum Color { RED, GREEN }"
                " public static Color one; }"
            ))
            r = self._run(original, previous, candidate)
            self.assertEqual(r["missing_nested_enum_typed_field_declarations"], 2)
            self.assertEqual(r["unique_nested_jvm_enum_types"], 2)

    def test_javac_forbids_enum_named_the_same_as_its_parent(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "Outer.java"
            src.write_text(
                "package p; public class Outer { public enum Outer { X } }",
                encoding="utf-8",
            )
            result = subprocess.run(
                ["javac", "--release", "9", "-proc:none", "-d", d, str(src)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Outer", result.stderr)
            self.assertIn("already defined", result.stderr)

    def test_top_level_dollar_named_enum_is_only_a_type_shell(self):
        # Java permits a top-level type with a dollar-sign in the simple
        # name; its binary descriptor can therefore match an obfuscated
        # owner-nested type even though InnerClasses/source nesting is NOT
        # certified by that descriptor.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "source" / "p"
            classes = root / "classes"
            src.mkdir(parents=True)
            classes.mkdir()
            (src / "Outer.java").write_text(
                "package p; public class Outer {"
                " public static Outer$Inner current;"
                " public static final Outer$Inner initial = Outer$Inner.A;"
                "}",
                encoding="utf-8",
            )
            (src / "Outer$Inner.java").write_text(
                "package p; public enum Outer$Inner { A, B }",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                ["javac", "--release", "9", "-g:none", "-proc:none",
                 "-d", str(classes),
                 str(src / "Outer.java"), str(src / "Outer$Inner.java")],
                capture_output=True, text=True,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            from spk_recovery.bytecode_profile import profile_class_field_accesses
            profile = profile_class_field_accesses(
                (classes / "p" / "Outer.class").read_bytes()
            )
            fields = {(r["name"], r["descriptor"]): r
                      for r in profile["fields"]}
            self.assertEqual(len(fields), 2)
            self.assertIn(("current", "Lp/Outer$Inner;"), fields)
            self.assertIn(("initial", "Lp/Outer$Inner;"), fields)
            self.assertTrue(fields[("initial", "Lp/Outer$Inner;")]["access"] & 0x0010)
            self.assertTrue((classes / "p" / "Outer$Inner.class").exists())
            # No claim that these generated shell binaries match original
            # nested enum method bodies or InnerClasses attributes.

    def test_wrong_previous_jar_pin_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            old, previous, candidate = self._pair(Path(d))
            with self.assertRaisesRegex(
                NestedEnumClosureError, "WHOLE_JAR_SHA256_MISMATCH",
            ):
                self._run(old, previous, candidate, previous_pin="0" * 64)

    def test_duplicate_nested_class_entry_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old, previous, candidate = self._pair(root)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(previous, "a") as archive:
                    archive.writestr("p/Outer$Color.class", b"bad duplicate")
            with self.assertRaisesRegex(
                NestedEnumClosureError,
                "EXACT_NESTED_CLASS_ENTRY_MISSING_OR_DUPLICATE",
            ):
                self._run(old, previous, candidate)


if __name__ == "__main__":
    unittest.main()

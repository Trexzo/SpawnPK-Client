"""R48: original JVM mutable scalar initialization, synthetic Java9 only."""
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
from spk_recovery.mutable_scalar_initializer_source import (
    ScalarInitializerRecoveryError,
    build_private_scalar_initializer_fragment,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ScalarInitializerPrivateReplayTests(unittest.TestCase):
    def _jar(self, root: Path, label: str, body: str) -> Path:
        java = root / label / "source" / "p" / "Demo.java"
        classes = root / label / "classes"
        java.parent.mkdir(parents=True)
        classes.mkdir(parents=True)
        java.write_text(
            "package p; public final class Demo { " + body
            + " public static int read(){return number;} }",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(java)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as archive:
            archive.write(classes / "p" / "Demo.class", "p/Demo.class")
        return jar

    def _pair(self, root: Path):
        old = self._jar(
            root, "original",
            'public static boolean on=true; '
            'public static int number=7; '
            'public static boolean off=false; '
            'public static String place="ORIGINAL"; '
            'public static String blank=""; ',
        )
        new = self._jar(
            root, "candidate",
            'public static boolean on; '
            'public static int number; '
            'public static boolean off; '
            'public static String place; '
            'public static String blank; ',
        )
        return old, new

    def _replay(self, original, candidate, out, *, orig_sha=None, cand_sha=None):
        return build_private_scalar_initializer_fragment(
            original, candidate, out,
            original_sha256=orig_sha or _sha(original),
            candidate_sha256=cand_sha or _sha(candidate),
            class_entry="p/Demo.class",
        )

    def test_exact_literals_compiled_into_same_jvm_store_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = self._pair(root)
            out = root / "private"
            result = self._replay(old, new, out)
            self.assertEqual(result["original_mutable_scalar_field_count"], 5)
            self.assertEqual(result["literal_assignment_count"], 5)
            self.assertEqual(result["conditional_store_fields_excluded"], 0)
            self.assertTrue(result["all_original_scalar_field_initializers_recovered"])
            self.assertEqual(result["assignment_type_counts"],
                             {"boolean": 2, "integer": 1, "string": 2})
            self.assertTrue(
                result["all_staged_assignments_have_immediate_literal_producers"]
            )
            self.assertTrue(result["staged_assignment_order_matches_original"])
            self.assertFalse(result["full_class_initializer_order_recovered"])
            self.assertFalse(result["source_equivalence_certified"])
            self.assertFalse(result["canonical_class_and_field_identities_accepted"])
            fragment = (out / "mutable-scalars-clinit.fragment.txt").read_text()
            for expected in (
                "on = true;", "number = 7;", "off = false;",
                'place = "ORIGINAL";', 'blank = "";',
            ):
                self.assertIn(expected, fragment)
            self.assertNotIn('"on"', json.dumps(result))
            self.assertNotIn("ORIGINAL", json.dumps(result))
            self.assertEqual(
                _sha(out / "mutable-scalars-clinit.fragment.txt"),
                result["private_source_fragment_sha256"],
            )
            source_fields = (
                'public static boolean on; public static int number; '
                'public static boolean off; public static String place; '
                'public static String blank; '
            )
            compiled = self._jar(root, "recompiled", source_fields + fragment)
            original_profile = profile_jar_class(old, "p/Demo.class")
            candidate_profile = profile_jar_class(compiled, "p/Demo.class")
            def class_initializer(prof):
                return next(x for x in prof["methods"] if x["name"] == "<clinit>")
            def semantic_instructions(prof):
                return [
                    (x["opcode"], x.get("int_constant"), x.get("constant"),
                     x.get("name"), x.get("descriptor"))
                    for x in class_initializer(prof)["instructions"]
                ]
            self.assertEqual(
                semantic_instructions(original_profile),
                semantic_instructions(candidate_profile),
            )

    def test_branch_join_excludes_conditional_bool_instead_of_guessing_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._jar(
                root, "original",
                'public static int number=3;'
                'public static boolean flag='
                '(System.getProperty("synthetic.setting") == null ? true : false);',
            )
            candidate = self._jar(
                root, "candidate",
                "public static int number; public static boolean flag;",
            )
            report = self._replay(original, candidate, root / "private")
            self.assertEqual(report["original_mutable_scalar_field_count"], 2)
            self.assertEqual(report["literal_assignment_count"], 1)
            self.assertEqual(report["conditional_store_fields_excluded"], 1)
            self.assertFalse(report["all_original_scalar_field_initializers_recovered"])
            snippet = (root / "private" / "mutable-scalars-clinit.fragment.txt").read_text()
            self.assertIn("number = 3;", snippet)
            self.assertNotIn("flag =", snippet)
            self.assertFalse(report["full_class_initializer_order_recovered"])

    def test_original_field_without_explicit_assignment_is_not_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = self._jar(root, "original", "public static int number;")
            new = self._jar(root, "candidate", "public static int number;")
            with self.assertRaisesRegex(
                ScalarInitializerRecoveryError,
                "ORIGINAL_CLASS_INITIALIZER_MISSING",
            ):
                self._replay(old, new, root / "failed")

    def test_unsupported_original_unicode_string_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = self._jar(
                root, "original",
                'public static int number=1; public static String place="Å";',
            )
            new = self._jar(
                root, "candidate",
                "public static int number; public static String place;",
            )
            with self.assertRaisesRegex(
                ScalarInitializerRecoveryError,
                "NON_ASCII_STRING_REQUIRES_MANUAL_LITERAL_RECOVERY",
            ):
                self._replay(old, new, root / "failed")

    def test_preexisting_candidate_scalar_assignment_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, _ = self._pair(root)
            new = self._jar(
                root, "candidate",
                "public static int number=5;"
                "public static boolean on; public static boolean off;"
                "public static String place; public static String blank;",
            )
            with self.assertRaisesRegex(
                ScalarInitializerRecoveryError,
                "CANDIDATE_SCALAR_ALREADY_INITIALIZED",
            ):
                self._replay(old, new, root / "failed")

    def test_wrong_jar_hash_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = self._pair(root)
            output = root / "not-created"
            with self.assertRaisesRegex(
                ScalarInitializerRecoveryError, "COMPLETE_JAR_SHA256_MISMATCH",
            ):
                self._replay(old, new, output, cand_sha="0" * 64)
            self.assertFalse(output.exists())

    def test_output_collisions_keep_existing_private_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = self._pair(root)
            output = root / "occupied"
            output.mkdir()
            marker = output / "KEEP.txt"
            marker.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                ScalarInitializerRecoveryError, "SCALAR_OUTPUT_ALREADY_EXISTS",
            ):
                self._replay(old, new, output)
            self.assertEqual(marker.read_text(), "KEEP")

    def test_deterministic_output_same_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old, new = self._pair(root)
            one = self._replay(old, new, root / "one")
            two = self._replay(old, new, root / "two")
            self.assertEqual(one, two)
            self.assertEqual(
                (root / "one" / "mutable-scalars-clinit.fragment.txt").read_bytes(),
                (root / "two" / "mutable-scalars-clinit.fragment.txt").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()

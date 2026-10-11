"""R51: javac-backed source-form reconstruction and fail-closed negative tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.boolean_predicate_source import (
    PredicateSourceFormError,
    build_private_boolean_predicate_source,
    plan_exact_boolean_predicate_forms,
)
from spk_recovery.bytecode_profile import profile_jar_class


@unittest.skipUnless(shutil.which("javac"), "javac required")
class BooleanPredicateSourceTests(unittest.TestCase):
    def _jar(self, root: Path, label: str, members: str) -> Path:
        src = root / label / "source" / "p" / "Demo.java"
        partner = src.with_name("Partner.java")
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class Demo { " + members + " }",
            encoding="utf-8",
        )
        partner.write_text(
            "package p; public final class Partner { public static Object remote; }",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src), str(partner)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as z:
            for name in ("Demo", "Partner"):
                z.write(classes / "p" / (name + ".class"),
                        "p/" + name + ".class")
        return jar

    @staticmethod
    def _sha(p: Path):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def _pair(self, root: Path):
        original = self._jar(
            root, "original",
            "public static Object local; public static boolean prev;"
            " public static boolean compare=(local==Partner.remote);"
            " public static boolean inverted=(!prev);",
        )
        candidate = self._jar(
            root, "candidate",
            "public static Object local; public static boolean prev;"
            " public static boolean compare; public static boolean inverted;",
        )
        return original, candidate

    def _build(self, original, candidate, out, *, sha=None):
        return build_private_boolean_predicate_source(
            original, candidate, "p/Demo.class", out,
            original_sha256=sha or self._sha(original),
            candidate_sha256=self._sha(candidate),
        )

    def test_compilable_reference_equality_and_negation_preserve_jvm_instructions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            out = root / "private"
            report = self._build(original, candidate, out)
            self.assertEqual(report["exact_join_witnesses"], 2)
            self.assertEqual(report["candidate_predicate_expressions_staged"], 2)
            self.assertEqual(report["unproven_predicate_forms"], 0)
            self.assertEqual(report["expression_type_counts"], {
                "reference_identity_equality": 1,
                "boolean_negation": 1,
            })
            self.assertFalse(report["original_authorial_java_source_certified"])
            self.assertFalse(report["jvm_classfile_parity_certified"])
            self.assertFalse(report["runtime_equivalence_certified"])
            fragment = (out / "boolean-predicate-source.private.txt").read_text()
            self.assertIn("compare = (local == p.Partner.remote);", fragment)
            self.assertIn("inverted = (!prev);", fragment)
            self.assertNotIn('"compare"', json.dumps(report))
            self.assertNotIn("p.Partner.remote", json.dumps(report))
            rebuilt = self._jar(
                root, "rebuilt",
                "public static Object local; public static boolean prev;"
                " public static boolean compare; public static boolean inverted;"
                + fragment,
            )
            old_prof = profile_jar_class(original, "p/Demo.class")
            new_prof = profile_jar_class(rebuilt, "p/Demo.class")
            def ops(prof):
                method = next(m for m in prof["methods"] if m["name"] == "<clinit>")
                return [
                    (r["opcode"], r.get("name"), r.get("descriptor"),
                     r.get("owner"), r.get("int_constant"))
                    for r in method["instructions"]
                ]
            self.assertEqual(ops(old_prof), ops(new_prof))

    def test_non_static_field_predicate_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._jar(
                root, "original",
                'public static boolean invert=(!Boolean.getBoolean("setting"));',
            )
            candidate = self._jar(
                root, "candidate", "public static boolean invert;",
            )
            out = root / "private"
            report = self._build(original, candidate, out)
            self.assertEqual(report["exact_join_witnesses"], 1)
            self.assertEqual(report["candidate_predicate_expressions_staged"], 0)
            self.assertEqual(report["unproven_predicate_forms"], 1)

    def test_different_reference_descriptors_cannot_be_assumed_equivalent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            old = profile_jar_class(original, "p/Demo.class")
            new = profile_jar_class(candidate, "p/Demo.class")
            init = next(m for m in old["methods"] if m["name"] == "<clinit>")
            loads = [row for row in init["instructions"]
                     if row.get("opcode") == "0xb2"
                     and row.get("descriptor") == "Ljava/lang/Object;"]
            self.assertGreaterEqual(len(loads), 2)
            loads[1]["descriptor"] = "Ljava/lang/String;"
            plan = plan_exact_boolean_predicate_forms(old, new)
            self.assertEqual(plan["exact_join_witnesses"], 2)
            self.assertEqual(plan["candidate_predicate_expressions_staged"], 1)
            self.assertEqual(plan["expression_type_counts"][
                "reference_identity_equality"], 0)

    def test_bad_jar_pin_preserves_nonexistent_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            out = root / "private"
            with self.assertRaisesRegex(
                PredicateSourceFormError, "INPUT_JAR_SHA256_MISMATCH",
            ):
                self._build(original, candidate, out, sha="0" * 64)
            self.assertFalse(out.exists())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            out = root / "private"
            out.mkdir()
            marker = out / "KEEP"
            marker.write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(
                PredicateSourceFormError, "PREDICATE_SOURCE_OUTPUT_ALREADY_EXISTS",
            ):
                self._build(original, candidate, out)
            self.assertEqual(marker.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()

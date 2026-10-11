"""R54 Java9 synthetic conditional StringConcatFactory source-form tests."""
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
from spk_recovery.conditional_concat_string_source import (
    ConditionalConcatSourceError,
    build_private_conditional_concat_source,
    plan_conditional_concat_strings,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ConditionalConcatStringTests(unittest.TestCase):
    def _jar(self, root: Path, label: str, fields: str) -> Path:
        java = root / label / "source" / "p" / "Demo.java"
        classes = root / label / "classes"
        java.parent.mkdir(parents=True)
        classes.mkdir()
        java.write_text(
            "package p; public final class Demo {"
            " public enum Mode { FIRST, SECOND; }"
            " public static Mode selected=Mode.FIRST;"
            + fields + " }",
            encoding="utf-8",
        )
        run = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(java)],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as archive:
            for name in ("Demo", "Demo$Mode"):
                archive.write(classes / "p" / (name + ".class"),
                              "p/" + name + ".class")
        return jar

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _profiles(self, jar):
        return (
            profile_jar_class(jar, "p/Demo.class"),
            {"p/Demo$Mode": profile_jar_class(jar, "p/Demo$Mode.class")},
        )

    def _build(self, jar, out, *, pin=None):
        return build_private_conditional_concat_source(
            jar, "p/Demo.class", out,
            original_sha256=pin or self._sha(jar),
        )

    def test_two_real_java9_concat_branches_have_exact_source_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(
                root, "original",
                'public static final String endpoint = "pre" + '
                '(selected==Mode.FIRST ? "red":"blue") + "post";'
                'public static final String location = "left" + '
                '(selected==Mode.FIRST ? "go":"stop") + "right";'
            )
            out = root / "private"
            report = self._build(jar, out)
            self.assertEqual(report["original_dynamic_final_string_count"], 2)
            self.assertEqual(report["exact_conditional_concat_expression_forms"], 2)
            self.assertEqual(report["other_string_final_expression_forms_not_handled"], 0)
            self.assertFalse(report["runtime_equivalence_certified"])
            self.assertFalse(report["compiled_private_expression_parity_certified"])
            fragment = (out / "conditional-concat-source.private.txt").read_text()
            self.assertIn(
                'endpoint = "pre" + (selected == p.Demo$Mode.FIRST '
                '? "red" : "blue") + "post";',
                fragment,
            )
            self.assertIn(
                'location = "left" + (selected == p.Demo$Mode.FIRST '
                '? "go" : "stop") + "right";',
                fragment,
            )
            self.assertNotIn('"endpoint"', json.dumps(report))
            self.assertNotIn('"red"', json.dumps(report))
            self.assertEqual(
                self._sha(out / "conditional-concat-source.private.txt"),
                report["private_fragment_sha256"],
            )

    def test_wrong_string_concat_bootstrap_owner_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                'public static final String endpoint = "pre" + '
                '(selected==Mode.FIRST ? "red":"blue") + "post";'
            )
            original, nested = self._profiles(jar)
            original["bootstrap_methods"][0]["bootstrap_method"]["owner"] = "wrong/Factory"
            proof = plan_conditional_concat_strings(original, nested)
            self.assertEqual(proof["exact_conditional_concat_expression_forms"], 0)
            self.assertEqual(proof["other_string_final_expression_forms_not_handled"], 1)

    def test_extraneous_incoming_branch_to_concat_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                'public static final String endpoint = "pre" + '
                '(selected==Mode.FIRST ? "red":"blue") + "post";'
            )
            original, nested = self._profiles(jar)
            init = next(m for m in original["methods"] if m["name"] == "<clinit>")
            concat = next(x for x in init["instructions"]
                          if x.get("opcode") == "0xba")
            init["instructions"][0]["branch_target_offset"] = concat["offset"]
            result = plan_conditional_concat_strings(original, nested)
            self.assertEqual(result["exact_conditional_concat_expression_forms"], 0)

    def test_different_enum_constant_descriptor_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                'public static final String endpoint = "pre" + '
                '(selected==Mode.FIRST ? "red":"blue") + "post";'
            )
            original, nested = self._profiles(jar)
            init = next(m for m in original["methods"] if m["name"] == "<clinit>")
            rows = [x for x in init["instructions"] if x.get("opcode") == "0xb2"]
            self.assertGreaterEqual(len(rows), 2)
            rows[-1]["descriptor"] = "Ljava/lang/Object;"
            result = plan_conditional_concat_strings(original, nested)
            self.assertEqual(result["exact_conditional_concat_expression_forms"], 0)

    def test_duplicate_original_store_and_wrong_pin_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(
                root, "original",
                'public static final String endpoint = "pre" + '
                '(selected==Mode.FIRST ? "red":"blue") + "post";'
            )
            original, nested = self._profiles(jar)
            init = next(m for m in original["methods"] if m["name"] == "<clinit>")
            store = next(x for x in init["instructions"]
                         if x.get("opcode") == "0xb3"
                         and x.get("name") == "endpoint")
            init["instructions"].append(
                {**store, "offset": init["code_length"] + 4}
            )
            with self.assertRaisesRegex(
                ConditionalConcatSourceError,
                "STRING_FINAL_ORIGINAL_STORE_MISSING_OR_DUPLICATE"
            ):
                plan_conditional_concat_strings(original, nested)
            out = root / "private"
            with self.assertRaisesRegex(
                ConditionalConcatSourceError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                self._build(jar, out, pin="0" * 64)
            self.assertFalse(out.exists())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(
                root, "original",
                'public static final String endpoint = "pre" + '
                '(selected==Mode.FIRST ? "red":"blue") + "post";'
            )
            out = root / "occupied"
            out.mkdir()
            (out / "KEEP").write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                ConditionalConcatSourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                self._build(jar, out)
            self.assertEqual((out / "KEEP").read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

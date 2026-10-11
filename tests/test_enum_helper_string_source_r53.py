"""R53 synthetic Java9 tests for exact enum helper String final source forms."""
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
from spk_recovery.enum_helper_string_source import (
    EnumHelperStringSourceError, plan_enum_helper_strings,
    private_enum_helper_string_source,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class EnumHelperStringSourceTests(unittest.TestCase):
    def _jar(self, root: Path, label: str, body: str) -> Path:
        java = root / label / "source" / "p" / "Demo.java"
        classes = root / label / "classes"
        java.parent.mkdir(parents=True)
        classes.mkdir()
        java.write_text(
            "package p; public final class Demo {"
            "public enum Mode { FIRST, SECOND;"
            " public static String label(Mode m){return m.name();}"
            " public static String tag(Mode m){return m.toString();}"
            " } public static final Mode selected=Mode.FIRST;"
            + body + " }",
            encoding="utf-8"
        )
        run = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(java)],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as archive:
            for inner in ("Demo", "Demo$Mode"):
                archive.write(classes / "p" / (inner + ".class"),
                              "p/" + inner + ".class")
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
        return private_enum_helper_string_source(
            jar, "p/Demo.class", out,
            original_sha256=pin or self._sha(jar),
        )

    def test_two_original_enum_helper_strings_recovered_as_private_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(
                root, "original",
                "public static final String name=Mode.label(selected);"
                "public static final String info=Mode.tag(selected);"
            )
            out = root / "private"
            r = self._build(jar, out)
            self.assertEqual(r["original_nonconstant_final_string_fields"], 2)
            self.assertEqual(r["exact_enum_helper_string_initializers"], 2)
            self.assertEqual(r["remaining_string_initializer_forms_unrecovered"], 0)
            self.assertFalse(r["runtime_equivalence_certified"])
            self.assertFalse(r["original_enum_helper_runtime_behavior_verified"])
            source = (out / "enum-helper-strings.private.txt").read_text()
            self.assertIn("name = p.Demo$Mode.label(selected);", source)
            self.assertIn("info = p.Demo$Mode.tag(selected);", source)
            self.assertNotIn('"name"', json.dumps(r))
            self.assertNotIn('"selected"', json.dumps(r))
            self.assertEqual(
                self._sha(out / "enum-helper-strings.private.txt"),
                r["private_fragment_sha256"],
            )

    def test_mismatched_enum_helper_descriptor_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                "public static final String name=Mode.label(selected);"
            )
            owner, classes = self._profiles(jar)
            init = next(m for m in owner["methods"] if m["name"] == "<clinit>")
            call = next(r for r in init["instructions"]
                        if r.get("opcode") == "0xb8"
                        and r.get("name") == "label")
            call["descriptor"] = "()Ljava/lang/String;"
            proof = plan_enum_helper_strings(owner, classes)
            self.assertEqual(proof["exact_enum_helper_string_initializers"], 0)
            self.assertEqual(proof["remaining_string_initializer_forms_unrecovered"], 1)

    def test_incoming_branch_to_method_operand_is_vetoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                "public static final String name=Mode.label(selected);"
            )
            owner, enums = self._profiles(jar)
            init = next(m for m in owner["methods"] if m["name"] == "<clinit>")
            call = next(r for r in init["instructions"]
                        if r.get("opcode") == "0xb8"
                        and r.get("name") == "label")
            init["instructions"][0]["branch_target_offset"] = call["offset"]
            result = plan_enum_helper_strings(owner, enums)
            self.assertEqual(result["exact_enum_helper_string_initializers"], 0)

    def test_duplicate_original_final_string_write_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                "public static final String name=Mode.label(selected);"
            )
            owner, enums = self._profiles(jar)
            init = next(m for m in owner["methods"] if m["name"] == "<clinit>")
            store = next(r for r in init["instructions"]
                         if r.get("opcode") == "0xb3"
                         and r.get("name") == "name")
            init["instructions"].append(
                {**store, "offset": init["code_length"] + 2}
            )
            with self.assertRaisesRegex(
                EnumHelperStringSourceError,
                "FINAL_STRING_STORE_MISSING_OR_DUPLICATED",
            ):
                plan_enum_helper_strings(owner, enums)

    def test_wrong_sha_and_output_collision_preserve_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(
                root, "original",
                "public static final String name=Mode.label(selected);"
            )
            out = root / "private"
            with self.assertRaisesRegex(
                EnumHelperStringSourceError, "ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH"
            ):
                self._build(jar, out, pin="0" * 64)
            self.assertFalse(out.exists())
            out.mkdir()
            (out / "KEEP").write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                EnumHelperStringSourceError, "OUTPUT_ALREADY_EXISTS",
            ):
                self._build(jar, out)
            self.assertEqual((out / "KEEP").read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

"""R67 Java9 roundtrip: exact 26 Boolean/3 int original source families."""
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
from spk_recovery.large_method_cfg_parity import compare_large_method_cfg
from spk_recovery.local_exception_primitive_source import (
    LocalExceptionPrimitiveSourceError,
    plan_private_local_exception_primitive_sources,
    recover_private_local_exception_sources,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class OriginalLocalExceptionPrimitiveSourceTests(unittest.TestCase):
    METHOD = "(Ljava/lang/Object;Lp/Provider;I)V"
    FIELDS = ("first", "second", "zero", "otherZero", "immediate")

    @classmethod
    def _original(cls) -> str:
        sections = []
        for field, key, kind, default in (
            ("first", "flag.first", "Boolean", "false"),
            ("second", "flag.second", "Boolean", "true"),
            ("zero", "level.zero", "Integer", "0"),
            ("otherZero", "level.other", "Integer", "0"),
            ("immediate", "level.immediate", "Integer", "42"),
        ):
            unbox = "booleanValue" if kind == "Boolean" else "intValue"
            sections.append(
                "try { if(originalLocalSlot1.get(" + json.dumps(key)
                + ")==null) {" + field + "=" + default + ";} else {"
                + field + "=" + kind + ".valueOf(originalLocalSlot1.get("
                + json.dumps(key) + "))." + unbox + "();}"
                + "} catch (Exception ignored) {}"
            )
        return "".join(sections)

    def _compile(self, root: Path, label: str, classname: str,
                 body: str) -> Path:
        src = root / label / "p" / (classname + ".java")
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class " + classname + " {"
            + "public static boolean first, second;"
            + "public static int zero, otherZero, immediate;"
            + "public static void restore(Object arg0,"
            + " Provider originalLocalSlot1, int arg2) {" + body + "}"
            + "}"
            + "class Provider {public String get(String k){return k;}}",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as archive:
            for name in (classname, "Provider"):
                archive.write(classes / "p" / (name + ".class"),
                              "p/" + name + ".class")
        return jar

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar: Path, name: str) -> dict:
        return profile_jar_class(jar, "p/" + name + ".class")

    def test_primitive_java9_original_recompile_exact_exception_cfg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(root, "original", "Owner", self._original())
            original_class = self._profile(original, "Owner")
            private_dir = root / "private"
            report = recover_private_local_exception_sources(
                original, "p/Owner.class", "restore", self.METHOD,
                private_dir, original_sha256=self._sha(original),
            )
            self.assertEqual(report["original_local_exception_handlers"], 5)
            self.assertEqual(report["exact_conditional_boolean_try_catch_regions"], 5)
            self.assertEqual(report["conditional_boolean_regions"], 2)
            self.assertEqual(report["conditional_integer_regions"], 3)
            self.assertEqual(report["conditional_true_default_regions"], 1)
            self.assertEqual(report["conditional_false_default_regions"], 1)
            self.assertEqual(report["conditional_integer_zero_default_regions"], 2)
            self.assertEqual(report["conditional_integer_nonzero_default_regions"], 1)
            self.assertEqual(report["other_exception_local_regions_not_reconstructed"], 0)
            source = (
                private_dir / "local-exception-primitive-source.private.java.txt"
            ).read_text(encoding="utf-8")
            self.assertEqual(source.count("catch (java.lang.Exception ignored)"), 5)
            self.assertEqual(source.count("originalLocalSlot1.get("), 10)
            self.assertIn("first = false", source)
            self.assertIn("second = true", source)
            self.assertIn("zero = 0", source)
            self.assertIn("immediate = 42", source)
            self.assertIn(".intValue()", source)
            candidate = self._compile(root, "candidate", "Recompiled", source)
            compiled_class = self._profile(candidate, "Recompiled")
            aliases = [
                {"original": {"name": f, "descriptor": "Z" if f in
                              ("first", "second") else "I"},
                 "candidate": {"name": f, "descriptor": "Z" if f in
                              ("first", "second") else "I"}}
                for f in self.FIELDS
            ]
            proof = compare_large_method_cfg(
                original_class, "restore", self.METHOD,
                compiled_class, "restore", self.METHOD, aliases
            )
            self.assertEqual(proof["ordered_static_field_writes"], 10)
            self.assertEqual(proof["ordered_typed_exception_table_entries"], 5)
            self.assertTrue(proof["exact_exception_type_and_instruction_ordinal_ranges"])
            self.assertTrue(proof["exact_branch_target_instruction_ordinals"])
            self.assertFalse(proof["runtime_equivalence_certified"])
            public = (private_dir / "local-exception-primitive.aggregate.json"
                      ).read_text(encoding="utf-8")
            for key in ("flag.first", "flag.second", "level.zero",
                        "level.other", "level.immediate", '"first"',
                        '"zero"', "p/Owner"):
                self.assertNotIn(key, public)

    def test_changed_repeated_key_and_handler_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(root, "original", "Owner", self._original())
            profile = self._profile(original, "Owner")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            ldcs = [r for r in method["instructions"] if r.get("opcode") == "0x12"]
            self.assertGreaterEqual(len(ldcs), 10)
            ldcs[1]["constant"] = "not-original-key"
            result = plan_private_local_exception_primitive_sources(
                profile, "restore", self.METHOD
            )
            self.assertEqual(result["exact_conditional_boolean_try_catch_regions"], 4)
            profile = self._profile(original, "Owner")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            pc = method["exception_handlers"][0]["handler_pc"]
            next(x for x in method["instructions"] if x["offset"] == pc)[
                "opcode"] = "0x57"
            result = plan_private_local_exception_primitive_sources(
                profile, "restore", self.METHOD
            )
            self.assertEqual(result["exact_conditional_boolean_try_catch_regions"], 4)

    def test_pin_and_existing_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(root, "original", "Owner", self._original())
            output = root / "private"
            with self.assertRaisesRegex(
                LocalExceptionPrimitiveSourceError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_local_exception_sources(
                    original, "p/Owner.class", "restore", self.METHOD,
                    output, original_sha256="0" * 64
                )
            self.assertFalse(output.exists())
            output.mkdir()
            keep = output / "KEEP"
            keep.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                LocalExceptionPrimitiveSourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_local_exception_sources(
                    original, "p/Owner.class", "restore", self.METHOD,
                    output, original_sha256=self._sha(original)
                )
            self.assertEqual(keep.read_text(encoding="utf-8"), "KEEP")


if __name__ == "__main__":
    unittest.main()

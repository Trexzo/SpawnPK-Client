"""R73 synthetic Java9 indexed int[] original/candidate exact source proof."""
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
from spk_recovery.indexed_properties_array_source import (
    IndexedArraySourceError, plan_private_indexed_array_source,
    recover_private_indexed_loop,
)
from spk_recovery.large_method_cfg_parity import compare_large_method_cfg


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ExactIndexedPropertiesArraySourceTests(unittest.TestCase):
    METHOD = "(Ljava/lang/Object;Ljava/util/Properties;I)V"

    @staticmethod
    def _source() -> str:
        return (
            "try {"
            "for (int originalArrayIndex = 0;"
            "originalArrayIndex < values.length; originalArrayIndex++) {"
            'if (originalLocalSlot1.getProperty("key_" + originalArrayIndex) != null) {'
            "values[originalArrayIndex] = Integer.valueOf("
            'originalLocalSlot1.getProperty("key_" + originalArrayIndex)'
            ").intValue();"
            "}"
            "}"
            "} catch (java.lang.Exception ignored) {}"
        )

    def _compile(self, root: Path, label: str,
                 classname: str, body: str) -> Path:
        src = root / label / "p" / (classname + ".java")
        target = root / label / "classes"
        src.parent.mkdir(parents=True)
        target.mkdir()
        src.write_text(
            "package p; public final class " + classname + " {"
            "public static int[] values = new int[3];"
            "public static void restore(Object arg0,"
            "java.util.Properties originalLocalSlot1, int arg2) {"
            + body + "}"
            "}", encoding="utf-8",
        )
        p = subprocess.run([
            "javac", "--release", "9", "-g:none", "-proc:none",
            "-d", str(target), str(src),
        ], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as archive:
            archive.write(target / "p" / (classname + ".class"),
                          "p/" + classname + ".class")
        return jar

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar: Path, classname: str) -> dict:
        return profile_jar_class(jar, "p/" + classname + ".class")

    def test_exact_java9_indexed_loop_source_roundtrip_via_R66(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(
                root, "original", "Owner", self._source())
            private_out = root / "private"
            proof = recover_private_indexed_loop(
                original, "p/Owner.class", "restore",
                self.METHOD, private_out,
                complete_jar_sha256=self._sha(original),
            )
            self.assertEqual(
                proof["exact_indexed_array_empty_catch_source_regions"], 1)
            self.assertTrue(
                proof["original_concat_recipe_verified_including_prefix"])
            self.assertTrue(proof["original_getProperty_repeated_when_present"])
            self.assertFalse(proof["original_runtime_behavior_equivalent"])
            recovered = (
                private_out / "indexed-array-loop.private.java.txt"
            ).read_text(encoding="utf-8")
            self.assertIn('"key_" + originalArrayIndex', recovered)
            self.assertEqual(recovered.count('getProperty("key_"'), 2)
            self.assertIn("originalArrayIndex++", recovered)
            rebuilt = self._compile(
                root, "candidate", "Recompiled", recovered)
            parity = compare_large_method_cfg(
                self._profile(original, "Owner"),
                "restore", self.METHOD,
                self._profile(rebuilt, "Recompiled"),
                "restore", self.METHOD, [],
            )
            self.assertEqual(parity["ordered_typed_exception_table_entries"], 1)
            self.assertEqual(parity["ordered_static_field_writes"], 0)
            self.assertTrue(parity["exact_branch_target_instruction_ordinals"])
            self.assertTrue(parity["exact_exception_type_and_instruction_ordinal_ranges"])
            public = (private_out / "indexed-array-loop.aggregate.json").read_text()
            for sensitive in ('"key_"', '"values"', "p/Owner"):
                self.assertNotIn(sensitive, public)

    def test_changed_concat_recipe_is_a_hard_original_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(root, "original", "Owner", self._source())
            profile = self._profile(original, "Owner")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            indy = next(row for row in method["instructions"]
                        if row.get("opcode") == "0xba")
            idx = indy["bootstrap_method_attr_index"]
            bootstrap = next(b for b in profile["bootstrap_methods"]
                             if b["index"] == idx)
            bootstrap["arguments"][0]["value"] = "forged\x01\x01"
            with self.assertRaisesRegex(
                IndexedArraySourceError, "INDEXED_CONCAT_RECIPE_HAS_UNSUPPORTED"
            ):
                plan_private_indexed_array_source(
                    profile, "restore", self.METHOD
                )

    def test_changed_second_indy_or_loop_branch_cannot_be_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(root, "original", "Owner", self._source())
            profile = self._profile(original, "Owner")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            indy = [x for x in method["instructions"]
                    if x.get("opcode") == "0xba"]
            self.assertEqual(len(indy), 2)
            indy[-1]["bootstrap_method_attr_index"] = 999
            result = plan_private_indexed_array_source(
                profile, "restore", self.METHOD)
            self.assertEqual(
                result["exact_indexed_array_empty_catch_source_regions"], 0
            )
            profile = self._profile(original, "Owner")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            jump = next(x for x in method["instructions"]
                        if x.get("opcode") == "0xa2")
            jump["branch_target_offset"] = method["instructions"][0]["offset"]
            result = plan_private_indexed_array_source(
                profile, "restore", self.METHOD
            )
            self.assertEqual(
                result["exact_indexed_array_empty_catch_source_regions"], 0
            )

    def test_wrong_pinned_jar_and_occupied_output_preserve_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(root, "original", "Owner", self._source())
            out = root / "private"
            with self.assertRaisesRegex(
                IndexedArraySourceError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_indexed_loop(
                    original, "p/Owner.class", "restore",
                    self.METHOD, out, complete_jar_sha256="0" * 64,
                )
            self.assertFalse(out.exists())
            out.mkdir()
            sentinel = out / "KEEP"
            sentinel.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                IndexedArraySourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_indexed_loop(
                    original, "p/Owner.class", "restore",
                    self.METHOD, out,
                    complete_jar_sha256=self._sha(original),
                )
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "KEEP")


if __name__ == "__main__":
    unittest.main()

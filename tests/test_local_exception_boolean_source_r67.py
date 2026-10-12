"""R67: real Java9 exact empty-catch Boolean protected-source roundtrip."""
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
from spk_recovery.local_exception_boolean_source import (
    LocalExceptionSourceError,
    plan_private_local_exception_boolean_sources,
    recover_private_local_exception_sources,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class OriginalLocalExceptionBooleanSourceTests(unittest.TestCase):
    METHOD = "(Ljava/lang/Object;Lp/Provider;I)V"

    def _compile(self, root: Path, label: str, classname: str,
                 method_source: str) -> Path:
        source = root / label / "p" / (classname + ".java")
        classes = root / label / "classes"
        source.parent.mkdir(parents=True)
        classes.mkdir()
        source.write_text(
            "package p; public final class " + classname + " {"
            " public static boolean first, second;"
            " public static void restore(Object arg0, Provider originalLocalSlot1,"
            " int arg2) {" + method_source + "}"
            "}"
            "class Provider {public String get(String key){return key;}}",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(source)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as out:
            out.write(classes / "p" / (classname + ".class"),
                      "p/" + classname + ".class")
            out.write(classes / "p" / "Provider.class",
                      "p/Provider.class")
        return jar

    @staticmethod
    def _source() -> str:
        return (
            'try { if(originalLocalSlot1.get("flag.first")==null) {'
            'first=false;} else {'
            'first=Boolean.valueOf(originalLocalSlot1.get("flag.first")).booleanValue();}'
            '} catch(Exception ignored){}'
            'try { if(originalLocalSlot1.get("flag.second")==null) {'
            'second=true;} else {'
            'second=Boolean.valueOf(originalLocalSlot1.get("flag.second")).booleanValue();}'
            '} catch(Exception ignored){}'
        )

    @staticmethod
    def _sha(jar: Path) -> str:
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar: Path, name: str) -> dict:
        return profile_jar_class(jar, "p/" + name + ".class")

    def test_original_two_empty_catches_compile_to_same_jvm_cfg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(root, "original", "Owner", self._source())
            profile = self._profile(original, "Owner")
            private_dir = root / "private"
            report = recover_private_local_exception_sources(
                original, "p/Owner.class", "restore", self.METHOD,
                private_dir, original_sha256=self._sha(original),
            )
            self.assertEqual(report["original_local_exception_handlers"], 2)
            self.assertEqual(report["exact_conditional_boolean_try_catch_regions"], 2)
            self.assertEqual(report["other_exception_local_regions_not_reconstructed"], 0)
            self.assertEqual(report["conditional_true_default_regions"], 1)
            self.assertEqual(report["conditional_false_default_regions"], 1)
            self.assertFalse(report["complete_original_method_java_source_recovered"])
            self.assertFalse(report["entire_original_class_runtime_equivalent"])
            generated = (private_dir / "local-exception-boolean-source.private.java.txt"
                         ).read_text(encoding="utf-8")
            self.assertEqual(generated.count("catch (java.lang.Exception ignored)"), 2)
            self.assertEqual(generated.count("originalLocalSlot1.get("), 4)
            self.assertIn("first = false", generated)
            self.assertIn("second = true", generated)
            compiled = self._compile(root, "compiled", "Candidate", generated)
            a, b = profile, self._profile(compiled, "Candidate")
            aliases = [
                {"original": {"name": field, "descriptor": "Z"},
                 "candidate": {"name": field, "descriptor": "Z"}}
                for field in ("first", "second")
            ]
            proof = compare_large_method_cfg(
                a, "restore", self.METHOD,
                b, "restore", self.METHOD, aliases,
            )
            self.assertEqual(proof["ordered_typed_exception_table_entries"], 2)
            self.assertEqual(proof["ordered_static_field_writes"], 4)
            self.assertTrue(proof["exact_branch_target_instruction_ordinals"])
            self.assertTrue(proof["exact_exception_type_and_instruction_ordinal_ranges"])
            self.assertFalse(proof["runtime_equivalence_certified"])
            public = (private_dir / "local-exception-boolean.aggregate.json"
                      ).read_text(encoding="utf-8")
            for key in ("flag.first", "flag.second", '"first"', '"second"',
                        "p/Owner"):
                self.assertNotIn(key, public)

    def test_modified_second_lookup_literal_rejects_one_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._compile(root, "original", "Owner", self._source())
            profile = self._profile(jar, "Owner")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            strings = [r for r in method["instructions"]
                       if r.get("opcode") == "0x12"]
            self.assertEqual(len(strings), 4)
            strings[1]["constant"] = "fabricated.literal"
            result = plan_private_local_exception_boolean_sources(
                profile, "restore", self.METHOD
            )
            self.assertEqual(result["exact_conditional_boolean_try_catch_regions"], 1)
            self.assertEqual(result["other_exception_local_regions_not_reconstructed"], 1)

    def test_modified_catch_handler_and_branch_reject_exact_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._compile(root, "original", "Owner", self._source())
            profile = self._profile(jar, "Owner")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            handler = method["exception_handlers"][0]["handler_pc"]
            next(r for r in method["instructions"]
                 if r["offset"] == handler)["opcode"] = "0x57"
            result = plan_private_local_exception_boolean_sources(
                profile, "restore", self.METHOD
            )
            self.assertEqual(result["exact_conditional_boolean_try_catch_regions"], 1)
            profile = self._profile(jar, "Owner")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            branch = next(r for r in method["instructions"]
                          if r.get("opcode") == "0xc7")
            branch["branch_target_offset"] = method["instructions"][0]["offset"]
            result = plan_private_local_exception_boolean_sources(
                profile, "restore", self.METHOD
            )
            self.assertEqual(result["exact_conditional_boolean_try_catch_regions"], 1)

    def test_pin_and_preexisting_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._compile(root, "original", "Owner", self._source())
            out = root / "private"
            with self.assertRaisesRegex(
                LocalExceptionSourceError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_local_exception_sources(
                    jar, "p/Owner.class", "restore", self.METHOD,
                    out, original_sha256="0" * 64,
                )
            self.assertFalse(out.exists())
            out.mkdir()
            keep = out / "KEEP"
            keep.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                LocalExceptionSourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_local_exception_sources(
                    jar, "p/Owner.class", "restore", self.METHOD,
                    out, original_sha256=self._sha(jar),
                )
            self.assertEqual(keep.read_text(encoding="utf-8"), "KEEP")


if __name__ == "__main__":
    unittest.main()

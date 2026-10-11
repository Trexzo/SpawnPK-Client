"""R64 Java9 exact JVM conditional null -> boolean field write tests."""
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
from spk_recovery.null_guard_boolean_source import (
    NullGuardBooleanSourceError, build_private_null_guard_source,
    plan_original_null_guard_boolean_source,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class NullGuardBooleanSourceTests(unittest.TestCase):
    def _jar(self, root: Path, name: str) -> Path:
        src = root / name / "source" / "p" / "Demo.java"
        classes = root / name / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p;"
            "public final class Demo {"
            "public static boolean missing, present;"
            "public static void restore(String ctx) {"
            "Provider lookup=new Provider();"
            'if(lookup.get("missing.key")==null){missing=true;}'
            'if(lookup.get("present.key")==null){present=false;}'
            "}"
            "}"
            "class Provider {"
            "public Object get(String name){return name;}"
            "}",
            encoding="utf-8",
        )
        p = subprocess.run([
            "javac", "--release", "9", "-g:none", "-proc:none",
            "-d", str(classes), str(src)
        ], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as archive:
            archive.write(classes / "p" / "Demo.class", "p/Demo.class")
        return jar

    @staticmethod
    def _sha(jar: Path) -> str:
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar: Path):
        return profile_jar_class(jar, "p/Demo.class")

    def _plan(self, p):
        return plan_original_null_guard_boolean_source(
            p, "restore", "(Ljava/lang/String;)V"
        )

    def test_two_real_java9_null_guarded_static_boolean_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            out = root / "private"
            report = build_private_null_guard_source(
                jar, "p/Demo.class", "restore", "(Ljava/lang/String;)V",
                out, sha256=self._sha(jar)
            )
            self.assertEqual(report["original_six_instruction_null_guard_windows"], 2)
            self.assertEqual(report["exact_local_null_guard_source_shapes"], 2)
            self.assertEqual(report["boolean_true_on_null_stores"], 1)
            self.assertEqual(report["boolean_false_on_null_stores"], 1)
            self.assertFalse(report["original_local_one_java_variable_type_recovered"])
            self.assertFalse(report["original_class_runtime_equivalence_certified"])
            source = (out / "null-boolean-source.private.java.txt").read_text()
            self.assertIn('if (originalLocalSlot1.get("missing.key") == null)', source)
            self.assertIn("missing = true;", source)
            self.assertIn("present = false;", source)
            public = (out / "null-boolean-source.aggregate.json").read_text()
            for original_text in ("missing.key", "present.key",
                                  '"missing"', '"present"', "p/Demo"):
                self.assertNotIn(original_text, public)
            self.assertEqual(
                hashlib.sha256(source.encode("utf-8")).hexdigest(),
                report["private_java_shape_sha256"],
            )

    def test_wrong_branch_into_store_and_descriptor_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            profile = self._profile(jar)
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            branches = [r for r in method["instructions"]
                        if r.get("opcode") == "0xc7"]
            self.assertEqual(len(branches), 2)
            stores = [r for r in method["instructions"]
                      if r.get("opcode") == "0xb3"]
            branches[0]["branch_target_offset"] = stores[0]["offset"]
            report = self._plan(profile)
            self.assertEqual(report["exact_local_null_guard_source_shapes"], 1)
            self.assertEqual(report["rejected_due_to_branch_or_field_metadata"], 1)

            profile = self._profile(jar)
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            lookups = [r for r in method["instructions"]
                       if r.get("opcode") == "0xb6"]
            lookups[0]["descriptor"] = "()Ljava/lang/Object;"
            report = self._plan(profile)
            self.assertEqual(report["exact_local_null_guard_source_shapes"], 1)

    def test_sha_and_output_collision_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            output = root / "private"
            with self.assertRaisesRegex(
                NullGuardBooleanSourceError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                build_private_null_guard_source(
                    jar, "p/Demo.class", "restore", "(Ljava/lang/String;)V",
                    output, sha256="0" * 64
                )
            self.assertFalse(output.exists())
            output.mkdir()
            sentinel = output / "KEEP"
            sentinel.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                NullGuardBooleanSourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                build_private_null_guard_source(
                    jar, "p/Demo.class", "restore", "(Ljava/lang/String;)V",
                    output, sha256=self._sha(jar)
                )
            self.assertEqual(sentinel.read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

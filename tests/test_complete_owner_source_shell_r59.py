"""R59: synthetic Java9 compile/reparse of recovered full field+initializer shell."""
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
from spk_recovery.complete_owner_source_shell import (
    OwnerSourceShellError, plan_private_owner_source_shell,
    private_complete_owner_shell,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class CompleteOwnerSourceShellTests(unittest.TestCase):
    @staticmethod
    def _sha(path: Path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _compile(self, root: Path, label: str, source: str) -> Path:
        src = root / label / "src" / "p" / "Demo.java"
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(source, encoding="utf-8")
        p = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as out:
            out.write(classes / "p" / "Demo.class", "p/Demo.class")
        return jar

    @staticmethod
    def _original_java():
        return (
            "package p; public final class Demo {"
            "public static final int BUILD=309;"
            "public static final boolean ENABLED=true;"
            'public static final String SITE="example.test";'
            "public static int count=3;"
            "public static boolean active=true;"
            "public static final int[] BUFFER=new int[10];"
            "public static final Integer LIMIT=Integer.valueOf(35000);"
            "}"
        )

    @staticmethod
    def _profile(path: Path):
        return profile_jar_class(path, "p/Demo.class")

    def test_complete_shell_recompiles_with_exact_field_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._compile(root, "original", self._original_java())
            destination = root / "private"
            report = private_complete_owner_shell(
                jar, "p/Demo.class", destination, sha256=self._sha(jar),
            )
            self.assertEqual(report["original_field_declarations"], 7)
            self.assertEqual(report["original_static_final_fields"], 5)
            self.assertEqual(report["original_jvm_constantvalue_fields"], 3)
            self.assertEqual(report["original_blank_dynamic_final_fields"], 2)
            self.assertEqual(report["original_mutable_static_fields"], 2)
            self.assertEqual(report["ordered_initializer_writes"], 4)
            self.assertTrue(report["original_declarations_plus_init_in_one_java_shell"])
            self.assertFalse(report["java_recompilation_field_metadata_equivalence_certified"])
            self.assertFalse(report["runtime_behavior_equivalent"])
            source = (destination / "original-owner-shell.private.java.txt").read_text()
            self.assertIn("public static final int BUILD = 309;", source)
            self.assertIn("public static final boolean ENABLED = true;", source)
            self.assertIn('public static final java.lang.String SITE = "example.test";', source)
            self.assertIn("public static final int[] BUFFER;", source)
            self.assertIn("public static final java.lang.Integer LIMIT;", source)
            self.assertIn("BUFFER = new int[10];", source)
            self.assertIn("LIMIT = Integer.valueOf(35000);", source)
            recomp = self._compile(root, "recompiled", source)
            original_profile, compiled_profile = self._profile(jar), self._profile(recomp)
            assert_fields = ("name", "descriptor", "access", "signature", "constant_value")
            for a, b in zip(original_profile["fields"], compiled_profile["fields"]):
                self.assertEqual(
                    tuple(a[k] for k in assert_fields),
                    tuple(b[k] for k in assert_fields),
                )
            self.assertEqual(len(original_profile["fields"]), len(compiled_profile["fields"]))
            self.assertEqual(self._sha(destination / "original-owner-shell.private.java.txt"),
                             report["private_source_shell_sha256"])
            self.assertNotIn('"BUILD"', json.dumps(report))
            self.assertNotIn('"example.test"', json.dumps(report))

    def test_original_mutable_field_cannot_have_constantvalue(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._compile(Path(tmp), "original", self._original_java())
            p = self._profile(jar)
            row = next(f for f in p["fields"] if f["name"] == "count")
            row["constant_value"] = 3
            with self.assertRaisesRegex(
                OwnerSourceShellError, "CONSTANTVALUE_FIELD_IS_MUTABLE"
            ):
                plan_private_owner_source_shell(p, {})

    def test_generic_field_signature_requires_manual_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._compile(Path(tmp), "original", self._original_java())
            p = self._profile(jar)
            p["fields"][0]["signature"] = "Ljava/lang/Object;"
            with self.assertRaisesRegex(
                OwnerSourceShellError, "ORIGINAL_GENERIC_FIELD_SIGNATURE"
            ):
                plan_private_owner_source_shell(p, {})

    def test_pinned_original_jar_and_output_collision_preserve_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._compile(root, "original", self._original_java())
            dest = root / "private"
            with self.assertRaisesRegex(
                OwnerSourceShellError, "ORIGINAL_WHOLE_JAR_SHA256_MISMATCH"
            ):
                private_complete_owner_shell(
                    jar, "p/Demo.class", dest, sha256="0" * 64,
                )
            self.assertFalse(dest.exists())
            dest.mkdir()
            keep = dest / "KEEP"
            keep.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                OwnerSourceShellError, "OUTPUT_ALREADY_EXISTS"
            ):
                private_complete_owner_shell(
                    jar, "p/Demo.class", dest, sha256=self._sha(jar),
                )
            self.assertEqual(keep.read_text(encoding="utf-8"), "KEEP")


if __name__ == "__main__":
    unittest.main()

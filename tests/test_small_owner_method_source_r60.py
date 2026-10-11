"""R60 Java9 tests of original simple owner methods without fabricating others."""
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
from spk_recovery.small_owner_method_source import (
    SimpleOwnerMethodSourceError, plan_small_original_owner_methods,
    private_short_method_source,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class OriginalSimpleMethodSourcesTests(unittest.TestCase):
    def _jar(self, root: Path, label: str):
        src = root / label / "src" / "p" / "Demo.java"
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        writes = "".join(
            "BUFFER[" + str(i) + "]=" + str(116 + i) + ";"
            for i in range(10)
        )
        src.write_text(
            "package p; public final class Demo {"
            "public static boolean a=false,b=false,c=false,d=false;"
            "public static final int[] BUFFER=new int[10];"
            "public static boolean alwaysFalseA(){return false;}"
            "public static boolean alwaysFalseB(){return false;}"
            "public static boolean delegate(){return alwaysFalseB();}"
            "public static void toggle(boolean enabled){"
            "if(enabled){ a=true;b=false;c=false;d=false; }"
            "else { a=false;b=true;c=true;d=true; }"
            "}"
            "public static void writeArray(){" + writes + "}"
            "public static void unsupported(){int value=1;}"
            "}", encoding="utf-8",
        )
        p = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "Demo.class", "p/Demo.class")
        return jar

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar: Path):
        return profile_jar_class(jar, "p/Demo.class")

    def test_six_exact_short_methods_and_one_unknown_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            out = root / "private"
            result = private_short_method_source(
                jar, "p/Demo.class", out, original_sha256=self._sha(jar)
            )
            self.assertEqual(result["bounded_short_method_sources"], 6)
            self.assertEqual(result["remaining_methods_unreconstructed"], 1)
            self.assertEqual(result["exact_original_array_element_writes"], 10)
            self.assertEqual(result["source_method_form_counts"], {
                "array_element_writer": 1,
                "constant_false_boolean": 2,
                "default_constructor": 1,
                "static_boolean_delegate": 1,
                "two_branch_boolean_toggle": 1,
            })
            source = (out / "short-owner-methods.private.java.txt").read_text()
            self.assertIn("public Demo() {}", source)
            self.assertIn("public static boolean alwaysFalseA() { return false; }", source)
            self.assertIn("public static boolean delegate() { return alwaysFalseB(); }",
                          source)
            self.assertIn("public static void toggle(boolean value)", source)
            self.assertIn("BUFFER[9] = 125;", source)
            self.assertNotIn("unsupported(", source)
            self.assertFalse(result["full_original_class_method_body_parity_certified"])
            self.assertFalse(result["runtime_behavior_equivalence_certified"])
            self.assertNotIn('"alwaysFalseA"', json.dumps(result))
            self.assertEqual(self._sha(out / "short-owner-methods.private.java.txt"),
                             result["private_short_method_fragment_sha256"])

    def test_unproven_constant_false_method_must_be_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            original = self._profile(jar)
            m = next(x for x in original["methods"]
                     if x["name"] == "alwaysFalseA")
            m["instructions"][0]["opcode"] = "0x04"
            result = plan_small_original_owner_methods(original, {})
            self.assertEqual(
                result["source_method_form_counts"]["constant_false_boolean"], 1
            )
            self.assertEqual(result["remaining_methods_unreconstructed"], 2)

    def test_bad_original_array_store_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            original = self._profile(jar)
            m = next(x for x in original["methods"]
                     if x["name"] == "writeArray")
            row = next(r for r in m["instructions"]
                       if r["opcode"] == "0x4f")
            row["opcode"] = "0x50"
            result = plan_small_original_owner_methods(original, {})
            self.assertEqual(result["source_method_form_counts"].get("array_element_writer", 0), 0)
            self.assertEqual(result["remaining_methods_unreconstructed"], 2)

    def test_pins_and_existing_output_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            out = root / "private"
            with self.assertRaisesRegex(
                SimpleOwnerMethodSourceError, "ORIGINAL_WHOLE_JAR_SHA256_MISMATCH"
            ):
                private_short_method_source(
                    jar, "p/Demo.class", out, original_sha256="0"*64
                )
            self.assertFalse(out.exists())
            out.mkdir()
            marker = out / "KEEP"
            marker.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                SimpleOwnerMethodSourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                private_short_method_source(
                    jar, "p/Demo.class", out, original_sha256=self._sha(jar)
                )
            self.assertEqual(marker.read_text(encoding="utf-8"), "KEEP")


if __name__ == "__main__":
    unittest.main()

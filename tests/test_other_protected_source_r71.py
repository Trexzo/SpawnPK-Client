"""R71: Java9 original vs recovered list/int/String protected Java blocks."""
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
from spk_recovery.other_protected_source_r71 import (
    OtherProtectedSourceError, plan_original_other_protected_sources,
    recover_private_other_protected_sources,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class OtherProtectedSourceR71Tests(unittest.TestCase):
    DESC = "(Ljava/lang/Object;Ljava/util/Properties;I)V"

    @staticmethod
    def _body() -> str:
        return (
            'try {if(originalLocalSlot1.getProperty("item.a")!=null){LIST.add(A);}}'
            'catch(Exception ignored){}'
            'try {if(originalLocalSlot1.getProperty("item.b")!=null){LIST.add(B);}}'
            'catch(Exception ignored){}'
            'try {if(originalLocalSlot1.getProperty("item.c")!=null){LIST.add(C);}}'
            'catch(Exception ignored){}'
            'try {if(originalLocalSlot1.getProperty("count")!=null){'
            'count=Integer.valueOf(originalLocalSlot1.getProperty("count")).intValue();}}'
            'catch(Exception ignored){}'
            'try {if(originalLocalSlot1.getProperty("title")==null){'
            'title="untitled";}else{title=originalLocalSlot1.getProperty("title");}}'
            'catch(Exception ignored){}'
        )

    def _compile(self, root: Path, label: str, classname: str,
                 body: str) -> Path:
        src = root / label / "p" / (classname + ".java")
        target = root / label / "classes"
        src.parent.mkdir(parents=True)
        target.mkdir()
        src.write_text(
            "package p; public final class " + classname + " {"
            "public static java.util.List<Object> LIST = new java.util.ArrayList<>();"
            "public static final Object A = new Object(), B = new Object(), C = new Object();"
            "public static int count; public static String title;"
            "public static void restore(Object unusedParameter, "
            "java.util.Properties originalLocalSlot1, int arg2) {"
            + body + "}"
            "}", encoding="utf-8",
        )
        run = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(target), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as out:
            out.write(target / "p" / (classname + ".class"),
                      "p/" + classname + ".class")
        return jar

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _profile(path: Path, classname: str) -> dict:
        return profile_jar_class(path, "p/" + classname + ".class")

    def test_five_exact_protected_java9_regions_recompile_against_R66(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._compile(root, "original", "Owner", self._body())
            out = root / "private"
            info = recover_private_other_protected_sources(
                original, "p/Owner.class", "restore", self.DESC,
                out, sha256=self._sha(original)
            )
            self.assertEqual(info["exact_other_source_regions"], 5)
            self.assertEqual(info["bounded_original_source_kinds"], {
                "guarded_list_add": 3,
                "guarded_integer_conversion": 1,
                "nullable_string_default": 1,
            })
            source = (out / "other-protected-source.private.java.txt").read_text()
            self.assertEqual(source.count("catch (java.lang.Exception ignored)"), 5)
            self.assertEqual(source.count("LIST.add("), 3)
            self.assertIn('Integer.valueOf(originalLocalSlot1.getProperty("count"))', source)
            self.assertIn('title = "untitled"', source)
            recompiled = self._compile(root, "candidate", "Candidate", source)
            aliases = [
                {"original": {"name": n, "descriptor": d},
                 "candidate": {"name": n, "descriptor": d}}
                for n, d in (("count", "I"),
                             ("title", "Ljava/lang/String;"))
            ]
            parity = compare_large_method_cfg(
                self._profile(original, "Owner"), "restore", self.DESC,
                self._profile(recompiled, "Candidate"), "restore", self.DESC,
                aliases,
            )
            self.assertEqual(parity["ordered_typed_exception_table_entries"], 5)
            self.assertEqual(parity["ordered_static_field_writes"], 2)
            self.assertTrue(parity["exact_branch_target_instruction_ordinals"])
            self.assertFalse(parity["runtime_equivalence_certified"])
            public = (out / "other-protected-source.aggregate.json").read_text()
            for private in ('"item.a"', '"item.b"', '"count"', '"title"', '"untitled"'):
                self.assertNotIn(private, public)

    def test_changed_list_method_and_second_lookup_are_not_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._compile(root, "original", "Owner", self._body())
            original = self._profile(jar, "Owner")
            method = next(m for m in original["methods"] if m["name"] == "restore")
            call = next(r for r in method["instructions"] if r["opcode"] == "0xb9")
            call["name"] = "remove"
            result = plan_original_other_protected_sources(
                original, "restore", self.DESC
            )
            self.assertEqual(result["exact_other_source_regions"], 4)
            original = self._profile(jar, "Owner")
            method = next(m for m in original["methods"] if m["name"] == "restore")
            ldcs = [r for r in method["instructions"] if r["opcode"] == "0x12"]
            ldcs[-1]["constant"] = "forged"
            result = plan_original_other_protected_sources(
                original, "restore", self.DESC
            )
            self.assertEqual(result["exact_other_source_regions"], 4)

    def test_full_sha_and_existing_private_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._compile(root, "original", "Owner", self._body())
            out = root / "private"
            with self.assertRaisesRegex(
                OtherProtectedSourceError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_other_protected_sources(
                    jar, "p/Owner.class", "restore", self.DESC,
                    out, sha256="0" * 64,
                )
            self.assertFalse(out.exists())
            out.mkdir()
            sentinel = out / "KEEP"
            sentinel.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                OtherProtectedSourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_other_protected_sources(
                    jar, "p/Owner.class", "restore", self.DESC,
                    out, sha256=self._sha(jar),
                )
            self.assertEqual(sentinel.read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

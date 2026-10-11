"""R52: synthetic-only tests for exact nested-enum final source micro-slices."""
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
from spk_recovery.enum_final_reference_source import (
    EnumFinalSourceError, build_private_enum_reference_source,
    plan_exact_enum_reference,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class EnumFinalReferenceTests(unittest.TestCase):
    def _jar(self, root: Path, label: str, body: str) -> Path:
        src = root / label / "source" / "p" / "Demo.java"
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text("package p; public final class Demo {"
                       "public enum Mode { FIRST, SECOND; }"
                       + body + "}", encoding="utf-8")
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "Demo.class", "p/Demo.class")
            z.write(classes / "p" / "Demo$Mode.class", "p/Demo$Mode.class")
        return jar

    def _pair(self, jar: Path):
        return (profile_jar_class(jar, "p/Demo.class"),
                {"p/Demo$Mode":
                 profile_jar_class(jar, "p/Demo$Mode.class")})

    @staticmethod
    def _sha(jar: Path) -> str:
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    def test_exact_static_final_reference_is_staged_privately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original",
                            "public static final Mode current = Mode.FIRST;")
            output = root / "private"
            report = build_private_enum_reference_source(
                jar, "p/Demo.class", output, original_sha256=self._sha(jar)
            )
            self.assertEqual(report["original_nested_enum_final_fields_examined"], 1)
            self.assertEqual(report["exact_direct_enum_reference_store_pairs"], 1)
            self.assertEqual(report["unrecovered_enum_reference_fields"], 0)
            self.assertFalse(report["nested_enum_source_name_collision_resolved"])
            self.assertFalse(report["compiler_equivalence_certified"])
            self.assertFalse(report["runtime_equivalence_certified"])
            fragment = (output / "enum-final-source.private.txt").read_text()
            self.assertIn("current = p.Demo$Mode.FIRST;", fragment)
            self.assertNotIn('"current"', json.dumps(report))
            self.assertNotIn('"FIRST"', json.dumps(report))
            self.assertEqual(self._sha(output / "enum-final-source.private.txt"),
                             report["private_fragment_sha256"])

    def test_missing_or_wrong_enum_structural_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original",
                            "public static final Mode current = Mode.FIRST;")
            owner, enums = self._pair(jar)
            enums["p/Demo$Mode"]["super_name"] = "java/lang/Object"
            with self.assertRaisesRegex(
                EnumFinalSourceError, "NESTED_SOURCE_TYPE_NOT_PROVEN_ENUM"
            ):
                plan_exact_enum_reference(owner, enums)

    def test_getstatic_source_must_match_exact_enum_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original",
                            "public static final Mode current = Mode.FIRST;")
            owner, enums = self._pair(jar)
            init = next(m for m in owner["methods"] if m["name"] == "<clinit>")
            load = next(x for x in init["instructions"]
                        if x.get("opcode") == "0xb2")
            load["descriptor"] = "Ljava/lang/Object;"
            result = plan_exact_enum_reference(owner, enums)
            self.assertEqual(result["exact_direct_enum_reference_store_pairs"], 0)
            self.assertEqual(result["unrecovered_enum_reference_fields"], 1)

    def test_branch_directly_into_enum_store_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original",
                            "public static final Mode current = Mode.FIRST;")
            owner, enums = self._pair(jar)
            init = next(m for m in owner["methods"] if m["name"] == "<clinit>")
            store = next(x for x in init["instructions"]
                         if x.get("opcode") == "0xb3")
            # Synthetic adversarial incoming branch would skip the getstatic.
            init["instructions"][0]["branch_target_offset"] = store["offset"]
            result = plan_exact_enum_reference(owner, enums)
            self.assertEqual(result["exact_direct_enum_reference_store_pairs"], 0)
            self.assertEqual(result["unrecovered_enum_reference_fields"], 1)

    def test_duplicate_original_store_is_an_explicit_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original",
                            "public static final Mode current = Mode.FIRST;")
            owner, enums = self._pair(jar)
            init = next(m for m in owner["methods"] if m["name"] == "<clinit>")
            store = next(x for x in init["instructions"]
                         if x.get("opcode") == "0xb3")
            init["instructions"].append(
                {**store, "offset": init["code_length"] + 4}
            )
            with self.assertRaisesRegex(
                EnumFinalSourceError, "STATIC_FINAL_ENUM_STORE_MISSING_OR_DUPLICATED"
            ):
                plan_exact_enum_reference(owner, enums)

    def test_mismatched_full_jar_pin_and_existing_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original",
                            "public static final Mode current = Mode.FIRST;")
            out = root / "private"
            with self.assertRaisesRegex(
                EnumFinalSourceError, "ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH"
            ):
                build_private_enum_reference_source(
                    jar, "p/Demo.class", out, original_sha256="0" * 64
                )
            self.assertFalse(out.exists())
            out.mkdir()
            marker = out / "KEEP"
            marker.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                EnumFinalSourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                build_private_enum_reference_source(
                    jar, "p/Demo.class", out, original_sha256=self._sha(jar)
                )
            self.assertEqual(marker.read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

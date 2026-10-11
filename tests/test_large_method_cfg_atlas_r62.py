"""R62: synthetic JVM branch/exception/static-write atlas regression."""
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
from spk_recovery.large_method_cfg_atlas import (
    LargeMethodCfgError, build_private_cfg_atlas, plan_private_original_cfg,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class LargeMethodCfgAtlasTests(unittest.TestCase):
    def _jar(self, root: Path, label: str) -> Path:
        src = root / label / "source" / "p" / "Demo.java"
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class Demo {"
            "public static int first, second, third;"
            "public static void restore(boolean flag) {"
            "try {"
            "if(flag){first=11;}else{first=12;}"
            "second=first+3;"
            "} catch (RuntimeException error) { third=9; }"
            "}"
            "}", encoding="utf-8",
        )
        proc = subprocess.run([
            "javac", "--release", "9", "-g:none", "-proc:none",
            "-d", str(classes), str(src)
        ], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "Demo.class", "p/Demo.class")
        return jar

    @staticmethod
    def _sha(jar: Path) -> str:
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar: Path) -> dict:
        return profile_jar_class(jar, "p/Demo.class")

    def test_real_java9_try_catch_regions_and_static_field_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            plan = plan_private_original_cfg(self._profile(jar), "restore", "(Z)V")
            self.assertGreaterEqual(plan["original_jvm_instruction_count"], 10)
            self.assertGreaterEqual(plan["static_field_writes_total"], 4)
            self.assertGreater(plan["explicit_branch_edge_count"], 0)
            self.assertGreater(plan["exception_handler_entries"], 0)
            self.assertGreater(plan["basic_block_count"], 1)
            self.assertTrue(plan["control_flow_and_exception_ranges_all_accounted_for"])
            self.assertFalse(plan["exact_java_source_or_try_catch_structure_recovered"])
            self.assertFalse(plan["runtime_equivalence_certified"])

            destination = root / "private"
            aggregate = build_private_cfg_atlas(
                jar, "p/Demo.class", "restore", "(Z)V",
                destination, sha256=self._sha(jar)
            )
            private = json.loads(
                (destination / "original-method-cfg.private.json").read_text()
            )
            self.assertEqual(len(private["basic_blocks"]),
                             aggregate["basic_block_count"])
            self.assertEqual(len(private["static_field_writes"]),
                             aggregate["static_field_writes_total"])
            self.assertEqual(len(private["exception_table"]),
                             aggregate["exception_handler_entries"])
            summary = (destination / "original-method-cfg.aggregate.json").read_text()
            for member in ('"restore"', '"first"', '"second"', '"third"',
                           'p/Demo', 'java/lang/RuntimeException'):
                self.assertNotIn(member, summary)
            self.assertEqual(
                hashlib.sha256(
                    (destination / "original-method-cfg.private.json").read_bytes()
                ).hexdigest(),
                aggregate["private_cfg_atlas_sha256"],
            )

    def test_exception_pc_must_match_original_instruction_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            profile = self._profile(jar)
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            self.assertGreater(len(method["exception_handlers"]), 0)
            method["exception_handlers"][0]["handler_pc"] = 999999
            with self.assertRaisesRegex(
                LargeMethodCfgError, "EXCEPTION_HANDLER_NOT_AT_JVM_BOUNDARY"
            ):
                plan_private_original_cfg(profile, "restore", "(Z)V")

    def test_gapped_code_and_missing_method_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            profile = self._profile(jar)
            with self.assertRaisesRegex(
                LargeMethodCfgError, "PRIVATE_METHOD_EXACT_JVM_IDENTITY_NOT_UNIQUE"
            ):
                plan_private_original_cfg(profile, "unknown", "()V")
            method = next(m for m in profile["methods"] if m["name"] == "restore")
            method["instructions"][0]["length"] += 1
            with self.assertRaisesRegex(
                LargeMethodCfgError, "ORIGINAL_JVM_METHOD_HAS_GAPS"
            ):
                plan_private_original_cfg(profile, "restore", "(Z)V")

    def test_full_jar_pin_and_existing_private_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            dest = root / "private"
            with self.assertRaisesRegex(
                LargeMethodCfgError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                build_private_cfg_atlas(
                    jar, "p/Demo.class", "restore", "(Z)V",
                    dest, sha256="0" * 64
                )
            self.assertFalse(dest.exists())
            dest.mkdir()
            sentinel = dest / "KEEP"
            sentinel.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                LargeMethodCfgError, "OUTPUT_ALREADY_EXISTS"
            ):
                build_private_cfg_atlas(
                    jar, "p/Demo.class", "restore", "(Z)V",
                    dest, sha256=self._sha(jar)
                )
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "KEEP")


if __name__ == "__main__":
    unittest.main()

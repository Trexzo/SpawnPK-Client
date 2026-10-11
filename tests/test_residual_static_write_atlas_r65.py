"""R65: Java9 tests for complete disjoint original static-write partition."""
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
from spk_recovery.residual_static_write_atlas import (
    ResidualWriteAtlasError, plan_original_residual_writes,
    replay_private_residual_write_atlas,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class OriginalResidualWriteAtlasTests(unittest.TestCase):
    def _jar(self, root: Path, name: str) -> Path:
        src = root / name / "src" / "p" / "Demo.java"
        classes = root / name / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class Demo {"
            "public static boolean flag;"
            "public static int level;"
            "public static String label;"
            "public void restore(Reader reader) {"
            'flag = Codec.convert(reader.lookup("typed.flag")).asBoolean();'
            'level = Codec.convert(reader.lookup("typed.level")).asInt();'
            'if(reader.lookup("default.flag")==null){flag=true;}'
            'label=reader.lookup("direct.label");'
            "flag=false;"
            "label=null;"
            "}"
            "}"
            "class Reader {public String lookup(String key){return key;}}"
            "class Codec {public static Value convert(String s){return new Value();}}"
            "class Value {"
            "public boolean asBoolean(){return false;}"
            "public int asInt(){return 42;}"
            "}",
            encoding="utf-8",
        )
        cp = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr + cp.stdout)
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "Demo.class", "p/Demo.class")
        return jar

    @staticmethod
    def _sha(jar: Path) -> str:
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar: Path):
        return profile_jar_class(jar, "p/Demo.class")

    @staticmethod
    def _plan(owner: dict):
        return plan_original_residual_writes(
            owner, "restore", "(Lp/Reader;)V",
        )

    def test_full_synthetic_static_write_partition_is_exact_and_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = self._jar(root, "original")
            dest = root / "private"
            result = replay_private_residual_write_atlas(
                original, "p/Demo.class", "restore", "(Lp/Reader;)V",
                dest, original_sha256=self._sha(original)
            )
            self.assertEqual(result["original_owner_static_field_writes"], 6)
            self.assertEqual(result["original_typed_producer_write_sites"], 2)
            self.assertEqual(result["original_null_guard_boolean_write_sites"], 1)
            self.assertEqual(result["original_other_write_sites"], 3)
            self.assertEqual(result["residual_local_jvm_opcode_shape_counts"], {
                "direct_boolean_literal": 1,
                "direct_null_reference": 1,
                "direct_string_lookup": 1,
            })
            self.assertEqual(
                result["residual_sites_without_exact_local_opcode_shape"], 0
            )
            self.assertTrue(result["entire_original_static_write_site_partition_disjoint"])
            self.assertFalse(result["original_method_runtime_parity_certified"])
            self.assertFalse(result["residual_java_expression_source_recovered"])
            private = dest / "residual-static-write-sites.private.json"
            self.assertEqual(len(json.loads(private.read_text())), 3)
            public = (dest / "residual-static-write-atlas.aggregate.json").read_text()
            for sensitive in (
                '"flag"', '"label"', "typed.flag", "direct.label",
                "p/Demo", "p/Reader"
            ):
                self.assertNotIn(sensitive, public)
            self.assertEqual(self._sha(private),
                             result["private_residual_site_graph_sha256"])

    def test_unknown_residual_value_window_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            original = self._profile(jar)
            method = next(m for m in original["methods"] if m["name"] == "restore")
            # Mutate an original literal assignment into unsupported JVM opcode,
            # without changing the actual target-field declaration.
            writes = [i for i, row in enumerate(method["instructions"])
                      if row["opcode"] == "0xb3"]
            self.assertEqual(len(writes), 6)
            method["instructions"][writes[-2] - 1]["opcode"] = "0x09"
            result = self._plan(original)
            self.assertEqual(result["original_other_write_sites"], 3)
            self.assertEqual(result["residual_sites_without_exact_local_opcode_shape"], 1)
            self.assertEqual(
                result["residual_local_jvm_opcode_shape_counts"].get(
                    "direct_boolean_literal", 0),
                0,
            )

    def test_undeclared_static_write_is_a_hard_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            original = self._profile(jar)
            method = next(m for m in original["methods"] if m["name"] == "restore")
            store = next(r for r in method["instructions"]
                         if r["opcode"] == "0xb3")
            store["name"] = "fabricatedField"
            with self.assertRaisesRegex(
                ResidualWriteAtlasError,
                "ORIGINAL_STORE_TARGET_NOT_DECLARED_STATIC_OWNER_FIELD"
            ):
                self._plan(original)

    def test_wrong_pin_and_existing_output_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            out = root / "private"
            with self.assertRaisesRegex(
                ResidualWriteAtlasError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                replay_private_residual_write_atlas(
                    jar, "p/Demo.class", "restore", "(Lp/Reader;)V",
                    out, original_sha256="0" * 64
                )
            self.assertFalse(out.exists())
            out.mkdir()
            sentinel = out / "KEEP"
            sentinel.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                ResidualWriteAtlasError, "OUTPUT_ALREADY_EXISTS"
            ):
                replay_private_residual_write_atlas(
                    jar, "p/Demo.class", "restore", "(Lp/Reader;)V",
                    out, original_sha256=self._sha(jar)
                )
            self.assertEqual(sentinel.read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

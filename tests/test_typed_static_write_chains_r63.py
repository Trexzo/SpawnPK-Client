"""R63 Java9 synthetic exact typed static-write chain proof and veto tests."""
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
from spk_recovery.typed_static_write_chains import (
    TypedWriteChainError, plan_original_typed_write_chains,
    private_typed_write_chain_replay,
)


@unittest.skipUnless(shutil.which("javac"), "javac needed")
class TypedStaticWriteChainTests(unittest.TestCase):
    def _jar(self, root: Path, label: str) -> Path:
        src = root / label / "src" / "p" / "Demo.java"
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p;"
            "public final class Demo {"
            "public static boolean flag;"
            "public static int level;"
            "public static void restore(String ctx) {"
            "Reader reader=new Reader();"
            'flag = Codec.convert(reader.lookup("flag.key")).asBoolean();'
            'level = Codec.convert(reader.lookup("level.key")).asInt();'
            "}"
            "}"
            "class Reader {public String lookup(String key){return key;}}"
            "class Codec {public static Value convert(String input){return new Value();}}"
            "class Value {"
            "public boolean asBoolean(){return true;}"
            "public int asInt(){return 7;}"
            "}", encoding="utf-8",
        )
        result = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as out:
            out.write(classes / "p" / "Demo.class", "p/Demo.class")
        return jar

    @staticmethod
    def _sha(jar: Path) -> str:
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar):
        return profile_jar_class(jar, "p/Demo.class")

    def _plan(self, owner: dict):
        return plan_original_typed_write_chains(
            owner, "restore", "(Ljava/lang/String;)V"
        )

    def test_two_six_opcode_boolean_int_chains_and_private_literals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            result = private_typed_write_chain_replay(
                jar, "p/Demo.class", "restore", "(Ljava/lang/String;)V",
                root / "private", original_sha256=self._sha(jar),
            )
            self.assertEqual(result["original_raw_six_opcode_chain_sites"], 2)
            self.assertEqual(result["original_exact_descriptor_compatible_sites"], 2)
            self.assertEqual(result["original_accepted_no_incoming_edge_sites"], 2)
            self.assertEqual(result["original_boolean_target_chains"], 1)
            self.assertEqual(result["original_int_target_chains"], 1)
            self.assertFalse(result["original_source_expression_and_try_catch_recovered"])
            self.assertFalse(result["original_method_runtime_equivalent"])
            private = (root / "private" / "typed-write-chains.private.json")
            self.assertEqual(len(json.loads(private.read_text())), 2)
            public = (root / "private" / "typed-write-chains.aggregate.json").read_text()
            for secret in ("flag.key", "level.key", '"flag"', '"level"',
                           "p/Demo", "p/Value"):
                self.assertNotIn(secret, public)
            self.assertEqual(hashlib.sha256(private.read_bytes()).hexdigest(),
                             result["private_typed_chain_data_sha256"])

    def test_changed_intermediate_return_descriptor_vetoes_one_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = self._profile(self._jar(Path(tmp), "original"))
            method = next(m for m in owner["methods"] if m["name"] == "restore")
            calls = [r for r in method["instructions"] if r["opcode"] == "0xb8"]
            calls[0]["descriptor"] = "(Ljava/lang/Object;)Lp/Value;"
            result = self._plan(owner)
            self.assertEqual(result["original_raw_six_opcode_chain_sites"], 2)
            self.assertEqual(result["original_accepted_no_incoming_edge_sites"], 1)
            self.assertEqual(result["sites_vetoed_due_to_metadata_or_cfg"], 1)

    def test_branch_entry_into_producer_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = self._profile(self._jar(Path(tmp), "original"))
            method = next(m for m in owner["methods"] if m["name"] == "restore")
            invokes = [r for r in method["instructions"] if r["opcode"] == "0xb8"]
            method["instructions"][0]["branch_target_offset"] = invokes[0]["offset"]
            result = self._plan(owner)
            self.assertEqual(result["original_accepted_no_incoming_edge_sites"], 1)

    def test_wrong_jar_pin_and_output_collision_preserve_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            out = root / "out"
            with self.assertRaisesRegex(
                TypedWriteChainError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                private_typed_write_chain_replay(
                    jar, "p/Demo.class", "restore", "(Ljava/lang/String;)V",
                    out, original_sha256="0" * 64
                )
            self.assertFalse(out.exists())
            out.mkdir()
            sentinel = out / "KEEP"
            sentinel.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                TypedWriteChainError, "OUTPUT_ALREADY_EXISTS"
            ):
                private_typed_write_chain_replay(
                    jar, "p/Demo.class", "restore", "(Ljava/lang/String;)V",
                    out, original_sha256=self._sha(jar)
                )
            self.assertEqual(sentinel.read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

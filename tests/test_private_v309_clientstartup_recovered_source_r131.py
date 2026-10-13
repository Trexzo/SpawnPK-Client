"""R131: checked-in actual restored Java source, original opcode witness digest.

The original proprietary v309 client is not uploaded to GitHub CI.
The frozen instruction fingerprint was independently read from exact v309.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from spk_recovery.private_v309_clientstartup_frame_r131 import (
    VerifiedClientStartUpR131Error, _stackmap,
    rebind_clientstartup_stackmap,
)


SOURCE_SHA256 = "bcb0481037a066a6bc1687160a4d4274743a6581005f487aca070d2750139e7a"
ORIGINAL_V309_OPCODE_OPERAND_MANIFEST_SHA256 = (
    "9f83a6efc7fc7be4748671d4255d2171cab8275144cc55623c2ab05b910f3af7"
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap")
                     and shutil.which("java"),
                     "JDK needed for real Java9 source verification")
class RecoveredClientStartUpR131Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = Path(__file__).resolve().parents[1]
        self.java_source = (
            self.repo / "source-candidates" / "v309" / "src" /
            "rs" / "runelite" / "events" / "ClientStartUp.java"
        )
        self.assertTrue(self.java_source.is_file())
        self.assertEqual(hashlib.sha256(
            self.java_source.read_bytes()).hexdigest(), SOURCE_SHA256)
        self.empty = self.root / "empty-classpath"
        self.empty.mkdir()
        self.compiled = self.root / "compiled"
        self.compiled.mkdir()
        cmd = [
            shutil.which("javac"), "--release", "9",
            "-g:none", "-proc:none", "-implicit:none",
            "-encoding", "UTF-8",
            "-classpath", str(self.empty), "-sourcepath", str(self.empty),
            "-d", str(self.compiled), str(self.java_source),
        ]
        result = subprocess.run(cmd, capture_output=True)
        self.assertEqual(result.returncode, 0,
                         result.stderr.decode(errors="replace"))
        self.owner = (
            self.compiled / "rs" / "runelite" / "events" /
            "ClientStartUp.class"
        )
        self.assertTrue(self.owner.is_file())
        self.original_compiled_sha = hashlib.sha256(
            self.owner.read_bytes()).hexdigest()
        self.repaired_root = self.root / "repaired"
        self.renamed_class = (
            self.repaired_root / "rs" / "runelite" / "events" /
            "ClientStartUp.class"
        )
        self.renamed_class.parent.mkdir(parents=True)

    @staticmethod
    def _instruction_manifest(javap_output):
        rows = []
        for line in javap_output.splitlines():
            match = re.match(
                r"\s*(\d+):\s+([a-z][a-z_0-9]*)(.*)", line)
            if match:
                operand = re.sub(r"#\d+", "", match.group(3)).strip()
                operand = re.sub(r"\s+", " ", operand)
                rows.append((int(match.group(1)), match.group(2), operand))
        return rows

    def test_recovered_java_source_matches_original_instruction_witness(self):
        decompiled = subprocess.run([
            shutil.which("javap"), "-p", "-c", "-s",
            "-classpath", str(self.compiled),
            "rs.runelite.events.ClientStartUp",
        ], capture_output=True, text=True, check=True).stdout
        rows = self._instruction_manifest(decompiled)
        self.assertEqual(len(rows), 33)
        digest = hashlib.sha256(json.dumps(
            rows, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        self.assertEqual(
            digest, ORIGINAL_V309_OPCODE_OPERAND_MANIFEST_SHA256)

    def test_exact_original_stackmap_rebind_preserves_source_code(self):
        pre = _stackmap(self.owner.read_bytes())
        self.assertTrue(
            pre["raw"].startswith(bytes.fromhex("00030708fc000e07")))
        report = rebind_clientstartup_stackmap(
            self.owner, self.renamed_class,
            compiled_class_sha256=self.original_compiled_sha)
        after = _stackmap(self.renamed_class.read_bytes())
        self.assertEqual(after["raw"],
                         bytes.fromhex("00030708f9000e"))
        self.assertEqual(pre["code_bytes"], after["code_bytes"])
        self.assertEqual(report["method_count"], 5)
        self.assertEqual(report["field_count"], 0)
        self.assertTrue(report["executable_code_bytes_unchanged"])
        self.assertFalse(report["original_client_code_bytes_transferred"])
        self.assertFalse(report["whole_client_source_tree_accepted"])

    def test_rebuilt_repaired_class_verifies_and_behaves_without_original_jar(self):
        rebind_clientstartup_stackmap(
            self.owner, self.renamed_class,
            compiled_class_sha256=self.original_compiled_sha)
        verifier = self.root / "VerifyRecovered.java"
        verifier.write_text(
            "public class VerifyRecovered {\n"
            "  public static void main(String[] args) throws Exception {\n"
            "    Class<?> type = Class.forName("
            "\"rs.runelite.events.ClientStartUp\");\n"
            "    Object event = type.getDeclaredConstructor().newInstance();\n"
            "    if (!event.equals(event)) throw new Exception(\"equals\");\n"
            "    if (!\"ClientStartUp()\".equals(event.toString())) "
            "throw new Exception(\"text\");\n"
            "    System.out.println(\"R131_SOURCE_ONLY_VM_VERIFY_PASS\");\n"
            "  }\n"
            "}\n",
            encoding="utf-8")
        classes = self.root / "trusted-test-code"
        classes.mkdir()
        p = subprocess.run([
            shutil.which("javac"), "--release", "9",
            "-classpath", str(self.repaired_root),
            "-d", str(classes), str(verifier),
        ], capture_output=True)
        self.assertEqual(p.returncode, 0,
                         p.stderr.decode(errors="replace"))
        result = subprocess.run([
            shutil.which("java"), "-Xverify:all", "-classpath",
            os.pathsep.join((str(self.repaired_root), str(classes))),
            "VerifyRecovered",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("R131_SOURCE_ONLY_VM_VERIFY_PASS", result.stdout)

    def test_tampered_compiler_preimage_is_rejected(self):
        data = bytearray(self.owner.read_bytes())
        original = _stackmap(data)
        data[original["frame_start"] + 4] ^= 1
        self.owner.write_bytes(data)
        with self.assertRaisesRegex(
                VerifiedClientStartUpR131Error,
                "R131_EXPECTED_SOURCE_JAVAC_APPEND_FRAME_NOT_PRESENT"):
            rebind_clientstartup_stackmap(
                self.owner, self.renamed_class,
                compiled_class_sha256=hashlib.sha256(data).hexdigest())
        self.assertFalse(self.renamed_class.exists())

    def test_wrong_source_compiled_hash_is_rejected(self):
        with self.assertRaisesRegex(
                VerifiedClientStartUpR131Error,
                "R131_JAVA9_PREIMAGE_SHA256_MISMATCH"):
            rebind_clientstartup_stackmap(
                self.owner, self.renamed_class,
                compiled_class_sha256="0" * 64)
        self.assertFalse(self.renamed_class.exists())

    def test_fresh_output_is_required(self):
        self.renamed_class.write_bytes(b"do not overwrite")
        with self.assertRaisesRegex(
                VerifiedClientStartUpR131Error,
                "R131_FRESH_PRIVATE_SOURCE_BUILT_CLASS_OUTPUT_REQUIRED"):
            rebind_clientstartup_stackmap(
                self.owner, self.renamed_class,
                compiled_class_sha256=self.original_compiled_sha)
        self.assertEqual(self.renamed_class.read_bytes(), b"do not overwrite")

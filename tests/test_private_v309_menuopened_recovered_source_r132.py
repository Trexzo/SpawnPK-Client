"""R132: second real restored v309 event Java class, replayed source-first."""
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


OWNER = "rs/runelite/events/MenuOpened"
SOURCE_SHA = "bf7908561ce437099912fbad55e1a9e7e0bdabd8afae56cd3c28bd5fc622fef9"
ORIGINAL_OPCODE_SHA = "4b8ff0ac0750b72b766398f080ec4443c813af77cfb2cb66746cecee07e526ad"


@unittest.skipUnless(shutil.which("javac") and shutil.which("java") and
                     shutil.which("javap"), "JDK required")
class RestoredMenuOpenedR132Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = (Path(__file__).resolve().parents[1] /
                       "source-candidates/v309/src/" / (OWNER + ".java"))
        self.assertTrue(self.source.is_file())
        self.assertEqual(hashlib.sha256(
            self.source.read_bytes()).hexdigest(), SOURCE_SHA)
        empty = self.root / "empty-classpath"
        empty.mkdir()
        self.preimage_root = self.root / "source-compiled"
        self.preimage_root.mkdir()
        cmd = [
            shutil.which("javac"), "--release", "9", "-g:none",
            "-proc:none", "-implicit:none",
            "-classpath", str(empty), "-sourcepath", str(empty),
            "-d", str(self.preimage_root), str(self.source),
        ]
        p = subprocess.run(cmd, capture_output=True)
        self.assertEqual(p.returncode, 0,
                         p.stderr.decode(errors="replace"))
        self.preimage = self.preimage_root / (OWNER + ".class")
        self.assertTrue(self.preimage.is_file())
        self.original_compiled_sha = hashlib.sha256(
            self.preimage.read_bytes()).hexdigest()
        self.repaired_root = self.root / "verified-rebound"
        self.repaired = self.repaired_root / (OWNER + ".class")
        self.repaired.parent.mkdir(parents=True)

    def rebind(self, **kwargs):
        return rebind_clientstartup_stackmap(
            self.preimage, self.repaired,
            compiled_class_sha256=self.original_compiled_sha,
            expected_owner=OWNER, **kwargs)

    def test_source_java9_instructions_equal_original_frozen_witness(self):
        r = subprocess.run([
            shutil.which("javap"), "-p", "-c", "-s",
            "-classpath", str(self.preimage_root),
            OWNER.replace("/", "."),
        ], capture_output=True, text=True, check=True)
        rows = []
        for line in r.stdout.splitlines():
            match = re.match(
                r"\s*(\d+):\s+([a-z][a-z_0-9]*)(.*)", line)
            if match:
                operand = re.sub(r"#\d+", "", match.group(3)).strip()
                operand = re.sub(r"\s+", " ", operand)
                rows.append((int(match.group(1)),
                             match.group(2), operand))
        self.assertEqual(len(rows), 33)
        fingerprint = hashlib.sha256(json.dumps(
            rows, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        self.assertEqual(fingerprint, ORIGINAL_OPCODE_SHA)

    def test_metadata_only_original_stackmap_three_frames(self):
        before = _stackmap(self.preimage.read_bytes())
        self.assertTrue(before["raw"].startswith(
            bytes.fromhex("00030708fc000e07")))
        proof = self.rebind()
        after = _stackmap(self.repaired.read_bytes())
        self.assertEqual(after["raw"],
                         bytes.fromhex("00030708f9000e"))
        self.assertEqual(after["code_bytes"], before["code_bytes"])
        self.assertEqual(proof["method_count"], 5)
        self.assertTrue(proof["executable_code_bytes_unchanged"])
        self.assertFalse(proof["whole_client_source_tree_accepted"])

    def test_independent_rebuilt_class_jvm_verification(self):
        self.rebind()
        verify = self.root / "VerifyMenuOpened.java"
        verify.write_text(
            "public class VerifyMenuOpened {\n"
            "  public static void main(String[] args) throws Exception {\n"
            "    Class<?> t = Class.forName("
            "\"rs.runelite.events.MenuOpened\");\n"
            "    Object e = t.getDeclaredConstructor().newInstance();\n"
            "    if (!e.equals(e)) throw new Exception(\"self equals\");\n"
            "    if (!\"MenuOpened()\".equals(e.toString())) "
            "throw new Exception(\"toString\");\n"
            "    System.out.println(\"R132_REAL_JAVA_SOURCE_VM_PASS\");\n"
            "  }\n"
            "}\n",
            encoding="utf-8")
        trusted = self.root / "trusted-verification"
        trusted.mkdir()
        p = subprocess.run([
            shutil.which("javac"), "--release", "9",
            "-classpath", str(self.repaired_root),
            "-d", str(trusted), str(verify),
        ], capture_output=True)
        self.assertEqual(p.returncode, 0,
                         p.stderr.decode(errors="replace"))
        p = subprocess.run([
            shutil.which("java"), "-Xverify:all", "-classpath",
            os.pathsep.join((str(self.repaired_root), str(trusted))),
            "VerifyMenuOpened",
        ], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("R132_REAL_JAVA_SOURCE_VM_PASS", p.stdout)

    def test_unverified_owner_is_rejected(self):
        with self.assertRaisesRegex(
                VerifiedClientStartUpR131Error,
                "R132_UNVERIFIED_OR_UNSUPPORTED_EVENT_CLASS_OWNER"):
            rebind_clientstartup_stackmap(
                self.preimage, self.repaired,
                compiled_class_sha256=self.original_compiled_sha,
                expected_owner="rs/runelite/events/Unknown")
        self.assertFalse(self.repaired.exists())

    def test_source_compiled_hash_mismatch_is_rejected(self):
        with self.assertRaisesRegex(
                VerifiedClientStartUpR131Error,
                "R131_JAVA9_PREIMAGE_SHA256_MISMATCH"):
            rebind_clientstartup_stackmap(
                self.preimage, self.repaired,
                compiled_class_sha256="0" * 64,
                expected_owner=OWNER)
        self.assertFalse(self.repaired.exists())

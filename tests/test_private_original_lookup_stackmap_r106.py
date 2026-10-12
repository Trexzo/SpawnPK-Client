"""R106: exact Java9 three-constant case-insensitive enum lookup StackMap fix."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_original_lookup_stackmap_r106 import (
    OriginalEnumStackmapError,
    _frames,
    restore_single_original_lookup_frame,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "Java9-compatible javac/java required")
class OriginalJava9EnumStackmapTests(unittest.TestCase):
    def setUp(self):
        temp = self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        folder = self.root / "src" / "p"
        folder.mkdir(parents=True)
        java = folder / "Lookup.java"
        java.write_text(
            "package p; public class Lookup {"
            "public enum Mode { A, B, C;"
            "public static Mode lookup(String text) {"
            "for (Mode entry : values()) {"
            "if (entry.name().equalsIgnoreCase(text)) return entry;"
            "} return A; }"
            "}"
            "}", encoding="utf-8")
        self.classes = self.root / "classes"
        self.classes.mkdir()
        p = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(self.classes), str(java)],
            capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.entry = self.classes / "p" / "Lookup$Mode.class"
        self.candidate = self.entry.read_bytes()
        self.name = "lookup"
        self.descriptor = "(Ljava/lang/String;)Lp/Lookup$Mode;"
        record = _frames(self.candidate, self.name, self.descriptor)
        self.assertEqual(len(record["frames"]), 14)
        self.assertEqual(record["frames"][-3:], b"\xf8\x00\x05")
        # This independently manufactures the original-style *symbolic*
        # frame encoding in a synthetic fixture; the real pinned original
        # remains private and is not bundled in hosted CI.
        before = bytearray(self.candidate)
        replacement = record["frames"][:-3] + b"\xff\x00\x05\x00\x00\x00\x00"
        code = record["code_attr_offset"]
        length_pos = code + 2
        nested_len_pos = code + 6 + record["frames_offset_in_code"] + 2
        payload_pos = code + 6 + record["frames_offset_in_code"] + 6
        before[length_pos:length_pos + 4] = (
            record["code_attr_length"] + 4).to_bytes(4, "big")
        before[nested_len_pos:nested_len_pos + 4] = (
            len(replacement)).to_bytes(4, "big")
        self.original = (
            before[:payload_pos] + replacement +
            before[payload_pos + len(record["frames"]):]
        )
        self.assertEqual(
            _frames(bytes(self.original), self.name, self.descriptor)["frames"][-7:],
            b"\xff\x00\x05\x00\x00\x00\x00")
        self.original = bytes(self.original)

    def test_exact_original_full_frame_restored_no_code_changes(self):
        corrected = restore_single_original_lookup_frame(
            self.original, self.candidate,
            method_name=self.name, descriptor=self.descriptor)
        self.assertEqual(corrected, self.original)
        self.assertEqual(len(corrected)-len(self.candidate), 4)
        self.assertEqual(
            profile_class_field_accesses(self.candidate)["fields"],
            profile_class_field_accesses(corrected)["fields"])
        a = profile_class_field_accesses(self.candidate)
        b = profile_class_field_accesses(corrected)
        for old, new in zip(a["methods"], b["methods"]):
            self.assertEqual(old["instructions"], new["instructions"])
        changed_class = self.root / "patched" / "p" / "Lookup$Mode.class"
        changed_class.parent.mkdir(parents=True)
        changed_class.write_bytes(corrected)
        outer = self.classes / "p" / "Lookup.class"
        (changed_class.parent / "Lookup.class").write_bytes(outer.read_bytes())
        probe = self.root / "Probe.java"
        probe.write_text(
            "package p; public class Probe{public static void main(String[]x){"
            'if(Lookup.Mode.lookup("b")!=Lookup.Mode.B)'
            'throw new Error("original frame lookup");'
            "}}", encoding="utf-8")
        proc = subprocess.run(
            ["javac", "--release", "9", "-proc:none",
             "-d", str(self.root / "patched"), str(probe)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = subprocess.run(
            ["java", "-cp", str(self.root / "patched"), "p.Probe"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unmodified_chop_as_original_is_not_accepted(self):
        with self.assertRaisesRegex(
            OriginalEnumStackmapError,
            "ORIGINAL_CANDIDATE_LOOKUP_FINAL_FRAME_NOT_REVIEWED_SHAPE",
        ):
            restore_single_original_lookup_frame(
                self.candidate, self.candidate,
                method_name=self.name, descriptor=self.descriptor)

    def test_mutated_candidate_final_frame_is_rejected(self):
        mutated = bytearray(self.candidate)
        record = _frames(self.candidate, self.name, self.descriptor)
        position = (
            record["code_attr_offset"] + 6 +
            record["frames_offset_in_code"] + 6 +
            len(record["frames"]) - 1
        )
        mutated[position] = 6
        with self.assertRaisesRegex(
            OriginalEnumStackmapError,
            "ORIGINAL_CANDIDATE_LOOKUP_FINAL_FRAME_NOT_REVIEWED_SHAPE",
        ):
            restore_single_original_lookup_frame(
                self.original, bytes(mutated),
                method_name=self.name, descriptor=self.descriptor)

    def test_wrong_look_up_descriptor_does_not_qualify(self):
        with self.assertRaisesRegex(
            OriginalEnumStackmapError, "EXACT_LOOKUP_STACKMAPTABLE_NOT_UNIQUE",
        ):
            restore_single_original_lookup_frame(
                self.original, self.candidate,
                method_name=self.name,
                descriptor="(Ljava/lang/String;)Ljava/lang/String;")

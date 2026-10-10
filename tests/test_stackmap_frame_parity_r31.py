"""R31: JVM StackMapTable verification-frame decoding, with no private clients."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import (
    BytecodeProfileError,
    _stackmap_table,
    profile_class_field_accesses,
)
from spk_recovery.source_method_parity import build_report


def _synthetic_cp():
    # Two different class indexes can resolve to the same JVM internal name.
    return [None, (7, 2), (1, "java/lang/String"), (7, 2)]


def _parse(payload, code=b"\x03\xac", offsets=(0, 1)):
    return _stackmap_table(
        payload, _synthetic_cp(), code=code,
        instructions=[{"offset": off} for off in offsets],
    )


class StackMapFrameUnitTests(unittest.TestCase):
    def test_same_frame_and_extended_equivalent_shapes_are_distinct(self):
        self.assertEqual(
            _parse(bytes.fromhex("000100")),
            [{"frame_type": 0, "bytecode_offset": 0}],
        )
        self.assertEqual(
            _parse(bytes.fromhex("0001fb0000")),
            [{"frame_type": 251, "bytecode_offset": 0}],
        )
        self.assertNotEqual(
            _parse(bytes.fromhex("000100")),
            _parse(bytes.fromhex("0001fb0000")),
        )

    def test_object_type_is_resolved_without_cp_numeric_identity(self):
        first = _parse(bytes.fromhex("000140070001"))
        second = _parse(bytes.fromhex("000140070003"))
        expected = [{
            "frame_type": 64, "bytecode_offset": 0,
            "stack": [{"kind": "object", "class": "java/lang/String"}],
        }]
        self.assertEqual(first, expected)
        self.assertEqual(second, expected)

    def test_all_major_frame_formats(self):
        # Same locals/stack, append, chop and full-frame cases.
        cases = [
            "00014001",       # same_locals_1_stack, Integer
            "0001f7000001",   # extended same_locals_1_stack
            "0001f80000",     # chop 3 locals
            "0001fa0000",     # chop 1 local
            "0001fb0000",     # same_frame_extended
            "0001fc000001",   # append 1 integer local
            "0001ff00000001010000", # full frame with one integer local
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                self.assertEqual(len(_parse(bytes.fromhex(raw))), 1)

    def test_uninitialized_type_must_target_new(self):
        payload = bytes.fromhex("000140080000")
        good = _parse(payload, code=b"\xbb\x00\x01\xb0", offsets=(0, 3))
        self.assertEqual(good[0]["stack"][0],
                         {"kind": "uninitialized", "new_offset": 0})
        with self.assertRaisesRegex(BytecodeProfileError, "uninitialized target not new"):
            _parse(payload)

    def test_bad_frame_types_offsets_and_trailing_data_fail_closed(self):
        for bad, diagnostic in [
            ("000180", "reserved StackMapTable frame type"),
            ("00017f01", "frame not at instruction boundary"),
            ("000102", "frame not at instruction boundary"),
            ("00010000", "trailing bytes in StackMapTable"),
            ("00014009", "invalid StackMapTable verification type"),
            ("0001ff", "unexpected EOF"),
        ]:
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(BytecodeProfileError, diagnostic):
                    _parse(bytes.fromhex(bad))

    def test_append_full_frame_tracks_resolved_reference(self):
        frame = _parse(bytes.fromhex("0001ff000000010700010000"))
        self.assertEqual(frame[0]["locals"], [
            {"kind": "object", "class": "java/lang/String"},
        ])
        self.assertEqual(frame[0]["stack"], [])
        self.assertEqual(frame[0]["bytecode_offset"], 0)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class StackMapCompiledFixtureTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, code: str) -> Path:
        src = root / name / "src" / "p"
        classes = root / name / "classes"
        src.mkdir(parents=True)
        classes.mkdir(parents=True)
        file = src / "Branch.java"
        file.write_text(
            "package p; public class Branch { "
            "public String choose(boolean enabled) { "
            + code + " } }", encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-d", str(classes), str(file)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / f"{name}.jar"
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "Branch.class", "p/Branch.class")
        return jar

    def test_real_javac_branch_frames_and_parity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._jar(
                root, "original",
                'if (enabled) return "yes"; return "no";',
            )
            candidate = self._jar(
                root, "candidate",
                'if (enabled) return "yes"; return "no";',
            )
            with ZipFile(original) as archive:
                profile = profile_class_field_accesses(
                    archive.read("p/Branch.class")
                )
            method, = [
                m for m in profile["methods"]
                if m["name"] == "choose" and m["descriptor"] == "(Z)Ljava/lang/String;"
            ]
            self.assertTrue(method["stackmap_table_present"])
            self.assertGreaterEqual(len(method["stackmap_frames"]), 1)
            self.assertTrue(all("bytecode_offset" in frame
                                for frame in method["stackmap_frames"]))
            result = build_report(
                original, candidate,
                original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                entry_path="p/Branch.class",
                method_name="choose",
                descriptor="(Z)Ljava/lang/String;",
            )
            self.assertEqual(result["classification"], "CANDIDATE_INSTRUCTION_PARITY")
            self.assertTrue(result["checks"]["resolved_stackmap_frames"])
            self.assertFalse(result["full_method_equivalence_certified"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from spk_recovery.modified_utf8 import ModifiedUtf8Error, decode_modified_utf8
from spk_recovery.classfile import ClassFormatError, parse_class
from spk_recovery.bytecode_profile import (
    BytecodeProfileError,
    _instruction_length,
    _invokeinterface_argument_slots,
    profile_class_field_accesses,
    profile_class_utf8_constants,
)


class StrictModifiedUtf8Tests(unittest.TestCase):
    def test_plain_ascii_and_bmp_unicode(self):
        self.assertEqual(decode_modified_utf8(b"abc123"), "abc123")
        self.assertEqual(decode_modified_utf8("Résumé".encode("utf-8")), "Résumé")
        self.assertEqual(decode_modified_utf8("日本語".encode("utf-8")), "日本語")

    def test_modified_utf8_zero_and_supplementary_surrogate_pairs(self):
        self.assertEqual(decode_modified_utf8(b"left\xc0\x80right"), "left\x00right")
        self.assertEqual(
            decode_modified_utf8(b"\xed\xa0\xbd\xed\xb8\x80"), "\U0001f600"
        )

    def test_lone_utf16_surrogates_are_retained_as_distinct_exact_code_units(self):
        self.assertEqual(decode_modified_utf8(b"\xed\xa0\x80"), "\ud800")
        self.assertEqual(decode_modified_utf8(b"\xed\xb0\x80"), "\udc00")
        self.assertNotEqual(
            decode_modified_utf8(b"\xed\xa0\x80"),
            decode_modified_utf8(b"\xed\xa0\x81"),
        )

    def test_surrogate_json_and_structural_hash_are_lossless(self):
        import json
        from spk_recovery.indexer import write_index
        from spk_recovery.classfile import ParsedClass
        surrogate = decode_modified_utf8(b"\xed\xa0\x80")
        obj = ParsedClass(
            name="Synthetic", major=55, minor=0, access=1,
            super_name="java/lang/Object", interfaces=[],
            utf8_strings=[], literal_strings=[surrogate],
            numeric_constants=[], fields=[], methods=[], attributes=[],
            inner_outer_name=None, inner_simple_name=None,
            enclosing_class_name=None,
        )
        self.assertEqual(len(obj.structural_sha256()), 64)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "index.json"
            write_index({"surrogate": surrogate, "normal": "caf\u00e9"}, target)
            content = target.read_text(encoding="utf-8")
            self.assertIn(r"\ud800", content)
            self.assertEqual(json.loads(content)["surrogate"], surrogate)
            self.assertEqual(json.loads(content)["normal"], "caf\u00e9")

    def test_no_lossy_replacement_or_permissive_utf8(self):
        bad = (
            b"\x00",                 # literal zero forbidden
            b"\xc0\x81",             # overlong ASCII
            b"\xc1\x81",
            b"\xc2",                 # truncated two-byte
            b"\xe0\x80\x80",       # overlong three-byte
            b"\xe2\x82",            # truncated three-byte
            b"\xf0\x9f\x98\x80",  # four-byte UTF-8 is not JVM MUTF-8
            b"\x80",                 # orphan continuation
            b"\xff",
        )
        for item in bad:
            with self.subTest(value=item), self.assertRaises(ModifiedUtf8Error):
                decode_modified_utf8(item)

    def test_reject_non_bytes_input(self):
        with self.assertRaises(ModifiedUtf8Error):
            decode_modified_utf8("not bytes")  # type: ignore[arg-type]


class ExactJVMOpcodeTests(unittest.TestCase):
    def test_reserved_opcodes_always_fail(self):
        for opcode in range(0xCA, 0x100):
            with self.subTest(opcode=opcode), self.assertRaises(BytecodeProfileError):
                _instruction_length(bytes((opcode, 0xB1)), 0)

    def test_wide_rejects_invalid_or_legacy_ret_nested_opcodes(self):
        for nested in (0x00, 0xA9, 0xFF):
            with self.subTest(nested=nested), self.assertRaises(BytecodeProfileError):
                _instruction_length(bytes((0xC4, nested, 0, 0)), 0)
        self.assertEqual(_instruction_length(bytes((0xC4, 0x15, 0, 1)), 0), 4)
        self.assertEqual(_instruction_length(bytes((0xC4, 0x84, 0, 1, 0, 2)), 0), 6)

    def test_interface_argument_slots_include_receiver_and_wide_values(self):
        checks = {
            "()V": 1,
            "(I)V": 2,
            "(J)V": 3,
            "(D[JLjava/lang/String;)I": 5,
            "([[DLjava/lang/Runnable;[J)Ljava/lang/Object;": 4,
        }
        for desc, slots in checks.items():
            with self.subTest(desc=desc):
                self.assertEqual(_invokeinterface_argument_slots(desc), slots)

    def test_interface_rejects_invalid_descriptors(self):
        bad = ("", "(V)V", "(I)VX", "([V)V", "([[)V", "(I)", "I)V",
               "([Ljava/lang/String)V", "(Ljava/lang/String;)X")
        for desc in bad:
            with self.subTest(desc=desc), self.assertRaises(BytecodeProfileError):
                _invokeinterface_argument_slots(desc)


@unittest.skipUnless(shutil.which("javac"), "Java compiler required for exact classfile fixture")
class JavaCompilerModifiedUtf8Tests(unittest.TestCase):
    def _class_bytes(self) -> bytes:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            f = root / "JvmUtf8ProofFixture.java"
            f.write_text(
                r'public final class JvmUtf8ProofFixture {'
                r' public static final String VALUE="left\0right";'
                r' public static void call(Runnable r){r.run();}'
                r'}',
                encoding="utf-8",
            )
            result = subprocess.run(
                ["javac", "--release", "11", "-proc:none", "-d", str(root), str(f)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return (root / "JvmUtf8ProofFixture.class").read_bytes()

    def test_real_javac_modified_null_round_trip_in_both_decoders(self):
        data = self._class_bytes()
        self.assertIn(b"left\xc0\x80right", data)
        self.assertIn("left\x00right", parse_class(data).literal_strings)
        self.assertIn("left\x00right", profile_class_utf8_constants(data))
        calls = profile_class_field_accesses(data)
        method = next(x for x in calls["methods"] if x["name"] == "call")
        invoke = next(x for x in method["instructions"] if x["opcode"] == "0xb9")
        self.assertEqual(invoke["invokeinterface_count"], 1)
        self.assertEqual(invoke["invokeinterface_reserved"], 0)

    def test_mutating_real_javac_constant_pool_to_invalid_mutf8_fails_closed(self):
        data = self._class_bytes()
        self.assertEqual(data.count(b"left\xc0\x80right"), 1)
        malformed = data.replace(b"left\xc0\x80right", b"left\xc0\x81right")
        with self.assertRaises(ClassFormatError):
            parse_class(malformed)
        with self.assertRaises(BytecodeProfileError):
            profile_class_field_accesses(malformed)


if __name__ == "__main__":
    unittest.main()

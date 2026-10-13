"""R114: bounded original 697-source R81 and unresolved 161 StackMap frames."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import spk_recovery.private_recompiled_v309_loader_preimage_r114 as gate
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)


def fake_method(length, name):
    return {
        "name": name, "descriptor": "()V", "access": 9,
        "instructions": [
            {"offset": i, "opcode": "0xb1"} for i in range(length)
        ],
        "exception_handlers": [], "signature": None,
        "max_stack": 4 if length == 697 else 1,
        "max_locals": 6 if length == 697 else 0,
        "stackmap_table_present": length == 697,
        "stackmap_frames": [],
    }


def frame_pair():
    left = [{"frame_type": 15, "bytecode_offset": i * 4}
            for i in range(161)]
    right = deepcopy(left)
    left[1] = {
        "frame_type": 255, "bytecode_offset": 4,
        "locals": [{"kind": "top"}, {"kind": "object", "class": "java/util/Properties"}],
        "stack": [{"kind": "object", "class": "java/lang/Exception"}],
    }
    right[1] = {
        "frame_type": 255, "bytecode_offset": 4,
        "locals": [{"kind": "object", "class": "java/io/File"},
                   {"kind": "object", "class": "java/util/Properties"},
                   {"kind": "object", "class": "java/io/FileInputStream"}],
        "stack": [{"kind": "object", "class": "java/lang/Exception"}],
    }
    for i, la, rb in ((23, 253, 252), (25, 249, 250),
                      (156, 249, 251), (158, 251, 248)):
        left[i]["frame_type"] = la
        right[i]["frame_type"] = rb
    left[23]["appended_locals"] = [
        {"kind": "top"}, {"kind": "integer"}]
    right[23]["appended_locals"] = [{"kind": "integer"}]
    return left, right


class Original697PreimageContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original_jar = self.root / "original.jar"
        self.candidate_jar = self.root / "candidate.jar"
        for jar, marker in ((self.original_jar, b"fake original"),
                            (self.candidate_jar, b"source compiled")):
            with ZipFile(jar, "w") as zipout:
                zipout.writestr("p/Owner.class", marker)
        self.output = self.root / "private-output"
        self.old = {
            "internal_name": "p/Owner", "classfile_major": 53,
            "class_access": 49, "super_name": "java/lang/Object",
            "fields": [{"name": "f" + str(i)} for i in range(126)],
            "methods": [fake_method(n, "m" + str(i))
                        for i, n in enumerate(
                            (2, 2, 2, 3, 4, 20, 41, 213, 364, 697))],
        }
        self.old["methods"][-1]["max_stack"] = 4
        self.old["methods"][-1]["max_locals"] = 6
        self.new = {
            "internal_name": "p/Owner", "classfile_major": 53,
            "class_access": 49, "super_name": "java/lang/Object",
            "fields": [],
            "methods": [deepcopy(self.old["methods"][-1])],
        }
        self.old["methods"][-1]["stackmap_frames"], self.new["methods"][0][
            "stackmap_frames"] = frame_pair()
        self.compared = 0

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def expected_parity(self, *args):
        self.compared += 1
        self.assertEqual(args[1:3], ("m9", "()V"))
        self.assertEqual(args[4:6], ("m9", "()V"))
        self.assertEqual(args[6:9], ([], [], []))
        return {
            "original_instructions_with_all_semantic_operands_compared": 697,
            "original_explicit_branches": 120,
            "original_ordered_typed_exception_entries": 44,
            "original_ordered_static_writes": 78,
            "all_parsed_JVM_operands_equal_with_private_aliases": True,
            "original_invokedynamic_bootstrap_semantics_equal": True,
        }

    def mock_profiles(self, comparator=None):
        self.addCleanup(patch.stopall)
        def profile(path, entry):
            self.assertEqual(entry, "p/Owner.class")
            return deepcopy(self.old if Path(path) == self.original_jar
                            else self.new)
        patch.object(gate, "profile_jar_class", profile).start()
        patch.object(gate, "compare_all_method_operands",
                     comparator or self.expected_parity).start()

    def call(self, pin=None, source_pin=None):
        return gate.accept_original_recompiled_loader_preimage(
            self.original_jar, self.candidate_jar,
            "p/Owner.class", self.output,
            original_sha256=pin or self.digest(self.original_jar),
            candidate_sha256=source_pin or self.digest(self.candidate_jar),
        )

    def test_positive_true_preimage_frontier_is_not_exact_stackmap_cert(self):
        self.mock_profiles()
        report = self.call()
        self.assertEqual(self.compared, 1)
        self.assertEqual(report["original_697_loader_jvm_instructions_R81_compared"], 697)
        self.assertEqual(report["original_loader_ordered_typed_handlers_equal"], 44)
        self.assertEqual(report["original_loader_ordered_static_writes_equal"], 78)
        self.assertEqual(report["original_loader_stackmap_ordinal_destinations_equal"], 161)
        self.assertEqual(report["original_loader_stackmap_frame_encoding_category_differences"], 4)
        self.assertEqual(report["original_loader_stackmap_explicit_local_payload_differences"], 2)
        self.assertEqual(report["original_loader_stackmap_stack_payload_differences"], 0)
        self.assertFalse(report["R114_exact_original_StackMap_encoding_accepted"])
        self.assertFalse(report["R107_complete_owner_accepted"])
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_original_pin_vetoes_before_parsing(self):
        self.mock_profiles()
        with self.assertRaisesRegex(gate.OriginalLoaderR114Error,
                                    "SHA256_MISMATCH"):
            self.call(pin="0" * 64)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.compared, 0)

    def test_missing_original_frame_is_a_hard_failure(self):
        self.old["methods"][-1]["stackmap_frames"].pop()
        self.mock_profiles()
        with self.assertRaisesRegex(gate.OriginalLoaderR114Error,
                                    "161_FRAME_REQUIRED"):
            self.call()
        self.assertFalse(self.output.exists())

    def test_wrong_frame_instruction_ordinal_vetoes(self):
        self.new["methods"][0]["stackmap_frames"][3]["bytecode_offset"] = 15
        self.mock_profiles()
        with self.assertRaisesRegex(gate.OriginalLoaderR114Error,
                                    "NOT_ORDINAL_ALIGNED"):
            self.call()
        self.assertFalse(self.output.exists())

    def test_changed_original_frame_category_delta_must_not_be_hidden(self):
        self.new["methods"][0]["stackmap_frames"][23]["frame_type"] = 253
        self.mock_profiles()
        with self.assertRaisesRegex(gate.OriginalLoaderR114Error,
                                    "NOT_THE_PINNED_FRONTIER"):
            self.call()
        self.assertFalse(self.output.exists())

    def test_changed_full_frame_locals_are_not_ignored(self):
        self.new["methods"][0]["stackmap_frames"][1]["locals"] = (
            self.old["methods"][-1]["stackmap_frames"][1]["locals"])
        self.mock_profiles()
        with self.assertRaisesRegex(gate.OriginalLoaderR114Error,
                                    "NOT_THE_PINNED_FRONTIER"):
            self.call()
        self.assertFalse(self.output.exists())

    def test_r81_rejects_changed_original_member_operands(self):
        def error(*args):
            raise WholeMethodOperandError("symbolic mismatch")
        self.mock_profiles(comparator=error)
        with self.assertRaisesRegex(gate.OriginalLoaderR114Error,
                                    "R66_R81_FULL_697_JVM_OPERAND"):
            self.call()
        self.assertFalse(self.output.exists())

    def test_source_method_missing_does_not_substitute_other_method(self):
        self.new["methods"][0]["name"] = "another"
        self.mock_profiles()
        with self.assertRaisesRegex(gate.OriginalLoaderR114Error,
                                    "METHOD_JVM_IDENTITY_MISSING"):
            self.call()
        self.assertEqual(self.compared, 0)
        self.assertFalse(self.output.exists())


@unittest.skipUnless(shutil.which("javac"), "javac with Java9 target required")
class IndependentActualJava9R81LargeMethodTests(unittest.TestCase):
    def test_two_independently_compiled_697_op_sources_pass_r81(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profiles=[]
            for side in ("original", "candidate"):
                base=root/side
                src=base/"p"/"Owner.java"
                src.parent.mkdir(parents=True)
                src.write_text(
                    "package p;public final class Owner{"
                    "public static void writer(){"
                    + "System.out.println(1);"*232
                    + "}}", encoding="utf-8")
                classes=base/"classes"
                classes.mkdir()
                proc=subprocess.run(
                    ["javac","--release","9","-g:none","-proc:none",
                     "-d",str(classes),str(src)],
                    capture_output=True,text=True)
                self.assertEqual(proc.returncode,0,proc.stderr)
                jar=base/"candidate.jar"
                with ZipFile(jar,"w") as z:
                    z.write(classes/"p"/"Owner.class","p/Owner.class")
                profiles.append(profile_jar_class(jar,"p/Owner.class"))
            rows=[m for m in profiles[0]["methods"] if m["name"]=="writer"]
            self.assertEqual(len(rows),1)
            self.assertEqual(len(rows[0]["instructions"]),697)
            result=compare_all_method_operands(
                profiles[0],"writer","()V",
                profiles[1],"writer","()V",[],[],[])
            self.assertEqual(
                result["original_instructions_with_all_semantic_operands_compared"],697)
            self.assertTrue(result["all_parsed_JVM_operands_equal_with_private_aliases"])

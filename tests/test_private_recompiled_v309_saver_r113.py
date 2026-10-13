"""R113: mock-contracted 364 original saver + actual Java9 R81 large-method smoke."""
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

import spk_recovery.private_recompiled_v309_saver_r113 as gate
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.whole_method_operand_parity import (
    WholeMethodOperandError, compare_all_method_operands,
)


def fake_method(count, name):
    return {
        "name": name, "descriptor": "()V", "access": 10 if count == 364 else 9,
        "instructions": [{"opcode": "0xb1", "offset": i} for i in range(count)],
        "exception_handlers": [
            {"start_pc": 0, "end_pc": 920, "handler_pc": 923,
             "catch_type": "java/lang/Exception"}
        ] if count == 364 else [],
        "signature": None,
        "code_length": 929 if count == 364 else count,
        "max_stack": 6 if count == 364 else 1,
        "max_locals": 3 if count == 364 else 0,
        "stackmap_table_present": count == 364,
        "stackmap_frames": [
            {"frame_type": t, "bytecode_offset": i}
            for i, t in enumerate([252,255,36,250,251,23,23,251,255,4])
        ] if count == 364 else [],
    }


class OriginalSaverR113ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.orig = self.root / "original.jar"
        self.candidate = self.root / "candidate.jar"
        self.output = self.root / "accepted"
        for jar, marker in ((self.orig, b"original-private-v309"),
                            (self.candidate, b"rebuilt-independent-java9")):
            with ZipFile(jar, "w") as z:
                z.writestr("p/Owner.class", marker)
        self.original_sha = hashlib.sha256(self.orig.read_bytes()).hexdigest()
        self.candidate_sha = hashlib.sha256(
            self.candidate.read_bytes()).hexdigest()
        self.original = {
            "internal_name": "p/Owner", "classfile_major": 53,
            "class_access": 49, "super_name": "java/lang/Object",
            "fields": [{"name": f"field{i}", "descriptor": "Z", "access": 9}
                       for i in range(126)],
            "methods": [
                fake_method(n, f"m{i}") for i,n in enumerate(
                    [2,2,2,3,4,20,41,213,364,697]
                )],
        }
        self.candidate_profile = deepcopy(self.original)
        self.candidate_profile["methods"] = [
            fake_method(364, "m8")
        ]
        self.compare_called = 0

    def comparison(self, *args, **kwargs):
        self.compare_called += 1
        self.assertEqual(args[1:3], ("m8", "()V"))
        self.assertEqual(args[4:6], ("m8", "()V"))
        self.assertEqual(args[6:9], ([],[],[]))
        return {
            "original_instructions_with_all_semantic_operands_compared": 364,
            "original_ordered_typed_exception_entries": 1,
            "original_explicit_branches": 9,
            "original_ordered_static_writes": 0,
            "all_parsed_JVM_operands_equal_with_private_aliases": True,
            "original_invokedynamic_bootstrap_semantics_equal": True,
        }

    def call(self, *, pin=None):
        return gate.accept_original_source_recompiled_saver(
            self.orig, self.candidate, "p/Owner.class",
            self.output, original_sha256=pin or self.original_sha,
            candidate_sha256=self.candidate_sha,
        )

    def mocks(self, *, comparator=None):
        from contextlib import ExitStack
        ctx = ExitStack()
        self.addCleanup(ctx.close)
        def fake_profile(jar, entry):
            self.assertEqual(entry, "p/Owner.class")
            return (deepcopy(self.original) if Path(jar) == self.orig
                    else deepcopy(self.candidate_profile))
        ctx.enter_context(patch.object(gate,"profile_jar_class",fake_profile))
        ctx.enter_context(patch.object(
            gate,"compare_all_method_operands",
            comparator or self.comparison))
        return ctx

    def test_exact_364_stackmap_and_r81_gate_accepts_only_report(self):
        self.mocks()
        report = self.call()
        self.assertEqual(self.compare_called, 1)
        self.assertEqual(report["original_saver_method_jvm_instructions"], 364)
        self.assertEqual(report["original_saver_jvm_StackMapTable_frames_equal"], 10)
        self.assertTrue(report["original_saver_R66_R81_all_operands_passed"])
        self.assertFalse(report["original_loader_697_op_source_recovered"])
        self.assertFalse(report["original_complete_owner_R107_passed"])
        self.assertFalse(report["whole_original_client_runtime_equivalence_certified"])
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_wrong_full_original_pin_vetoes_before_profile_parse(self):
        self.mocks()
        with self.assertRaisesRegex(
            gate.OriginalSaverMethodAcceptanceError,
            "COMPLETE_ORIGINAL_OR_SOURCE_CANDIDATE_SHA256_MISMATCH"):
            self.call(pin="0"*64)
        self.assertEqual(self.compare_called, 0)
        self.assertFalse(self.output.exists())

    def test_unrecovered_364_stub_cannot_pass(self):
        self.candidate_profile["methods"][0]["instructions"] = [{"opcode":"0xb1"}]
        self.mocks()
        with self.assertRaisesRegex(
            gate.OriginalSaverMethodAcceptanceError,
            "SAVER_METHOD_INSTRUCTION_COUNT_WRONG"):
            self.call()
        self.assertEqual(self.compare_called, 0)
        self.assertFalse(self.output.exists())

    def test_source_candidate_stackmap_must_match_original_encoding(self):
        self.candidate_profile["methods"][0]["stackmap_frames"][1][
            "frame_type"] = 253
        self.mocks()
        with self.assertRaisesRegex(
            gate.OriginalSaverMethodAcceptanceError,
            "ALL_TEN_STACKMAP_FRAMES_NOT_EXACT"):
            self.call()
        self.assertEqual(self.compare_called, 1)
        self.assertFalse(self.output.exists())

    def test_changed_original_364_method_does_not_bypass_inventory(self):
        self.original["methods"][8]["instructions"].pop()
        self.mocks()
        with self.assertRaisesRegex(
            gate.OriginalSaverMethodAcceptanceError,
            "INVENTORY_NOT_PROVEN"):
            self.call()
        self.assertEqual(self.compare_called, 0)
        self.assertFalse(self.output.exists())

    def test_original_r81_failure_vetoes_entire_output(self):
        def fail(*args):
            raise WholeMethodOperandError("candidate member ref mismatch")
        self.mocks(comparator=fail)
        with self.assertRaisesRegex(
            gate.OriginalSaverMethodAcceptanceError,
            "ORIGINAL_R66_R81_364_METHOD_OPERANDS_NOT_ACCEPTED"):
            self.call()
        self.assertFalse(self.output.exists())

    def test_missing_typed_exception_vetoes(self):
        self.candidate_profile["methods"][0]["exception_handlers"] = []
        self.mocks()
        with self.assertRaisesRegex(
            gate.OriginalSaverMethodAcceptanceError,
            "EXCEPTION_REGION_NOT_EXACT"):
            self.call()
        self.assertFalse(self.output.exists())

    def test_source_compiler_owner_version_change_vetoes(self):
        self.candidate_profile["classfile_major"] = 52
        self.mocks()
        with self.assertRaisesRegex(
            gate.OriginalSaverMethodAcceptanceError,
            "OWNER_CLASS_IDENTITY_NOT_EQUAL"):
            self.call()
        self.assertEqual(self.compare_called, 0)


@unittest.skipUnless(shutil.which("javac"),
                     "Java9 compatible compiler required")
class ActualJava9OpcodeOperandWitnessTests(unittest.TestCase):
    def test_two_independent_java9_364_op_methods_pass_real_R66_R81(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archives = []
            for label in ("original", "candidate"):
                src = root / label / "src" / "p"
                src.mkdir(parents=True)
                (src / "Owner.java").write_text(
                    "package p; public final class Owner {"
                    "private static void writer() {"
                    + "System.out.println(1);"*121 + "}"
                    "}", encoding="utf-8")
                out = root / label / "classes"
                out.mkdir()
                comp = subprocess.run(
                    ["javac", "--release", "9", "-g:none", "-proc:none",
                     "-d", str(out), str(src / "Owner.java")],
                    capture_output=True, text=True)
                self.assertEqual(comp.returncode, 0, comp.stderr)
                jar = root / (label + ".jar")
                with ZipFile(jar,"w") as z:
                    z.write(out / "p" / "Owner.class", "p/Owner.class")
                archives.append(jar)
            a = profile_jar_class(archives[0], "p/Owner.class")
            b = profile_jar_class(archives[1], "p/Owner.class")
            m = next(x for x in a["methods"] if x["name"] == "writer")
            self.assertEqual(len(m["instructions"]), 364)
            parity = compare_all_method_operands(
                a, "writer", "()V", b, "writer", "()V", [], [], [])
            self.assertEqual(
                parity["original_instructions_with_all_semantic_operands_compared"],
                364)
            self.assertTrue(parity["all_parsed_JVM_operands_equal_with_private_aliases"])

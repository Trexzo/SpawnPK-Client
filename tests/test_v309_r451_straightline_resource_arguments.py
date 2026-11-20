"""R451 fabricated straight-line JVM resource operand regression tests.

All classfiles, JARs, code strings and private TEMP directories are fabricated.
No actual SpawnPK client class/source/assets, user history or journals are used.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r450_generic_resource_proximity as r450_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r451 import audit_resource_operand_arguments as r451
from tools.r451 import straightline_resource_operands as operands

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r451/audit_resource_operand_arguments.py"


def literal(idx: int) -> str | None:
    return {1: "images/logo.png", 2: "textures/missing.png",
            3: "notes/not-a-resource"}.get(idx)


def method_ref(idx: int):
    if idx == 8:
        return ("java/lang/Class", "getResource",
                "(Ljava/lang/String;)Ljava/net/URL;")
    if idx == 9:
        return ("java/lang/ClassLoader", "getSystemResourceAsStream",
                "(Ljava/lang/String;)Ljava/io/InputStream;")
    if idx == 10:
        return ("rs/Other", "unrelated", "()Ljava/lang/String;")
    if idx == 11:
        return ("rs/Other", "hasLong", "(J)Ljava/lang/String;")
    raise operands.Refused("R451_SYNTHETIC_METHOD_REF_ABSENT")


def resource_filter(name: str) -> str | None:
    return r451.r449.resource_literal(name)


def trace(code: bytes, *, max_stack: int = 2, max_locals: int = 2,
          exceptions: int = 0):
    return operands.trace_method(
        code, max_stack, max_locals, exceptions,
        literal, method_ref, resource_filter)


class R451StraightlinePureTests(unittest.TestCase):
    def test_01_actual_ldc_is_invocation_argument(self):
        code = b"\x2a\x12\x01\xb6\x00\x08\x57\xb1"
        self.assertEqual(trace(code), (["images/logo.png"], 1))

    def test_02_nearby_string_popped_is_not_invocation_argument(self):
        code = (b"\x2a\x12\x01\x57\x12\x02\xb6\x00\x08"
                b"\x57\xb1")
        self.assertEqual(trace(code), (["textures/missing.png"], 1))

    def test_03_non_resource_literal_at_call_not_counted(self):
        code = b"\x2a\x12\x03\xb6\x00\x08\x57\xb1"
        self.assertEqual(trace(code), ([], 1))

    def test_04_real_local_store_load_propagates_literal(self):
        code = b"\x12\x01\x4c\x2a\x2b\xb6\x00\x08\x57\xb1"
        self.assertEqual(trace(code), (["images/logo.png"], 1))

    def test_05_local_overwrite_taints_prior_literal(self):
        code = (b"\x12\x01\x4c\x01\x4c\x2a\x2b"
                b"\xb6\x00\x08\x57\xb1")
        self.assertEqual(trace(code), ([], 1))

    def test_06_ldc_w_supported(self):
        code = b"\x2a\x13\x00\x01\xb6\x00\x08\x57\xb1"
        self.assertEqual(trace(code), (["images/logo.png"], 1))

    def test_07_static_resource_api_uses_argument_without_receiver(self):
        code = b"\x12\x01\xb8\x00\x09\x57\xb1"
        self.assertEqual(trace(code, max_stack=1), (["images/logo.png"], 1))

    def test_08_dup_and_pop_symbolically_preserve_operand(self):
        code = b"\x2a\x12\x01\x59\x57\xb6\x00\x08\x57\xb1"
        self.assertEqual(trace(code), (["images/logo.png"], 1))

    def test_09_swap_rearranges_reference_and_argument_correctly(self):
        # ldc string, aload_0, swap -> receiver then literal
        code = b"\x12\x01\x2a\x5f\xb6\x00\x08\x57\xb1"
        self.assertEqual(trace(code), (["images/logo.png"], 1))

    def test_10_branching_method_is_excluded_not_guessed(self):
        code = b"\x2a\x12\x01\xa7\x00\x03\xb6\x00\x08\x57\xb1"
        self.assertIsNone(trace(code))

    def test_11_exceptions_disable_straightline_claim(self):
        code = b"\x2a\x12\x01\xb6\x00\x08\x57\xb1"
        self.assertIsNone(trace(code, exceptions=1))

    def test_12_unsupported_getstatic_disables_entire_method(self):
        code = b"\xb2\x00\x0c\x12\x01\xb6\x00\x08\x57\xb1"
        self.assertIsNone(trace(code))

    def test_13_unmodeled_invokedynamic_disables_entire_method(self):
        code = b"\xba\x00\x0d\x00\x00\xb1"
        self.assertIsNone(trace(code))

    def test_14_missing_receiver_or_missing_string_disables_proof(self):
        self.assertIsNone(trace(b"\x12\x01\xb6\x00\x08\x57\xb1"))
        self.assertIsNone(trace(b"\x2a\xb6\x00\x08\x57\xb1"))

    def test_15_stack_max_and_local_limits_refuse_uncertainty(self):
        code = b"\x2a\x12\x01\xb6\x00\x08\x57\xb1"
        self.assertIsNone(trace(code, max_stack=1))
        self.assertIsNone(trace(code, max_locals=0))

    def test_16_wide_argument_invocation_refused_safely(self):
        code = b"\x2a\xb6\x00\x0b\x57\xb1"
        self.assertIsNone(trace(code))

    def test_17_method_descriptor_arg_and_return_shape(self):
        self.assertEqual(operands.method_shape(
            "(Ljava/lang/String;)Ljava/net/URL;"), (1, True, False))
        self.assertEqual(operands.method_shape(
            "([Ljava/lang/String;I)V"), (2, False, False))
        self.assertEqual(operands.method_shape(
            "(J)Ljava/lang/String;"), (1, True, True))
        self.assertEqual(operands.method_shape("(I)[[D"), (1, True, False))

    def test_18_bad_descriptors_refuse_not_fabricate_shape(self):
        for desc in ("", "I", "(Ljava/lang/String;)",
                     "(V)V", "([V)V", "(L../Foo;)V",
                     "([[[Lrs/Foo;)Zoops", "(Ljava/lang/String;)Vx"):
            with self.subTest(descriptor=desc):
                with self.assertRaises(operands.Refused):
                    operands.method_shape(desc)

    def test_19_truncated_bytecode_is_refused_not_skipped(self):
        with self.assertRaisesRegex(
                operands.Refused, "R451_MALFORMED_INSTRUCTION_STREAM"):
            trace(b"\x2a\x12")

    def test_20_symbolic_calls_are_bounded(self):
        code = b"\x2a\x12\x01\xb6\x00\x08\x57\xb1"
        with patch.object(operands, "MAX_TRACKED_CALLS", 0):
            with self.assertRaisesRegex(
                    operands.Refused, "R451_METHOD_CALL_BUDGET"):
                trace(code)

    def test_21_no_extra_opcode_is_inferred_as_argument(self):
        # A hidden lambda or invocation may replace stack values; do not
        # accept an earlier literal if any unsupported opcode appears.
        code = b"\x2a\x12\x01\x60\xb6\x00\x08\x57\xb1"
        self.assertIsNone(trace(code))

    def test_22a_unreachable_code_after_return_is_never_attributed(self):
        # A parseable dead tail is not a feasible straight-line method.
        code = (b"\xb1" + b"\x2a\x12\x01\xb6\x00\x08\x57\xb1")
        self.assertIsNone(trace(code))
        self.assertIsNone(trace(b"\x2a\x12\x01\xb6\x00\x08\x57"))

    def test_22_two_resource_calls_track_separate_literals(self):
        code = (b"\x2a\x12\x01\xb6\x00\x08\x57"
                b"\x2a\x12\x02\xb6\x00\x08\x57\xb1")
        self.assertEqual(trace(code), (
            ["images/logo.png", "textures/missing.png"], 2))


class R451OwnerFakeIsolatedPipeline(unittest.TestCase):
    def setUp(self):
        r450_fixture.R450OwnerOfflinePipeline.setUp(self)

    def folders(self):
        return sorted(self.temp.glob(r451.PREFIX+"*"))

    def test_23_fake_current_class_sha_and_call_operands_observed(self):
        summary, private = r451.inspect(self.original_jar)
        self.assertEqual(summary["status"],
                         "R451_STRAIGHTLINE_STATIC_RESOURCE_OPERAND_AUDIT_UNAPPROVED")
        self.assertEqual(summary["original_v309_classes"], 5)
        self.assertEqual(summary["original_v309_resources"], 2)
        self.assertEqual(summary["isolated_r421_java_sources"], 2)
        self.assertEqual(summary["isolated_r421_compiled_classes"], 2)
        self.assertEqual(summary["allowlisted_resource_api_calls_total"], 2)
        self.assertEqual(
            summary["allowlisted_resource_api_calls_in_fully_modeled_methods"], 2)
        self.assertEqual(
            summary["literal_argument_occurrences_in_modeled_resource_calls"], 2)
        self.assertEqual(summary["unique_literal_resource_arguments_modeled"], 2)
        self.assertEqual(
            summary["modeled_literal_resource_argument_names_in_original"], 1)
        self.assertEqual(
            summary["modeled_literal_resource_argument_names_absent_from_original"], 1)
        self.assertEqual(
            summary["proximity_site_pairs_not_attributed_as_literal_arguments"], 0)
        self.assertFalse(summary["resource_successfully_loaded_proven"])
        self.assertFalse(summary["release_authorized"])
        self.assertEqual(private["schema"], r451.SCHEMA)

    def test_24_default_run_no_write_aggregate_only(self):
        result = r451.run(self.original_jar)
        self.assertFalse(result["private_worklist_saved"])
        self.assertEqual(self.folders(), [])
        output = json.dumps(result)
        for sensitive in ("rs/plugins/loottracker/LootHistoryStore",
                          "textures/missing.png", "images/logo.png",
                          str(self.temp), r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(sensitive, output)

    def test_25_explicit_private_name_worklist_only(self):
        result = r451.run(self.original_jar, save=True)
        self.assertTrue(result["private_worklist_saved"])
        self.assertEqual(len(self.folders()), 1)
        report = json.loads((self.folders()[0]/r451.NAME).read_text("ascii"))
        self.assertEqual(report["schema"], r451.SCHEMA)
        details = report["owner_private_resource_argument_worklist"]
        names = {x["possible_resource_path"]
                 for x in details["modeled_static_literal_call_arguments"]}
        self.assertEqual(names, {"images/logo.png", "textures/missing.png"})
        self.assertFalse(report["historical_R421_inventory_approved"])
        self.assertFalse(report["runtime_tested"])
        self.assertFalse(report["release_authorized"])

    def test_26_two_private_runs_never_overwrite(self):
        a = r451.run(self.original_jar, save=True)
        saved = self.folders()[0] / r451.NAME
        original_bytes = saved.read_bytes()
        b = r451.run(self.original_jar, save=True)
        self.assertEqual(len(self.folders()), 2)
        self.assertNotEqual(a["owner_private_report_directory"],
                            b["owner_private_report_directory"])
        self.assertEqual(saved.read_bytes(), original_bytes)

    def test_27_original_jar_sha_mismatch_refused(self):
        self.original_jar.write_bytes(b"modified original snapshot")
        with self.assertRaises(r451.r447.Refused):
            r451.inspect(self.original_jar)

    def test_28_class_modified_after_snapshot_refused(self):
        observed, _ = r451.r446.observe()
        (self.compiled/"rs/Bridge.class").write_bytes(b"\xca\xfe\xba\xbe")
        with self.assertRaisesRegex(
                r451.Refused, "R451_R421_CLASS_CHANGED_OR_UNSAFE"):
            r451.owner_metadata(observed)

    def test_29_double_scan_modification_refuses_private_write(self):
        old = r451.inspect
        called = [0]
        def changed(*args, **kwargs):
            outcome = old(*args, **kwargs)
            called[0] += 1
            if called[0] == 1:
                (self.compiled/"rs/Bridge.class").write_bytes(
                    r450_fixture.preceding.r448_test_fixture.fake_java11_class(
                        "rs/Bridge", ("rs/ChangedType",)))
            return outcome
        with patch.object(r451, "inspect", side_effect=changed):
            with self.assertRaises(r451.Refused):
                r451.run(self.original_jar, save=True)
        self.assertEqual(self.folders(), [])

    def test_30_private_report_size_cap(self):
        with patch.object(r451, "MAX_PRIVATE_REPORT_BYTES", 30):
            with self.assertRaisesRegex(
                    r451.Refused, "R451_PRIVATE_WORKLIST_TOO_LARGE"):
                r451.run(self.original_jar, save=True)
        self.assertEqual(self.folders(), [])

    def test_31_refuse_missing_original_public_CLI_no_paths(self):
        absent = self.temp/"owner original absent.jar"
        proc = subprocess.run(
            [sys.executable, "-B", str(CLI),
             "--original-v309-jar", str(absent)],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        status = json.loads(proc.stdout)
        self.assertEqual(status["status"], "R451_RESOURCE_OPERAND_AUDIT_REFUSED")
        self.assertFalse(status["release_authorized"])
        self.assertNotIn(str(absent), proc.stdout)

    def test_32_no_release_merge_original_runtime_or_user_history(self):
        result = r451.run(self.original_jar)
        for key in (
                "private_client_executed", "bytecode_behavioural_parity_proven",
                "full_deobfuscated_source_verified", "assets_repackaged_or_installed",
                "historical_R421_inventory_approved", "compile_authorized",
                "release_authorized", "merge_authorized",
                "resource_successfully_loaded_proven"):
            self.assertFalse(result[key])


if __name__ == "__main__":
    unittest.main()

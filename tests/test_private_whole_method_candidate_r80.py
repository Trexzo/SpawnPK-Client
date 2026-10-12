"""R80: synthetic full-method layout and bounded candidate composition."""
import unittest
from unittest.mock import patch

from spk_recovery.private_local_coverage import FAMILIES, LocalCoverageError
from spk_recovery.private_whole_method_candidate import plan_original_private_method_candidate


def make_fixture():
    # 48 prefix, 560 protected instructions, 42 gotos, 42 catch entries,
    # five final IOException/return instructions = 697.
    lengths = {
        "R67": [13]*29, "R68": [6]*2,
        "R71": [8, 8, 8, 10, 11], "R72": [11],
        "R73": [22], "R74": [15, 19], "R75": [23], "R76": [36],
    }
    rows = [
        {"offset": i, "length": 1, "opcode": "0x00"} for i in range(697)
    ]
    sites, handlers, cursor = {}, [], 48
    n_write = 0
    for family, (count, a, b, c, source_key) in FAMILIES.items():
        assert len(lengths[family]) == count
        sites[family] = []
        for size in lengths[family]:
            start, end, caught = cursor, cursor+size, cursor+size+1
            for i in range(start, end):
                if n_write < 74:
                    rows[i]["opcode"] = "0xb3"
                    n_write += 1
            rows[end].update(opcode="0xa7", branch_target_offset=caught+1)
            rows[caught]["opcode"] = "0x4e"
            sites[family].append({
                a: start, b: end, c: caught,
                source_key: "try { check(); } catch (java.lang.Exception ignored) {}"
            })
            handlers.append({
                "start_pc": start, "end_pc": end, "handler_pc": caught,
                "catch_type": "java/lang/Exception",
            })
            cursor = caught+1
    assert cursor == 692
    for i in range(24, 28):
        rows[i]["opcode"] = "0xb3"
    for i, op in enumerate(["0xa7","0x4b","0x2a","0xb6","0xb1"], 692):
        rows[i]["opcode"] = op
    rows[692]["branch_target_offset"] = 696
    handlers.extend([
        {"start_pc": 3, "end_pc": 21, "handler_pc": 693,
         "catch_type": "java/io/IOException"},
        {"start_pc": 22, "end_pc": 692, "handler_pc": 693,
         "catch_type": "java/io/IOException"},
    ])
    prefix = "\n".join([
        "preflight();",
        "java.io.File originalLocalSlot0 = new java.io.File(path);",
        "if (!originalLocalSlot0.exists()) return;",
        "java.util.Properties originalLocalSlot1 = new java.util.Properties();",
        "java.io.FileInputStream originalLocalSlot2 = new java.io.FileInputStream(originalLocalSlot0);",
        "originalLocalSlot1.load(originalLocalSlot2);",
        "originalLocalSlot2.close();",
        "bool1 = true;", "bool2 = false;", "int1 = 1;", "bool3 = true;",
    ])
    profile = {
        "internal_name": "PrivateOwner",
        "methods": [{
            "name": "restore", "descriptor": "()V",
            "instructions": rows, "exception_handlers": handlers
        }]
    }
    return profile, sites, prefix


class WholeCandidateTests(unittest.TestCase):
    def proof(self, profile, sites, prefix):
        with patch(
            "spk_recovery.private_whole_method_candidate.plan_private_original_48_op_prefix",
            return_value={"private_original_48_instruction_java_source": prefix},
        ), patch(
            "spk_recovery.private_whole_method_candidate.plan_original_outer_io_source_envelope",
            return_value={
                "original_io_typed_exception_handler_entries": 2,
                "original_io_catch_calls_printStackTrace_once": True,
            },
        ):
            return plan_original_private_method_candidate(
                profile, "restore", "()V", sites)

    def test_697_partition_and_ordered_private_method_body(self):
        profile, sites, prefix = make_fixture()
        result = self.proof(profile, sites, prefix)
        self.assertEqual(result["original_jvm_instructions_accounted_for"], 697)
        self.assertEqual(result["original_local_protected_body_instructions"], 560)
        self.assertEqual(result["original_local_catch_entry_instructions"], 42)
        self.assertEqual(result["original_local_skip_goto_instructions"], 42)
        source = result["private_java_method_body_candidate"]
        self.assertEqual(source.count("try {"), 43)
        self.assertEqual(source.count("catch (java.lang.Exception ignored)"), 42)
        self.assertEqual(source.count("catch (java.io.IOException"), 1)
        self.assertTrue(source.index("preflight();") < source.index("try {"))
        self.assertFalse(result["candidate_has_been_compiled_against_original_dependencies"])
        self.assertFalse(result["original_client_runtime_equivalence_certified"])

    def test_single_missing_inter_region_goto_rejected(self):
        profile, sites, prefix = make_fixture()
        idx = next(i for i,row in enumerate(profile["methods"][0]["instructions"])
                   if row.get("opcode") == "0xa7")
        profile["methods"][0]["instructions"][idx]["opcode"] = "0x00"
        with self.assertRaisesRegex(LocalCoverageError, "EXCEPTION_SEPARATOR"):
            self.proof(profile, sites, prefix)

    def test_wrong_local_handler_and_tail_rejected(self):
        profile, sites, prefix = make_fixture()
        profile["methods"][0]["instructions"][692]["opcode"] = "0x00"
        with self.assertRaisesRegex(LocalCoverageError, "FIVE_INSTRUCTION_IO_EPILOGUE"):
            self.proof(profile, sites, prefix)

    def test_unsupported_io_proof_veto(self):
        profile, sites, prefix = make_fixture()
        with patch(
            "spk_recovery.private_whole_method_candidate.plan_private_original_48_op_prefix",
            return_value={"private_original_48_instruction_java_source": prefix},
        ), patch(
            "spk_recovery.private_whole_method_candidate.plan_original_outer_io_source_envelope",
            return_value={"original_io_typed_exception_handler_entries": 0},
        ):
            with self.assertRaisesRegex(LocalCoverageError, "IO_EXCEPTION_ENVELOPE_NOT_PROVEN"):
                plan_original_private_method_candidate(profile, "restore", "()V", sites)


if __name__ == "__main__":
    unittest.main()

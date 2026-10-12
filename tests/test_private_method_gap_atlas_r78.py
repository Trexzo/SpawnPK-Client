"""R78 complete JVM instruction gap-atlas tests."""
import unittest
from spk_recovery.private_method_gap_atlas import plan_original_method_gap_atlas
from spk_recovery.private_local_coverage import FAMILIES, LocalCoverageError


def synthetic():
    rows = [{"offset": i, "length": 1, "opcode": "0x00"} for i in range(697)]
    for i in range(400, 478):
        rows[i]["opcode"] = "0xb3"
    handlers, artifacts = [], {}
    idx = 0
    for family, (count, start, end, caught, source) in FAMILIES.items():
        items = []
        for _ in range(count):
            begin = idx * 3
            handlers.append({
                "start_pc": begin, "end_pc": begin + 1,
                "handler_pc": begin + 2, "catch_type": "java/lang/Exception"})
            items.append({
                start: begin, end: begin + 1, caught: begin + 2,
                source: "try { noop(); } catch (java.lang.Exception ignored) {}"})
            idx += 1
        artifacts[family] = items
    handlers.extend([
        {"start_pc": 0, "end_pc": 1, "handler_pc": 160,
         "catch_type": "java/io/IOException"},
        {"start_pc": 1, "end_pc": 2, "handler_pc": 160,
         "catch_type": "java/io/IOException"},
    ])
    profile = {"methods": [{"name": "restore", "descriptor": "()V",
                           "instructions": rows, "exception_handlers": handlers}]}
    return profile, artifacts


class GapAtlasTests(unittest.TestCase):
    def test_697_positions_are_exhaustive_and_remaining_gaps_visible(self):
        profile, artifacts = synthetic()
        result = plan_original_method_gap_atlas(profile, "restore", "()V", artifacts)
        counts = result["classification_instruction_counts"]
        self.assertEqual(counts, {
            "protected_source_body": 42,
            "local_catch_entry": 42,
            "not_yet_sourced": 613,
        })
        spans = result["private_original_method_gap_spans"]
        self.assertEqual(sum(s["instruction_count"] for s in spans), 697)
        self.assertEqual(sum(s["putstatic_count"] for s in spans), 78)
        self.assertFalse(result["every_not_yet_sourced_instruction_has_recovered_java"])
        self.assertFalse(result["runtime_equivalence_certified"])

    def test_handler_in_protected_range_rejected(self):
        profile, artifacts = synthetic()
        # Real original catch entries must not be inside another recovered body.
        profile["methods"][0]["exception_handlers"][0]["handler_pc"] = 3
        artifacts["R67"][0]["original_handler_pc"] = 3
        with self.assertRaisesRegex(LocalCoverageError,
                                    "LOCAL_CATCH_ENTRY_INSIDE_ANOTHER_PROTECTED_SOURCE"):
            plan_original_method_gap_atlas(profile, "restore", "()V", artifacts)

    def test_original_static_write_mutation_veto(self):
        profile, artifacts = synthetic()
        profile["methods"][0]["instructions"][401]["opcode"] = "0x00"
        with self.assertRaisesRegex(LocalCoverageError, "ORIGINAL_78_STATIC_WRITES"):
            plan_original_method_gap_atlas(profile, "restore", "()V", artifacts)


if __name__ == "__main__":
    unittest.main()

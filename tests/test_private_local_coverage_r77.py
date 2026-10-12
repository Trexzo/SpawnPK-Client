"""R77 cross-family full-original-local-handler inventory tests."""
import copy
import unittest
from spk_recovery.private_local_coverage import (
    FAMILIES, LocalCoverageError, verify_local_site_inventory,
)

def fixture():
    rows = [{"offset": i, "length": 1, "opcode": "0x00"} for i in range(697)]
    for i in range(200, 278):
        rows[i]["opcode"] = "0xb3"
    handlers, artifacts = [], {}
    i = 0
    for family, (count, a, b, c, source_key) in FAMILIES.items():
        sites = []
        for _ in range(count):
            start = i * 3
            end, target = start + 1, start + 2
            handlers.append({"start_pc": start, "end_pc": end,
                             "handler_pc": target, "catch_type": "java/lang/Exception"})
            sites.append({a: start, b: end, c: target, source_key:
                          "try {\n  noop();\n} catch (java.lang.Exception ignored) {}\n"})
            i += 1
        artifacts[family] = sites
    handlers.extend([
        {"start_pc": 0, "end_pc": 1, "handler_pc": 150,
         "catch_type": "java/io/IOException"},
        {"start_pc": 1, "end_pc": 2, "handler_pc": 150,
         "catch_type": "java/io/IOException"},
    ])
    profile = {"methods": [{"name": "restore", "descriptor": "()V",
                           "instructions": rows, "exception_handlers": handlers}]}
    return profile, artifacts

class PrivateLocalCoverageTests(unittest.TestCase):
    def test_all_42_original_regions_covered_without_full_method_claim(self):
        p, a = fixture()
        r = verify_local_site_inventory(p, "restore", "()V", a)
        self.assertEqual(r["covered_original_local_exception_entries"], 42)
        self.assertEqual(r["covered_original_protected_instructions"], 42)
        self.assertEqual(sum(r["source_families"].values()), 42)
        self.assertEqual(r["private_ordered_java_fragments"].count(
            "missing inter-region and outer method statements"), 42)
        self.assertFalse(r["complete_697_instruction_method_compiled"])
        self.assertFalse(r["runtime_equivalence_certified"])

    def test_duplicate_site_and_changed_handler_fail(self):
        p, a = fixture()
        a["R67"][0] = dict(a["R67"][1])
        with self.assertRaisesRegex(LocalCoverageError, "DUPLICATE_PRIVATE_SITE"):
            verify_local_site_inventory(p, "restore", "()V", a)
        p, a = fixture()
        a["R76"][0]["original_end_pc"] += 1
        with self.assertRaisesRegex(LocalCoverageError, "UNKNOWN_ORIGINAL_SITE"):
            verify_local_site_inventory(p, "restore", "()V", a)

    def test_missing_source_and_original_layout_drift_fail(self):
        p, a = fixture()
        a["R73"][0]["private_java_source"] = ""
        with self.assertRaisesRegex(LocalCoverageError, "SOURCE_FRAGMENT_MISSING"):
            verify_local_site_inventory(p, "restore", "()V", a)
        p, a = fixture()
        del a["R74"]
        with self.assertRaisesRegex(LocalCoverageError, "EIGHT_PRIVATE_FAMILY"):
            verify_local_site_inventory(p, "restore", "()V", a)
        p, a = fixture()
        p["methods"][0]["instructions"][200]["opcode"] = "0x00"
        with self.assertRaisesRegex(LocalCoverageError, "ORIGINAL_78_STATIC_WRITES"):
            verify_local_site_inventory(p, "restore", "()V", a)

if __name__ == "__main__":
    unittest.main()

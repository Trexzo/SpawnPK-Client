"""R449 public fabricated JVM descriptors and resource-string candidate tests.

No owner files, real SpawnPK Java classes or history are used. Tests exercise
actual classfile constant pool parsing and bounded owner-TEMP quarantine
against in-memory fabricated Java 11 classfiles and ZIPs.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r448_rebuilt_bytecode_linkage as r448_test_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r449 import audit_descriptor_resource_gaps as r449

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r449/audit_descriptor_resource_gaps.py"


def described_class(
    name: str,
    field_type: str = "Lrs/DescriptorMissing;",
    method_type: str = "(Lrs/DescriptorMissing;[Lrs/Legacy;)Lrs/ReturnOnly;",
    name_and_type: str = "(Lrs/NatOnly;)V",
    methodtype: str = "(Lrs/MethodTypeOnly;)V",
    resources=(
        "images/logo.png", "/META-INF/MANIFEST.MF",
        "textures/missing.png", "../outside.json", "not-a-resource",
    ),
) -> bytes:
    """Make a valid minimal invented Java 11 classfile using named CP tags."""
    pool: list[bytes] = []

    def utf(value: str) -> int:
        raw = value.encode("utf-8")
        idx = len(pool) + 1
        pool.append(b"\x01" + len(raw).to_bytes(2, "big") + raw)
        return idx

    def cls(value: str) -> int:
        idx = utf(value)
        class_idx = len(pool) + 1
        pool.append(b"\x07" + idx.to_bytes(2, "big"))
        return class_idx

    own_index = cls(name)
    super_index = cls("java/lang/Object")
    cls("rs/Bridge")  # class-index reference, not a descriptor-only gap
    field_name_idx = utf("payload")
    field_desc_idx = utf(field_type)
    method_name_idx = utf("getPayload")
    method_desc_idx = utf(method_type)
    nat_name_idx = utf("syntheticCall")
    nat_desc_idx = utf(name_and_type)
    pool.append(b"\x0c" + nat_name_idx.to_bytes(2, "big")
                + nat_desc_idx.to_bytes(2, "big"))
    methodtype_idx = utf(methodtype)
    pool.append(b"\x10" + methodtype_idx.to_bytes(2, "big"))
    for name in resources:
        string_idx = utf(name)
        pool.append(b"\x08" + string_idx.to_bytes(2, "big"))
    result = (b"\xca\xfe\xba\xbe\x00\x00\x00\x37"
              + (len(pool) + 1).to_bytes(2, "big")
              + b"".join(pool))
    result += (0x21).to_bytes(2, "big")
    result += own_index.to_bytes(2, "big")
    result += super_index.to_bytes(2, "big")
    result += (0).to_bytes(2, "big")  # interfaces
    result += (1).to_bytes(2, "big")  # fields
    result += (0x2).to_bytes(2, "big") + field_name_idx.to_bytes(2, "big")
    result += field_desc_idx.to_bytes(2, "big") + (0).to_bytes(2, "big")
    result += (1).to_bytes(2, "big")  # methods
    result += (0x1).to_bytes(2, "big") + method_name_idx.to_bytes(2, "big")
    result += method_desc_idx.to_bytes(2, "big") + (0).to_bytes(2, "big")
    result += (0).to_bytes(2, "big")  # class attrs
    return result


class R449DescriptorResourceRegression(unittest.TestCase):
    def setUp(self):
        # Reuse synthetic owner TEMP layout, pinned fingerprints and dummy JAR
        # from R448 without inheriting its tests (which run separately in CI).
        r448_test_fixture.R448InventedStaticGaps.setUp(self)
        self.described = described_class(
            "rs/plugins/loottracker/LootHistoryStore")
        self.store_class.write_bytes(self.described)
        self.original_entries.pop("rs/Extra.class")
        self.original_entries["rs/DescriptorMissing.class"] = (
            b"R449 invented original-only class, not JVM bytecode")
        self.original_jar.write_bytes(r448_test_fixture.fake_zip(self.original_entries))
        for obj, prop, value in (
            (r425, "PINNED_R421_STORE_CLASS",
             sha256(self.described).hexdigest()),
            (r449.r447, "ORIGINAL_SHA",
             sha256(self.original_jar.read_bytes()).hexdigest()),
        ):
            p = patch.object(obj, prop, value)
            p.start()
            self.addCleanup(p.stop)

    def private_outputs(self):
        return sorted(self.temp.glob(r449.PREFIX + "*"))

    def test_01_field_method_nat_and_methodtype_references_found(self):
        classes, descriptor_refs, resources = r449.class_metadata(self.described)
        self.assertIn("rs/Bridge.class", classes)
        self.assertNotIn("rs/DescriptorMissing.class", classes)
        self.assertEqual(descriptor_refs, {
            "rs/DescriptorMissing.class", "rs/Legacy.class",
            "rs/ReturnOnly.class", "rs/NatOnly.class",
            "rs/MethodTypeOnly.class",
        })
        self.assertEqual(resources, {
            "images/logo.png", "META-INF/MANIFEST.MF",
            "textures/missing.png",
        })

    def test_02_actual_isolated_fake_files_give_descriptor_gap_counts(self):
        report, private = r449.inspect(self.original_jar)
        self.assertEqual(report["status"],
                         "R449_DESCRIPTOR_AND_RESOURCE_LITERAL_GAPS_UNAPPROVED")
        self.assertEqual(report["rebuilt_java_sources"], 2)
        self.assertEqual(report["rebuilt_compiled_class_files"], 2)
        self.assertEqual(report["original_class_files"], 5)
        self.assertEqual(report["original_resource_files"], 2)
        self.assertEqual(report["newly_discovered_descriptor_targets_not_in_any_class_index"], 5)
        self.assertEqual(report["newly_unresolved_descriptor_class_targets"], 5)
        self.assertEqual(report["new_unresolved_descriptor_targets_present_in_original_v309"], 1)
        self.assertEqual(report["new_unresolved_descriptor_targets_absent_from_original_v309"], 4)
        self.assertEqual(report["new_unresolved_descriptor_targets_present_in_alternate_dependency"], 1)
        self.assertEqual(report["possible_literal_resource_paths"], 3)
        self.assertEqual(report["possible_literal_resource_paths_present_in_original"], 2)
        self.assertEqual(report["possible_literal_resource_paths_absent_from_original"], 1)
        self.assertFalse(report["resource_literal_usage_proven"])
        self.assertFalse(report["build_authorized"])
        self.assertFalse(report["release_authorized"])
        self.assertEqual(len(private["descriptor_and_resource_details"][
            "new_descriptor_only_unresolved_references"]), 5)

    def test_03_default_no_write_and_no_private_names_in_stdout(self):
        report = r449.run(self.original_jar)
        self.assertFalse(report["private_worklist_saved"])
        self.assertEqual(self.private_outputs(), [])
        redacted = json.dumps(report)
        for private in (
            "rs/DescriptorMissing.class", "rs/NatOnly.class",
            "rs/MethodTypeOnly.class", "textures/missing.png",
            "META-INF/MANIFEST.MF", str(self.temp)):
            self.assertNotIn(private, redacted)

    def test_04_explicit_private_worklist_contains_references_not_bytes(self):
        report = r449.run(self.original_jar, save_private=True)
        self.assertTrue(report["private_worklist_saved"])
        outputs = self.private_outputs()
        self.assertEqual(len(outputs), 1)
        private = json.loads((outputs[0] / r449.REPORT_NAME).read_text("ascii"))
        self.assertEqual(private["schema"], r449.SCHEMA)
        details = private["descriptor_and_resource_details"]
        descs = {
            item["class_name"]: item
            for item in details["new_descriptor_only_unresolved_references"]
        }
        self.assertTrue(descs["rs/DescriptorMissing.class"][
            "present_in_original_v309"])
        self.assertTrue(descs["rs/Legacy.class"][
            "available_in_alternate_dependency"])
        self.assertFalse(private["historical_R421_reference_approved"])
        self.assertFalse(private["release_authorized"])
        self.assertNotIn(str(self.temp), json.dumps(report))

    def test_05_private_reports_never_overwrite_one_another(self):
        old = r449.run(self.original_jar, save_private=True)
        first_file = self.private_outputs()[0] / r449.REPORT_NAME
        original_bytes = first_file.read_bytes()
        newer = r449.run(self.original_jar, save_private=True)
        self.assertEqual(len(self.private_outputs()), 2)
        self.assertNotEqual(old["private_quarantine_directory_name"],
                            newer["private_quarantine_directory_name"])
        self.assertEqual(first_file.read_bytes(), original_bytes)

    def test_06_field_and_method_arrays_and_void_are_correct(self):
        self.assertEqual(r449.descriptor_classes("[[Lrs/ArrayItem;"),
                         {"rs/ArrayItem.class"})
        self.assertEqual(
            r449.descriptor_classes("([I[[Lrs/A;Ljava/lang/String;)Lrs/B;"),
            {"rs/A.class", "java/lang/String.class", "rs/B.class"})
        self.assertEqual(r449.descriptor_classes("([[Lrs/Foo;)V"),
                         {"rs/Foo.class"})
        self.assertEqual(r449.descriptor_classes("()V"), set())
        self.assertEqual(r449.descriptor_classes("I"), set())

    def test_07_invalid_descriptor_shapes_refuse(self):
        for value in ("", "Lrs/Missing", "L../Secret;", "[V", "V",
                      "()Lrs/Foo;extra", "(Lrs/Foo;)Q",
                      "([[Lrs/Foo)V", "(I", "Lrs\\Bad;",
                      "Lrs/./Foo;", "[", "(V)V"):
            with self.subTest(descriptor=value):
                with self.assertRaises(r449.Refused):
                    r449.descriptor_classes(value)

    def test_08_no_resource_match_from_unsafe_string(self):
        for value in ("../escape.json", "/../escape.json",
                      r"images\\bad.png", "file:///tmp/test.png",
                      "https://example.com/test.png", "some random text",
                      "A.class", "missing-resource", "bad name.png",
                      "literal\nnew.png"):
            with self.subTest(value=value):
                self.assertIsNone(r449.resource_literal(value))

    def test_09_root_relative_normalized_resource_candidate(self):
        self.assertEqual(
            r449.resource_literal("/images/logo.png"), "images/logo.png")
        self.assertEqual(
            r449.resource_literal("META-INF/MANIFEST.MF"), "META-INF/MANIFEST.MF")
        self.assertEqual(r449.resource_literal("textures/ui.atlas"),
                         "textures/ui.atlas")

    def test_10_generic_utf8_not_treated_as_resources(self):
        data = described_class("rs/Original", resources=())
        self.assertEqual(r449.class_metadata(data)[2], set())
        # Add an incidental UTF8 token that ends in '.png' but isn't
        # referenced by any CONSTANT_String (not a candidate).
        phantom = data.replace(b"payload", b"img.png")
        self.assertEqual(r449.class_metadata(phantom)[2], set())

    def test_11_wrong_major_version_refused(self):
        mutated = self.described[:6] + (61).to_bytes(2, "big") + self.described[8:]
        with self.assertRaisesRegex(r449.Refused, "R449_JAVA11_CLASSFILE_REQUIRED"):
            r449.class_metadata(mutated)

    def test_12_invalid_constant_pool_tag_refused(self):
        mutated = self.described[:10] + b"\xff" + self.described[11:]
        with self.assertRaisesRegex(r449.Refused, "R449_UNKNOWN_CONSTANT_POOL_TAG"):
            r449.class_metadata(mutated)

    def test_13_truncated_classfile_fails_closed(self):
        for raw in (self.described[:-1], self.described[:17],
                    self.described[:10]):
            with self.subTest(length=len(raw)):
                with self.assertRaises(r449.Refused):
                    r449.class_metadata(raw)

    def test_14_extra_classfile_bytes_refused(self):
        with self.assertRaisesRegex(r449.Refused, "R449_CLASSFILE_TRAILING_DATA"):
            r449.class_metadata(self.described + b"excess")

    def test_15_bad_descriptor_in_field_member_refused(self):
        raw = described_class(
            "rs/plugins/loottracker/LootHistoryStore",
            field_type="Lrs/BadType")
        with self.assertRaises(r449.Refused):
            r449.class_metadata(raw)

    def test_16_invalid_methodtype_entry_refused(self):
        raw = described_class(
            "rs/plugins/loottracker/LootHistoryStore",
            methodtype="(I")
        with self.assertRaisesRegex(
                r449.Refused, "R449_METHOD_CLOSING_PAREN_MISSING"):
            r449.class_metadata(raw)

    def test_17_reference_budget_prevents_oversized_analysis(self):
        observed, _ = r449.r446.observe()
        with patch.object(r449, "MAX_REFS", 1):
            with self.assertRaisesRegex(r449.Refused,
                                        "R449_REFERENCE_BUDGET_EXCEEDED"):
                r449.combined_graph(observed)

    def test_18_resource_candidate_budget_refusal(self):
        observed, _ = r449.r446.observe()
        with patch.object(r449, "MAX_STRING_CANDIDATES", 1):
            with self.assertRaisesRegex(
                    r449.Refused, "R449_RESOURCE_CANDIDATE_BUDGET_EXCEEDED"):
                r449.combined_graph(observed)

    def test_19_current_observation_changed_before_class_read_refused(self):
        observed, _ = r449.r446.observe()
        bridge = self.compiled / "rs/Bridge.class"
        bridge.write_bytes(r448_test_fixture.fake_java11_class(
            "rs/Bridge", ("rs/TamperedClass",)))
        with self.assertRaisesRegex(
                r449.Refused, "R449_COMPILED_CLASS_CHANGED_DURING_AUDIT"):
            r449.combined_graph(observed)

    def test_20_missing_original_JAR_or_wrong_pin_fails_closed(self):
        self.original_jar.unlink()
        with self.assertRaisesRegex(
                r449.r447.Refused, "R447_ORIGINAL_JAR_MISSING_OR_UNSAFE"):
            r449.inspect(self.original_jar)

    def test_21_resource_path_coverage_is_not_load_verification(self):
        report, _ = r449.inspect(self.original_jar)
        self.assertFalse(report["resource_literal_usage_proven"])
        self.assertFalse(report["assets_packaged_proven"])
        self.assertFalse(report["runtime_tested"] if "runtime_tested" in report
                         else report["owner_private_classes_executed"])
        self.assertFalse(report["prior_R421_custody_approved"])

    def test_22_companion_real_bytes_only_if_requested(self):
        companion = self.temp / "resource-companion"
        companion.mkdir()
        for name, data in self.original_entries.items():
            if name.endswith(".class"):
                continue
            p = companion / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        report, _ = r449.inspect(self.original_jar, companion)
        self.assertTrue(report["original_resource_companion_checked"])
        self.assertEqual(report["companion_resource_byte_matches"], 2)
        self.assertEqual(report["companion_resource_missing"], 0)
        self.assertFalse(report["assets_packaged_proven"])

    def test_23_private_output_rechecks_exact_results_before_write(self):
        actual = r449.inspect
        count = [0]
        def changed(*args, **kwargs):
            outcome = actual(*args, **kwargs)
            count[0] += 1
            if count[0] == 1:
                self.original_jar.write_bytes(b"changed between complete audits")
            return outcome
        with patch.object(r449, "inspect", side_effect=changed):
            with self.assertRaises(r449.r447.Refused):
                r449.run(self.original_jar, save_private=True)
        self.assertEqual(self.private_outputs(), [])

    def test_24_private_output_size_limit_refusal(self):
        with patch.object(r449, "MAX_OUTPUT_BYTES", 100):
            with self.assertRaisesRegex(
                    r449.Refused, "R449_PRIVATE_WORKLIST_TOO_LARGE"):
                r449.run(self.original_jar, save_private=True)
        self.assertEqual(self.private_outputs(), [])

    def test_25_cli_with_missing_original_never_leaks_path(self):
        missing = self.temp / "absent-private-original.jar"
        result = subprocess.run([
            sys.executable, "-B", str(CLI),
            "--original-v309-jar", str(missing),
        ], capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 2)
        message = json.loads(result.stdout)
        self.assertEqual(message["status"],
                         "R449_DESCRIPTOR_RESOURCE_AUDIT_REFUSED")
        self.assertFalse(message["release_authorized"])
        self.assertNotIn(str(missing), result.stdout)

    def test_26_static_pure_graph_unresolved_coverage_counts(self):
        class_graph = {
            "rs/A.class": {"rs/OnlyInClassIndex.class", "java/lang/Object.class"},
            "rs/B.class": set(),
        }
        desc = {"rs/A.class": {"rs/Missing.class", "java/lang/String.class"},
                "rs/B.class": {"rs/Missing.class", "rs/Alternate.class"}}
        resources = {"rs/A.class": {"icons/a.png", "icons/missing.png"},
                     "rs/B.class": {"icons/a.png"}}
        summary, private = r449.analyze_graphs(
            class_graph, desc, resources,
            {"rs/Missing.class"},
            {"rs/OnlyInClassIndex.class"},
            {"rs/Alternate.class"},
            {"icons/a.png"},
        )
        self.assertEqual(summary["newly_unresolved_descriptor_class_targets"], 2)
        self.assertEqual(summary["new_unresolved_descriptor_targets_present_in_original_v309"], 1)
        self.assertEqual(summary["new_unresolved_descriptor_targets_present_in_alternate_dependency"], 1)
        self.assertEqual(summary["possible_literal_resource_paths"], 2)
        self.assertEqual(summary["possible_literal_resource_paths_present_in_original"], 1)
        self.assertEqual(
            private["new_descriptor_only_unresolved_references"][0][
                "class_name"], "rs/Missing.class")
        self.assertEqual(
            private["new_descriptor_only_unresolved_references"][0][
                "referencer_count"], 2)

    def test_27_rebuilt_class_sets_must_align(self):
        with self.assertRaisesRegex(r449.Refused, "R449_GRAPH_KEYS_MISMATCH"):
            r449.analyze_graphs(
                {"rs/A.class": set()},
                {"rs/B.class": set()},
                {"rs/A.class": set()},
                set(), set(), set(), set())


if __name__ == "__main__":
    unittest.main()

"""R448 offline static Java 11 constant-pool and reconstruction worklist tests.

All input ZIPs and JVM classfiles are invented and generated in temporary
directories. No actual SpawnPK client, owner-private Java, history, assets or
original binary is executed or uploaded.
"""
from __future__ import annotations

from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r448 import audit_rebuilt_class_linkage as r448

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r448/audit_rebuilt_class_linkage.py"


def fake_java11_class(name: str, references=()) -> bytes:
    """Invented Java 11 classfile with valid constant-pool Class entries."""
    values = [name, "java/lang/Object", *references]
    constants = []
    for value in values:
        encoded = value.encode("ascii")
        utf8_index = len(constants) + 1
        constants.append(b"\x01" + len(encoded).to_bytes(2, "big") + encoded)
        constants.append(b"\x07" + utf8_index.to_bytes(2, "big"))
    pool = b"".join(constants)
    head = b"\xca\xfe\xba\xbe" + (0).to_bytes(2, "big")
    head += (55).to_bytes(2, "big") + (len(constants) + 1).to_bytes(2, "big")
    # Minimal Class/Java11 header, no fields or method implementation.
    # Tests cover parsing Class constant-pool references, not JVM execution.
    tail = (0x21).to_bytes(2, "big") + (2).to_bytes(2, "big")
    tail += (4).to_bytes(2, "big") + b"\x00\x00" * 4
    return head + pool + tail


def fake_zip(items: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for key, data in items.items():
            z.writestr(key, data)
    return buffer.getvalue()


class R448InventedStaticGaps(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory(prefix="R448-Invented-")
        self.addCleanup(workspace.cleanup)
        self.temp = Path(workspace.name)
        parent = (self.temp / "SpawnPK-R386-Isolated-Acceptance"
                  / "R421-Private-NoFollow-Cache-Directory-Preflight")
        self.candidate = parent / "Source-Candidate-R421"
        self.source = self.candidate / "source"
        self.compiled = parent / "R421-Compiled-Classes"
        self.dependencies = self.candidate / "dependencies"
        self.dependencies.mkdir(parents=True)
        self.store_java = self.source / r425.STORE
        self.store_class = self.compiled / r425.EXPECTED_CHANGED_EXISTING_CLASS
        self.store_java.parent.mkdir(parents=True)
        self.store_class.parent.mkdir(parents=True)
        self.store_java.write_bytes(b"R448 invented Store.java text")
        self.store_class.write_bytes(fake_java11_class(
            "rs/plugins/loottracker/LootHistoryStore", (
                "rs/Candidate",
                "rs/Bridge",
                "rs/Legacy",
                "rs/Unseen",
                "lib/Shared",
            )))
        (self.source / "rs/Bridge.java").write_bytes(b"R448 invented Bridge.java")
        (self.compiled / "rs/Bridge.class").write_bytes(fake_java11_class(
            "rs/Bridge", ("rs/Candidate", "rs/Unseen")))
        self.original_entries = {
            r425.EXPECTED_CHANGED_EXISTING_CLASS: b"imaginary original class",
            "rs/Bridge.class": b"original Bridge",
            "rs/Candidate.class": b"original recoverable candidate",
            "rs/Extra.class": b"not referenced by compiled reconstruction",
            "lib/Shared.class": b"original third-party",
            "images/logo.png": b"R448 invented png",
            "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\n",
        }
        self.original_jar = self.temp / "original-v309-synthetic.jar"
        self.original_jar.write_bytes(fake_zip(self.original_entries))
        self.depa = self.dependencies / "R239_filtered.jar"
        self.depb = self.dependencies / "R218.jar"
        self.depa.write_bytes(fake_zip({
            "lib/Shared.class": b"shared",
            "lib/Addon.class": b"addon",
        }))
        self.depb.write_bytes(fake_zip({
            "lib/Shared.class": b"shared-alt",
            "rs/Legacy.class": b"alternate-only",
        }))
        self.patchers = [
            patch.object(r448.r446.tempfile, "gettempdir",
                         return_value=str(self.temp)),
            patch.object(r425, "PINNED_R421_STORE_SHA",
                         sha256(self.store_java.read_bytes()).hexdigest()),
            patch.object(r425, "PINNED_R421_STORE_CLASS",
                         sha256(self.store_class.read_bytes()).hexdigest()),
            patch.object(r425, "BASELINE_SOURCE_COUNT", 2),
            patch.object(r425, "BASELINE_CLASS_COUNT", 2),
            patch.object(r448.r447, "ORIGINAL_SHA",
                         sha256(self.original_jar.read_bytes()).hexdigest()),
            patch.object(r448.r447, "ORIGINAL_CLASSES", 5),
            patch.object(r448.r447, "ORIGINAL_RESOURCES", 2),
        ]
        for item in self.patchers:
            item.start()
            self.addCleanup(item.stop)

    def private_outputs(self):
        return sorted(self.temp.glob(r448.PREFIX + "*"))

    def test_01_real_constant_pool_parser_on_invented_java11_classes(self):
        graph = r448.source_class_refs(r448.r446.observe()[0])
        self.assertEqual(len(graph), 2)
        self.assertIn("rs/Candidate.class", graph[
            r425.EXPECTED_CHANGED_EXISTING_CLASS])
        self.assertIn("rs/Legacy.class", graph[
            r425.EXPECTED_CHANGED_EXISTING_CLASS])
        self.assertIn("java/lang/Object.class", graph["rs/Bridge.class"])

    def test_02_exact_original_linkage_gap_counts(self):
        summary, worklist = r448.inspect(self.original_jar)
        self.assertEqual(summary["status"],
                         "R448_REBUILT_CONSTANT_POOL_GAP_ANALYSIS_UNAPPROVED")
        self.assertEqual(summary["original_class_count"], 5)
        self.assertEqual(summary["original_resource_count"], 2)
        self.assertEqual(summary["reconstructed_java_sources"], 2)
        self.assertEqual(summary["reconstructed_classfiles"], 2)
        self.assertEqual(summary["unique_rebuilt_nonplatform_class_targets"], 6)
        self.assertEqual(summary["class_targets_unresolved_in_preferred_runtime"], 3)
        self.assertEqual(summary["unresolved_class_targets_present_in_original_v309"], 1)
        self.assertEqual(summary["unresolved_class_targets_absent_from_original_v309"], 2)
        self.assertEqual(summary["unresolved_class_targets_available_in_alternate_dependency"], 1)
        self.assertEqual(summary["original_class_names_not_on_combined_classpath"], 2)
        self.assertEqual(summary["original_resource_file_extension_counts"],
                         {"mf": 1, "png": 1})
        self.assertFalse(summary["runtime_linkage_proven"])
        self.assertFalse(summary["release_authorized"])
        targets = {x["class_name"]: x
                   for x in worklist["missing_class_details"]}
        self.assertEqual(set(targets), {
            "rs/Candidate.class", "rs/Legacy.class", "rs/Unseen.class"})
        self.assertEqual(
            targets["rs/Candidate.class"]["direct_rebuilt_referencer_count"], 2)
        self.assertTrue(
            targets["rs/Candidate.class"]["original_v309_class_name_present"])
        self.assertTrue(
            targets["rs/Legacy.class"]["available_only_in_alternate_dependency"])

    def test_03_aggregate_stdout_contains_no_private_class_names(self):
        report = r448.run(self.original_jar)
        encoded = json.dumps(report)
        for private_name in (
            "rs/Candidate.class", "rs/Unseen.class", "rs/Legacy.class",
            "rs/Bridge.class", str(self.temp),
            r425.EXPECTED_CHANGED_EXISTING_CLASS):
            self.assertNotIn(private_name, encoded)
        self.assertFalse(report["private_worklist_saved"])
        self.assertEqual(self.private_outputs(), [])

    def test_04_prioritized_private_recovery_worklist_opt_in(self):
        report = r448.run(self.original_jar, save_private=True)
        self.assertTrue(report["private_worklist_saved"])
        outputs = self.private_outputs()
        self.assertEqual(len(outputs), 1)
        data = json.loads((outputs[0] / r448.NAME).read_text("ascii"))
        self.assertEqual(data["schema"], r448.SCHEMA)
        self.assertFalse(data["release_authorized"])
        self.assertFalse(data["historical_R421_reference_approved"])
        self.assertEqual([x["class_name"] for x in
                          data["missing_class_details"]],
                         ["rs/Candidate.class", "rs/Unseen.class",
                          "rs/Legacy.class"])
        self.assertNotIn(str(self.temp), json.dumps(report))

    def test_05_original_jar_shas_are_mandatory(self):
        self.original_entries["images/logo.png"] = b"changed!"
        self.original_jar.write_bytes(fake_zip(self.original_entries))
        with self.assertRaisesRegex(
                r448.r447.Refused, "R447_ORIGINAL_V309_SHA_MISMATCH"):
            r448.inspect(self.original_jar)

    def test_06_compiled_class_sha_race_is_refused(self):
        observed = r448.r446.observe()[0]
        (self.compiled / "rs/Bridge.class").write_bytes(fake_java11_class(
            "rs/Bridge", ("rs/OtherThing",)))
        with self.assertRaisesRegex(
                r448.Refused, "R448_R421_COMPILED_MEMBER_CHANGED_SINCE_OBSERVATION"):
            r448.source_class_refs(observed)

    def test_07_non_java11_compiled_class_refused(self):
        original = (self.compiled / "rs/Bridge.class").read_bytes()
        (self.compiled / "rs/Bridge.class").write_bytes(
            original[:6] + (61).to_bytes(2, "big") + original[8:])
        observation = r448.r446.observe()[0]
        with self.assertRaisesRegex(
                r448.Refused, "R448_JAVA11_R421_CLASSFILE_REQUIRED"):
            r448.source_class_refs(observation)

    def test_08_malformed_constant_pool_fails_closed(self):
        (self.compiled / "rs/Bridge.class").write_bytes(
            b"\xca\xfe\xba\xbe\x00\x00\x00\x37\x00\x09\xff")
        observation = r448.r446.observe()[0]
        with self.assertRaisesRegex(
                r448.Refused, "R448_BAD_OR_TRUNCATED_CLASS_CONSTANT_POOL"):
            r448.source_class_refs(observation)

    def test_09_original_resource_extensions_classified_not_exposed(self):
        self.assertEqual(
            r448.resource_extension_counts({
                "images/banner.PNG", "docs/license.TXT", "blob",
                "META-INF/MANIFEST.MF", "cache/bad.!long?extension",
            }),
            {"<no extension>": 1, "<other>": 1,
             "mf": 1, "png": 1, "txt": 1})

    def test_10_selected_rebuilt_entrypoint_stops_at_dependencies(self):
        summary, detail = r448.inspect(
            self.original_jar,
            entrypoint=r425.EXPECTED_CHANGED_EXISTING_CLASS)
        self.assertTrue(summary["selected_rebuilt_entrypoint_requested"])
        self.assertEqual(
            summary["selected_entrypoint_rebuilt_reachable_classes"], 2)
        self.assertEqual(
            summary["selected_entrypoint_reachable_unresolved_present_in_original"], 1)
        self.assertEqual(
            summary["selected_entrypoint_reachable_unresolved_absent_from_original"], 2)
        self.assertEqual(detail["selected_entrypoint_reachable_missing_class_names"],
                         ["rs/Candidate.class", "rs/Legacy.class",
                          "rs/Unseen.class"])

    def test_11_nonexistent_entrypoint_refused_not_fabricated(self):
        with self.assertRaisesRegex(
                r448.Refused, "R448_ENTRYPOINT_NOT_IN_REBUILT_TREE"):
            r448.inspect(self.original_jar,
                         entrypoint="rs/NotActuallyInCompiledTree.class")

    def test_12_original_class_present_but_preferred_dep_missing_prioritized(self):
        graph = {
            "rs/A.class": {"rs/C.class", "java/lang/String.class",
                           "lib/P.class"},
            "rs/B.class": {"rs/C.class", "rs/X.class"},
        }
        report, detail = r448.direct_graph_worklist(
            graph, {"rs/C.class", "rs/A.class", "rs/B.class"},
            {"lib/P.class"}, {"rs/X.class"},
            {"rs/A.java", "rs/B.java"},
        )
        self.assertEqual(report["class_targets_unresolved_in_preferred_runtime"], 2)
        self.assertEqual(report["unresolved_class_targets_present_in_original_v309"], 1)
        self.assertEqual(report["unresolved_class_targets_available_in_alternate_dependency"], 1)
        self.assertEqual(detail["unresolved_reconstruction_worklist"][0]["class_name"],
                         "rs/C.class")
        self.assertEqual(detail["unresolved_reconstruction_worklist"][0][
            "direct_rebuilt_referencer_count"], 2)

    def test_13_unresolved_class_names_without_referencers_never_ranked(self):
        graph = {"rs/A.class": {"java/lang/Object.class"}}
        report, detail = r448.direct_graph_worklist(
            graph, {"rs/Missing.class"}, set(), set(), {"rs/A.java"})
        self.assertEqual(report["class_targets_unresolved_in_preferred_runtime"], 0)
        self.assertEqual(detail["unresolved_reconstruction_worklist"], [])

    def test_14_platform_class_prefixes_not_treated_as_rebuild_gaps(self):
        graph = {
            "rs/A.class": {"java/lang/Object.class",
                           "javax/swing/JFrame.class",
                           "jdk/internal/Unsafe.class",
                           "rs/RealGap.class"}
        }
        report, _ = r448.direct_graph_worklist(
            graph, {"rs/A.class"}, set(), set(), {"rs/A.java"})
        self.assertEqual(report["unique_rebuilt_nonplatform_class_targets"], 1)
        self.assertEqual(report["class_targets_unresolved_in_preferred_runtime"], 1)

    def test_15_graph_with_no_entrypoint_does_not_claim_reachability(self):
        summary, _ = r448.inspect(self.original_jar)
        self.assertIsNone(summary["selected_entrypoint_rebuilt_reachable_classes"])
        self.assertIsNone(
            summary["selected_entrypoint_reachable_unresolved_present_in_original"])
        self.assertFalse(summary["selected_rebuilt_entrypoint_requested"])

    def test_16_unchanged_private_worklist_no_overwrite(self):
        one = r448.run(self.original_jar, save_private=True)
        first = self.private_outputs()[0] / r448.NAME
        original = first.read_bytes()
        two = r448.run(self.original_jar, save_private=True)
        self.assertEqual(len(self.private_outputs()), 2)
        self.assertNotEqual(one["private_quarantine_directory_name"],
                            two["private_quarantine_directory_name"])
        self.assertEqual(original, first.read_bytes())

    def test_17_candidate_class_file_too_large_refused_before_parse(self):
        (self.compiled / "rs/Bridge.class").write_bytes(b"x" * 1024)
        with patch.object(r448, "MAX_CLASS_BYTES", 80):
            observation = r448.r446.observe()[0]
            with self.assertRaisesRegex(
                    r448.scanner.Refused, "R448_COMPILED_CLASS_FILE_TOO_LARGE"):
                r448.source_class_refs(observation)

    def test_18_total_compiled_bytes_budget_refusal(self):
        observation = r448.r446.observe()[0]
        with patch.object(r448, "MAX_CLASS_TOTAL_BYTES", 40):
            with self.assertRaisesRegex(
                    r448.Refused, "R448_R421_COMPILED_TOTAL_BYTES_LIMIT"):
                r448.source_class_refs(observation)

    def test_19_class_reference_budget_refusal(self):
        observation = r448.r446.observe()[0]
        with patch.object(r448, "MAX_CLASS_REFS", 1):
            with self.assertRaisesRegex(
                    r448.Refused, "R448_CLASS_REFERENCE_BUDGET_EXCEEDED"):
                r448.source_class_refs(observation)

    def test_20_companion_optional_resource_hash_pass(self):
        companion = self.temp / "original-resource-companion"
        companion.mkdir()
        for name, data in self.original_entries.items():
            if name.endswith(".class"):
                continue
            target = companion / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        result, _ = r448.inspect(self.original_jar, companion)
        self.assertTrue(result["resource_companion_examined"])
        self.assertEqual(result["companion_resource_byte_matches"], 2)
        self.assertEqual(result["companion_resource_missing"], 0)
        self.assertEqual(result["companion_resource_mismatches"], 0)
        self.assertFalse(result["assets_packaged_into_rebuilt_JAR_proven"])

    def test_21_no_runtime_or_private_source_equivalence_claim(self):
        summary, _ = r448.inspect(self.original_jar)
        for key in ("runtime_tested", "client_runnable_proven",
                    "complete_deobfuscation_proven",
                    "bytecode_instruction_parity_proven",
                    "independent_prior_R421_custody_proven",
                    "build_authorized", "release_authorized",
                    "merge_authorized", "client_started"):
            self.assertFalse(summary[key])

    def test_22_changed_input_between_rechecks_refuses_private_output(self):
        real_inspect = r448.inspect
        calls = [0]
        def changed(*args, **kwargs):
            result = real_inspect(*args, **kwargs)
            calls[0] += 1
            if calls[0] == 1:
                (self.compiled / "rs/Bridge.class").write_bytes(
                    fake_java11_class("rs/Bridge", ("rs/Replacement",)))
            return result
        with patch.object(r448, "inspect", side_effect=changed):
            with self.assertRaisesRegex(
                    r448.Refused, "R448_INPUT_CHANGED_BEFORE_PRIVATE_REPORT"):
                # Actual changed bytes alter the graph; each full scan remains
                # permitted because it records the observed file state.
                r448.run(self.original_jar, save_private=True)
        self.assertEqual(self.private_outputs(), [])

    def test_23_expected_exception_if_compiled_class_tree_missing(self):
        self.store_class.unlink()
        with self.assertRaisesRegex(
                r448.r446.Refused,
                "R446_ORIGINAL_INVENTORY_COUNT_MISMATCH"):
            r448.inspect(self.original_jar)

    def test_24_cli_with_missing_original_jar_refuses_no_names_in_stdout(self):
        not_here = self.temp / "missing_original.jar"
        process = subprocess.run([
            sys.executable, "-B", str(CLI),
            "--original-v309-jar", str(not_here),
        ], capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(process.returncode, 2)
        receipt = json.loads(process.stdout)
        self.assertEqual(receipt["status"],
                         "R448_REBUILT_REFERENCE_ANALYSIS_REFUSED")
        self.assertFalse(receipt["release_authorized"])
        self.assertNotIn(str(not_here), process.stdout)

    def test_25_save_requires_explicit_flag_and_stays_private(self):
        code = (ROOT / "tools/r448/audit_rebuilt_class_linkage.py").read_text(
            encoding="utf-8")
        self.assertIn("--save-private-unapproved-worklist", code)
        self.assertIn("O_EXCL", code)
        self.assertIn("private_worklist_saved", code)
        self.assertNotIn("subprocess.run(", code)
        self.assertNotIn("shutil.copy(", code)
        self.assertNotIn("player-history.json", code)
        self.assertNotIn("client.jar", code)
        self.assertIn("original_v309_exact_SHA_matched", code)


if __name__ == "__main__":
    unittest.main()

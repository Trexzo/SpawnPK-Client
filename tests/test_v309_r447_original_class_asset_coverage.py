"""R447 public-only original-JAR class/resource coverage regressions.

Only invented Java class names, dummy bytes and sandbox ZIP files. No
original SpawnPK client, recovered source code, history, JAR install, or
deletion journal enters hosted CI.
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
import warnings
import zipfile

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r447 import audit_original_class_asset_coverage as r447

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r447/audit_original_class_asset_coverage.py"


def zip_bytes(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return stream.getvalue()


class R447OriginalV309Coverage(unittest.TestCase):
    def setUp(self):
        self.working = tempfile.TemporaryDirectory(prefix="R447-Synthetic-")
        self.addCleanup(self.working.cleanup)
        self.temp = Path(self.working.name)
        self.parent = (self.temp / "SpawnPK-R386-Isolated-Acceptance"
                       / "R421-Private-NoFollow-Cache-Directory-Preflight")
        self.candidate = self.parent / "Source-Candidate-R421"
        self.src = self.candidate / "source"
        self.cls = self.parent / "R421-Compiled-Classes"
        self.dependencies = self.candidate / "dependencies"
        self.dependencies.mkdir(parents=True)
        self.store_src = self.src / r425.STORE
        self.store_cls = self.cls / r425.EXPECTED_CHANGED_EXISTING_CLASS
        self.store_src.parent.mkdir(parents=True)
        self.store_cls.parent.mkdir(parents=True)
        self.store_src.write_bytes(b"R447 invented Store source")
        self.store_cls.write_bytes(b"R447 invented Store class bytes")
        (self.src / "rs/Fabricated.java").write_bytes(b"R447 invented Java")
        (self.cls / "rs/Fabricated.class").write_bytes(b"R447 invented class")

        self.original_entries = {
            r425.EXPECTED_CHANGED_EXISTING_CLASS: b"R447 original Store class",
            "rs/Fabricated.class": b"R447 original fabricated class",
            "rs/OriginalExtra.class": b"R447 original extra",
            "rs/legacy/Legacy.class": b"R447 original legacy",
            "lib/Shared.class": b"R447 third-party shared",
            "rs/Unmapped.class": b"R447 original unmapped",
            "images/logo.png": b"PNG-not-real-image",
            "data/client.bin": b"R447 invented resource bytes",
            "META-INF/MANIFEST.MF": b"Manifest-Version: 1.0\n",
        }
        self.original = self.temp / "original-v309-client.jar"
        self.write_original()
        depa = self.dependencies / "R239_filtered.jar"
        depb = self.dependencies / "R218.jar"
        depa.write_bytes(zip_bytes({
            "lib/Shared.class": b"R447 same third-party",
            "lib/Addon.class": b"R447 addon",
            "rs/legacy/Legacy.class": b"R447 legacy",
        }))
        depb.write_bytes(zip_bytes({
            "lib/Shared.class": b"R447 shared alternate",
            "lib/B.class": b"R447 alternative",
        }))
        self.depa = depa
        self.depb = depb
        self.companion = self.temp / "private-resource-companion"
        self.companion.mkdir()
        self.patches = [
            patch.object(r447.r446.tempfile, "gettempdir",
                         return_value=str(self.temp)),
            patch.object(r425, "PINNED_R421_STORE_SHA",
                         sha256(self.store_src.read_bytes()).hexdigest()),
            patch.object(r425, "PINNED_R421_STORE_CLASS",
                         sha256(self.store_cls.read_bytes()).hexdigest()),
            patch.object(r425, "BASELINE_SOURCE_COUNT", 2),
            patch.object(r425, "BASELINE_CLASS_COUNT", 2),
            patch.object(r447, "ORIGINAL_SHA", sha256(self.original.read_bytes()).hexdigest()),
            patch.object(r447, "ORIGINAL_CLASSES", 6),
            patch.object(r447, "ORIGINAL_RESOURCES", 3),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def write_original(self):
        self.original.write_bytes(zip_bytes(self.original_entries))

    def output_dirs(self):
        return sorted(p for p in self.temp.iterdir()
                      if p.name.startswith(r447.PRIVATE_PREFIX))

    def test_01_exact_original_and_rebuilt_coverage_counts(self):
        summary, detail = r447.examine(self.original)
        self.assertEqual(summary["status"],
                         "R447_ORIGINAL_CLASS_ASSET_COVERAGE_UNAPPROVED")
        self.assertEqual(summary["original_class_count"], 6)
        self.assertEqual(summary["original_nonclass_resource_count"], 3)
        self.assertEqual(summary["r421_observed_java_sources"], 2)
        self.assertEqual(summary["r421_observed_compiled_classes"], 2)
        self.assertEqual(summary["preferred_dependency_classes"], 3)
        self.assertEqual(summary["alternate_dependency_classes"], 2)
        self.assertEqual(summary["combined_preferred_classpath_unique_paths"], 5)
        self.assertEqual(summary["original_class_names_on_combined_classpath"], 4)
        self.assertEqual(summary["original_class_names_absent_from_combined_classpath"], 2)
        self.assertEqual(summary["combined_classpaths_not_named_in_original"], 1)
        self.assertEqual(summary["rebuilt_classes_also_named_in_original"], 2)
        self.assertEqual(summary["preferred_alternate_dependency_overlap"], 1)
        self.assertEqual(detail["original_class_names_not_on_reconstructed_classpath"],
                         ["rs/OriginalExtra.class", "rs/Unmapped.class"])
        self.assertFalse(summary["complete_readable_client_source_proven"])
        self.assertFalse(summary["compiled_class_behavioural_equivalence_proven"])
        self.assertFalse(summary["release_authorized"])

    def test_02_no_write_default_stays_aggregate_only(self):
        summary = r447.run(self.original)
        self.assertFalse(summary["private_name_map_created"])
        self.assertFalse(summary["client_started"])
        self.assertFalse(summary["assets_packaged_in_rebuilt_client_verified"])
        self.assertEqual(self.output_dirs(), [])
        text = json.dumps(summary)
        for original_name in self.original_entries:
            self.assertNotIn(original_name, text)
        self.assertNotIn(str(self.temp), text)
        self.assertNotIn(r447.ORIGINAL_SHA, text)

    def test_03_private_opt_in_writes_new_quarantine_only(self):
        report = r447.run(self.original, save_private_map=True)
        self.assertTrue(report["private_name_map_created"])
        self.assertEqual(len(self.output_dirs()), 1)
        output = self.output_dirs()[0] / r447.PRIVATE_NAME
        detail = json.loads(output.read_text("ascii"))
        self.assertEqual(detail["schema"], r447.PRIVATE_SCHEMA)
        self.assertEqual(detail["original_class_names_not_on_reconstructed_classpath"],
                         ["rs/OriginalExtra.class", "rs/Unmapped.class"])
        self.assertEqual(len(detail["original_resource_names_needing_byte_verification"]), 3)
        self.assertFalse(detail["compilation_authorized"])
        self.assertFalse(detail["release_authorized"])
        self.assertNotIn(str(self.temp), json.dumps(report))

    def test_04_no_overwrite_on_separate_private_reports(self):
        first = r447.run(self.original, save_private_map=True)
        original = self.output_dirs()[0] / r447.PRIVATE_NAME
        old_bytes = original.read_bytes()
        second = r447.run(self.original, save_private_map=True)
        self.assertEqual(len(self.output_dirs()), 2)
        self.assertNotEqual(first["private_quarantine_directory_name"],
                            second["private_quarantine_directory_name"])
        self.assertEqual(original.read_bytes(), old_bytes)

    def test_05_original_sha_mismatch_refused_even_if_zip_is_well_formed(self):
        self.original_entries["images/logo.png"] = b"modified"
        self.write_original()
        with self.assertRaisesRegex(r447.Refused, "R447_ORIGINAL_V309_SHA_MISMATCH"):
            r447.examine(self.original)

    def test_06_missing_original_or_symlink_is_never_opened(self):
        self.original.unlink()
        with self.assertRaisesRegex(r447.Refused, "R447_ORIGINAL_JAR_MISSING_OR_UNSAFE"):
            r447.examine(self.original)
        elsewhere = self.temp / "outside.bin"
        elsewhere.write_bytes(b"untrusted user file")
        try:
            self.original.symlink_to(elsewhere)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable on test host")
        with self.assertRaisesRegex(r447.Refused, "R447_ORIGINAL_JAR_MISSING_OR_UNSAFE"):
            r447.examine(self.original)
        self.assertEqual(elsewhere.read_bytes(), b"untrusted user file")

    def test_07_original_class_or_resource_count_drift_refused(self):
        with patch.object(r447, "ORIGINAL_CLASSES", 7):
            with self.assertRaisesRegex(
                    r447.Refused, "R447_PINNED_ORIGINAL_ARCHIVE_INVENTORY_DRIFT"):
                r447.examine(self.original)
        with patch.object(r447, "ORIGINAL_RESOURCES", 4):
            with self.assertRaisesRegex(
                    r447.Refused, "R447_PINNED_ORIGINAL_ARCHIVE_INVENTORY_DRIFT"):
                r447.examine(self.original)

    def test_08_zip_directory_entries_ignored_and_not_resources(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("directory/", b"")
            z.writestr("directory/Fabricated.class", b"fake class")
            z.writestr("images/logo.png", b"fake image")
        classes, resources, _ = r447.archive(stream.getvalue(), "original")
        self.assertEqual(classes, {"directory/Fabricated.class"})
        self.assertEqual(resources, {"images/logo.png"})

    def test_09_duplicate_zip_entries_refused(self):
        stream = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(stream, "w") as z:
                z.writestr("rs/Dupe.class", b"one")
                z.writestr("rs/Dupe.class", b"two")
        with self.assertRaisesRegex(r447.Refused, "R447_DUPLICATE_ZIP_ENTRY"):
            r447.archive(stream.getvalue(), "original")

    def test_10_path_escape_and_backslash_zip_entries_refused(self):
        for name in ("../secret.class", "/root.class", "./relative.class",
                     "sub\\windows.class", "sub//double.class",
                     "sub/./dot.class", "sub/../traversal.class"):
            with self.subTest(path=name):
                data = zip_bytes({name: b"unsafe"})
                with self.assertRaisesRegex(r447.Refused, "R447_UNSAFE_ZIP_ENTRY_PATH"):
                    r447.archive(data, "original")

    def test_11_zip_entry_and_total_uncompressed_size_bounds(self):
        data = zip_bytes({"rs/A.class": b"a"*100, "rs/B.class": b"b"*100})
        with patch.object(r447, "MAX_UNCOMPRESSED_ENTRY", 80):
            with self.assertRaisesRegex(
                    r447.Refused, "R447_UNCOMPRESSED_ENTRY_TOO_LARGE"):
                r447.archive(data, "original")
        with patch.object(r447, "MAX_UNCOMPRESSED_TOTAL", 150):
            with self.assertRaisesRegex(
                    r447.Refused, "R447_UNCOMPRESSED_TOTAL_BUDGET_EXCEEDED"):
                r447.archive(data, "original")

    def test_12_zip_entry_budget_refusal(self):
        data = zip_bytes({"rs/A.class": b"a", "rs/B.class": b"b"})
        with patch.object(r447, "MAX_ZIP_ENTRIES", 1):
            with self.assertRaisesRegex(r447.Refused, "R447_ZIP_ENTRY_BUDGET_EXCEEDED"):
                r447.archive(data, "original")

    def test_13_truncated_or_nonzip_bytes_refused(self):
        for data in (b"not zip", b"PK\x03\x04", b""):
            with self.subTest(data=data):
                with self.assertRaisesRegex(
                        r447.Refused, "R447_INVALID_ZIP_ARCHIVE|R447_EMPTY_ARCHIVE_BYTES"):
                    r447.archive(data, "original")

    def test_14_companion_byte_for_byte_complete(self):
        for name, data in self.original_entries.items():
            if name.endswith(".class"):
                continue
            path = self.companion / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        summary, detail = r447.examine(self.original, self.companion)
        self.assertTrue(summary["resource_companion_examined"])
        self.assertEqual(summary["companion_resource_byte_matches"], 3)
        self.assertEqual(summary["companion_resource_missing"], 0)
        self.assertEqual(summary["companion_resource_mismatches"], 0)
        self.assertEqual(summary["companion_unreferenced_files"], 0)
        self.assertEqual(detail["original_resource_names_needing_byte_verification"], [])
        self.assertFalse(summary["assets_packaged_in_rebuilt_client_verified"])

    def test_15_companion_missing_mismatched_and_extra_resources(self):
        logo = self.companion / "images/logo.png"
        logo.parent.mkdir(parents=True)
        logo.write_bytes(b"wrong bytes")
        extra = self.companion / "unrelated/orphan.png"
        extra.parent.mkdir(parents=True)
        extra.write_bytes(b"something unrelated")
        summary, detail = r447.examine(self.original, self.companion)
        self.assertEqual(summary["companion_resource_byte_matches"], 0)
        self.assertEqual(summary["companion_resource_mismatches"], 1)
        self.assertEqual(summary["companion_resource_missing"], 2)
        self.assertEqual(summary["companion_unreferenced_files"], 1)
        self.assertEqual(len(detail["original_resource_names_needing_byte_verification"]), 3)
        self.assertEqual(detail["companion_extra_resource_paths"], ["unrelated/orphan.png"])

    def test_16_companion_extra_symlink_refused_not_traversed(self):
        external = self.temp / "external resource"
        external.write_bytes(b"external")
        shortcut = self.companion / "outside.txt"
        try:
            shortcut.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable on test host")
        with self.assertRaisesRegex(r447.Refused, "R447_COMPANION_LINK_OR_SPECIAL"):
            r447.examine(self.original, self.companion)
        self.assertEqual(external.read_bytes(), b"external")

    def test_17_companion_entry_limit_refuses_before_unbounded_enumeration(self):
        for i in range(5):
            (self.companion / f"extra{i}.txt").write_bytes(b"file")
        with patch.object(r447, "MAX_COMPANION_ENTRIES", 3):
            with self.assertRaisesRegex(r447.scanner.Refused,
                                        "R447_COMPANION_DIR_TOO_LARGE"):
                r447.examine(self.original, self.companion)

    def test_18_missing_dependency_refused_by_r446_before_jar_coverage(self):
        self.depa.unlink()
        with self.assertRaisesRegex(r447.r446.Refused,
                                    "R446_DEPENDENCY_MISSING_OR_CHANGED"):
            r447.examine(self.original)

    def test_19_nonzip_dependency_not_accepted_as_class_coverage(self):
        self.depa.write_bytes(b"not actually a jar")
        with self.assertRaisesRegex(r447.Refused, "R447_INVALID_ZIP_ARCHIVE"):
            r447.examine(self.original)

    def test_20_changed_original_between_scans_blocks_private_map(self):
        first = r447.examine
        count = [0]
        def changed(*args, **kwargs):
            result = first(*args, **kwargs)
            count[0] += 1
            if count[0] == 1:
                self.original.write_bytes(b"R447 changed original byte stream")
            return result
        with patch.object(r447, "examine", side_effect=changed):
            with self.assertRaisesRegex(r447.Refused, "R447_ORIGINAL_V309_SHA_MISMATCH"):
                r447.run(self.original, save_private_map=True)
        self.assertEqual(count[0], 1)
        self.assertEqual(self.output_dirs(), [])

    def test_21_companion_resources_only_byte_checks_not_client_installation(self):
        for key in ("release_authorized", "merge_authorized",
                    "v312_compatibility_proven", "client_started",
                    "candidate_compiled", "history_accessed",
                    "compiled_class_behavioural_equivalence_proven"):
            report = r447.run(self.original)
            self.assertFalse(report[key])
        self.assertEqual(self.output_dirs(), [])

    def test_22_test_r447_single_class_source_heuristic_is_advisory(self):
        self.assertEqual(r447.java_owner_heuristic(
            "rs/Outer$Nested.class"), "rs/Outer.java")
        self.assertEqual(r447.java_owner_heuristic(
            "rs/Outer.class"), "rs/Outer.java")
        self.assertEqual(r447.java_owner_heuristic(
            "rs/pkg/package-info.class"), "rs/pkg/package-info.java")

    def test_23_public_cli_missing_approved_original_never_leaks_path(self):
        absent = self.temp / "nonexistent original JAR"
        proc = subprocess.run(
            [sys.executable, "-B", str(CLI),
             "--original-v309-jar", str(absent)],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["status"],
                         "R447_ORIGINAL_CLASS_ASSET_COVERAGE_REFUSED")
        self.assertFalse(receipt["release_authorized"])
        self.assertNotIn(str(absent), proc.stdout)

    def test_24_exact_v309_original_SHA_pin_not_caller_supplied(self):
        script = (ROOT / "tools/r447/audit_original_class_asset_coverage.py").read_text(
            "utf-8")
        self.assertIn('ORIGINAL_SHA = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"', script)
        self.assertIn("ORIGINAL_CLASSES = 10502", script)
        self.assertIn("ORIGINAL_RESOURCES = 419", script)
        self.assertNotIn("--override-original-sha", script)
        self.assertNotIn("subprocess.run(", script)
        self.assertNotIn("os.system(", script)  # no shell or game startup
        self.assertIn("R447_ORIGINAL_V309_SHA_MISMATCH", script)


if __name__ == "__main__":
    unittest.main()

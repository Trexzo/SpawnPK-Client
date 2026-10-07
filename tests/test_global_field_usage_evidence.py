from __future__ import annotations

from collections import Counter
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from spk_recovery.global_field_usage_evidence import (
    GlobalFieldUsageEvidenceError,
    _scan_source_class_usage,
    _scan_usage,
    _stable_reviews,
    build_global_field_usage_evidence,
)


@unittest.skipUnless(shutil.which("javac"), "Java compiler required")
class GlobalFieldUsageScannerTests(unittest.TestCase):
    def _jar(self, root: Path) -> Path:
        src = root / "src" / "rs"
        classes = root / "classes"
        src.mkdir(parents=True)
        classes.mkdir()

        (src / "A.java").write_text(
            "package rs; public class A { public int x; }\n",
            encoding="utf-8",
        )
        (src / "B.java").write_text(
            "package rs; public class B { "
            "public static int read(A a) { return a.x; } "
            "public static void write(A a, int v) { a.x = v; } "
            "public static int ignored(A a) { return a.x + 1; } "
            "}\n",
            encoding="utf-8",
        )
        compiled = subprocess.run(
            [
                "javac",
                "-g:none",
                "-d",
                str(classes),
                str(src / "A.java"),
                str(src / "B.java"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            compiled.returncode,
            0,
            compiled.stdout + compiled.stderr,
        )

        jar = root / "client.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(
                    path,
                    path.relative_to(classes).as_posix(),
                )
        return jar

    def test_scans_only_canonical_methods_and_exact_field_operations(self):
        with tempfile.TemporaryDirectory() as td:
            jar = self._jar(Path(td))
            usage, summary = _scan_usage(
                jar,
                {
                    "rs/B": {
                        ("read", "(Lrs/A;)I"): "CLIENT_METHOD_READ",
                        ("write", "(Lrs/A;I)V"): "CLIENT_METHOD_WRITE",
                    }
                },
                {("rs/A", "x", "I")},
            )

            self.assertEqual(
                usage[("rs/A", "x", "I")],
                Counter(
                    {
                        ("CLIENT_METHOD_READ", "getfield"): 1,
                        ("CLIENT_METHOD_WRITE", "putfield"): 1,
                    }
                ),
            )
            self.assertEqual(summary["source_classes_scanned"], 1)
            self.assertEqual(summary["source_classes_relevant"], 1)
            self.assertEqual(summary["field_access_observations"], 2)

    def test_source_class_topology_includes_noncanonical_methods(self):
        with tempfile.TemporaryDirectory() as td:
            jar = self._jar(Path(td))
            usage, summary = _scan_source_class_usage(
                jar,
                {"rs/B": "CLIENT_CLASS_B"},
                {("rs/A", "x", "I")},
            )

            self.assertEqual(
                usage[("rs/A", "x", "I")],
                Counter(
                    {
                        ("CLIENT_CLASS_B", "getfield"): 2,
                        ("CLIENT_CLASS_B", "putfield"): 1,
                    }
                ),
            )
            self.assertGreaterEqual(summary["classes_scanned"], 2)
            self.assertEqual(summary["classes_relevant"], 1)
            self.assertEqual(summary["field_access_observations"], 3)

    def test_noncanonical_method_access_is_not_counted(self):
        with tempfile.TemporaryDirectory() as td:
            jar = self._jar(Path(td))
            usage, _summary = _scan_usage(
                jar,
                {
                    "rs/B": {
                        ("read", "(Lrs/A;)I"): "CLIENT_METHOD_READ",
                    }
                },
                {("rs/A", "x", "I")},
            )

            self.assertEqual(
                usage[("rs/A", "x", "I")],
                Counter(
                    {
                        ("CLIENT_METHOD_READ", "getfield"): 1,
                    }
                ),
            )


class GlobalFieldUsageEvidenceTests(unittest.TestCase):
    def _classes(self):
        return {
            "builds": [
                {"build_id": "v308", "sha256": "1" * 64},
                {"build_id": "v309", "sha256": "2" * 64},
            ]
        }

    def _review(self, relationship_id: str, field: str):
        return {
            "relationship_id": relationship_id,
            "logical_class_id": "CLIENT_CLASS_000001",
            "old_owner": "rs/A",
            "new_owner": "rs/A",
            "old": {
                "name": field,
                "descriptor": "I",
                "access": 1,
            },
            "new": {
                "name": field,
                "descriptor": "I",
                "access": 1,
            },
        }

    def test_report_emits_only_equal_nonempty_global_topology(self):
        r1 = self._review("MEMREL_1", "x")
        r2 = self._review("MEMREL_2", "y")
        old_usage = {
            ("rs/A", "x", "I"): Counter(
                {
                    ("CLIENT_METHOD_1", "getfield"): 2,
                    ("CLIENT_METHOD_2", "putfield"): 1,
                }
            ),
            ("rs/A", "y", "I"): Counter(),
        }
        new_usage = {
            ("rs/A", "x", "I"): Counter(
                {
                    ("CLIENT_METHOD_1", "getfield"): 2,
                    ("CLIENT_METHOD_2", "putfield"): 1,
                }
            ),
            ("rs/A", "y", "I"): Counter(),
        }
        scan_summary = {
            "source_classes_scanned": 2,
            "source_classes_relevant": 1,
            "canonical_methods_scanned": 2,
            "field_access_observations": 3,
        }
        old_class_usage = {
            ("rs/A", "x", "I"): Counter(
                {("CLIENT_CLASS_B", "getfield"): 3}
            ),
            ("rs/A", "y", "I"): Counter(),
        }
        new_class_usage = {
            ("rs/A", "x", "I"): Counter(
                {("CLIENT_CLASS_B", "getfield"): 3}
            ),
            ("rs/A", "y", "I"): Counter(),
        }
        class_scan_summary = {
            "classes_scanned": 3,
            "classes_relevant": 1,
            "field_access_observations": 3,
        }

        with (
            patch(
                "spk_recovery.global_field_usage_evidence.validate_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "validate_member_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence.sha256_file",
                side_effect=["1" * 64, "2" * 64],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence._stable_reviews",
                return_value=[r1, r2],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "_paired_method_maps",
                return_value=(
                    {"rs/B": {("m", "()V"): "CLIENT_METHOD_1"}},
                    {"rs/B": {("m", "()V"): "CLIENT_METHOD_1"}},
                    1,
                ),
            ),
            patch(
                "spk_recovery.global_field_usage_evidence._scan_usage",
                side_effect=[
                    (old_usage, scan_summary),
                    (new_usage, scan_summary),
                ],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "_scan_source_class_usage",
                side_effect=[
                    (old_class_usage, class_scan_summary),
                    (new_class_usage, class_scan_summary),
                ],
            ),
        ):
            report = build_global_field_usage_evidence(
                self._classes(),
                {"members": [], "unresolved": []},
                {"sha256": "1" * 64},
                {"sha256": "2" * 64},
                Path("old.jar"),
                Path("new.jar"),
                old_build_id="v308",
                new_build_id="v309",
            )

        self.assertFalse(report["canonical"])
        self.assertEqual(report["summary"]["input_stable_symbol_reviews"], 2)
        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(report["summary"]["empty_both"], 1)
        self.assertEqual(
            report["summary"]["remaining_without_global_topology_proof"],
            1,
        )
        candidate = report["candidates"][0]
        self.assertEqual(candidate["relationship_id"], "MEMREL_1")
        self.assertTrue(candidate["supports_existing_review"])
        self.assertEqual(
            candidate["strategy"],
            "canonical_method_and_global_class_usage_topology_exact",
        )
        self.assertEqual(candidate["observations"], 3)
        self.assertEqual(candidate["canonical_methods"], 2)

    def test_mismatched_topology_remains_unresolved(self):
        review = self._review("MEMREL_1", "x")
        old_usage = {
            ("rs/A", "x", "I"): Counter(
                {("CLIENT_METHOD_1", "getfield"): 1}
            )
        }
        new_usage = {
            ("rs/A", "x", "I"): Counter(
                {("CLIENT_METHOD_1", "putfield"): 1}
            )
        }
        scan_summary = {
            "source_classes_scanned": 1,
            "source_classes_relevant": 1,
            "canonical_methods_scanned": 1,
            "field_access_observations": 1,
        }
        class_usage = {
            ("rs/A", "x", "I"): Counter(
                {("CLIENT_CLASS_B", "getfield"): 1}
            )
        }
        class_scan_summary = {
            "classes_scanned": 2,
            "classes_relevant": 1,
            "field_access_observations": 1,
        }

        with (
            patch(
                "spk_recovery.global_field_usage_evidence.validate_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "validate_member_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence.sha256_file",
                side_effect=["1" * 64, "2" * 64],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence._stable_reviews",
                return_value=[review],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "_paired_method_maps",
                return_value=(
                    {"rs/B": {("m", "()V"): "CLIENT_METHOD_1"}},
                    {"rs/B": {("m", "()V"): "CLIENT_METHOD_1"}},
                    1,
                ),
            ),
            patch(
                "spk_recovery.global_field_usage_evidence._scan_usage",
                side_effect=[
                    (old_usage, scan_summary),
                    (new_usage, scan_summary),
                ],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "_scan_source_class_usage",
                side_effect=[
                    (class_usage, class_scan_summary),
                    (class_usage, class_scan_summary),
                ],
            ),
        ):
            report = build_global_field_usage_evidence(
                self._classes(),
                {"members": [], "unresolved": []},
                {"sha256": "1" * 64},
                {"sha256": "2" * 64},
                Path("old.jar"),
                Path("new.jar"),
                old_build_id="v308",
                new_build_id="v309",
            )

        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(report["summary"]["changed_or_one_sided"], 1)
        self.assertEqual(report["candidates"], [])

    def test_global_class_topology_can_veto_method_match(self):
        review = self._review("MEMREL_1", "x")
        method_usage = {
            ("rs/A", "x", "I"): Counter(
                {("CLIENT_METHOD_1", "getfield"): 1}
            )
        }
        old_class_usage = {
            ("rs/A", "x", "I"): Counter(
                {("CLIENT_CLASS_B", "getfield"): 1}
            )
        }
        new_class_usage = {
            ("rs/A", "x", "I"): Counter(
                {
                    ("CLIENT_CLASS_B", "getfield"): 1,
                    ("CLIENT_CLASS_C", "putfield"): 1,
                }
            )
        }
        method_summary = {
            "source_classes_scanned": 1,
            "source_classes_relevant": 1,
            "canonical_methods_scanned": 1,
            "field_access_observations": 1,
        }
        old_class_summary = {
            "classes_scanned": 2,
            "classes_relevant": 1,
            "field_access_observations": 1,
        }
        new_class_summary = {
            "classes_scanned": 3,
            "classes_relevant": 2,
            "field_access_observations": 2,
        }

        with (
            patch(
                "spk_recovery.global_field_usage_evidence.validate_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "validate_member_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence.sha256_file",
                side_effect=["1" * 64, "2" * 64],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence._stable_reviews",
                return_value=[review],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "_paired_method_maps",
                return_value=(
                    {"rs/B": {("m", "()V"): "CLIENT_METHOD_1"}},
                    {"rs/B": {("m", "()V"): "CLIENT_METHOD_1"}},
                    1,
                ),
            ),
            patch(
                "spk_recovery.global_field_usage_evidence._scan_usage",
                side_effect=[
                    (method_usage, method_summary),
                    (method_usage, method_summary),
                ],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "_scan_source_class_usage",
                side_effect=[
                    (old_class_usage, old_class_summary),
                    (new_class_usage, new_class_summary),
                ],
            ),
        ):
            report = build_global_field_usage_evidence(
                self._classes(),
                {"members": [], "unresolved": []},
                {"sha256": "1" * 64},
                {"sha256": "2" * 64},
                Path("old.jar"),
                Path("new.jar"),
                old_build_id="v308",
                new_build_id="v309",
            )

        self.assertEqual(
            report["summary"]["canonical_method_topology_matches"],
            1,
        )
        self.assertEqual(
            report["summary"]["global_class_topology_guard_rejected"],
            1,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(report["candidates"], [])

    def test_raw_source_class_support_is_refused(self):
        review = self._review("MEMREL_1", "x")
        method_usage = {
            ("rs/A", "x", "I"): Counter(
                {("CLIENT_METHOD_1", "getfield"): 1}
            )
        }
        class_usage = {
            ("rs/A", "x", "I"): Counter(
                {("RAW:rs/unmapped", "getfield"): 1}
            )
        }
        method_summary = {
            "source_classes_scanned": 1,
            "source_classes_relevant": 1,
            "canonical_methods_scanned": 1,
            "field_access_observations": 1,
        }
        class_summary = {
            "classes_scanned": 2,
            "classes_relevant": 1,
            "field_access_observations": 1,
        }

        with (
            patch(
                "spk_recovery.global_field_usage_evidence.validate_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "validate_member_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence.sha256_file",
                side_effect=["1" * 64, "2" * 64],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence._stable_reviews",
                return_value=[review],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "_paired_method_maps",
                return_value=(
                    {"rs/B": {("m", "()V"): "CLIENT_METHOD_1"}},
                    {"rs/B": {("m", "()V"): "CLIENT_METHOD_1"}},
                    1,
                ),
            ),
            patch(
                "spk_recovery.global_field_usage_evidence._scan_usage",
                side_effect=[
                    (method_usage, method_summary),
                    (method_usage, method_summary),
                ],
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "_scan_source_class_usage",
                side_effect=[
                    (class_usage, class_summary),
                    (class_usage, class_summary),
                ],
            ),
        ):
            report = build_global_field_usage_evidence(
                self._classes(),
                {"members": [], "unresolved": []},
                {"sha256": "1" * 64},
                {"sha256": "2" * 64},
                Path("old.jar"),
                Path("new.jar"),
                old_build_id="v308",
                new_build_id="v309",
            )

        self.assertEqual(
            report["summary"]["canonical_method_topology_matches"],
            1,
        )
        self.assertEqual(
            report["summary"]["raw_source_guard_rejected"],
            1,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(report["candidates"], [])

    def test_duplicate_review_coordinate_is_refused(self):
        classes = {
            "classes": [
                {
                    "logical_id": "CLIENT_CLASS_000001",
                    "lineage": [
                        {
                            "build_id": "v308",
                            "internal_name": "rs/A",
                        },
                        {
                            "build_id": "v309",
                            "internal_name": "rs/A",
                        },
                    ],
                }
            ]
        }
        candidate = {
            "relationship_id": "MEMREL_1",
            "strategy": "stable_symbol",
            "old_owner": "rs/A.class",
            "new_owner": "rs/A.class",
            "old": {
                "name": "x",
                "descriptor": "I",
                "access": 1,
            },
            "new": {
                "name": "x",
                "descriptor": "I",
                "access": 1,
            },
        }
        second = {
            **candidate,
            "relationship_id": "MEMREL_2",
        }
        members = {
            "unresolved": [
                {
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "source": "member_identity_candidates",
                    "old_build_id": "v308",
                    "new_build_id": "v309",
                    "candidate": candidate,
                },
                {
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "source": "member_identity_candidates",
                    "old_build_id": "v308",
                    "new_build_id": "v309",
                    "candidate": second,
                },
            ]
        }
        index = {
            "classes": {
                "rs/A.class": {
                    "fields": [
                        {
                            "name": "x",
                            "descriptor": "I",
                            "access": 1,
                        }
                    ]
                }
            }
        }
        with self.assertRaisesRegex(
            GlobalFieldUsageEvidenceError,
            "duplicate old review coordinate",
        ):
            _stable_reviews(
                classes,
                members,
                index,
                index,
                old_build_id="v308",
                new_build_id="v309",
            )

    def test_exact_jar_index_sha_drift_is_refused(self):
        with (
            patch(
                "spk_recovery.global_field_usage_evidence.validate_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence."
                "validate_member_lineage"
            ),
            patch(
                "spk_recovery.global_field_usage_evidence.sha256_file",
                side_effect=["1" * 64, "2" * 64],
            ),
        ):
            with self.assertRaisesRegex(
                GlobalFieldUsageEvidenceError,
                "old JAR SHA does not match exact old index",
            ):
                build_global_field_usage_evidence(
                    self._classes(),
                    {"members": [], "unresolved": []},
                    {"sha256": "9" * 64},
                    {"sha256": "2" * 64},
                    Path("old.jar"),
                    Path("new.jar"),
                    old_build_id="v308",
                    new_build_id="v309",
                )


if __name__ == "__main__":
    unittest.main()

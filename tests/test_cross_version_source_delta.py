import copy
import tempfile
import unittest
from pathlib import Path

from spk_recovery.cross_version_source_delta import (
    CrossVersionSourceDeltaError,
    build_cross_version_source_delta,
)
from spk_recovery.source_digest import source_tree_digest


OLD_SHA = "1" * 64
NEW_SHA = "2" * 64


def _lineage():
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v307",
        "builds": [
            {
                "build_id": "v307",
                "build_number": 307,
                "sha256": OLD_SHA,
                "source_name": "old.jar",
                "authority": "EXACT_HISTORICAL_CLIENT",
            },
            {
                "build_id": "v308",
                "build_number": 308,
                "sha256": NEW_SHA,
                "source_name": "new.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            },
        ],
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000001",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v307",
                        "internal_name": "rs/A",
                        "entry_path": "rs/A.class",
                        "entry_sha256": "a" * 64,
                        "structural_sha256": "b" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": "EXACT_HISTORICAL_CLIENT",
                                "source": "test",
                            }
                        ],
                    },
                    {
                        "build_id": "v308",
                        "internal_name": "rs/B",
                        "entry_path": "rs/B.class",
                        "entry_sha256": "c" * 64,
                        "structural_sha256": "b" * 64,
                        "relation": "STRUCTURAL",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": "CROSS_BUILD",
                                "source": "test",
                            }
                        ],
                    },
                ],
                "semantic_provenance": [],
            },
            {
                "logical_id": "CLIENT_CLASS_000002",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v307",
                        "internal_name": "rs/C",
                        "entry_path": "rs/C.class",
                        "entry_sha256": "d" * 64,
                        "structural_sha256": "e" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": "EXACT_HISTORICAL_CLIENT",
                                "source": "test",
                            }
                        ],
                    },
                    {
                        "build_id": "v308",
                        "internal_name": "rs/C",
                        "entry_path": "rs/C.class",
                        "entry_sha256": "f" * 64,
                        "structural_sha256": "e" * 64,
                        "relation": "STRUCTURAL",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": "CROSS_BUILD",
                                "source": "test",
                            }
                        ],
                    },
                ],
                "semantic_provenance": [],
            },
            {
                "logical_id": "CLIENT_CLASS_000003",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v307",
                        "internal_name": "rs/C$Inner",
                        "entry_path": "rs/C$Inner.class",
                        "entry_sha256": "7" * 64,
                        "structural_sha256": "8" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": "EXACT_HISTORICAL_CLIENT",
                                "source": "test",
                            }
                        ],
                    },
                    {
                        "build_id": "v308",
                        "internal_name": "rs/C$Inner",
                        "entry_path": "rs/C$Inner.class",
                        "entry_sha256": "9" * 64,
                        "structural_sha256": "8" * 64,
                        "relation": "EXACT_HASH",
                        "confidence": 1.0,
                        "provenance": [
                            {
                                "authority": "CROSS_BUILD",
                                "source": "test",
                            }
                        ],
                    },
                ],
                "semantic_provenance": [],
            },
        ],
        "unresolved": [],
    }


def _plan(build, sha):
    return {
        "schema_version": 1,
        "kind": "remap_plan",
        "build_id": build,
        "source_sha256": sha,
        "class_count": 0,
        "classes": [],
    }


def _release(build, sha, root, release_id):
    tree, _files, _bytes = source_tree_digest(root)
    return {
        "schema_version": 1,
        "kind": "recovery_release_manifest",
        "release_id": release_id,
        "build_id": build,
        "authority_sha256": sha,
        "final_source_tree_sha256": tree,
        "ready_for_release": True,
        "blockers": [],
    }


class CrossVersionSourceDeltaTests(unittest.TestCase):
    def _roots(self, root: Path):
        old = root / "old"
        new = root / "new"
        (old / "rs").mkdir(parents=True)
        (new / "rs").mkdir(parents=True)

        # Logical class 1 moves A -> B but canonical text happens to stay equal.
        (old / "rs" / "A.java").write_text(
            "package rs; class Shared {}\n",
            encoding="utf-8",
        )
        (new / "rs" / "B.java").write_text(
            "package rs; class Shared {}\n",
            encoding="utf-8",
        )

        # Logical class 2 stays at C and has one source-level delta.
        (old / "rs" / "C.java").write_text(
            "package rs; class C { static final int BUILD = 307; }\n",
            encoding="utf-8",
        )
        (new / "rs" / "C.java").write_text(
            "package rs; class C { static final int BUILD = 308; }\n",
            encoding="utf-8",
        )
        return old, new

    def test_logical_source_delta_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = (
                _release("v307", OLD_SHA, old, "RECOVERY_OLD"),
                _release("v308", NEW_SHA, new, "RECOVERY_NEW"),
                _lineage(),
                _plan("v307", OLD_SHA),
                _plan("v308", NEW_SHA),
                old,
                new,
            )
            a = build_cross_version_source_delta(*args)
            b = build_cross_version_source_delta(*copy.deepcopy(args))

            self.assertEqual(a, b)
            self.assertTrue(a["report_id"].startswith("XVERSRC_"))
            self.assertEqual(
                a["summary"],
                {
                    "old_source_units": 2,
                    "new_source_units": 2,
                    "common_logical_units": 2,
                    "unchanged_source_units": 1,
                    "changed_source_units": 1,
                    "moved_source_paths": 1,
                    "old_only_source_units": 0,
                    "new_only_source_units": 0,
                },
            )
            self.assertEqual(
                [row["logical_id"] for row in a["changed"]],
                ["CLIENT_CLASS_000002"],
            )
            self.assertEqual(
                [row["logical_id"] for row in a["moved"]],
                ["CLIENT_CLASS_000001"],
            )

    def test_line_endings_are_canonicalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            (new / "rs" / "B.java").write_bytes(
                b"package rs; class Shared {}\r\n"
            )
            report = build_cross_version_source_delta(
                _release("v307", OLD_SHA, old, "RECOVERY_OLD"),
                _release("v308", NEW_SHA, new, "RECOVERY_NEW"),
                _lineage(),
                _plan("v307", OLD_SHA),
                _plan("v308", NEW_SHA),
                old,
                new,
            )
            self.assertIn(
                "CLIENT_CLASS_000001",
                [row["logical_id"] for row in report["unchanged"]],
            )

    def test_release_tree_hash_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            old_release = _release(
                "v307", OLD_SHA, old, "RECOVERY_OLD"
            )
            old_release["final_source_tree_sha256"] = "0" * 64
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(
                    old_release,
                    _release(
                        "v308", NEW_SHA, new, "RECOVERY_NEW"
                    ),
                    _lineage(),
                    _plan("v307", OLD_SHA),
                    _plan("v308", NEW_SHA),
                    old,
                    new,
                )

    def test_extra_unmapped_source_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            old_release = _release(
                "v307", OLD_SHA, old, "RECOVERY_OLD"
            )
            new_release = _release(
                "v308", NEW_SHA, new, "RECOVERY_NEW"
            )
            (new / "rs" / "Extra.java").write_text(
                "package rs; class Extra {}\n",
                encoding="utf-8",
            )
            # Rebind release hash so the failure is specifically coverage.
            new_release = _release(
                "v308", NEW_SHA, new, "RECOVERY_NEW"
            )
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(
                    old_release,
                    new_release,
                    _lineage(),
                    _plan("v307", OLD_SHA),
                    _plan("v308", NEW_SHA),
                    old,
                    new,
                )

    def test_class_plan_authority_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            bad_plan = _plan("v308", "9" * 64)
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(
                    _release(
                        "v307", OLD_SHA, old, "RECOVERY_OLD"
                    ),
                    _release(
                        "v308", NEW_SHA, new, "RECOVERY_NEW"
                    ),
                    _lineage(),
                    _plan("v307", OLD_SHA),
                    bad_plan,
                    old,
                    new,
                )


if __name__ == "__main__":
    unittest.main()

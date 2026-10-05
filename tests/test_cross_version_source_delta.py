import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from spk_recovery.cross_version_source_delta import (
    CrossVersionSourceDeltaError,
    build_cross_version_source_delta,
)
from spk_recovery.cross_version_source_delta_cli import (
    _load as _source_delta_load,
)
from spk_recovery.source_digest import source_tree_digest


OLD_SHA = "1" * 64
NEW_SHA = "2" * 64
READABLE = "3" * 64


def _release_id(release: dict) -> str:
    material = {
        "build_id": release.get("build_id"),
        "authority_sha256": release.get("authority_sha256"),
        "namespace_id": release.get("namespace_id"),
        "readable_jar_sha256": release.get("readable_jar_sha256"),
        "final_workspace_id": release.get("final_workspace_id"),
        "final_source_tree_sha256": release.get(
            "final_source_tree_sha256"
        ),
        "source_state": release.get("source_state"),
        "pins": release.get("authority_pins"),
        "blockers": release.get("blockers"),
    }
    return "RECOVERY_" + _digest(material)[:20].upper()


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


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


def _collision_mapping_sha256(plan):
    material = [
        {
            "old_internal_name": row["old_internal_name"],
            "new_internal_name": row["new_internal_name"],
        }
        for row in sorted(
            plan.get("remaps", []),
            key=lambda row: row["old_internal_name"],
        )
    ]
    return _digest(material)


def _collision(plan_id, *, readable=READABLE, remaps=None):
    return {
        "schema_version": 1,
        "kind": "class_package_namespace_collision_plan",
        "plan_id": plan_id,
        "collision_report_id": "JNSCOLLISION_TEST",
        "readable_jar_sha256": readable,
        "identifiers_included": True,
        "remaps": list(remaps or []),
    }


def _authority_bundle(
    build,
    sha,
    root,
    release_id,
    *,
    plan=None,
    collision_plan=None,
):
    plan = copy.deepcopy(plan or _plan(build, sha))
    tree, _files, total_bytes = source_tree_digest(root)
    workspace_id = "SRCWS_" + (
        "A" * 20 if build == "v307" else "B" * 20
    )
    recovered = {
        "schema_version": 1,
        "kind": "recovered_source_workspace_manifest",
        "workspace_id": workspace_id,
        "build_id": build,
        "source_authority_sha256": sha,
        "readable_jar_sha256": READABLE,
        "namespace_id": "SEMNS_TEST",
        "class_plan_digest": _digest(plan),
        "member_plan_digest": "4" * 64,
        "engine": "procyon",
        "decompiler_sha256": "5" * 64,
        "source_tree_sha256": tree,
        "java_file_count": len(list(root.rglob("*.java"))),
        "source_bytes": total_bytes,
        "source_directory": "src",
    }
    if collision_plan is not None:
        recovered.update(
            {
                "collision_plan_id": collision_plan["plan_id"],
                "collision_transform_id": "JNSREWRITE_" + "C" * 20,
                "collision_report_id": collision_plan[
                    "collision_report_id"
                ],
                "collision_mapping_sha256": (
                    _collision_mapping_sha256(collision_plan)
                ),
                "base_readable_jar_sha256": READABLE,
            }
        )

    release = {
        "schema_version": 1,
        "kind": "recovery_release_manifest",
        "release_id": release_id,
        "build_id": build,
        "authority_sha256": sha,
        "namespace_id": "SEMNS_TEST",
        "readable_jar_sha256": READABLE,
        "recovered_workspace_id": workspace_id,
        "final_workspace_id": workspace_id,
        "final_source_tree_sha256": tree,
        "source_state": "workspace",
        "ready_for_release": True,
        "blockers": [],
        "authority_pins": {
            "class_lineage_sha256": _digest(_lineage()),
            "recovered_source_manifest_sha256": _digest(recovered),
        },
    }
    release["release_id"] = _release_id(release)
    return release, recovered, plan


class CrossVersionSourceDeltaTests(unittest.TestCase):
    def _roots(self, root: Path):
        old = root / "old"
        new = root / "new"
        (old / "rs").mkdir(parents=True)
        (new / "rs").mkdir(parents=True)

        (old / "rs" / "A.java").write_text(
            "package rs; class Shared {}\n",
            encoding="utf-8",
        )
        (new / "rs" / "B.java").write_text(
            "package rs; class Shared {}\n",
            encoding="utf-8",
        )
        (old / "rs" / "C.java").write_text(
            "package rs; class C { static final int BUILD = 307; }\n",
            encoding="utf-8",
        )
        (new / "rs" / "C.java").write_text(
            "package rs; class C { static final int BUILD = 308; }\n",
            encoding="utf-8",
        )
        return old, new

    def _args(self, old, new, *, old_plan=None, new_plan=None):
        old_release, old_recovered, old_plan = _authority_bundle(
            "v307",
            OLD_SHA,
            old,
            "RECOVERY_OLD",
            plan=old_plan,
        )
        new_release, new_recovered, new_plan = _authority_bundle(
            "v308",
            NEW_SHA,
            new,
            "RECOVERY_NEW",
            plan=new_plan,
        )
        return (
            old_release,
            new_release,
            old_recovered,
            new_recovered,
            _lineage(),
            old_plan,
            new_plan,
            old,
            new,
        )

    def test_logical_source_delta_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = self._args(old, new)
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
                *self._args(old, new)
            )
            self.assertIn(
                "CLIENT_CLASS_000001",
                [row["logical_id"] for row in report["unchanged"]],
            )

    def test_forged_release_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = list(self._args(old, new))
            args[0]["release_id"] = "RECOVERY_" + "0" * 20

            with self.assertRaisesRegex(
                CrossVersionSourceDeltaError,
                "release_id is not deterministic",
            ):
                build_cross_version_source_delta(*args)

    def test_ready_release_with_blockers_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = list(self._args(old, new))
            args[0]["blockers"] = [
                {
                    "gate": "clean_compile",
                    "reason": "synthetic_blocker",
                }
            ]

            with self.assertRaisesRegex(
                CrossVersionSourceDeltaError,
                "ready release retains blockers",
            ):
                build_cross_version_source_delta(*args)

    def test_ready_release_requires_blocker_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = list(self._args(old, new))
            args[1].pop("blockers")

            with self.assertRaisesRegex(
                CrossVersionSourceDeltaError,
                "blockers must be a list",
            ):
                build_cross_version_source_delta(*args)

    def test_release_tree_hash_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = list(self._args(old, new))
            args[0]["final_source_tree_sha256"] = "0" * 64
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(*args)

    def test_release_pinned_class_lineage_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = list(self._args(old, new))
            lineage = copy.deepcopy(args[4])
            lineage["builds"][0]["source_name"] = "drifted-old.jar"
            args[4] = lineage

            with self.assertRaisesRegex(
                CrossVersionSourceDeltaError,
                "class lineage digest does not match release pin",
            ):
                build_cross_version_source_delta(*args)

    def test_recovered_manifest_release_pin_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = list(self._args(old, new))
            args[2]["source_bytes"] += 1
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(*args)

    def test_extra_unmapped_source_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            (new / "rs" / "Extra.java").write_text(
                "package rs; class Extra {}\n",
                encoding="utf-8",
            )
            args = self._args(old, new)
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(*args)

    def test_class_plan_target_resolves_effective_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            (new / "rs" / "B.java").unlink()
            (new / "rs" / "ReadableB.java").write_text(
                "package rs; class Shared {}\n",
                encoding="utf-8",
            )
            new_plan = _plan("v308", NEW_SHA)
            new_plan["class_count"] = 1
            new_plan["classes"] = [
                {
                    "logical_id": "CLIENT_CLASS_000001",
                    "source_internal_name": "rs/B",
                    "source_entry_path": "rs/B.class",
                    "source_entry_sha256": "c" * 64,
                    "target_internal_name": "rs/ReadableB",
                    "target_entry_path": "rs/ReadableB.class",
                    "confidence": 1.0,
                    "provenance": [{"kind": "test"}],
                }
            ]
            report = build_cross_version_source_delta(
                *self._args(old, new, new_plan=new_plan)
            )
            moved = {
                row["logical_id"]: row
                for row in report["moved"]
            }
            self.assertEqual(
                moved["CLIENT_CLASS_000001"]["new_source_path"],
                "rs/ReadableB.java",
            )

    def test_class_plan_digest_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            args = list(self._args(old, new))
            args[6]["classes"].append(
                {
                    "logical_id": "CLIENT_CLASS_999999",
                    "source_internal_name": "rs/X",
                    "source_entry_path": "rs/X.class",
                    "source_entry_sha256": "0" * 64,
                    "target_internal_name": "rs/Y",
                    "target_entry_path": "rs/Y.class",
                    "confidence": 1.0,
                    "provenance": [{"kind": "test"}],
                }
            )
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(*args)

    def test_collision_plan_resolves_final_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            (new / "rs" / "C.java").unlink()
            (new / "rs" / "Recovered_Blocker.java").write_text(
                "package rs; class C { static final int BUILD = 308; }\n",
                encoding="utf-8",
            )
            collision = _collision(
                "JNSPLAN_" + "A" * 20,
                remaps=[
                    {
                        "old_internal_name": "rs/C",
                        "new_internal_name": "rs/Recovered_Blocker",
                    }
                ],
            )
            old_release, old_rec, old_plan = _authority_bundle(
                "v307", OLD_SHA, old, "RECOVERY_OLD"
            )
            new_release, new_rec, new_plan = _authority_bundle(
                "v308",
                NEW_SHA,
                new,
                "RECOVERY_NEW",
                collision_plan=collision,
            )
            report = build_cross_version_source_delta(
                old_release,
                new_release,
                old_rec,
                new_rec,
                _lineage(),
                old_plan,
                new_plan,
                old,
                new,
                new_collision_plan=collision,
            )
            changed = {
                row["logical_id"]: row
                for row in report["changed"]
            }
            self.assertEqual(
                changed["CLIENT_CLASS_000002"]["new_source_path"],
                "rs/Recovered_Blocker.java",
            )
            self.assertEqual(
                report["new_collision_plan_id"],
                collision["plan_id"],
            )

    def test_collision_private_mapping_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            (new / "rs" / "C.java").unlink()
            (new / "rs" / "Recovered_Blocker.java").write_text(
                "package rs; class C { static final int BUILD = 308; }\n",
                encoding="utf-8",
            )
            collision = _collision(
                "JNSPLAN_" + "A" * 20,
                remaps=[
                    {
                        "old_internal_name": "rs/C",
                        "new_internal_name": "rs/Recovered_Blocker",
                    }
                ],
            )
            old_release, old_rec, old_plan = _authority_bundle(
                "v307", OLD_SHA, old, "RECOVERY_OLD"
            )
            new_release, new_rec, new_plan = _authority_bundle(
                "v308",
                NEW_SHA,
                new,
                "RECOVERY_NEW",
                collision_plan=collision,
            )
            wrong = copy.deepcopy(collision)
            wrong["remaps"][0]["old_internal_name"] = "rs/A"

            with self.assertRaisesRegex(
                CrossVersionSourceDeltaError,
                "private collision mapping",
            ):
                build_cross_version_source_delta(
                    old_release,
                    new_release,
                    old_rec,
                    new_rec,
                    _lineage(),
                    old_plan,
                    new_plan,
                    old,
                    new,
                    new_collision_plan=wrong,
                )

    def test_collision_plan_id_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            collision = _collision("JNSPLAN_" + "A" * 20)
            old_release, old_rec, old_plan = _authority_bundle(
                "v307", OLD_SHA, old, "RECOVERY_OLD"
            )
            new_release, new_rec, new_plan = _authority_bundle(
                "v308",
                NEW_SHA,
                new,
                "RECOVERY_NEW",
                collision_plan=collision,
            )
            wrong = copy.deepcopy(collision)
            wrong["plan_id"] = "JNSPLAN_" + "B" * 20
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(
                    old_release,
                    new_release,
                    old_rec,
                    new_rec,
                    _lineage(),
                    old_plan,
                    new_plan,
                    old,
                    new,
                    new_collision_plan=wrong,
                )

    def test_collision_plan_readable_authority_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            collision = _collision(
                "JNSPLAN_" + "A" * 20,
                readable="9" * 64,
            )
            old_release, old_rec, old_plan = _authority_bundle(
                "v307", OLD_SHA, old, "RECOVERY_OLD"
            )
            new_release, new_rec, new_plan = _authority_bundle(
                "v308",
                NEW_SHA,
                new,
                "RECOVERY_NEW",
                collision_plan=collision,
            )
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(
                    old_release,
                    new_release,
                    old_rec,
                    new_rec,
                    _lineage(),
                    old_plan,
                    new_plan,
                    old,
                    new,
                    new_collision_plan=collision,
                )

    def test_class_plan_row_lineage_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            bad_plan = _plan("v308", NEW_SHA)
            bad_plan["class_count"] = 1
            bad_plan["classes"] = [
                {
                    "logical_id": "CLIENT_CLASS_000001",
                    "source_internal_name": "rs/Wrong",
                    "source_entry_path": "rs/Wrong.class",
                    "source_entry_sha256": "0" * 64,
                    "target_internal_name": "rs/ReadableB",
                    "target_entry_path": "rs/ReadableB.class",
                    "confidence": 1.0,
                    "provenance": [{"kind": "test"}],
                }
            ]
            args = self._args(old, new, new_plan=bad_plan)
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(*args)

    def test_class_plan_authority_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._roots(Path(tmp))
            bad_plan = _plan("v308", "9" * 64)
            # Bind the recovered manifest to the bad plan so the intended
            # failure is exact client authority, not plan digest drift.
            new_release, new_rec, _ = _authority_bundle(
                "v308",
                NEW_SHA,
                new,
                "RECOVERY_NEW",
                plan=bad_plan,
            )
            old_release, old_rec, old_plan = _authority_bundle(
                "v307", OLD_SHA, old, "RECOVERY_OLD"
            )
            with self.assertRaises(CrossVersionSourceDeltaError):
                build_cross_version_source_delta(
                    old_release,
                    new_release,
                    old_rec,
                    new_rec,
                    _lineage(),
                    old_plan,
                    bad_plan,
                    old,
                    new,
                )


    def test_cli_loader_rejects_nested_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate.json"
            path.write_text(
                '{"release":{"build_id":"v307","build_id":"v308"}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                CrossVersionSourceDeltaError,
                "duplicate JSON key: 'build_id'",
            ):
                _source_delta_load(path)


if __name__ == "__main__":
    unittest.main()

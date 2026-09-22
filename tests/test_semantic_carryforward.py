import unittest

from spk_recovery.semantic_carryforward import (
    _sha256_json,
    build_semantic_carryforward,
)


def _class_record(logical_id, name, entries):
    return {
        "logical_id": logical_id,
        "semantic_name": name,
        "semantic_status": "ACCEPTED",
        "semantic_confidence": 0.95,
        "lineage": entries,
        "semantic_provenance": [{"source": "test"}],
    }


def _entry(build_id, internal):
    return {
        "build_id": build_id,
        "internal_name": internal,
        "entry_path": internal + ".class",
        "entry_sha256": "e" * 64,
        "structural_sha256": "f" * 64,
        "relation": "BASELINE" if build_id == "v308" else "STRUCTURAL",
        "confidence": 1.0,
        "provenance": [],
    }


def _class_lineage(include_blocker=True):
    classes = [
        _class_record(
            "CLIENT_CLASS_000001",
            "CarriedClass",
            [_entry("v308", "rs/a"), _entry("v309", "rs/b")],
        ),
        _class_record(
            "CLIENT_CLASS_000003",
            "NewOnlyClass",
            [_entry("v309", "rs/c")],
        ),
    ]
    if include_blocker:
        classes.append(
            _class_record(
                "CLIENT_CLASS_000002",
                "OldOnlyClass",
                [_entry("v308", "rs/d")],
            )
        )
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [
            {
                "build_id": "v308",
                "build_number": 308,
                "sha256": "a" * 64,
                "source_name": "v308.jar",
                "authority": "EXACT_HISTORICAL_CLIENT",
            },
            {
                "build_id": "v309",
                "build_number": 309,
                "sha256": "b" * 64,
                "source_name": "v309.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            },
        ],
        "classes": classes,
        "unresolved": [],
    }


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "a" * 64,
        "members": [],
        "unresolved": [],
    }


def _authorities(classes, members):
    previous = {
        "schema_version": 1,
        "kind": "authority_snapshot",
        "authority_id": "AUTHORITY_" + "1" * 20,
        "state": "EXACT_CURRENT_CLIENT",
        "build_id": "v308",
        "sha256": "a" * 64,
    }
    new = {
        "schema_version": 1,
        "kind": "authority_snapshot",
        "authority_id": "AUTHORITY_" + "2" * 20,
        "state": "EXACT_CURRENT_CLIENT",
        "build_id": "v309",
        "sha256": "b" * 64,
        "class_lineage_sha256": _sha256_json(classes),
        "member_lineage_sha256": _sha256_json(members),
    }
    return previous, new


def _new_index():
    return {
        "sha256": "b" * 64,
        "classes": {
            "rs/b.class": {
                "internal_name": "rs/b",
                "fields": [],
                "methods": [],
            },
            "rs/c.class": {
                "internal_name": "rs/c",
                "fields": [],
                "methods": [],
            },
        },
    }


class SemanticCarryForwardTests(unittest.TestCase):
    def test_missing_new_identity_blocks_readable_carryforward(self):
        classes = _class_lineage(include_blocker=True)
        members = _member_lineage()
        old_auth, new_auth = _authorities(classes, members)
        report, namespace, class_plan, member_plan = build_semantic_carryforward(
            old_auth,
            new_auth,
            classes,
            members,
            _new_index(),
        )
        self.assertFalse(report["ready_for_readable_build"])
        self.assertEqual(report["summary"]["classes_carried"], 1)
        self.assertEqual(
            report["summary"]["accepted_blocked_missing_new_identity"],
            1,
        )
        self.assertEqual(report["summary"]["classes_new_only"], 1)
        self.assertEqual(class_plan["class_count"], 2)
        self.assertEqual(member_plan["member_count"], 0)
        self.assertEqual(report["namespace_id"], namespace["namespace_id"])

    def test_surviving_accepted_identity_is_ready(self):
        classes = _class_lineage(include_blocker=False)
        members = _member_lineage()
        old_auth, new_auth = _authorities(classes, members)
        report, _, class_plan, _ = build_semantic_carryforward(
            old_auth,
            new_auth,
            classes,
            members,
            _new_index(),
        )
        self.assertTrue(report["ready_for_readable_build"])
        self.assertEqual(
            report["summary"]["accepted_blocked_missing_new_identity"],
            0,
        )
        self.assertEqual(report["summary"]["classes_carried"], 1)
        self.assertEqual(report["summary"]["classes_new_only"], 1)
        self.assertEqual(class_plan["class_count"], 2)


if __name__ == "__main__":
    unittest.main()

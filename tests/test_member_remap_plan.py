import copy
import unittest

from spk_recovery.member_remap_plan import (
    MemberRemapPlanError,
    build_member_remap_plan,
)


SHA = "a" * 64


def _class_lineage():
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [{
            "build_id": "v308",
            "build_number": 308,
            "sha256": SHA,
            "source_name": "client.jar",
            "authority": "EXACT_CURRENT_CLIENT",
        }],
        "classes": [{
            "logical_id": "CLIENT_CLASS_000001",
            "semantic_name": None,
            "semantic_status": "UNKNOWN",
            "semantic_confidence": 0.0,
            "lineage": [{
                "build_id": "v308",
                "internal_name": "rs/A",
                "entry_path": "rs/A.class",
                "entry_sha256": "b" * 64,
                "structural_sha256": "c" * 64,
                "relation": "BASELINE",
                "confidence": 1.0,
                "provenance": [],
            }],
            "semantic_provenance": [],
        }],
        "unresolved": [],
    }


def _member(kind, mid, name, desc, semantic=None):
    return {
        "member_id": mid,
        "owner_logical_id": "CLIENT_CLASS_000001",
        "kind": kind,
        "semantic_name": semantic,
        "semantic_status": "ACCEPTED" if semantic else "UNKNOWN",
        "semantic_confidence": 0.99 if semantic else 0.0,
        "lineage": [{
            "build_id": "v308",
            "owner_internal_name": "rs/A",
            "name": name,
            "descriptor": desc,
            "access": 1,
            **({"code_length": 8} if kind == "method" else {}),
            "relation": "BASELINE",
            "confidence": 1.0,
            "provenance": [],
        }],
        "semantic_provenance": (
            [{"proposal_id": "SEMPROP_TEST"}] if semantic else []
        ),
    }


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": SHA,
        "members": [
            _member("field", "CLIENT_FIELD_000001", "x", "I", "rewardIndex"),
            _member("field", "CLIENT_FIELD_000002", "y", "J"),
            _member("method", "CLIENT_METHOD_000001", "a", "(J)V", "addFriend"),
            _member("method", "CLIENT_METHOD_000002", "b", "()V"),
        ],
        "unresolved": [],
    }


def _index():
    return {
        "sha256": SHA,
        "classes": {
            "rs/A.class": {
                "internal_name": "rs/A",
                "fields": [
                    {"name": "x", "descriptor": "I"},
                    {"name": "y", "descriptor": "J"},
                ],
                "methods": [
                    {"name": "<init>", "descriptor": "()V"},
                    {"name": "a", "descriptor": "(J)V"},
                    {"name": "b", "descriptor": "()V"},
                ],
            }
        },
    }


class MemberRemapPlanTests(unittest.TestCase):
    def test_only_accepted_non_noop_members_enter_plan(self):
        plan = build_member_remap_plan(
            _class_lineage(),
            _member_lineage(),
            _index(),
            build_id="v308",
        )
        self.assertEqual(plan["member_count"], 2)
        self.assertEqual(plan["field_count"], 1)
        self.assertEqual(plan["method_count"], 1)
        self.assertEqual(
            {r["target_name"] for r in plan["members"]},
            {"rewardIndex", "addFriend"},
        )

    def test_wrong_index_sha_is_rejected(self):
        index = _index()
        index["sha256"] = "d" * 64
        with self.assertRaises(MemberRemapPlanError):
            build_member_remap_plan(
                _class_lineage(),
                _member_lineage(),
                index,
                build_id="v308",
            )

    def test_field_collision_with_unmapped_member_is_rejected(self):
        members = _member_lineage()
        members["members"][0]["semantic_name"] = "y"
        with self.assertRaises(MemberRemapPlanError):
            build_member_remap_plan(
                _class_lineage(),
                members,
                _index(),
                build_id="v308",
            )

    def test_method_collision_same_descriptor_is_rejected(self):
        members = _member_lineage()
        members["members"][2]["semantic_name"] = "b"
        members["members"][3]["lineage"][0]["descriptor"] = "(J)V"
        index = _index()
        index["classes"]["rs/A.class"]["methods"][2]["descriptor"] = "(J)V"
        with self.assertRaises(MemberRemapPlanError):
            build_member_remap_plan(
                _class_lineage(),
                members,
                index,
                build_id="v308",
            )


if __name__ == "__main__":
    unittest.main()

import copy
import unittest

from spk_recovery.member_lineage import (
    MemberLineageError,
    seed_member_lineage,
    validate_member_lineage,
)


def _class_lineage():
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
                "source_name": "client.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            }
        ],
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000001",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/A",
                        "entry_path": "rs/A.class",
                        "entry_sha256": "b" * 64,
                        "structural_sha256": "c" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _index():
    return {
        "sha256": "a" * 64,
        "classes": {
            "rs/A.class": {
                "fields": [
                    {"name": "z", "descriptor": "I", "access": 1},
                    {"name": "a", "descriptor": "Ljava/lang/String;", "access": 2},
                ],
                "methods": [
                    {"name": "<init>", "descriptor": "()V", "access": 1, "code_length": 5},
                    {"name": "b", "descriptor": "(I)V", "access": 1, "code_length": 8},
                    {"name": "a", "descriptor": "()I", "access": 1, "code_length": 4},
                ],
            }
        },
    }


class MemberLineageTests(unittest.TestCase):
    def test_seed_is_deterministic_and_excludes_constructors(self):
        a = seed_member_lineage(_class_lineage(), _index(), build_id="v308")
        b = seed_member_lineage(_class_lineage(), _index(), build_id="v308")
        self.assertEqual(a, b)
        self.assertEqual(
            [x["member_id"] for x in a["members"]],
            [
                "CLIENT_FIELD_000001",
                "CLIENT_FIELD_000002",
                "CLIENT_METHOD_000001",
                "CLIENT_METHOD_000002",
            ],
        )
        summary = validate_member_lineage(a, class_lineage=_class_lineage())
        self.assertEqual(summary["fields"], 2)
        self.assertEqual(summary["methods"], 2)

    def test_wrong_index_sha_is_rejected(self):
        index = _index()
        index["sha256"] = "d" * 64
        with self.assertRaises(MemberLineageError):
            seed_member_lineage(_class_lineage(), index, build_id="v308")

    def test_duplicate_member_coordinate_is_rejected(self):
        doc = seed_member_lineage(_class_lineage(), _index(), build_id="v308")
        duplicate = copy.deepcopy(doc["members"][0])
        duplicate["member_id"] = "CLIENT_FIELD_999999"
        doc["members"].append(duplicate)
        with self.assertRaises(MemberLineageError):
            validate_member_lineage(doc, class_lineage=_class_lineage())


if __name__ == "__main__":
    unittest.main()

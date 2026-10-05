import copy
import unittest

from spk_recovery.member_lineage import (
    MemberLineageError,
    seed_member_lineage,
    validate_member_lineage,
)
from spk_recovery.semantic_authority import semantic_proposal_id


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

    def _accepted(self):
        class_lineage = _class_lineage()
        doc = seed_member_lineage(
            class_lineage,
            _index(),
            build_id="v308",
        )
        record = doc["members"][0]
        entry = record["lineage"][0]
        record["semantic_name"] = "readableField"
        record["semantic_status"] = "ACCEPTED"
        record["semantic_confidence"] = 0.9
        record["semantic_provenance"] = [
            {
                "proposal_id": semantic_proposal_id(
                    "a" * 64,
                    record["kind"],
                    record["member_id"],
                    "readableField",
                ),
                "review_id": "SEMREVIEW_" + "B" * 20,
                "source_build": "v308",
                "source_sha256": "a" * 64,
                "source_coordinate": {
                    "owner": entry["owner_internal_name"],
                    "name": entry["name"],
                    "descriptor": entry["descriptor"],
                },
                "evidence": [],
            }
        ]
        return class_lineage, doc

    def test_accepted_member_requires_canonical_provenance(self):
        class_lineage, doc = self._accepted()
        summary = validate_member_lineage(
            doc,
            class_lineage=class_lineage,
        )
        self.assertEqual(summary["members"], 4)

    def test_accepted_member_rejects_empty_provenance(self):
        class_lineage, doc = self._accepted()
        doc["members"][0]["semantic_provenance"] = []
        with self.assertRaisesRegex(
            MemberLineageError,
            "requires provenance",
        ):
            validate_member_lineage(
                doc,
                class_lineage=class_lineage,
            )

    def test_accepted_member_rejects_cross_target_provenance(self):
        class_lineage, doc = self._accepted()
        doc["members"][0]["semantic_provenance"][0][
            "source_coordinate"
        ]["name"] = "forged"
        with self.assertRaisesRegex(
            MemberLineageError,
            "source_coordinate does not match member",
        ):
            validate_member_lineage(
                doc,
                class_lineage=class_lineage,
            )

    def test_accepted_member_rejects_forged_proposal_id(self):
        class_lineage, doc = self._accepted()
        doc["members"][0]["semantic_provenance"][0][
            "proposal_id"
        ] = "SEMPROP_" + "0" * 20
        with self.assertRaisesRegex(
            MemberLineageError,
            "proposal_id does not match",
        ):
            validate_member_lineage(
                doc,
                class_lineage=class_lineage,
            )

    def test_duplicate_accepted_field_semantic_name_is_rejected(self):
        class_lineage, doc = self._accepted()
        record = doc["members"][1]
        entry = record["lineage"][0]
        record["semantic_name"] = "readableField"
        record["semantic_status"] = "ACCEPTED"
        record["semantic_confidence"] = 0.8
        record["semantic_provenance"] = [
            {
                "proposal_id": semantic_proposal_id(
                    "a" * 64,
                    "field",
                    record["member_id"],
                    "readableField",
                ),
                "review_id": "SEMREVIEW_" + "C" * 20,
                "source_build": "v308",
                "source_sha256": "a" * 64,
                "source_coordinate": {
                    "owner": entry["owner_internal_name"],
                    "name": entry["name"],
                    "descriptor": entry["descriptor"],
                },
                "evidence": [],
            }
        ]
        with self.assertRaisesRegex(
            MemberLineageError,
            "accepted field semantic name",
        ):
            validate_member_lineage(
                doc,
                class_lineage=class_lineage,
            )

    def test_duplicate_accepted_method_signature_is_rejected(self):
        class_lineage = _class_lineage()
        doc = seed_member_lineage(
            class_lineage,
            _index(),
            build_id="v308",
        )
        first = doc["members"][2]
        second = doc["members"][3]
        second["lineage"][0]["descriptor"] = (
            first["lineage"][0]["descriptor"]
        )

        for record, review_digit in (
            (first, "D"),
            (second, "E"),
        ):
            entry = record["lineage"][0]
            record["semantic_name"] = "runTask"
            record["semantic_status"] = "ACCEPTED"
            record["semantic_confidence"] = 0.8
            record["semantic_provenance"] = [
                {
                    "proposal_id": semantic_proposal_id(
                        "a" * 64,
                        "method",
                        record["member_id"],
                        "runTask",
                    ),
                    "review_id": (
                        "SEMREVIEW_" + review_digit * 20
                    ),
                    "source_build": "v308",
                    "source_sha256": "a" * 64,
                    "source_coordinate": {
                        "owner": entry["owner_internal_name"],
                        "name": entry["name"],
                        "descriptor": entry["descriptor"],
                    },
                    "evidence": [],
                }
            ]

        with self.assertRaisesRegex(
            MemberLineageError,
            "accepted method semantic signature",
        ):
            validate_member_lineage(
                doc,
                class_lineage=class_lineage,
            )

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

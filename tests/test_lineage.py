import copy
import unittest

from spk_recovery.lineage import LineageValidationError, seed_lineage, validate_lineage
from spk_recovery.semantic_authority import semantic_proposal_id


def _index():
    def cls(name: str, structural: str):
        return {
            "internal_name": name,
            "structural_sha256": structural,
        }

    return {
        "source_name": "client-test.jar",
        "sha256": "a" * 64,
        "entries": {
            "rs/z.class": {"sha256": "1" * 64},
            "rs/a.class": {"sha256": "2" * 64},
            "other/X.class": {"sha256": "3" * 64},
        },
        "classes": {
            "rs/z.class": cls("rs/z", "4" * 64),
            "rs/a.class": cls("rs/a", "5" * 64),
            "other/X.class": cls("other/X", "6" * 64),
        },
    }


class LineageTest(unittest.TestCase):
    def test_seed_is_deterministic_and_rs_scoped(self):
        doc = seed_lineage(
            _index(),
            build_id="v308",
            build_number=308,
            authority="EXACT_CURRENT_CLIENT",
        )
        self.assertEqual([r["logical_id"] for r in doc["classes"]], ["CLIENT_CLASS_000001", "CLIENT_CLASS_000002"])
        self.assertEqual([r["lineage"][0]["internal_name"] for r in doc["classes"]], ["rs/a", "rs/z"])
        self.assertEqual(validate_lineage(doc)["logical_classes"], 2)

    def test_duplicate_build_class_is_rejected(self):
        doc = seed_lineage(
            _index(),
            build_id="v308",
            build_number=308,
            authority="EXACT_CURRENT_CLIENT",
        )
        duplicate = copy.deepcopy(doc["classes"][0])
        duplicate["logical_id"] = "CLIENT_CLASS_999999"
        doc["classes"].append(duplicate)
        with self.assertRaises(LineageValidationError):
            validate_lineage(doc)

    def test_unknown_semantic_name_is_rejected(self):
        doc = seed_lineage(
            _index(),
            build_id="v308",
            build_number=308,
            authority="EXACT_CURRENT_CLIENT",
        )
        doc["classes"][0]["semantic_name"] = "SomethingReadable"
        with self.assertRaises(LineageValidationError):
            validate_lineage(doc)

    def _accepted(self):
        doc = seed_lineage(
            _index(),
            build_id="v308",
            build_number=308,
            authority="EXACT_CURRENT_CLIENT",
        )
        record = doc["classes"][0]
        entry = record["lineage"][0]
        record["semantic_name"] = "ReadableClass"
        record["semantic_status"] = "ACCEPTED"
        record["semantic_confidence"] = 0.9
        record["semantic_provenance"] = [
            {
                "proposal_id": semantic_proposal_id(
                    "a" * 64,
                    "class",
                    record["logical_id"],
                    "ReadableClass",
                ),
                "review_id": "SEMREVIEW_" + "A" * 20,
                "source_build": "v308",
                "source_sha256": "a" * 64,
                "source_coordinate": {
                    "owner": entry["internal_name"],
                    "name": None,
                    "descriptor": None,
                },
                "evidence": [],
            }
        ]
        return doc

    def test_accepted_semantic_requires_canonical_provenance(self):
        doc = self._accepted()
        self.assertEqual(
            validate_lineage(doc)["semantic_named"],
            1,
        )

    def test_accepted_semantic_rejects_empty_provenance(self):
        doc = self._accepted()
        doc["classes"][0]["semantic_provenance"] = []
        with self.assertRaisesRegex(
            LineageValidationError,
            "requires provenance",
        ):
            validate_lineage(doc)

    def test_accepted_semantic_rejects_cross_target_provenance(self):
        doc = self._accepted()
        doc["classes"][0]["semantic_provenance"][0][
            "source_coordinate"
        ]["owner"] = "rs/z"
        with self.assertRaisesRegex(
            LineageValidationError,
            "source_coordinate does not match class",
        ):
            validate_lineage(doc)

    def test_accepted_semantic_rejects_forged_proposal_id(self):
        doc = self._accepted()
        doc["classes"][0]["semantic_provenance"][0][
            "proposal_id"
        ] = "SEMPROP_" + "0" * 20
        with self.assertRaisesRegex(
            LineageValidationError,
            "proposal_id does not match",
        ):
            validate_lineage(doc)

    def test_confidence_range_is_enforced(self):
        doc = seed_lineage(
            _index(),
            build_id="v308",
            build_number=308,
            authority="EXACT_CURRENT_CLIENT",
        )
        doc["classes"][0]["lineage"][0]["confidence"] = 1.1
        with self.assertRaises(LineageValidationError):
            validate_lineage(doc)


if __name__ == "__main__":
    unittest.main()

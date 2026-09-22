import copy
import unittest

from spk_recovery.source_name_review import (
    SourceNameCandidateError,
    resolve_source_name_candidates,
)


def _inventory():
    return {
        "schema_version": 1,
        "kind": "source_symbol_inventory",
        "inventory_id": "SRCINV_0123456789ABCDEF0123",
        "workspace_id": "SRCWS_TEST",
        "build_id": "v308",
        "source_tree_sha256": "a" * 64,
        "symbols": [
            {
                "source_symbol_id": "SRC_PARAM_0123456789ABCDEF0123",
                "source_method_id": "SRC_METHOD_0123456789ABCDEF0123",
                "canonical_method_id": "CLIENT_METHOD_000001",
                "kind": "parameter",
                "current_name": "var1",
                "declared_type": "int",
            },
            {
                "source_symbol_id": "SRC_LOCAL_0123456789ABCDEF0123",
                "source_method_id": "SRC_METHOD_0123456789ABCDEF0123",
                "canonical_method_id": "CLIENT_METHOD_000001",
                "kind": "local",
                "current_name": "var2",
                "declared_type": "String",
            },
        ],
    }


def _set(rows):
    return {
        "schema_version": 1,
        "kind": "source_name_candidate_set",
        "canonical": False,
        "inventory_id": "SRCINV_0123456789ABCDEF0123",
        "source_tree_sha256": "a" * 64,
        "candidates": rows,
    }


def _candidate(symbol, name, confidence=0.9, family="type_flow"):
    return {
        "source_symbol_id": symbol,
        "proposed_name": name,
        "confidence": confidence,
        "evidence": [
            {
                "family": family,
                "detail": "test evidence",
            }
        ],
    }


class SourceNameReviewTests(unittest.TestCase):
    def test_review_is_deterministic_and_deduplicates(self):
        symbol = "SRC_PARAM_0123456789ABCDEF0123"
        candidate = _candidate(symbol, "itemId")
        first = resolve_source_name_candidates(
            _inventory(),
            _set([candidate, copy.deepcopy(candidate)]),
        )
        second = resolve_source_name_candidates(
            _inventory(),
            _set([copy.deepcopy(candidate), candidate]),
        )
        self.assertEqual(first["review_id"], second["review_id"])
        self.assertEqual(first["summary"]["candidate_rows"], 1)
        self.assertEqual(first["summary"]["reviewable_proposals"], 1)

    def test_conflicting_names_stay_conflicts(self):
        symbol = "SRC_LOCAL_0123456789ABCDEF0123"
        out = resolve_source_name_candidates(
            _inventory(),
            _set(
                [
                    _candidate(symbol, "playerName", 0.91),
                    _candidate(symbol, "displayName", 0.89),
                ]
            ),
        )
        self.assertEqual(out["summary"]["reviewable_proposals"], 0)
        self.assertEqual(out["summary"]["conflicts"], 1)

    def test_unknown_symbol_is_rejected(self):
        with self.assertRaises(SourceNameCandidateError):
            resolve_source_name_candidates(
                _inventory(),
                _set([_candidate("SRC_LOCAL_DEADBEEFDEADBEEFDEAD", "value")]),
            )

    def test_java_keyword_is_rejected(self):
        with self.assertRaises(SourceNameCandidateError):
            resolve_source_name_candidates(
                _inventory(),
                _set(
                    [
                        _candidate(
                            "SRC_PARAM_0123456789ABCDEF0123",
                            "class",
                        )
                    ]
                ),
            )

    def test_certainty_one_is_rejected_for_inferred_name(self):
        with self.assertRaises(SourceNameCandidateError):
            resolve_source_name_candidates(
                _inventory(),
                _set(
                    [
                        _candidate(
                            "SRC_PARAM_0123456789ABCDEF0123",
                            "itemId",
                            1.0,
                        )
                    ]
                ),
            )

    def test_noop_name_is_rejected(self):
        with self.assertRaises(SourceNameCandidateError):
            resolve_source_name_candidates(
                _inventory(),
                _set(
                    [
                        _candidate(
                            "SRC_PARAM_0123456789ABCDEF0123",
                            "var1",
                        )
                    ]
                ),
            )


if __name__ == "__main__":
    unittest.main()

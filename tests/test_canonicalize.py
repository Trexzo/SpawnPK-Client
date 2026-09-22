import unittest

from spk_recovery.canonicalize import (
    CandidateApplicationError,
    apply_lineage_candidates,
)
from spk_recovery.lineage import seed_lineage, validate_lineage


def _class(name: str, structural: str):
    return {
        "internal_name": name,
        "structural_sha256": structural,
    }


def _old_index():
    return {
        "source_name": "old.jar",
        "sha256": "a" * 64,
        "entries": {
            "rs/a.class": {"sha256": "1" * 64},
            "rs/b.class": {"sha256": "2" * 64},
        },
        "classes": {
            "rs/a.class": _class("rs/a", "3" * 64),
            "rs/b.class": _class("rs/b", "4" * 64),
        },
    }


def _new_index():
    return {
        "source_name": "new.jar",
        "sha256": "b" * 64,
        "entries": {
            "rs/a.class": {"sha256": "1" * 64},
            "rs/c.class": {"sha256": "5" * 64},
            "rs/new.class": {"sha256": "6" * 64},
        },
        "classes": {
            "rs/a.class": _class("rs/a", "3" * 64),
            "rs/c.class": _class("rs/c", "4" * 64),
            "rs/new.class": _class("rs/new", "7" * 64),
        },
    }


def _candidates():
    return {
        "schema_version": 1,
        "kind": "lineage_candidates",
        "canonicalization_owner": "main_integration_chat",
        "old_sha256": "a" * 64,
        "new_sha256": "b" * 64,
        "old_build": "v308",
        "new_build": "v309",
        "relationships": [
            {
                "relationship_id": "REL_EXACT",
                "from": {"build": "v308", "path": "rs/a.class"},
                "to": {"build": "v309", "path": "rs/a.class"},
                "strategy": "exact_sha256",
                "confidence": "EXACT",
                "score": 1.0,
                "evidence": {},
            },
            {
                "relationship_id": "REL_STRUCT",
                "from": {"build": "v308", "path": "rs/b.class"},
                "to": {"build": "v309", "path": "rs/c.class"},
                "strategy": "structural_unique",
                "confidence": "CROSS_BUILD",
                "score": 0.995,
                "evidence": {},
            },
        ],
        "ambiguous": [],
        "unmatched_old": [],
        "unmatched_new": ["rs/new.class"],
    }


class CanonicalizeTests(unittest.TestCase):
    def _lineage(self):
        return seed_lineage(
            _old_index(),
            build_id="v308",
            build_number=308,
            authority="EXACT_CURRENT_CLIENT",
        )

    def test_applies_verified_relations_and_preserves_unmatched(self):
        out, summary = apply_lineage_candidates(
            self._lineage(),
            _old_index(),
            _new_index(),
            _candidates(),
            old_build_id="v308",
            new_build_id="v309",
            new_build_number=309,
            new_authority="EXACT_CURRENT_CLIENT",
        )
        self.assertEqual(summary["applied_relationships"], 2)
        self.assertEqual(summary["unresolved_added"], 1)
        self.assertEqual(validate_lineage(out)["builds"], 2)
        first = out["classes"][0]["lineage"][1]
        second = out["classes"][1]["lineage"][1]
        self.assertEqual(first["relation"], "EXACT_HASH")
        self.assertEqual(second["relation"], "STRUCTURAL")
        self.assertEqual(second["internal_name"], "rs/c")
        self.assertEqual(out["unresolved"][0]["kind"], "unmatched_new")

    def test_candidate_sha_mismatch_is_rejected(self):
        candidates = _candidates()
        candidates["new_sha256"] = "f" * 64
        with self.assertRaises(CandidateApplicationError):
            apply_lineage_candidates(
                self._lineage(),
                _old_index(),
                _new_index(),
                candidates,
                old_build_id="v308",
                new_build_id="v309",
                new_build_number=309,
                new_authority="EXACT_CURRENT_CLIENT",
            )

    def test_structural_claim_is_reverified(self):
        new = _new_index()
        new["classes"]["rs/c.class"]["structural_sha256"] = "9" * 64
        with self.assertRaises(CandidateApplicationError):
            apply_lineage_candidates(
                self._lineage(),
                _old_index(),
                new,
                _candidates(),
                old_build_id="v308",
                new_build_id="v309",
                new_build_number=309,
                new_authority="EXACT_CURRENT_CLIENT",
            )

    def test_unknown_old_path_is_rejected(self):
        candidates = _candidates()
        candidates["relationships"][0]["from"]["path"] = "rs/missing.class"
        with self.assertRaises(CandidateApplicationError):
            apply_lineage_candidates(
                self._lineage(),
                _old_index(),
                _new_index(),
                candidates,
                old_build_id="v308",
                new_build_id="v309",
                new_build_number=309,
                new_authority="EXACT_CURRENT_CLIENT",
            )

    def test_duplicate_new_path_is_rejected(self):
        candidates = _candidates()
        candidates["relationships"][1]["to"]["path"] = "rs/a.class"
        with self.assertRaises(CandidateApplicationError):
            apply_lineage_candidates(
                self._lineage(),
                _old_index(),
                _new_index(),
                candidates,
                old_build_id="v308",
                new_build_id="v309",
                new_build_number=309,
                new_authority="EXACT_CURRENT_CLIENT",
            )


if __name__ == "__main__":
    unittest.main()

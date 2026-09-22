import unittest

from spk_recovery.canonicalize import apply_lineage_candidates
from spk_recovery.lineage import seed_lineage
from spk_recovery.promotion import (
    NewClassPromotionError,
    promote_new_classes,
)


def _cls(name, structural):
    return {"internal_name": name, "structural_sha256": structural}


def _old():
    return {
        "source_name": "old.jar",
        "sha256": "a" * 64,
        "entries": {"rs/a.class": {"sha256": "1" * 64}},
        "classes": {"rs/a.class": _cls("rs/a", "2" * 64)},
    }


def _new():
    return {
        "source_name": "new.jar",
        "sha256": "b" * 64,
        "entries": {
            "rs/a.class": {"sha256": "1" * 64},
            "rs/new.class": {"sha256": "3" * 64},
        },
        "classes": {
            "rs/a.class": _cls("rs/a", "2" * 64),
            "rs/new.class": _cls("rs/new", "4" * 64),
        },
    }


def _candidate():
    return {
        "schema_version": 1,
        "kind": "lineage_candidates",
        "old_sha256": "a" * 64,
        "new_sha256": "b" * 64,
        "relationships": [
            {
                "relationship_id": "REL_A",
                "from": {"path": "rs/a.class"},
                "to": {"path": "rs/a.class"},
                "strategy": "exact_sha256",
                "score": 1.0,
            }
        ],
        "ambiguous": [],
        "unmatched_old": [],
        "unmatched_new": ["rs/new.class"],
    }


def _lineage_with_new_build():
    base = seed_lineage(
        _old(),
        build_id="v308",
        build_number=308,
        authority="EXACT_CURRENT_CLIENT",
    )
    out, _ = apply_lineage_candidates(
        base,
        _old(),
        _new(),
        _candidate(),
        old_build_id="v308",
        new_build_id="v309",
        new_build_number=309,
        new_authority="EXACT_CURRENT_CLIENT",
    )
    return out


class PromotionTests(unittest.TestCase):
    def test_promotes_only_reviewed_unmatched_path(self):
        out, summary = promote_new_classes(
            _lineage_with_new_build(),
            _new(),
            build_id="v309",
            paths=["rs/new.class"],
        )
        self.assertEqual(summary["promoted_new_classes"], 1)
        self.assertEqual(summary["unresolved_removed"], 1)
        self.assertEqual(
            out["classes"][-1]["logical_id"],
            "CLIENT_CLASS_000002",
        )
        self.assertEqual(
            out["classes"][-1]["lineage"][0]["relation"],
            "MANUAL",
        )
        self.assertEqual(out["unresolved"], [])

    def test_rejects_path_not_in_unmatched_new(self):
        with self.assertRaises(NewClassPromotionError):
            promote_new_classes(
                _lineage_with_new_build(),
                _new(),
                build_id="v309",
                paths=["rs/a.class"],
            )

    def test_rejects_wrong_index_build(self):
        new = _new()
        new["sha256"] = "f" * 64
        with self.assertRaises(NewClassPromotionError):
            promote_new_classes(
                _lineage_with_new_build(),
                new,
                build_id="v309",
                paths=["rs/new.class"],
            )

    def test_batch_order_is_deterministic(self):
        lineage = _lineage_with_new_build()
        new = _new()
        new["entries"]["rs/aaa.class"] = {"sha256": "5" * 64}
        new["classes"]["rs/aaa.class"] = _cls("rs/aaa", "6" * 64)
        lineage["unresolved"].append(
            {
                "old_build_id": "v308",
                "new_build_id": "v309",
                "kind": "unmatched_new",
                "candidate": "rs/aaa.class",
                "source": "lineage_candidates",
            }
        )
        out, _ = promote_new_classes(
            lineage,
            new,
            build_id="v309",
            paths=["rs/new.class", "rs/aaa.class"],
        )
        self.assertEqual(
            out["classes"][-2]["lineage"][0]["entry_path"],
            "rs/aaa.class",
        )
        self.assertEqual(
            out["classes"][-1]["lineage"][0]["entry_path"],
            "rs/new.class",
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from spk_recovery.lineage_candidates import build_lineage_candidates


class LineageCandidateTests(unittest.TestCase):
    def test_candidates_do_not_claim_canonical_ids(self):
        old = {
            "sha256": "old",
            "entries": {"rs/a.class": {"sha256": "one"}},
        }
        new = {
            "sha256": "new",
            "entries": {"rs/b.class": {"sha256": "two"}},
        }
        report = {
            "matches": [
                {
                    "old": "rs/a.class",
                    "new": "rs/b.class",
                    "strategy": "structural_unique",
                    "confidence": "CROSS_BUILD",
                    "score": 0.995,
                    "evidence": {"structural_sha256_equal": True},
                }
            ],
            "ambiguous": [],
            "unmatched_old": [],
            "unmatched_new": [],
        }
        out = build_lineage_candidates(
            old,
            new,
            report,
            old_build=307,
            new_build=308,
        )
        rel = out["relationships"][0]
        self.assertIsNone(rel["canonical_logical_id"])
        self.assertEqual(
            out["canonicalization_owner"],
            "main_integration_chat",
        )
        self.assertEqual(
            rel["classification"],
            "modified_or_reobfuscated",
        )
        self.assertTrue(rel["relationship_id"].startswith("REL_"))

    def test_relationship_id_is_deterministic(self):
        old = {
            "sha256": "old",
            "entries": {"rs/a.class": {"sha256": "same"}},
        }
        new = {
            "sha256": "new",
            "entries": {"rs/a.class": {"sha256": "same"}},
        }
        report = {
            "matches": [
                {
                    "old": "rs/a.class",
                    "new": "rs/a.class",
                    "strategy": "exact_sha256",
                    "confidence": "EXACT",
                    "score": 1.0,
                    "evidence": {},
                }
            ],
            "ambiguous": [],
            "unmatched_old": [],
            "unmatched_new": [],
        }
        a = build_lineage_candidates(
            old,
            new,
            report,
            old_build=307,
            new_build=308,
        )
        b = build_lineage_candidates(
            old,
            new,
            report,
            old_build=307,
            new_build=308,
        )
        self.assertEqual(
            a["relationships"][0]["relationship_id"],
            b["relationships"][0]["relationship_id"],
        )
        self.assertEqual(
            a["relationships"][0]["classification"],
            "unchanged",
        )




    def test_unsupported_strategy_stays_research_only(self):
        old = {
            "sha256": "old",
            "entries": {"rs/m/a.class": {"sha256": "one"}},
        }
        new = {
            "sha256": "new",
            "entries": {"rs/l/a.class": {"sha256": "two"}},
        }
        report = {
            "matches": [
                {
                    "old": "rs/m/a.class",
                    "new": "rs/l/a.class",
                    "strategy": "package_anchor",
                    "confidence": "INFERRED_HIGH",
                    "score": 0.91,
                    "evidence": {
                        "package_anchor": {
                            "support": 133,
                            "dominance": 1.0,
                        }
                    },
                }
            ],
            "ambiguous": [],
            "unmatched_old": [],
            "unmatched_new": [],
        }
        out = build_lineage_candidates(
            old,
            new,
            report,
            old_build="alternate",
            new_build="v308",
        )
        self.assertEqual(out["relationships"], [])
        self.assertEqual(len(out["research_only"]), 1)
        self.assertEqual(len(out["ambiguous"]), 1)
        self.assertEqual(
            out["research_only"][0]["strategy"],
            "package_anchor",
        )

if __name__ == "__main__":
    unittest.main()

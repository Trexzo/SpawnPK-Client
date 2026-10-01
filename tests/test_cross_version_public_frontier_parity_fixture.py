from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CrossVersionPublicFrontierParityFixtureTests(unittest.TestCase):
    def load(self, rel: str):
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_v307_v308_public_frontier_authority_matches(self):
        old = self.load("fixtures/v307-source-m1-frontier-proof.json")
        new = self.load("fixtures/v308-source-m1-frontier-proof.json")
        parity = self.load(
            "fixtures/v307-v308-source-m1-public-frontier-parity.json"
        )

        old_frontier = old["clean_rebuild_frontier"]
        new_frontier = new["clean_rebuild_frontier"]
        public = parity["public_frontier"]

        self.assertEqual(
            old_frontier["javac_frontier_id"],
            new_frontier["javac_frontier_id"],
        )
        self.assertEqual(
            public["old_javac_frontier_id"],
            old_frontier["javac_frontier_id"],
        )
        self.assertEqual(
            public["new_javac_frontier_id"],
            new_frontier["javac_frontier_id"],
        )
        self.assertTrue(public["frontier_ids_equal"])
        self.assertEqual(
            old_frontier["total_errors"],
            new_frontier["total_errors"],
        )
        self.assertEqual(
            old_frontier["affected_files"],
            new_frontier["affected_files"],
        )
        self.assertEqual(
            old_frontier["cannot_find_symbol"],
            new_frontier["cannot_find_symbol"],
        )
        self.assertEqual(
            old_frontier["categories"],
            new_frontier["categories"],
        )
        self.assertTrue(public["aggregate_categories_equal"])

    def test_public_parity_does_not_claim_private_exact_comparison(self):
        parity = self.load(
            "fixtures/v307-v308-source-m1-public-frontier-parity.json"
        )
        excluded = set(parity["truth_boundary"]["does_not_prove"])
        self.assertIn(
            "the private spk-cross-version-javac-frontier report has executed successfully",
            excluded,
        )
        self.assertIn(
            "the private exact javac input SHA-256 values are equal",
            excluded,
        )
        self.assertIn(
            "either recovery release is release-ready",
            excluded,
        )


if __name__ == "__main__":
    unittest.main()

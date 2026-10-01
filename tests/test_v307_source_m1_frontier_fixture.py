from __future__ import annotations

import json
from pathlib import Path
import unittest


class HistoricalV307SourceM1FrontierFixtureTests(unittest.TestCase):
    def test_fixture_preserves_exact_historical_frontier(self):
        repo = Path(__file__).resolve().parents[1]
        path = (
            repo
            / "fixtures"
            / "v307-source-m1-frontier-proof.json"
        )
        value = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(value["schema_version"], 1)
        self.assertEqual(
            value["kind"],
            "historical_source_m1_frontier_proof",
        )
        self.assertEqual(
            value["authority_commit"],
            "ce3d43e34f53a3991f30f5911bbd0235f73fe6f9",
        )
        self.assertEqual(
            value["inputs"]["client_sha256"],
            "6232bae206846a4ba8d09766a2dee886"
            "b69016066a3f50f83b201bf705f93662",
        )
        self.assertEqual(
            value["readable_source"]["java_file_count"],
            1048,
        )
        self.assertEqual(
            value["readable_source"]["source_tree_sha256"],
            "3d630d3cc6b194959da2e9d907e5680f"
            "f282c1bf7edffc7774e4a1e72023d449",
        )

        frontier = value["clean_rebuild_frontier"]
        self.assertEqual(
            frontier["javac_frontier_id"],
            "JAVACFRONTIER_79F76A743656F3D6EB8F",
        )
        self.assertEqual(frontier["total_errors"], 405)
        self.assertEqual(frontier["affected_files"], 75)
        self.assertEqual(frontier["cannot_find_symbol"], 178)
        self.assertEqual(sum(frontier["categories"].values()), 405)
        self.assertEqual(frontier["wrapper_exit"], 3)
        self.assertTrue(frontier["safety_authority_pass"])
        self.assertFalse(frontier["recovery_release_pass"])
        self.assertFalse(frontier["ready_for_release"])

    def test_fixture_keeps_release_readiness_outside_truth_boundary(self):
        repo = Path(__file__).resolve().parents[1]
        path = (
            repo
            / "fixtures"
            / "v307-source-m1-frontier-proof.json"
        )
        value = json.loads(path.read_text(encoding="utf-8"))
        does_not_prove = " ".join(
            value["truth_boundary"]["does_not_prove"]
        ).lower()

        self.assertIn("release-ready", does_not_prove)
        self.assertIn("cross-version pass", does_not_prove)


if __name__ == "__main__":
    unittest.main()

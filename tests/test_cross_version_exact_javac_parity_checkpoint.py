from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CrossVersionExactJavacParityCheckpointTests(unittest.TestCase):
    def load(self, rel: str):
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_exact_private_comparator_checkpoint(self):
        checkpoint = self.load(
            "fixtures/v307-v308-source-m1-exact-javac-parity-07ed6f9.json"
        )
        comparison = checkpoint["comparison"]
        bindings = checkpoint["bindings"]
        run_state = checkpoint["run_state"]

        self.assertEqual(
            checkpoint["kind"],
            "cross_version_exact_javac_frontier_parity_checkpoint",
        )
        self.assertEqual(
            checkpoint["measurement_status"],
            "exact_private_comparator_executed_redacted_checkpoint",
        )
        self.assertEqual(
            checkpoint["tooling_commit"],
            "07ed6f961fd9ab67439b1d9428446f914bafeabf",
        )
        self.assertEqual(
            checkpoint["old_authority_sha256"],
            "6232bae206846a4ba8d09766a2dee886"
            "b69016066a3f50f83b201bf705f93662",
        )
        self.assertEqual(
            checkpoint["new_authority_sha256"],
            "854f26ff9f134b0317572e7ac1688e6f"
            "40a231d5a4c66f8db5d655b7f45ce7c6",
        )

        self.assertEqual(
            comparison["old_frontier_id"],
            "JAVACFRONTIER_D028FE33F2F3EC395B94",
        )
        self.assertEqual(
            comparison["new_frontier_id"],
            comparison["old_frontier_id"],
        )
        self.assertTrue(comparison["exact_frontier_equal"])
        self.assertEqual(comparison["old_total_errors"], 350)
        self.assertEqual(comparison["new_total_errors"], 350)
        self.assertEqual(comparison["shared_errors"], 350)
        self.assertEqual(comparison["old_only_errors"], 0)
        self.assertEqual(comparison["new_only_errors"], 0)
        self.assertEqual(comparison["shared_percent_of_old"], 100.0)
        self.assertEqual(comparison["shared_percent_of_new"], 100.0)
        self.assertEqual(comparison["old_affected_files"], 75)
        self.assertEqual(comparison["new_affected_files"], 75)
        self.assertEqual(comparison["shared_affected_files"], 75)
        self.assertEqual(sum(comparison["categories"].values()), 350)

        self.assertNotEqual(
            bindings["old_diagnostic_report_id"],
            bindings["new_diagnostic_report_id"],
        )
        self.assertNotEqual(
            bindings["old_diagnostic_input_sha256"],
            bindings["new_diagnostic_input_sha256"],
        )
        self.assertNotEqual(
            bindings["old_source_tree_sha256"],
            bindings["new_source_tree_sha256"],
        )

        self.assertFalse(run_state["old_release_ready"])
        self.assertFalse(run_state["new_release_ready"])
        self.assertFalse(
            run_state["equivalent_tooling_recovery_releases_ready"]
        )
        self.assertEqual(run_state["wrapper_exit"], 3)
        self.assertTrue(run_state["frozen_tooling_cleanup_pass"])

    def test_historical_public_anchor_remains_distinct(self):
        anchor = self.load(
            "fixtures/v307-v308-source-m1-public-frontier-parity.json"
        )
        checkpoint = self.load(
            "fixtures/v307-v308-source-m1-exact-javac-parity-07ed6f9.json"
        )

        self.assertEqual(
            checkpoint["historical_public_anchor_fixture"],
            "fixtures/v307-v308-source-m1-public-frontier-parity.json",
        )
        self.assertEqual(
            anchor["public_frontier"]["old_total_errors"],
            405,
        )
        self.assertEqual(
            checkpoint["comparison"]["old_total_errors"],
            350,
        )
        self.assertIn(
            "the private spk-cross-version-javac-frontier report has executed successfully",
            set(anchor["truth_boundary"]["does_not_prove"]),
        )
        self.assertIn(
            "the private cross-version javac comparator executed successfully on exact v307 and exact v308 diagnostics generated under one frozen recovery-tooling commit",
            set(checkpoint["truth_boundary"]["proves"]),
        )

    def test_checkpoint_does_not_claim_release_readiness(self):
        checkpoint = self.load(
            "fixtures/v307-v308-source-m1-exact-javac-parity-07ed6f9.json"
        )
        excluded = set(checkpoint["truth_boundary"]["does_not_prove"])

        self.assertIn(
            "either recovery release is release-ready",
            excluded,
        )
        self.assertIn(
            "the final strict recovered-source v307-to-v308 cross-version PASS",
            excluded,
        )


if __name__ == "__main__":
    unittest.main()

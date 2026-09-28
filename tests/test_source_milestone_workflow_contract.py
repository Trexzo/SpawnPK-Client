from __future__ import annotations

from pathlib import Path
import unittest


class SourceMilestoneWorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.workflow = (
            self.root
            / ".github"
            / "workflows"
            / "source-milestone-1.yml"
        )
        self.text = self.workflow.read_text(encoding="utf-8")

    def test_supports_manual_and_reusable_triggers(self):
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("workflow_call:", self.text)
        self.assertIn(
            "authority_run_id:\n"
            "        description: Optional prior run ID; "
            "blank consumes the caller run artifact",
            self.text,
        )

    def test_same_run_and_prior_run_downloads_are_distinct(self):
        same_start = self.text.index(
            "- name: Download Source M1 authority artifact "
            "from caller run"
        )
        prior_start = self.text.index(
            "- name: Download Source M1 authority artifact "
            "from prior run"
        )
        validate_start = self.text.index(
            "- name: Validate authority artifact contract"
        )

        same = self.text[same_start:prior_start]
        prior = self.text[prior_start:validate_start]

        self.assertIn(
            "if: ${{ inputs.authority_run_id == '' }}",
            same,
        )
        self.assertNotIn("run-id:", same)
        self.assertNotIn("github-token:", same)

        self.assertIn(
            "if: ${{ inputs.authority_run_id != '' }}",
            prior,
        )
        self.assertIn(
            "github-token: ${{ github.token }}",
            prior,
        )
        self.assertIn(
            "run-id: ${{ inputs.authority_run_id }}",
            prior,
        )

    def test_reusable_outputs_are_verification_backed(self):
        for name in (
            "milestone_id",
            "bundle_id",
            "authority_verification_id",
            "bundle_verification_id",
            "source_tree_sha256",
            "publication_artifact_name",
        ):
            expected = (
                name
                + ": ${{ steps.result.outputs."
                + name
                + " }}"
            )
            self.assertIn(expected, self.text)

        result_start = self.text.index(
            "- name: Export verified workflow outputs"
        )
        upload_start = self.text.index(
            "- name: Upload verified Source Milestone artifact"
        )
        result = self.text[result_start:upload_start]

        self.assertIn(
            'if not authority_verification.get("verified")',
            result,
        )
        self.assertIn(
            'if not bundle_verification.get("verified")',
            result,
        )
        self.assertIn(
            'if not milestone.get("publishable")',
            result,
        )

    def test_workflow_has_no_publication_write_permissions(self):
        permissions_start = self.text.index("permissions:")
        jobs_start = self.text.index("\njobs:")
        permissions = self.text[permissions_start:jobs_start]

        self.assertIn("contents: read", permissions)
        self.assertIn("actions: read", permissions)
        self.assertNotIn("write", permissions.lower())
        self.assertNotIn("git push", self.text.lower())
        self.assertNotIn("gh repo create", self.text.lower())


if __name__ == "__main__":
    unittest.main()

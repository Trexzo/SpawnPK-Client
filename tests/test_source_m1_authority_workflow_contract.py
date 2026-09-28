from __future__ import annotations

from pathlib import Path
import unittest


class SourceM1AuthorityWorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.workflow = (
            self.root
            / ".github"
            / "workflows"
            / "source-m1-authority.yml"
        )
        self.text = self.workflow.read_text(encoding="utf-8")

    def test_supports_manual_and_reusable_triggers(self):
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("workflow_call:", self.text)
        self.assertIn(
            "workspace_run_id:\n"
            "        description: Optional prior run ID; "
            "blank consumes the caller run artifact",
            self.text,
        )

    def test_same_run_and_prior_run_downloads_are_distinct(self):
        same_start = self.text.index(
            "- name: Download recovered workspace artifact "
            "from caller run"
        )
        prior_start = self.text.index(
            "- name: Download recovered workspace artifact "
            "from prior run"
        )
        validate_start = self.text.index(
            "- name: Validate recovered workspace contract"
        )

        same = self.text[same_start:prior_start]
        prior = self.text[prior_start:validate_start]

        self.assertIn(
            "if: ${{ inputs.workspace_run_id == '' }}",
            same,
        )
        self.assertNotIn("run-id:", same)
        self.assertNotIn("github-token:", same)

        self.assertIn(
            "if: ${{ inputs.workspace_run_id != '' }}",
            prior,
        )
        self.assertIn(
            "github-token: ${{ github.token }}",
            prior,
        )
        self.assertIn(
            "run-id: ${{ inputs.workspace_run_id }}",
            prior,
        )

    def test_prior_run_provenance_is_validated_before_download(self):
        validate_start = self.text.index(
            "- name: Validate prior recovered workspace run provenance"
        )
        prior_start = self.text.index(
            "- name: Download recovered workspace artifact "
            "from prior run"
        )
        validate = self.text[validate_start:prior_start]

        self.assertIn(
            "if: ${{ inputs.workspace_run_id != '' }}",
            validate,
        )
        self.assertIn(
            "workspace_run_id must be a positive decimal run ID",
            validate,
        )
        self.assertIn(
            'run.get("status") != "completed"',
            validate,
        )
        self.assertIn(
            'run.get("conclusion") != "success"',
            validate,
        )
        self.assertIn(
            'run_repository != repository',
            validate,
        )
        self.assertIn(
            "/actions/runs/{run_id}",
            validate,
        )
        self.assertIn(
            "/compare/",
            validate,
        )
        self.assertIn(
            'comparison.get("status") not in {"ahead", "identical"}',
            validate,
        )
        self.assertIn(
            "authority commit is not an ancestor of ",
            validate,
        )
        self.assertIn(
            "the workspace run head",
            validate,
        )

    def test_recovered_workspace_contract_is_source_only(self):
        validate_start = self.text.index(
            "- name: Validate recovered workspace contract"
        )
        build_start = self.text.index(
            "- name: Build Source M1 authority artifact"
        )
        validate = self.text[validate_start:build_start]

        for name in (
            "class-lineage.json",
            "member-lineage.json",
            "readable-client-manifest.json",
            "recovered-source-manifest.json",
            "clean-rebuild.json",
            "recovery-release.json",
            "release-verification.json",
        ):
            self.assertIn(name, validate)

        self.assertIn(
            'rel.startswith("src/") and rel.endswith(".java")',
            validate,
        )
        self.assertIn(
            "recovered workspace contains forbidden files",
            validate,
        )
        self.assertIn(
            "recovered workspace contains no Java source files",
            validate,
        )

    def test_authority_is_built_then_independently_verified(self):
        build_start = self.text.index(
            "- name: Build Source M1 authority artifact"
        )
        verify_start = self.text.index(
            "- name: Independently verify Source M1 authority artifact"
        )
        export_start = self.text.index(
            "- name: Export verified authority outputs"
        )

        build = self.text[build_start:verify_start]
        verify = self.text[verify_start:export_start]

        self.assertIn(
            "spk_recovery.source_authority_artifact_cli build",
            build,
        )
        self.assertIn("--out-dir authority", build)
        self.assertIn(
            "spk_recovery.source_authority_artifact_cli verify",
            verify,
        )
        self.assertIn(
            "--artifact-dir authority",
            verify,
        )
        self.assertIn(
            "--out verification/SOURCE-AUTHORITY-VERIFICATION.json",
            verify,
        )

    def test_outputs_require_verified_matching_authority(self):
        export_start = self.text.index(
            "- name: Export verified authority outputs"
        )
        upload_start = self.text.index(
            "- name: Upload verified Source M1 authority artifact"
        )
        export = self.text[export_start:upload_start]

        self.assertIn(
            'manifest.get("preflight_publishable") is not True',
            export,
        )
        self.assertIn(
            'verification.get("verified") is not True',
            export,
        )
        self.assertIn(
            'verification.get("artifact_id")',
            export,
        )
        self.assertIn(
            'verification.get("source_tree_sha256")',
            export,
        )

        for name in (
            "artifact_id",
            "verification_id",
            "source_tree_sha256",
            "authority_artifact_name",
        ):
            expected = (
                name
                + ": ${{ steps.result.outputs."
                + name
                + " }}"
            )
            self.assertIn(expected, self.text)

    def test_upload_and_permissions_are_read_only(self):
        permissions_start = self.text.index("permissions:")
        jobs_start = self.text.index("\njobs:")
        permissions = self.text[permissions_start:jobs_start]

        self.assertIn("contents: read", permissions)
        self.assertIn("actions: read", permissions)
        self.assertNotIn("write", permissions.lower())

        upload_start = self.text.index(
            "- name: Upload verified Source M1 authority artifact"
        )
        upload = self.text[upload_start:]

        self.assertIn("path: authority", upload)
        self.assertNotIn("verification/", upload)
        self.assertNotIn("git push", self.text.lower())
        self.assertNotIn("gh repo create", self.text.lower())


if __name__ == "__main__":
    unittest.main()

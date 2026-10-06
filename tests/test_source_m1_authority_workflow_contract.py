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

    def test_exact_public_tooling_checkout_supports_private_callers(self):
        syntax_start = self.text.index(
            "- name: Validate authority commit syntax"
        )
        checkout_start = self.text.index(
            "- name: Checkout exact recovery tooling"
        )
        prove_start = self.text.index(
            "- name: Prove exact recovery tooling checkout"
        )
        setup_start = self.text.index("- name: Set up Python")

        self.assertLess(syntax_start, checkout_start)
        self.assertLess(checkout_start, prove_start)
        self.assertLess(prove_start, setup_start)

        checkout = self.text[checkout_start:prove_start]
        self.assertIn(
            "repository: Trexzo/SpawnPK-Client",
            checkout,
        )
        self.assertIn(
            "ref: ${{ inputs.authority_commit }}",
            checkout,
        )
        self.assertIn("fetch-depth: 0", checkout)
        self.assertIn("persist-credentials: false", checkout)

        prove = self.text[prove_start:setup_start]
        self.assertIn('actual="$(git rev-parse HEAD)"', prove)
        self.assertIn(
            'test "$actual" = "$AUTHORITY_COMMIT"',
            prove,
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
            "AUTHORITY_REPOSITORY_VALUE: Trexzo/SpawnPK-Client",
            validate,
        )
        self.assertIn(
            "if repository == authority_repository:",
            validate,
        )
        self.assertIn(
            "/compare/",
            validate,
        )
        self.assertIn(
            'comparison.get("status") not in {',
            validate,
        )
        self.assertIn('"ahead"', validate)
        self.assertIn('"identical"', validate)
        self.assertIn(
            "authority commit is not an ancestor of ",
            validate,
        )
        self.assertIn(
            "the workspace run head",
            validate,
        )
        self.assertIn(
            "cross-repository caller: authority ancestry ",
            validate,
        )
        self.assertIn(
            "semantic ",
            validate,
        )
        self.assertIn(
            "authority verification",
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

    def test_trusted_preflight_milestone_anchors_artifact_verification(self):
        preflight_start = self.text.index(
            "- name: Build trusted preflight Source Milestone manifest"
        )
        build_start = self.text.index(
            "- name: Build Source M1 authority artifact"
        )
        verify_start = self.text.index(
            "- name: Independently verify Source M1 authority artifact"
        )
        export_start = self.text.index(
            "- name: Export verified authority outputs"
        )

        self.assertLess(preflight_start, build_start)
        self.assertLess(build_start, verify_start)

        preflight = self.text[preflight_start:build_start]
        verify = self.text[verify_start:export_start]

        self.assertIn(
            "spk_recovery.source_milestone_cli build",
            preflight,
        )
        self.assertIn(
            "--out verification/PREFLIGHT-SOURCE-MILESTONE.json",
            preflight,
        )
        self.assertIn(
            "--source-root workspace/src",
            preflight,
        )
        self.assertIn(
            "--semantic-review "
            "mappings/candidates/v308.semantic-review.chat2.r2.json",
            preflight,
        )
        self.assertIn(
            "--semantic-acceptance "
            "mappings/v308.semantic.acceptance.json",
            preflight,
        )
        self.assertIn(
            "verification/PREFLIGHT-SOURCE-MILESTONE.json",
            verify,
        )
        self.assertIn(
            'EXPECTED_MILESTONE_ID="$(',
            verify,
        )
        self.assertIn(
            '--expected-authority-commit "$AUTHORITY_COMMIT"',
            verify,
        )
        self.assertIn(
            '--expected-milestone-id "$EXPECTED_MILESTONE_ID"',
            verify,
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
        self.assertIn(
            "SOURCE_AUTHORITY_DIR: ${{ runner.temp }}/source-m1-authority",
            build,
        )
        self.assertIn(
            '--out-dir "$SOURCE_AUTHORITY_DIR"',
            build,
        )
        self.assertIn(
            "--semantic-review "
            "mappings/candidates/v308.semantic-review.chat2.r2.json",
            build,
        )
        self.assertIn(
            "--semantic-acceptance "
            "mappings/v308.semantic.acceptance.json",
            build,
        )
        self.assertNotIn("--out-dir authority", build)
        self.assertIn(
            "spk_recovery.source_authority_artifact_cli verify",
            verify,
        )
        self.assertIn(
            "SOURCE_AUTHORITY_DIR: ${{ runner.temp }}/source-m1-authority",
            verify,
        )
        self.assertIn(
            '--artifact-dir "$SOURCE_AUTHORITY_DIR"',
            verify,
        )
        self.assertNotIn("--artifact-dir authority", verify)
        self.assertIn(
            "--out verification/SOURCE-AUTHORITY-VERIFICATION.json",
            verify,
        )

    def test_authority_output_is_runner_isolated_from_checkout(self):
        build_start = self.text.index(
            "- name: Build Source M1 authority artifact"
        )
        upload_start = self.text.index(
            "- name: Upload verified Source M1 authority artifact"
        )
        section = self.text[build_start:]
        export = self.text[
            self.text.index("- name: Export verified authority outputs"):
            upload_start
        ]

        self.assertEqual(
            section.count(
                "SOURCE_AUTHORITY_DIR: "
                "${{ runner.temp }}/source-m1-authority"
            ),
            3,
        )
        self.assertIn('test ! -e "$SOURCE_AUTHORITY_DIR"', section)
        self.assertIn(
            'Path(os.environ["SOURCE_AUTHORITY_DIR"])',
            export,
        )
        self.assertNotIn(
            '"authority/SOURCE-AUTHORITY-ARTIFACT.json"',
            export,
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

        self.assertIn(
            "path: ${{ runner.temp }}/source-m1-authority",
            upload,
        )
        self.assertNotIn("path: authority", upload)
        self.assertNotIn("verification/", upload)
        self.assertNotIn("git push", self.text.lower())
        self.assertNotIn("gh repo create", self.text.lower())


if __name__ == "__main__":
    unittest.main()

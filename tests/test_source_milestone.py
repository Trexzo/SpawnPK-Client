from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.source_digest import source_tree_digest
from spk_recovery.source_milestone import (
    SourceMilestoneError,
    build_source_milestone_manifest,
)
from spk_recovery.source_milestone_verify import (
    verify_source_milestone,
)
from spk_recovery.source_repository_export import (
    SourceRepositoryExportError,
    export_source_repository,
)
from spk_recovery.source_authority_bundle import (
    SourceAuthorityBundleError,
    build_source_authority_bundle,
)


AUTH = "a" * 64
READABLE = "b" * 64
REBUILT = "c" * 64
COMMIT = "d" * 40


def _docs(source_tree_sha: str, java_count: int, source_bytes: int):
    authority = {"sha256": AUTH}
    readable = {
        "schema_version": 1,
        "kind": "readable_client_build_manifest",
        "manifest_id": "READABLE_TEST",
        "build_id": "v308",
        "namespace_id": "SEMNS_TEST",
        "source_sha256": AUTH,
        "output_sha256": READABLE,
        "class_plan_digest": "1" * 64,
        "member_plan_digest": "2" * 64,
        "status": "complete",
        "verification_pass": True,
        "source_safe_fallback": True,
        "fallback_name_prefix": "Recovered_",
        "semantic_summary": {
            "accepted_classes": 4,
            "accepted_members": 6,
            "source_safety_fallbacks": 3,
        },
    }
    recovered = {
        "schema_version": 1,
        "kind": "recovered_source_workspace_manifest",
        "workspace_id": "SRCWS_TEST",
        "build_id": "v308",
        "source_authority_sha256": AUTH,
        "readable_jar_sha256": READABLE,
        "namespace_id": "SEMNS_TEST",
        "class_plan_digest": "1" * 64,
        "member_plan_digest": "2" * 64,
        "source_tree_sha256": source_tree_sha,
        "java_file_count": java_count,
        "source_bytes": source_bytes,
        "source_scope": "project_classes",
        "collision_transform_id": "JNSTRANSFORM_TEST",
        "collision_plan_id": "JNSPLAN_TEST",
        "collision_report_id": "JNSCOLLISION_TEST",
        "base_readable_jar_sha256": READABLE,
    }
    clean = {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": "CLEANBUILD_TEST",
        "status": "complete",
        "workspace_id": "SRCWS_TEST",
        "build_id": "v308",
        "source_authority_sha256": AUTH,
        "readable_jar_sha256": READABLE,
        "namespace_id": "SEMNS_TEST",
        "source_tree_sha256": source_tree_sha,
        "build_authority_id": "BUILDAUTH_TEST",
        "project_classes": {
            "expected_count": 3,
            "generated_count": 3,
            "missing": [],
            "unexpected": [],
            "binary_fallback_count": 0,
        },
        "rebuilt_client": {"sha256": REBUILT},
        "clean_project_build": True,
    }
    return authority, readable, recovered, clean


class SourceMilestoneTests(unittest.TestCase):
    def _source(self, root: Path) -> tuple[Path, str, int, int]:
        src = root / "source"
        pkg = src / "rs"
        pkg.mkdir(parents=True)
        (pkg / "A.java").write_text(
            "package rs; public class A {}\n",
            encoding="utf-8",
        )
        tree, files, source_bytes = source_tree_digest(src)
        return src, tree, len(files), source_bytes

    def test_publishable_manifest_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, tree, count, size = self._source(root)
            docs = _docs(tree, count, size)
            a = build_source_milestone_manifest(
                *docs,
                authority_commit=COMMIT,
            )
            b = build_source_milestone_manifest(
                *copy.deepcopy(docs),
                authority_commit=COMMIT,
            )
            self.assertEqual(a, b)
            self.assertTrue(a["publishable"])
            self.assertEqual(a["blockers"], [])
            self.assertEqual(
                a["project_class_set"]["binary_fallback_count"],
                0,
            )
            self.assertFalse(
                a["naming_policy"]["invented_semantics_allowed"]
            )

    def test_fallback_and_classset_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _src, tree, count, size = self._source(root)
            authority, readable, recovered, clean = _docs(
                tree, count, size
            )
            readable["source_safe_fallback"] = False
            readable["fallback_name_prefix"] = None
            clean["project_classes"]["generated_count"] = 2
            clean["project_classes"]["binary_fallback_count"] = 1
            clean["project_classes"]["missing"] = ["rs/B.class"]
            manifest = build_source_milestone_manifest(
                authority,
                readable,
                recovered,
                clean,
                authority_commit=COMMIT,
            )
            self.assertFalse(manifest["publishable"])
            reasons = {row["reason"] for row in manifest["blockers"]}
            self.assertIn("source_safe_fallback_not_enabled", reasons)
            self.assertIn("project_binary_fallback_present", reasons)
            self.assertIn("generated_expected_count_mismatch", reasons)
            self.assertIn("missing_project_classes", reasons)

    def test_authority_commit_must_be_exact_full_sha(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _src, tree, count, size = self._source(root)
            with self.assertRaisesRegex(
                SourceMilestoneError,
                "40-hex",
            ):
                build_source_milestone_manifest(
                    *_docs(tree, count, size),
                    authority_commit="deadbeef",
                )

    def test_authority_bundle_is_exact_and_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, tree, count, size = self._source(root)
            docs = _docs(tree, count, size)

            out_a = root / "bundle-a"
            out_b = root / "bundle-b"

            a = build_source_authority_bundle(
                *docs,
                src,
                out_a,
                authority_commit=COMMIT,
            )
            b = build_source_authority_bundle(
                *copy.deepcopy(docs),
                src,
                out_b,
                authority_commit=COMMIT,
            )

            self.assertEqual(a, b)
            self.assertTrue(
                a["bundle_id"].startswith("SOURCE_AUTHORITY_")
            )
            self.assertEqual(a["source_tree_sha256"], tree)
            self.assertEqual(a["authority_commit"], COMMIT)
            self.assertEqual(a["java_file_count"], count)

            for rel in (
                "authority-index.json",
                "readable-client-manifest.json",
                "recovered-source-manifest.json",
                "clean-rebuild.json",
                "SOURCE-AUTHORITY.json",
                "src/rs/A.java",
            ):
                self.assertEqual(
                    (out_a / rel).read_bytes(),
                    (out_b / rel).read_bytes(),
                )

    def test_authority_bundle_refuses_source_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, tree, count, size = self._source(root)
            docs = _docs(tree, count, size)
            (src / "rs" / "A.java").write_text(
                "package rs; public class A { int drift; }\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                SourceAuthorityBundleError,
                "source tree SHA-256",
            ):
                build_source_authority_bundle(
                    *docs,
                    src,
                    root / "bundle",
                    authority_commit=COMMIT,
                )

    def test_export_is_byte_faithful_and_verifiable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, tree, count, size = self._source(root)
            docs = _docs(tree, count, size)
            manifest = build_source_milestone_manifest(
                *docs,
                authority_commit=COMMIT,
            )
            out = root / "export"
            (src / "UNBOUND.txt").write_text(
                "must not publish\n",
                encoding="utf-8",
            )
            exported = export_source_repository(
                manifest,
                src,
                out,
            )
            self.assertTrue(exported["publishable"])
            self.assertFalse((out / "src" / "UNBOUND.txt").exists())
            self.assertEqual(exported["source_tree_sha256"], tree)

            verified = verify_source_milestone(
                manifest,
                *docs,
                authority_commit=COMMIT,
                source_root=src,
                exported_repository_root=out,
            )
            self.assertTrue(verified["verified"])
            self.assertTrue(verified["publishable"])

            (out / "src" / "rs" / "A.java").write_text(
                "package rs; public class A { int x; }\n",
                encoding="utf-8",
            )
            drift = verify_source_milestone(
                manifest,
                *docs,
                authority_commit=COMMIT,
                exported_repository_root=out,
            )
            self.assertFalse(drift["verified"])

    def test_export_refuses_blocked_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, tree, count, size = self._source(root)
            authority, readable, recovered, clean = _docs(
                tree, count, size
            )
            clean["status"] = "compile_failed"
            clean["clean_project_build"] = False
            manifest = build_source_milestone_manifest(
                authority,
                readable,
                recovered,
                clean,
                authority_commit=COMMIT,
            )
            with self.assertRaisesRegex(
                SourceRepositoryExportError,
                "not publishable",
            ):
                export_source_repository(
                    manifest,
                    src,
                    root / "export",
                )


if __name__ == "__main__":
    unittest.main()

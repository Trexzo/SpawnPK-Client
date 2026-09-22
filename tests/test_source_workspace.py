from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.source_workspace import (
    SourceWorkspaceError,
    build_source_workspace,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest(jar_sha: str) -> dict:
    return {
        "schema_version": 1,
        "kind": "readable_client_build_manifest",
        "build_id": "v308",
        "namespace_id": "SEMNS_1234567890ABCDEF1234",
        "source_sha256": "a" * 64,
        "target_package": "recovered/spawnpk/client",
        "class_plan_digest": "c" * 64,
        "member_plan_digest": "d" * 64,
        "status": "complete",
        "output_sha256": jar_sha,
        "verification_pass": True,
        "semantic_summary": {},
        "blocker": None,
        "artifact_names": {},
        "manifest_id": "READABLE_1234567890ABCDEF1234",
    }


class SourceWorkspaceTests(unittest.TestCase):
    def test_rejects_non_complete_readable_build(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = root / "readable.jar"
            jar.write_bytes(b"jar")
            manifest = _manifest(_sha(b"jar"))
            manifest["status"] = "blocked"
            manifest["verification_pass"] = None
            with self.assertRaises(SourceWorkspaceError):
                build_source_workspace(
                    manifest,
                    jar,
                    root / "decompiler.jar",
                    expected_decompiler_sha256="b" * 64,
                    engine="cfr",
                    out_dir=root / "out",
                )

    def test_rejects_readable_jar_hash_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = root / "readable.jar"
            jar.write_bytes(b"wrong")
            with self.assertRaises(SourceWorkspaceError):
                build_source_workspace(
                    _manifest("f" * 64),
                    jar,
                    root / "decompiler.jar",
                    expected_decompiler_sha256="b" * 64,
                    engine="cfr",
                    out_dir=root / "out",
                )

    @patch("spk_recovery.source_workspace.run_decompiler")
    def test_source_tree_is_hash_pinned(self, run):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar_bytes = b"readable"
            jar = root / "readable.jar"
            jar.write_bytes(jar_bytes)
            decompiler = root / "decompiler.jar"
            decompiler.write_bytes(b"tool")
            out = root / "out"

            def fake_decompile(
                input_jar,
                decompiler_jar,
                *,
                expected_decompiler_sha256,
                engine,
                out_dir,
                clean_out,
            ):
                (out_dir / "pkg").mkdir(parents=True)
                (out_dir / "pkg" / "A.java").write_text(
                    "package pkg; class A {}\n",
                    encoding="utf-8",
                )
                return {
                    "schema_version": 1,
                    "kind": "decompiler_result",
                    "engine": engine,
                    "input_sha256": _sha(jar_bytes),
                    "decompiler_sha256": expected_decompiler_sha256,
                    "java_file_count": 1,
                    "output_directory": str(out_dir),
                    "stdout": "",
                    "stderr": "",
                }

            run.side_effect = fake_decompile
            manifest = build_source_workspace(
                _manifest(_sha(jar_bytes)),
                jar,
                decompiler,
                expected_decompiler_sha256="b" * 64,
                engine="cfr",
                out_dir=out,
            )
            self.assertEqual(manifest["java_file_count"], 1)
            self.assertEqual(manifest["source_directory"], "src")
            self.assertTrue((out / "src" / "pkg" / "A.java").is_file())
            self.assertTrue((out / "recovered-source-manifest.json").is_file())
            self.assertTrue(manifest["source_tree_sha256"])


if __name__ == "__main__":
    unittest.main()

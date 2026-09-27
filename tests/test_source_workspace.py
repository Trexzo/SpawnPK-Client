from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from spk_recovery.source_workspace import (
    SourceWorkspaceError,
    build_source_workspace,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _transform_report(
    input_sha: str,
    output_sha: str,
    *,
    transform_id: str = "JNSREWRITE_1234567890ABCDEF1234",
) -> dict:
    return {
        "schema_version": 1,
        "kind": "namespace_collision_bytecode_transform",
        "transform_id": transform_id,
        "plan_id": "JNSPLAN_1234567890ABCDEF1234",
        "collision_report_id": "JNSCOLLISION_1234567890ABCDEF12",
        "input_jar_sha256": input_sha,
        "output_jar_sha256": output_sha,
        "summary": {},
    }


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


    @patch("spk_recovery.source_workspace.run_decompiler")
    def test_collision_transform_provenance_is_bound_into_workspace(
        self,
        run,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base_bytes = b"base-readable"
            transformed_bytes = b"collision-remapped-readable"

            jar = root / "readable-remapped.jar"
            jar.write_bytes(transformed_bytes)
            decompiler = root / "decompiler.jar"
            decompiler.write_bytes(b"tool")

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
                    "input_sha256": _sha(transformed_bytes),
                    "decompiler_sha256": expected_decompiler_sha256,
                    "java_file_count": 1,
                    "output_directory": str(out_dir),
                    "stdout": "",
                    "stderr": "",
                }

            run.side_effect = fake_decompile

            transform = _transform_report(
                _sha(base_bytes),
                _sha(transformed_bytes),
            )
            manifest = build_source_workspace(
                _manifest(_sha(base_bytes)),
                jar,
                decompiler,
                expected_decompiler_sha256="b" * 64,
                engine="cfr",
                out_dir=root / "out",
                collision_transform_report=transform,
            )

            self.assertEqual(
                manifest["readable_jar_sha256"],
                _sha(transformed_bytes),
            )
            self.assertEqual(
                manifest["base_readable_jar_sha256"],
                _sha(base_bytes),
            )
            self.assertEqual(
                manifest["collision_transform_id"],
                transform["transform_id"],
            )
            self.assertEqual(
                manifest["collision_plan_id"],
                transform["plan_id"],
            )
            self.assertEqual(
                manifest["collision_report_id"],
                transform["collision_report_id"],
            )

            manifest_file = json.loads(
                (
                    root
                    / "out"
                    / "recovered-source-manifest.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                manifest_file["collision_transform_id"],
                transform["transform_id"],
            )

    def test_collision_transform_input_must_bind_base_readable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            transformed = b"collision-remapped-readable"
            jar = root / "readable-remapped.jar"
            jar.write_bytes(transformed)

            report = _transform_report(
                "f" * 64,
                _sha(transformed),
            )
            with self.assertRaisesRegex(
                SourceWorkspaceError,
                "transform input SHA",
            ):
                build_source_workspace(
                    _manifest("a" * 64),
                    jar,
                    root / "decompiler.jar",
                    expected_decompiler_sha256="b" * 64,
                    engine="cfr",
                    out_dir=root / "out",
                    collision_transform_report=report,
                )

    def test_collision_transform_output_must_bind_actual_readable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = b"base-readable"
            jar = root / "readable-remapped.jar"
            jar.write_bytes(b"actual-remapped")

            report = _transform_report(
                _sha(base),
                "f" * 64,
            )
            with self.assertRaisesRegex(
                SourceWorkspaceError,
                "transformed readable client SHA-256",
            ):
                build_source_workspace(
                    _manifest(_sha(base)),
                    jar,
                    root / "decompiler.jar",
                    expected_decompiler_sha256="b" * 64,
                    engine="cfr",
                    out_dir=root / "out",
                    collision_transform_report=report,
                )

    @patch("spk_recovery.source_workspace.run_decompiler")
    def test_legacy_workspace_id_material_is_unchanged_without_transform(
        self,
        run,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar_bytes = b"legacy-readable"
            jar = root / "readable.jar"
            jar.write_bytes(jar_bytes)
            decompiler = root / "decompiler.jar"
            decompiler.write_bytes(b"tool")

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

            readable = _manifest(_sha(jar_bytes))
            manifest = build_source_workspace(
                readable,
                jar,
                decompiler,
                expected_decompiler_sha256="b" * 64,
                engine="cfr",
                out_dir=root / "out",
            )

            material = {
                "source_sha256": readable["source_sha256"],
                "readable_jar_sha256": _sha(jar_bytes),
                "namespace_id": readable["namespace_id"],
                "class_plan_digest": readable[
                    "class_plan_digest"
                ],
                "member_plan_digest": readable[
                    "member_plan_digest"
                ],
                "engine": "cfr",
                "decompiler_sha256": "b" * 64,
                "source_tree_sha256": manifest[
                    "source_tree_sha256"
                ],
                "source_scope": "whole_archive",
                "project_source_prefixes": [],
                "selected_class_count": None,
                "selected_class_digest": None,
            }
            expected_id = (
                "SRCWS_"
                + hashlib.sha256(
                    json.dumps(
                        material,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest()[:20].upper()
            )

            self.assertEqual(
                manifest["workspace_id"],
                expected_id,
            )
            self.assertNotIn(
                "collision_transform_id",
                manifest,
            )
            self.assertNotIn(
                "base_readable_jar_sha256",
                manifest,
            )

    @patch("spk_recovery.source_workspace.run_decompiler")
    def test_procyon_normalization_is_bound_into_workspace(self, run):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = root / "readable.jar"
            with zipfile.ZipFile(jar, "w") as z:
                z.writestr("pkg/A.class", b"class-context")
            decompiler = root / "procyon.jar"
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
                    "package pkg;\n"
                    "class A\n"
                    "{\n"
                    "    void m(int n)\n"
                    "    {\n"
                    "        \"value=\" + n;\n"
                    "    }\n"
                    "}\n",
                    encoding="utf-8",
                )
                return {
                    "schema_version": 1,
                    "kind": "decompiler_result",
                    "engine": "procyon",
                    "input_sha256": _sha(jar.read_bytes()),
                    "decompiler_sha256": expected_decompiler_sha256,
                    "java_file_count": 1,
                    "output_directory": str(out_dir),
                    "stdout": "",
                    "stderr": "",
                }

            run.side_effect = fake_decompile
            manifest = build_source_workspace(
                _manifest(_sha(jar.read_bytes())),
                jar,
                decompiler,
                expected_decompiler_sha256="b" * 64,
                engine="procyon",
                out_dir=out,
            )

            self.assertTrue(
                manifest["normalization_id"].startswith("SRCNORM_")
            )
            self.assertEqual(
                manifest["normalization_summary"][
                    "discarded_string_expression_count"
                ],
                1,
            )
            self.assertTrue(
                (out / "source-normalization.json").is_file()
            )
            text = (out / "src" / "pkg" / "A.java").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                "final String recoveredDiscardedExpression_",
                text,
            )


if __name__ == "__main__":
    unittest.main()

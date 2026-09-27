from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.source_workspace_cli import main


class SourceWorkspaceCollisionCliTests(unittest.TestCase):
    @patch("spk_recovery.source_workspace_cli.build_source_workspace")
    def test_cli_loads_and_forwards_collision_transform_report(
        self,
        build,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            readable_manifest = root / "readable.json"
            readable_manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "kind": "readable_client_build_manifest",
                    }
                ),
                encoding="utf-8",
            )

            transform = {
                "schema_version": 1,
                "kind": "namespace_collision_bytecode_transform",
                "transform_id": "JNSREWRITE_1234567890ABCDEF1234",
                "plan_id": "JNSPLAN_1234567890ABCDEF1234",
                "collision_report_id": (
                    "JNSCOLLISION_1234567890ABCDEF12"
                ),
                "input_jar_sha256": "a" * 64,
                "output_jar_sha256": "b" * 64,
            }
            transform_path = root / "transform.json"
            transform_path.write_text(
                json.dumps(transform),
                encoding="utf-8",
            )

            build.return_value = {
                "workspace_id": "SRCWS_1234567890ABCDEF1234",
                "namespace_id": "SEMNS_1234567890ABCDEF1234",
                "engine": "procyon",
                "java_file_count": 1,
                "source_tree_sha256": "c" * 64,
                "collision_transform_id": transform["transform_id"],
                "collision_plan_id": transform["plan_id"],
                "base_readable_jar_sha256": "a" * 64,
            }

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = main(
                    [
                        str(readable_manifest),
                        str(root / "readable.jar"),
                        str(root / "decompiler.jar"),
                        "--decompiler-sha256",
                        "d" * 64,
                        "--engine",
                        "procyon",
                        "--collision-transform-report",
                        str(transform_path),
                        "--out-dir",
                        str(root / "out"),
                    ]
                )

            self.assertEqual(rc, 0)
            kwargs = build.call_args.kwargs
            self.assertEqual(
                kwargs["collision_transform_report"],
                transform,
            )

            text = stdout.getvalue()
            self.assertIn(
                "collision_transform_id="
                + transform["transform_id"],
                text,
            )
            self.assertIn(
                "collision_plan_id=" + transform["plan_id"],
                text,
            )


if __name__ == "__main__":
    unittest.main()

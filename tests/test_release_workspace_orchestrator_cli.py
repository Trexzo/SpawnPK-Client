from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery import release_workspace_orchestrator_cli


class ReleaseWorkspaceOrchestratorCliTests(unittest.TestCase):
    def test_cli_passes_existing_workspace_and_collision_plan(self):
        report = {
            "run_id": "RELEASE_RUN_TEST",
            "status": "complete",
            "ready_for_release": True,
            "terminal_stage": "release_manifest",
            "stage_ids": {
                "collision_plan_id": "COLLPLAN_TEST",
                "collision_transform_id": "COLLTRANS_TEST",
            },
        }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_jar = root / "client.jar"
            source_jar.write_bytes(b"jar")

            source_index = root / "source-index.json"
            source_index.write_text("{}\n", encoding="utf-8")

            class_lineage = root / "class-lineage.json"
            class_lineage.write_text(
                '{"schema_version":1,"kind":"class_lineage","builds":[],"logical_classes":[]}\n',
                encoding="utf-8",
            )
            member_lineage = root / "member-lineage.json"
            member_lineage.write_text(
                '{"schema_version":1,"kind":"member_lineage","members":[]}\n',
                encoding="utf-8",
            )

            recovered_manifest = root / "recovered.json"
            recovered_manifest.write_text(
                json.dumps(
                    {
                        "collision_transform_id": "COLLTRANS_TEST",
                        "collision_plan_id": "COLLPLAN_TEST",
                        "collision_report_id": "COLLREPORT_TEST",
                        "base_readable_jar_sha256": "b" * 64,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            source_root = root / "source"
            source_root.mkdir()
            plan = root / "private-plan.json"
            plan.write_text("{}\n", encoding="utf-8")

            args = [
                str(source_jar),
                str(source_index),
                str(class_lineage),
                str(member_lineage),
                str(recovered_manifest),
                str(source_root),
                str(plan),
                "--build-id",
                "v308",
                "--source-prefix",
                "rs/",
                "--private-diagnostic-report-out",
                str(root / "private-javac.json"),
                "--out-dir",
                str(root / "out"),
            ]

            output = io.StringIO()
            with (
                patch(
                    "spk_recovery.release_workspace_orchestrator_cli."
                    "load_lineage",
                    return_value={},
                ),
                patch(
                    "spk_recovery.release_workspace_orchestrator_cli."
                    "load_member_lineage",
                    return_value={},
                ),
                patch(
                    "spk_recovery.release_workspace_orchestrator_cli."
                    "build_existing_authority_release_from_workspace",
                    return_value=report,
                ) as mocked,
                contextlib.redirect_stdout(output),
            ):
                code = release_workspace_orchestrator_cli.main(args)

            self.assertEqual(code, 0)
            call = mocked.call_args
            self.assertEqual(call.args[4]["collision_plan_id"], "COLLPLAN_TEST")
            self.assertEqual(call.args[5], source_root)
            self.assertEqual(call.args[6], plan)
            self.assertEqual(
                call.kwargs["source_prefixes"],
                ["rs/"],
            )
            self.assertEqual(
                call.kwargs["private_diagnostic_report_out"],
                root / "private-javac.json",
            )

        text = output.getvalue()
        self.assertIn(
            "SPK_RECOVERY_RELEASE_BUILD_RECOVERED",
            text,
        )
        self.assertIn(
            "ready_for_release=true",
            text,
        )
        self.assertIn(
            "collision_plan_id=COLLPLAN_TEST",
            text,
        )
        self.assertIn(
            "collision_transform_id=COLLTRANS_TEST",
            text,
        )


if __name__ == "__main__":
    unittest.main()

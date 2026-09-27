from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery import clean_rebuild_cli


class CleanRebuildCliTests(unittest.TestCase):
    def test_private_collision_plan_path_is_passed_to_clean_rebuild(self):
        report = {
            "rebuild_id": "CLEANBUILD_COLLISION",
            "status": "complete",
            "source_scope": {"project_source_files": 1},
            "project_classes": {
                "expected_count": 1,
                "generated_count": 1,
                "binary_fallback_count": 0,
            },
            "compiler": {
                "diagnostic_classification": None,
            },
            "rebuilt_client": {
                "sha256": "a" * 64,
            },
            "compile_transport": {
                "mode": "collision_derived_remap",
                "collision_compile_id": "COLLDERIVEDCOMPILE_TEST",
                "collision_transform_id": "JNSREWRITE_TEST",
                "collision_plan_id": "JCOLLISIONPLAN_TEST",
                "collision_report_id": "JNSCOLLISION_TEST",
                "runtime_transformed_dependency_allowed": False,
            },
        }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            json_paths = []
            for index in range(4):
                path = root / f"{index}.json"
                path.write_text("{}\n", encoding="utf-8")
                json_paths.append(path)

            collision_plan = root / "private-collision-plan.json"
            collision_plan.write_text(
                '{"identifiers_included": true}\n',
                encoding="utf-8",
            )

            args = [
                str(json_paths[0]),
                str(json_paths[1]),
                str(json_paths[2]),
                str(root / "readable.jar"),
                str(json_paths[3]),
                str(root / "source"),
                "--private-collision-plan",
                str(collision_plan),
                "--out-dir",
                str(root / "out"),
            ]

            output = io.StringIO()
            with patch(
                "spk_recovery.clean_rebuild_cli.clean_project_rebuild",
                return_value=report,
            ) as mocked, contextlib.redirect_stdout(output):
                code = clean_rebuild_cli.main(args)

            self.assertEqual(code, 0)
            self.assertEqual(
                mocked.call_args.kwargs[
                    "private_collision_plan_path"
                ],
                collision_plan,
            )

        text = output.getvalue()
        self.assertIn(
            "compile_transport_mode=collision_derived_remap",
            text,
        )
        self.assertIn(
            "collision_compile_id=COLLDERIVEDCOMPILE_TEST",
            text,
        )
        self.assertIn(
            "collision_transform_id=JNSREWRITE_TEST",
            text,
        )
        self.assertIn(
            "collision_plan_id=JCOLLISIONPLAN_TEST",
            text,
        )
        self.assertIn(
            "collision_report_id=JNSCOLLISION_TEST",
            text,
        )
        self.assertIn(
            "runtime_transformed_dependency_allowed=False",
            text,
        )
        self.assertNotIn("namespace_compile_id=", text)
        self.assertNotIn("namespace_alias_plan_id=", text)

    def test_collision_transport_output_rejects_unknown_mode(self):
        report = {
            "rebuild_id": "CLEANBUILD_UNKNOWN",
            "status": "complete",
            "source_scope": {"project_source_files": 1},
            "project_classes": {
                "expected_count": 1,
                "generated_count": 1,
                "binary_fallback_count": 0,
            },
            "compiler": {
                "diagnostic_classification": None,
            },
            "rebuilt_client": {
                "sha256": "a" * 64,
            },
            "compile_transport": {
                "mode": "unexpected_transport",
            },
        }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            json_paths = []
            for index in range(4):
                path = root / f"{index}.json"
                path.write_text("{}\n", encoding="utf-8")
                json_paths.append(path)

            args = [
                str(json_paths[0]),
                str(json_paths[1]),
                str(json_paths[2]),
                str(root / "readable.jar"),
                str(json_paths[3]),
                str(root / "source"),
                "--out-dir",
                str(root / "out"),
            ]

            with patch(
                "spk_recovery.clean_rebuild_cli.clean_project_rebuild",
                return_value=report,
            ), self.assertRaisesRegex(
                ValueError,
                "unsupported compile transport mode",
            ):
                clean_rebuild_cli.main(args)

    def test_compile_failure_prints_only_redacted_diagnostic_summary(self):
        report = {
            "rebuild_id": "CLEANBUILD_TEST",
            "status": "compile_failed",
            "source_scope": {"project_source_files": 1048},
            "project_classes": {
                "expected_count": 1129,
                "generated_count": 0,
                "binary_fallback_count": 0,
            },
            "compiler": {
                "diagnostic_classification": {
                    "report_id": "JAVACDIAG_TEST",
                    "frontier_id": "JAVACFRONTIER_TEST",
                    "input_sha256": "a" * 64,
                    "identifiers_included": False,
                    "summary": {
                        "total_errors": 1288,
                        "affected_files": 110,
                        "categories": {
                            "cannot_find_symbol": 680,
                            "incompatible_types": 100,
                        },
                        "cannot_find_symbol": {
                            "count": 680,
                            "symbol_kinds": {
                                "method": 400,
                                "variable": 280,
                            },
                            "location_kinds": {
                                "class": 680,
                            },
                            "symbol_shapes": {
                                "method/arity_1": 400,
                                "variable": 280,
                            },
                            "symbol_clusters": [
                                {
                                    "symbol_id": "JSYM_TEST",
                                    "symbol_kind": "method",
                                    "symbol_shape": "method/arity_1",
                                    "count": 300,
                                }
                            ],
                            "location_clusters": [
                                {
                                    "location_id": "JLOC_TEST",
                                    "location_kind": "class",
                                    "count": 500,
                                }
                            ],
                        },
                        "clusters": [],
                    },
                }
            },
            "rebuilt_client": {"sha256": None},
        }

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            json_paths = []
            for index in range(5):
                path = root / f"{index}.json"
                path.write_text("{}\n", encoding="utf-8")
                json_paths.append(path)

            args = [
                str(json_paths[0]),
                str(json_paths[1]),
                str(json_paths[2]),
                str(root / "readable.jar"),
                str(json_paths[3]),
                str(root / "source"),
                "--out-dir",
                str(root / "out"),
            ]
            output = io.StringIO()
            with patch(
                "spk_recovery.clean_rebuild_cli.clean_project_rebuild",
                return_value=report,
            ), contextlib.redirect_stdout(output):
                code = clean_rebuild_cli.main(args)

        text = output.getvalue()
        self.assertEqual(code, 3)
        self.assertIn("javac_diagnostic_report_id=JAVACDIAG_TEST", text)
        self.assertIn("javac_frontier_id=JAVACFRONTIER_TEST", text)
        self.assertIn("javac_total_errors=1288", text)
        self.assertIn("javac_affected_files=110", text)
        self.assertIn("javac_cannot_find_symbol=680", text)
        self.assertIn(
            'javac_cannot_find_symbol_kinds_json={"method":400,"variable":280}',
            text,
        )
        self.assertIn(
            '"symbol_id":"JSYM_TEST"',
            text,
        )
        self.assertIn(
            '"location_id":"JLOC_TEST"',
            text,
        )
        self.assertNotIn("source_path", text)
        self.assertNotIn("symbol:", text)
        self.assertNotIn("location:", text)


if __name__ == "__main__":
    unittest.main()

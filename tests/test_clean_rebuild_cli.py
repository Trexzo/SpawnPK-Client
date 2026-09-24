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
        self.assertIn("javac_total_errors=1288", text)
        self.assertIn("javac_affected_files=110", text)
        self.assertIn("javac_cannot_find_symbol=680", text)
        self.assertIn(
            'javac_cannot_find_symbol_kinds_json={"method":400,"variable":280}',
            text,
        )
        self.assertNotIn("source_path", text)
        self.assertNotIn("symbol:", text)
        self.assertNotIn("location:", text)


if __name__ == "__main__":
    unittest.main()

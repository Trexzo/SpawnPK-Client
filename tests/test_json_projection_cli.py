from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.json_projection_cli import main, project


class JsonProjectionTests(unittest.TestCase):
    def test_case_distinct_source_keys_are_preserved(self):
        document = {
            "payload": {
                "D": 1,
                "d": 2,
            },
            "status": "complete",
        }

        result = project(
            document,
            required=[
                ("upper", "/payload/D"),
                ("lower", "/payload/d"),
                ("status", "/status"),
            ],
            optional=[],
        )

        self.assertEqual(
            result,
            {
                "upper": 1,
                "lower": 2,
                "status": "complete",
            },
        )

    def test_aliases_colliding_case_insensitively_are_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "collide case-insensitively",
        ):
            project(
                {"a": 1, "b": 2},
                required=[
                    ("Value", "/a"),
                    ("value", "/b"),
                ],
                optional=[],
            )

    def test_optional_missing_pointer_projects_null(self):
        result = project(
            {"status": "complete"},
            required=[("status", "/status")],
            optional=[("frontier", "/compiler/frontier")],
        )

        self.assertEqual(result["status"], "complete")
        self.assertIsNone(result["frontier"])

    def test_cli_projects_case_distinct_nested_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "authority.json"
            path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "D": 7,
                            "d": 8,
                        },
                        "verified": True,
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [
                        str(path),
                        "--field",
                        "upper=/summary/D",
                        "--field",
                        "lower=/summary/d",
                        "--field",
                        "verified=/verified",
                    ]
                )

            self.assertEqual(code, 0, stderr.getvalue())
            self.assertEqual(
                json.loads(stdout.getvalue()),
                {
                    "lower": 8,
                    "upper": 7,
                    "verified": True,
                },
            )

    def test_cli_rejects_exact_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "duplicate.json"
            path.write_text(
                '{"value":1,"value":2}',
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [
                        str(path),
                        "--field",
                        "value=/value",
                    ]
                )

            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn(
                "duplicate JSON key",
                stderr.getvalue(),
            )

    def test_cli_refuses_missing_required_pointer(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "missing.json"
            path.write_text(
                '{"status":"complete"}',
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main(
                    [
                        str(path),
                        "--field",
                        "frontier=/compiler/frontier",
                    ]
                )

            self.assertEqual(code, 2)
            self.assertIn(
                "required JSON Pointer is missing",
                stderr.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()

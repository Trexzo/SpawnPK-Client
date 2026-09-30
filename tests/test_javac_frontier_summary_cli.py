from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.javac_frontier_summary_cli import main, summarize


def _report() -> dict:
    rows = [
        {
            "category": "cannot_find_symbol",
            "source_path": r"C:\\src\\rs\\a\\k.java",
            "symbol_kind": "variable",
            "symbol": "x",
        },
        {
            "category": "cannot_find_symbol",
            "source_path": r"C:\\src\\rs\\a\\k.java",
            "symbol_kind": "variable",
            "symbol": "x",
        },
        {
            "category": "non_static_from_static_context",
            "source_path": r"C:\\src\\rs\\A\\k.java",
            "symbol_kind": None,
            "symbol": None,
        },
        {
            "category": "cannot_be_dereferenced",
            "source_path": r"C:\\src\\rs\\u\\g.java",
            "symbol_kind": None,
            "symbol": None,
        },
    ]
    return {
        "schema_version": 1,
        "kind": "javac_diagnostic_classification_report",
        "frontier_id": "JAVACFRONTIER_TEST",
        "identifiers_included": True,
        "summary": {
            "total_errors": 4,
            "affected_files": 3,
            "cannot_find_symbol": {
                "count": 2,
            },
        },
        "diagnostics": rows,
    }


class JavacFrontierSummaryTests(unittest.TestCase):
    def test_preserves_case_distinct_source_paths(self):
        lines = summarize(_report(), top=20)
        text = "\n".join(lines)

        self.assertIn(
            "    2  C:/src/rs/a/k.java",
            text,
        )
        self.assertIn(
            "    1  C:/src/rs/A/k.java",
            text,
        )

    def test_prints_deterministic_category_and_symbol_counts(self):
        lines = summarize(_report(), top=20)
        text = "\n".join(lines)

        self.assertIn(
            "    2  cannot_find_symbol",
            text,
        )
        self.assertIn(
            "    2  variable    x",
            text,
        )
        self.assertIn(
            "JAVAC_FRONTIER_ID=JAVACFRONTIER_TEST",
            text,
        )

    def test_refuses_public_redacted_report(self):
        report = _report()
        report["identifiers_included"] = False

        with self.assertRaisesRegex(
            ValueError,
            "must include identifiers",
        ):
            summarize(report, top=20)

    def test_cli_top_limit(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "private.json"
            path.write_text(
                json.dumps(_report()),
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
                        "--top",
                        "1",
                    ]
                )

            self.assertEqual(code, 0, stderr.getvalue())
            self.assertIn(
                "=== TOP 1 ERROR FILES ===",
                stdout.getvalue(),
            )

    def test_cli_rejects_invalid_top(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "private.json"
            path.write_text(
                json.dumps(_report()),
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
                        "--top",
                        "0",
                    ]
                )

            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn(
                "--top must be between 1 and 100",
                stderr.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.javac_frontier_summary_cli import (
    focus_diagnostics,
    main,
    summarize,
)


def _report() -> dict:
    rows = [
        {
            "category": "cannot_find_symbol",
            "source_path": r"C:\src\rs\a\k.java",
            "symbol_kind": "variable",
            "symbol": "x",
        },
        {
            "category": "cannot_find_symbol",
            "source_path": r"C:\src\rs\a\k.java",
            "symbol_kind": "variable",
            "symbol": "x",
        },
        {
            "category": "non_static_from_static_context",
            "source_path": r"C:\src\rs\A\k.java",
            "symbol_kind": None,
            "symbol": None,
        },
        {
            "category": "cannot_be_dereferenced",
            "source_path": r"C:\src\rs\u\g.java",
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

    def test_focus_diagnostics_preserves_top_file_case_and_rows(self):
        report = _report()
        report["diagnostics"][0]["line"] = 12
        report["diagnostics"][0]["message"] = "cannot find symbol"
        report["diagnostics"][0]["location_kind"] = "class"
        report["diagnostics"][0]["location"] = "C:/src/rs/a/k.java"
        report["diagnostics"][1]["line"] = 14
        report["diagnostics"][1]["message"] = "cannot find symbol"

        text = "\n".join(
            focus_diagnostics(
                report,
                focus_files=1,
            )
        )

        self.assertIn(
            "FOCUSED JAVAC DIAGNOSTICS: C:/src/rs/a/k.java",
            text,
        )
        self.assertIn("FOCUSED_TOTAL_ERRORS=2", text)
        self.assertIn("line=12", text)
        self.assertIn("symbol_kind=variable", text)
        self.assertIn("symbol=x", text)
        self.assertNotIn(
            "FOCUSED JAVAC DIAGNOSTICS: C:/src/rs/A/k.java",
            text,
        )

    def test_focus_diagnostics_zero_is_noop(self):
        self.assertEqual(
            focus_diagnostics(_report(), focus_files=0),
            [],
        )

    def test_source_m1_wrapper_prints_private_frontier_summary(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        text = script.read_text(encoding="utf-8")

        self.assertIn(
            "spk_recovery.javac_frontier_summary_cli",
            text,
        )
        self.assertIn("--top 20", text)
        self.assertIn("--focus-files 1", text)
        self.assertIn("private_javac_summary_failed=", text)
        self.assertIn("exit 3", text)
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

    def test_cli_rejects_invalid_focus_file_count(self):
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
                        "--focus-files",
                        "21",
                    ]
                )

            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn(
                "--focus-files must be between 0 and 20",
                stderr.getvalue(),
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

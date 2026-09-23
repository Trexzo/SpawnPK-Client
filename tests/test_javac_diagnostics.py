from __future__ import annotations

import hashlib
import unittest

from spk_recovery.javac_diagnostics import classify_javac_diagnostics


class JavacDiagnosticClassificationTests(unittest.TestCase):
    def test_classifies_redacted_cannot_find_symbol_shapes(self):
        raw = (
            "/tmp/src/rs/a/A.java:10: error: cannot find symbol\n"
            "        foo(a, b);\n"
            "        ^\n"
            "  symbol:   method foo(int,java.lang.String)\n"
            "  location: class A\n"
            "/tmp/src/rs/a/B.java:20: error: cannot find symbol\n"
            "  symbol:   variable bar\n"
            "  location: class B\n"
            "/tmp/src/rs/a/C.java:30: error: cannot find symbol\n"
            "  symbol:   class Missing\n"
            "  location: package rs.a\n"
        )

        report = classify_javac_diagnostics(raw)

        self.assertEqual(report["summary"]["total_errors"], 3)
        self.assertEqual(report["summary"]["affected_files"], 3)
        cannot = report["summary"]["cannot_find_symbol"]
        self.assertEqual(cannot["count"], 3)
        self.assertEqual(
            cannot["symbol_kinds"],
            {"class": 1, "method": 1, "variable": 1},
        )
        self.assertEqual(
            cannot["symbol_shapes"],
            {"class": 1, "method/arity_2": 1, "variable": 1},
        )
        for row in report["diagnostics"]:
            self.assertNotIn("source_path", row)
            self.assertNotIn("symbol", row)
            self.assertNotIn("location", row)
            self.assertTrue(row["file_id"].startswith("JFILE_"))

    def test_windows_paths_and_other_categories(self):
        raw = (
            "C:\\work\\src\\rs\\A.java:42: error: incompatible types: int cannot be converted to String\n"
            "C:\\work\\src\\rs\\B.java:8: error: package missing.pkg does not exist\n"
            "C:\\work\\src\\rs\\C.java:9: error: int cannot be dereferenced\n"
        )
        report = classify_javac_diagnostics(raw)

        self.assertEqual(report["summary"]["total_errors"], 3)
        self.assertEqual(
            report["summary"]["categories"],
            {
                "cannot_be_dereferenced": 1,
                "incompatible_types": 1,
                "package_does_not_exist": 1,
            },
        )

    def test_identifier_opt_in_is_explicit(self):
        raw = (
            "/x/A.java:1: error: cannot find symbol\n"
            "  symbol:   method secret(java.util.List<java.lang.String>,int[])\n"
            "  location: class Hidden\n"
        )
        report = classify_javac_diagnostics(
            raw,
            include_identifiers=True,
        )
        row = report["diagnostics"][0]
        self.assertEqual(row["source_path"], "/x/A.java")
        self.assertIn("secret", row["symbol"])
        self.assertEqual(row["location"], "Hidden")
        self.assertEqual(row["symbol_shape"], "method/arity_2")

    def test_report_is_deterministic_and_sha_bound(self):
        raw = (
            "/x/A.java:1: error: cannot find symbol\n"
            "  symbol:   variable a\n"
            "  location: class A\n"
        )
        first = classify_javac_diagnostics(raw)
        second = classify_javac_diagnostics(raw)
        changed = classify_javac_diagnostics(raw + "\n")

        self.assertEqual(first["report_id"], second["report_id"])
        self.assertEqual(
            first["input_sha256"],
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(first["input_sha256"], changed["input_sha256"])
        self.assertNotEqual(first["report_id"], changed["report_id"])

    def test_ansi_and_crlf_are_parseable_but_raw_sha_is_exact(self):
        raw = (
            "\x1b[31mC:\\src\\A.java:7: error: cannot find symbol\x1b[0m\r\n"
            "  symbol:   constructor A(int)\r\n"
            "  location: class A\r\n"
        )
        report = classify_javac_diagnostics(raw)

        self.assertEqual(report["summary"]["total_errors"], 1)
        self.assertEqual(
            report["summary"]["cannot_find_symbol"]["symbol_shapes"],
            {"constructor/arity_1": 1},
        )
        self.assertEqual(
            report["input_sha256"],
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()

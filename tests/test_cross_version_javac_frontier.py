from __future__ import annotations

import hashlib
import unittest

from spk_recovery.cross_version_javac_frontier import (
    CrossVersionJavacFrontierError,
    compare_javac_frontiers,
)


def report(frontier: str, rows: list[dict]):
    input_sha256 = hashlib.sha256(frontier.encode("utf-8")).hexdigest()
    return {
        "schema_version": 1,
        "kind": "javac_diagnostic_classification_report",
        "report_id": (
            "JAVACDIAG_"
            + hashlib.sha256((frontier + "-report").encode("utf-8"))
            .hexdigest()[:20]
            .upper()
        ),
        "frontier_id": frontier,
        "input_sha256": input_sha256,
        "identifiers_included": True,
        "diagnostics": rows,
    }


class CrossVersionJavacFrontierTests(unittest.TestCase):
    def test_multiset_overlap_and_redaction(self):
        old = report(
            "JAVACFRONTIER_OLD",
            [
                {
                    "source_path": r"C:\old\src\rs\A.java",
                    "category": "cannot_find_symbol",
                    "message": "cannot find symbol",
                    "symbol_kind": "variable",
                    "symbol": "secret",
                    "location_kind": "class",
                    "location": "A",
                    "symbol_shape": "variable",
                },
                {
                    "source_path": r"C:\old\src\rs\A.java",
                    "category": "cannot_find_symbol",
                    "message": "cannot find symbol",
                    "symbol_kind": "variable",
                    "symbol": "secret",
                    "location_kind": "class",
                    "location": "A",
                    "symbol_shape": "variable",
                },
                {
                    "source_path": r"C:\old\src\rs\B.java",
                    "category": "incompatible_types",
                    "message": (
                        "incompatible types: Object cannot be converted "
                        "to String"
                    ),
                    "symbol_kind": None,
                    "symbol": None,
                    "location_kind": None,
                    "location": None,
                    "symbol_shape": "none",
                },
            ],
        )
        new = report(
            "JAVACFRONTIER_NEW",
            [
                {
                    "source_path": "/new/work/src/rs/A.java",
                    "category": "cannot_find_symbol",
                    "message": "cannot find symbol",
                    "symbol_kind": "variable",
                    "symbol": "secret",
                    "location_kind": "class",
                    "location": "A",
                    "symbol_shape": "variable",
                },
                {
                    "source_path": "/new/work/src/rs/C.java",
                    "category": "private_access",
                    "message": "x has private access in C",
                    "symbol_kind": None,
                    "symbol": None,
                    "location_kind": None,
                    "location": None,
                    "symbol_shape": "none",
                },
            ],
        )
        value = compare_javac_frontiers(old, new)
        self.assertEqual(value["summary"]["old_total_errors"], 3)
        self.assertEqual(value["summary"]["new_total_errors"], 2)
        self.assertEqual(value["summary"]["shared_errors"], 1)
        self.assertEqual(value["summary"]["old_only_errors"], 2)
        self.assertEqual(value["summary"]["new_only_errors"], 1)
        self.assertEqual(value["summary"]["shared_affected_files"], 1)
        rendered = str(value)
        self.assertNotIn("secret", rendered)
        self.assertNotIn("rs/A.java", rendered)
        self.assertTrue(
            value["report_id"].startswith("XJAVACFRONTIER_")
        )

    def test_identifier_opt_in_exposes_private_context(self):
        row = {
            "source_path": "/x/src/rs/A.java",
            "category": "cannot_find_symbol",
            "message": "cannot find symbol",
            "symbol_kind": "variable",
            "symbol": "hidden",
            "location_kind": "class",
            "location": "A",
            "symbol_shape": "variable",
        }
        value = compare_javac_frontiers(
            report("JAVACFRONTIER_A", [row]),
            report("JAVACFRONTIER_B", [row]),
            include_identifiers=True,
        )
        family = value["families"][0]
        self.assertEqual(family["source_path"], "rs/A.java")
        self.assertEqual(family["symbol"], "hidden")
        self.assertEqual(value["summary"]["shared_errors"], 1)
        self.assertTrue(value["summary"]["exact_frontier_equal"])

    def test_report_id_does_not_depend_on_identifier_exposure(self):
        row = {
            "source_path": "/x/src/rs/A.java",
            "category": "other",
            "message": "some private message",
            "symbol_kind": None,
            "symbol": None,
            "location_kind": None,
            "location": None,
            "symbol_shape": "none",
        }
        old = report("JAVACFRONTIER_A", [row])
        new = report("JAVACFRONTIER_B", [row])
        redacted = compare_javac_frontiers(old, new)
        private = compare_javac_frontiers(
            old,
            new,
            include_identifiers=True,
        )
        self.assertEqual(redacted["report_id"], private["report_id"])

    def test_rejects_public_redacted_reports(self):
        value = report("JAVACFRONTIER_A", [])
        value["identifiers_included"] = False
        with self.assertRaisesRegex(
            CrossVersionJavacFrontierError,
            "requires a private diagnostic report",
        ):
            compare_javac_frontiers(
                value,
                report("JAVACFRONTIER_B", []),
            )

    def test_requires_src_boundary(self):
        row = {
            "source_path": "/x/A.java",
            "category": "other",
            "message": "x",
        }
        with self.assertRaisesRegex(
            CrossVersionJavacFrontierError,
            "src boundary",
        ):
            compare_javac_frontiers(
                report("JAVACFRONTIER_A", [row]),
                report("JAVACFRONTIER_B", []),
            )

    def test_output_binds_exact_diagnostic_reports(self):
        row = {
            "source_path": "/x/src/rs/A.java",
            "category": "other",
            "message": "some private message",
            "symbol_kind": None,
            "symbol": None,
            "location_kind": None,
            "location": None,
            "symbol_shape": "none",
        }
        old = report("JAVACFRONTIER_A", [row])
        new = report("JAVACFRONTIER_B", [row])

        first = compare_javac_frontiers(old, new)
        self.assertEqual(
            first["old_diagnostic_report_id"],
            old["report_id"],
        )
        self.assertEqual(
            first["new_diagnostic_report_id"],
            new["report_id"],
        )
        self.assertEqual(
            first["old_diagnostic_input_sha256"],
            old["input_sha256"],
        )
        self.assertEqual(
            first["new_diagnostic_input_sha256"],
            new["input_sha256"],
        )

        changed = dict(old)
        changed["input_sha256"] = "f" * 64
        changed["report_id"] = "JAVACDIAG_" + "F" * 20
        second = compare_javac_frontiers(changed, new)
        self.assertNotEqual(first["report_id"], second["report_id"])

    def test_rejects_missing_diagnostic_provenance(self):
        value = report("JAVACFRONTIER_A", [])
        del value["input_sha256"]
        with self.assertRaisesRegex(
            CrossVersionJavacFrontierError,
            "input SHA-256",
        ):
            compare_javac_frontiers(
                value,
                report("JAVACFRONTIER_B", []),
            )


if __name__ == "__main__":
    unittest.main()

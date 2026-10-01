from __future__ import annotations

import copy
import unittest

from spk_recovery.javac_build_binding import (
    JavacBuildBindingError,
    build_javac_build_binding,
)
from spk_recovery.javac_diagnostics import (
    classify_javac_diagnostics,
)


AUTHORITY = "a" * 64
TOOLING = "1" * 40


def private_diagnostic():
    return classify_javac_diagnostics(
        (
            "/x/src/rs/A.java:7: error: cannot find symbol\n"
            "  symbol:   variable hidden\n"
            "  location: class A\n"
        ),
        include_identifiers=True,
    )


def clean_rebuild(diagnostic):
    return {
        "schema_version": 1,
        "kind": "clean_project_rebuild_report",
        "rebuild_id": "CLEANBUILD_" + "A" * 20,
        "status": "compile_failed",
        "workspace_id": "SRCWS_TEST",
        "build_id": "v307",
        "source_authority_sha256": AUTHORITY,
        "source_tree_sha256": "b" * 64,
        "compiler": {
            "diagnostic_classification": {
                "report_id": diagnostic["report_id"],
                "frontier_id": diagnostic["frontier_id"],
                "input_sha256": diagnostic["input_sha256"],
                "summary": diagnostic["summary"],
                "identifiers_included": False,
            }
        },
        "project_classes": {
            "binary_fallback_count": 0,
        },
        "clean_project_build": False,
    }


class JavacBuildBindingTests(unittest.TestCase):
    def test_binds_exact_private_diagnostic_to_clean_rebuild(self):
        diagnostic = private_diagnostic()
        value = build_javac_build_binding(
            diagnostic,
            clean_rebuild(diagnostic),
            expected_build_id="v307",
            expected_authority_sha256=AUTHORITY,
            tooling_commit=TOOLING,
        )

        self.assertEqual(value["tooling_commit"], TOOLING)
        self.assertEqual(value["build_id"], "v307")
        self.assertEqual(
            value["diagnostic_report_id"],
            diagnostic["report_id"],
        )
        self.assertEqual(
            value["frontier_id"],
            diagnostic["frontier_id"],
        )
        self.assertEqual(value["project_binary_fallback_count"], 0)
        self.assertFalse(value["identifiers_included"])
        self.assertTrue(value["binding_id"].startswith("JAVACBIND_"))
        self.assertNotIn("hidden", str(value))

    def test_rejects_wrong_build_or_authority(self):
        diagnostic = private_diagnostic()
        rebuild = clean_rebuild(diagnostic)

        with self.assertRaisesRegex(
            JavacBuildBindingError,
            "build ID mismatch",
        ):
            build_javac_build_binding(
                diagnostic,
                rebuild,
                expected_build_id="v308",
                expected_authority_sha256=AUTHORITY,
                tooling_commit=TOOLING,
            )

        with self.assertRaisesRegex(
            JavacBuildBindingError,
            "source authority SHA-256 mismatch",
        ):
            build_javac_build_binding(
                diagnostic,
                rebuild,
                expected_build_id="v307",
                expected_authority_sha256="c" * 64,
                tooling_commit=TOOLING,
            )

    def test_rejects_diagnostic_authority_drift(self):
        diagnostic = private_diagnostic()
        rebuild = clean_rebuild(diagnostic)
        rebuild["compiler"]["diagnostic_classification"][
            "frontier_id"
        ] = "JAVACFRONTIER_" + "F" * 20

        with self.assertRaisesRegex(
            JavacBuildBindingError,
            "diagnostic authority mismatch: frontier_id",
        ):
            build_javac_build_binding(
                diagnostic,
                rebuild,
                expected_build_id="v307",
                expected_authority_sha256=AUTHORITY,
                tooling_commit=TOOLING,
            )

    def test_rejects_summary_drift(self):
        diagnostic = private_diagnostic()
        rebuild = clean_rebuild(diagnostic)
        rebuild["compiler"]["diagnostic_classification"]["summary"] = {
            "total_errors": 999
        }

        with self.assertRaisesRegex(
            JavacBuildBindingError,
            "diagnostic authority mismatch: summary",
        ):
            build_javac_build_binding(
                diagnostic,
                rebuild,
                expected_build_id="v307",
                expected_authority_sha256=AUTHORITY,
                tooling_commit=TOOLING,
            )

    def test_rejects_project_binary_fallback(self):
        diagnostic = private_diagnostic()
        rebuild = clean_rebuild(diagnostic)
        rebuild["project_classes"]["binary_fallback_count"] = 1

        with self.assertRaisesRegex(
            JavacBuildBindingError,
            "project binary fallback",
        ):
            build_javac_build_binding(
                diagnostic,
                rebuild,
                expected_build_id="v307",
                expected_authority_sha256=AUTHORITY,
                tooling_commit=TOOLING,
            )


    def test_rejects_boolean_fallback_and_missing_summary(self):
        diagnostic = private_diagnostic()
        rebuild = clean_rebuild(diagnostic)
        rebuild["project_classes"]["binary_fallback_count"] = False

        with self.assertRaisesRegex(
            JavacBuildBindingError,
            "project binary fallback",
        ):
            build_javac_build_binding(
                diagnostic,
                rebuild,
                expected_build_id="v307",
                expected_authority_sha256=AUTHORITY,
                tooling_commit=TOOLING,
            )

        diagnostic = private_diagnostic()
        del diagnostic["summary"]
        rebuild = clean_rebuild(private_diagnostic())

        with self.assertRaisesRegex(
            JavacBuildBindingError,
            "lacks aggregate summary",
        ):
            build_javac_build_binding(
                diagnostic,
                rebuild,
                expected_build_id="v307",
                expected_authority_sha256=AUTHORITY,
                tooling_commit=TOOLING,
            )

    def test_rejects_invalid_tooling_commit(self):
        diagnostic = private_diagnostic()
        with self.assertRaisesRegex(
            JavacBuildBindingError,
            "tooling commit must be lowercase 40-hex",
        ):
            build_javac_build_binding(
                diagnostic,
                clean_rebuild(diagnostic),
                expected_build_id="v307",
                expected_authority_sha256=AUTHORITY,
                tooling_commit="not-a-commit",
            )

    def test_binding_identity_changes_with_tooling_commit(self):
        diagnostic = private_diagnostic()
        rebuild = clean_rebuild(diagnostic)
        first = build_javac_build_binding(
            diagnostic,
            rebuild,
            expected_build_id="v307",
            expected_authority_sha256=AUTHORITY,
            tooling_commit="1" * 40,
        )
        second = build_javac_build_binding(
            diagnostic,
            rebuild,
            expected_build_id="v307",
            expected_authority_sha256=AUTHORITY,
            tooling_commit="2" * 40,
        )
        self.assertNotEqual(first["binding_id"], second["binding_id"])

    def test_binding_identity_changes_with_workspace(self):
        diagnostic = private_diagnostic()
        first_rebuild = clean_rebuild(diagnostic)
        second_rebuild = copy.deepcopy(first_rebuild)
        second_rebuild["workspace_id"] = "SRCWS_OTHER"

        first = build_javac_build_binding(
            diagnostic,
            first_rebuild,
            expected_build_id="v307",
            expected_authority_sha256=AUTHORITY,
            tooling_commit=TOOLING,
        )
        second = build_javac_build_binding(
            diagnostic,
            second_rebuild,
            expected_build_id="v307",
            expected_authority_sha256=AUTHORITY,
            tooling_commit=TOOLING,
        )
        self.assertNotEqual(first["binding_id"], second["binding_id"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from spk_recovery.source_normalization_summary_cli import (
    main,
    summarize,
)


def _report() -> dict:
    actions = [
        {
            "kind": (
                "shadowed_same_package_static_field_owner_type_context"
            ),
            "source_path": "rs/u/g.java",
            "method_name": "a",
            "method_descriptor": "(Lrs/u/g;F)F",
            "same_package_owners": ["rs/u/i"],
            "replacement_count": 2,
        },
        {
            "kind": (
                "shadowed_same_package_static_field_owner_type_context"
            ),
            "source_path": "rs/u/g.java",
            "method_name": "b",
            "method_descriptor": "(Lrs/u/g;[F[F)V",
            "same_package_owners": ["rs/u/f"],
            "replacement_count": 1,
        },
        {
            "kind": (
                "shadowed_same_package_static_field_owner_type_context"
            ),
            "source_path": "rs/A/g.java",
            "method_name": "a",
            "method_descriptor": "()V",
            "same_package_owners": ["rs/A/f"],
            "replacement_count": 1,
        },
        {
            "kind": "discarded_string_expression_capture",
            "source_path": "rs/Client.java",
        },
    ]
    return {
        "schema_version": 1,
        "kind": "procyon_source_normalization_report",
        "normalization_id": "SRCNORM_TEST",
        "summary": {
            "shadowed_same_package_static_field_method_count": 3,
            "shadowed_same_package_static_field_reference_count": 4,
        },
        "actions": actions,
    }


class SourceNormalizationSummaryTests(unittest.TestCase):
    def test_summarizes_per_source_actions_deterministically(self):
        text = "\n".join(summarize(_report(), top=10))

        self.assertIn(
            "SOURCE_NORMALIZATION_ID=SRCNORM_TEST",
            text,
        )
        self.assertIn(
            "SAME_PACKAGE_SHADOW_METHODS=3",
            text,
        )
        self.assertIn(
            "SAME_PACKAGE_SHADOW_REFERENCES=4",
            text,
        )
        self.assertIn(
            "SOURCE rs/u/g.java | methods=2 | references=3",
            text,
        )
        self.assertIn(
            "a(Lrs/u/g;F)F | references=2 | owners=rs/u/i",
            text,
        )
        self.assertIn(
            "b(Lrs/u/g;[F[F)V | references=1 | owners=rs/u/f",
            text,
        )

    def test_preserves_case_distinct_source_paths(self):
        text = "\n".join(summarize(_report(), top=10))

        self.assertIn(
            "SOURCE rs/u/g.java | methods=2 | references=3",
            text,
        )
        self.assertIn(
            "SOURCE rs/A/g.java | methods=1 | references=1",
            text,
        )

    def test_refuses_empty_same_package_owner_proof(self):
        report = _report()
        report["actions"][0]["same_package_owners"] = []

        with self.assertRaisesRegex(
            ValueError,
            "same_package_owners must be non-empty strings",
        ):
            summarize(report, top=10)

    def test_refuses_summary_action_count_mismatch(self):
        report = _report()
        report["summary"][
            "shadowed_same_package_static_field_reference_count"
        ] = 99

        with self.assertRaisesRegex(
            ValueError,
            "same-package reference count mismatch",
        ):
            summarize(report, top=10)

    def test_summarizes_new_frontier_families_by_source(self):
        report = _report()
        report["actions"] += [
            {
                "kind": "undeclared_linkedhashmap_cast_placeholder_wildcard",
                "source_path": "rs/gui/b/d.java",
                "method_name": "a",
                "method_descriptor": "(Ljava/lang/String;)V",
                "placeholder_counts": {"K": 12, "V": 4},
                "member_counts": {"get": 12, "keySet": 4},
                "replacement_count": 16,
            },
            {
                "kind": "shadowed_nested_static_field_owner_type_context",
                "source_path": "rs/a/a/a.java",
                "method_name": "d",
                "method_descriptor": "(I)V",
                "nested_owners": ["rs/a/a/a$b"],
                "replacement_count": 17,
            },
            {
                "kind": "primitive_scope_shadowed_self_static_field_owner_qualification",
                "source_path": "rs/k/i.java",
                "method_name": "a",
                "method_descriptor": "(I)V",
                "qualified_owner": "rs/k/i",
                "replacement_count": 27,
            },
            {
                "kind": "primitive_shadowed_instance_field_receiver_qualification",
                "source_path": "rs/k/i.java",
                "method_name": "a",
                "method_descriptor": "(I)V",
                "receiver_field_name": "h",
                "receiver_type_owner": "rs/a/h",
                "replacement_count": 6,
            },
            {
                "kind": "shadowed_imported_static_method_owner_qualification",
                "source_path": "rs/k/i.java",
                "method_name": "a",
                "method_descriptor": "(I)V",
                "simple_owner": "b",
                "imported_owner": "rs/k/c/b",
                "replacement_count": 2,
            },
            {
                "kind": "invokedynamic_helper_return_cast",
                "source_path": "rs/Client.java",
                "method_name": "a",
                "method_descriptor": "(Ljava/lang/Object;)Ljava/lang/String;",
                "cast_type": "java.lang.String",
                "replacement_count": 17,
            },
            {
                "kind": "shadowed_same_package_static_method_owner_qualification",
                "source_path": "rs/l/h.java",
                "method_name": "a",
                "method_descriptor": "(Ljava/lang/String;I)V",
                "simple_owner": "s",
                "same_package_owner": "rs/l/s",
                "replacement_count": 21,
            },
            {
                "kind": "scoped_same_package_static_field_owner_qualification",
                "source_path": "rs/a/a/a.java",
                "method_name": "a",
                "method_descriptor": "(Lrs/a/a/Recovered_CLIENT_CLASS_000050;)V",
                "simple_owner": "b",
                "same_package_owner": "rs/a/a/b",
                "replacement_count": 17,
            },
        ]
        report["summary"].update({
            "undeclared_linkedhashmap_cast_placeholder_method_count": 1,
            "undeclared_linkedhashmap_cast_placeholder_reference_count": 16,
            "shadowed_nested_static_field_method_count": 1,
            "shadowed_nested_static_field_reference_count": 17,
            "primitive_scope_shadowed_self_static_field_method_count": 1,
            "primitive_scope_shadowed_self_static_field_reference_count": 27,
            "primitive_shadowed_instance_receiver_method_count": 1,
            "primitive_shadowed_instance_receiver_reference_count": 6,
            "shadowed_imported_static_method_method_count": 1,
            "shadowed_imported_static_method_reference_count": 2,
            "invokedynamic_helper_return_cast_method_count": 1,
            "invokedynamic_helper_return_cast_reference_count": 17,
            "shadowed_same_package_static_method_method_count": 1,
            "shadowed_same_package_static_method_reference_count": 21,
            "scoped_same_package_static_field_method_count": 1,
            "scoped_same_package_static_field_reference_count": 17,
        })

        text = "\n".join(summarize(report, top=10))

        self.assertIn("LINKEDHASHMAP_PLACEHOLDER_REFERENCES=16", text)
        self.assertIn(
            "a(Ljava/lang/String;)V | references=16 | "
            "placeholders=K:12,V:4 | members=get:12,keySet:4",
            text,
        )
        self.assertIn("NESTED_STATIC_FIELD_SHADOW_REFERENCES=17", text)
        self.assertIn(
            "d(I)V | references=17 | owners=rs/a/a/a$b",
            text,
        )
        self.assertIn("PRIMITIVE_SCOPE_SELF_SHADOW_REFERENCES=27", text)
        self.assertIn("PRIMITIVE_INSTANCE_RECEIVER_REFERENCES=6", text)
        self.assertIn("IMPORTED_STATIC_METHOD_SHADOW_REFERENCES=2", text)
        self.assertIn(
            "INVOKEDYNAMIC_HELPER_RETURN_CAST_REFERENCES=17",
            text,
        )
        self.assertIn(
            "SAME_PACKAGE_STATIC_METHOD_SHADOW_REFERENCES=21",
            text,
        )
        self.assertIn(
            "SCOPED_SAME_PACKAGE_STATIC_FIELD_REFERENCES=17",
            text,
        )
        self.assertIn(
            "a(I)V | references=27 | owner=rs/k/i",
            text,
        )
        self.assertIn(
            "a(I)V | references=6 | field=h | owner=rs/a/h",
            text,
        )
        self.assertIn(
            "a(I)V | references=2 | simple=b | owner=rs/k/c/b",
            text,
        )
        self.assertIn(
            "a(Ljava/lang/Object;)Ljava/lang/String; | "
            "references=17 | cast=java.lang.String",
            text,
        )
        self.assertIn(
            "a(Ljava/lang/String;I)V | references=21 | "
            "simple=s | owner=rs/l/s",
            text,
        )
        self.assertIn(
            "a(Lrs/a/a/Recovered_CLIENT_CLASS_000050;)V | "
            "references=17 | simple=b | owner=rs/a/a/b",
            text,
        )

    def test_new_family_summary_mismatch_is_rejected(self):
        report = _report()
        report["actions"].append(
            {
                "kind": "shadowed_imported_static_method_owner_qualification",
                "source_path": "rs/k/i.java",
                "method_name": "a",
                "method_descriptor": "()V",
                "simple_owner": "b",
                "imported_owner": "rs/k/c/b",
                "replacement_count": 2,
            }
        )
        report["summary"].update({
            "shadowed_imported_static_method_method_count": 1,
            "shadowed_imported_static_method_reference_count": 99,
        })

        with self.assertRaisesRegex(
            ValueError,
            "IMPORTED STATIC METHOD SHADOW reference count mismatch",
        ):
            summarize(report, top=10)

    def test_cli_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "normalization.json"
            path.write_text(
                '{"kind":"procyon_source_normalization_report",'
                '"kind":"duplicate"}',
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                code = main([str(path)])

            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn(
                "duplicate JSON key",
                stderr.getvalue(),
            )

    def test_cli_top_limit(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "normalization.json"
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
                "=== TOP 1 SAME-PACKAGE SHADOW SOURCES ===",
                stdout.getvalue(),
            )

    @unittest.skipUnless(
        os.name == "nt",
        "Windows PowerShell parser is only available on Windows CI",
    )
    def test_source_m1_wrapper_parses_in_windows_powershell(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo
            / "scripts"
            / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        )
        script_literal = str(script).replace("'", "''")
        command = (
            "$tokens = $null; "
            "$errors = $null; "
            "[System.Management.Automation.Language.Parser]::"
            "ParseFile('"
            + script_literal
            + "', [ref]$tokens, [ref]$errors) "
            "| Out-Null; "
            "if ($errors.Count -ne 0) { "
            "$errors | ForEach-Object { "
            "[Console]::Error.WriteLine($_.Message) "
            "}; exit 1 }"
        )
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                command,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )

    def test_wrapper_invokes_normalization_evidence_summary(self):
        repo = Path(__file__).resolve().parents[1]
        script = (
            repo
            / "scripts"
            / "Invoke-SourceM1ExactLocalAcceptance.ps1"
        )
        text = script.read_text(encoding="utf-8")

        self.assertIn(
            'Join-Path $CollisionWorkspace "source-normalization.json"',
            text,
        )
        self.assertIn(
            "spk_recovery.source_normalization_summary_cli",
            text,
        )
        self.assertIn(
            "SUMMARIZE SOURCE NORMALIZATION EVIDENCE",
            text,
        )
        self.assertIn(
            "Normalization report ID is not bound to recovered workspace.",
            text,
        )
        self.assertIn(
            "PRIMITIVE_SCOPE_SELF_SHADOW_METHODS=",
            text,
        )
        self.assertIn(
            "INVOKEDYNAMIC_HELPER_RETURN_CAST_REFERENCES=",
            text,
        )
        self.assertIn(
            "NESTED_STATIC_FIELD_SHADOW_REFERENCES=",
            text,
        )
        self.assertIn(
            "LINKEDHASHMAP_PLACEHOLDER_REFERENCES=",
            text,
        )
        self.assertIn(
            "PRIMITIVE_SCOPE_SELF_SHADOW_REFERENCES=",
            text,
        )
        self.assertIn(
            "PRIMITIVE_INSTANCE_RECEIVER_REFERENCES=",
            text,
        )
        self.assertIn(
            "IMPORTED_STATIC_METHOD_SHADOW_REFERENCES=",
            text,
        )
        self.assertIn(
            "SAME_PACKAGE_STATIC_METHOD_SHADOW_REFERENCES=",
            text,
        )
        self.assertIn(
            "SCOPED_SAME_PACKAGE_STATIC_FIELD_REFERENCES=",
            text,
        )


if __name__ == "__main__":
    unittest.main()

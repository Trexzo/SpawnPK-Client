from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from spk_recovery.source_digest import source_tree_digest
from spk_recovery.source_readiness import (
    SourceReadinessError,
    audit_source_workspace,
)


def _tree_digest(root: Path) -> str:
    return source_tree_digest(root)[0]


def _manifest(root: Path) -> dict:
    files = list(root.rglob("*.java"))
    return {
        "schema_version": 1,
        "kind": "recovered_source_workspace_manifest",
        "workspace_id": "SRCWS_" + "1" * 20,
        "build_id": "v308",
        "source_authority_sha256": "a" * 64,
        "readable_jar_sha256": "b" * 64,
        "namespace_id": "SEMNS_" + "2" * 20,
        "class_plan_digest": "c" * 64,
        "member_plan_digest": "d" * 64,
        "engine": "cfr",
        "decompiler_sha256": "e" * 64,
        "source_tree_sha256": _tree_digest(root),
        "java_file_count": len(files),
        "source_bytes": source_tree_digest(root)[2],
        "source_directory": "src",
    }


class SourceReadinessTests(unittest.TestCase):
    def test_inventory_and_external_imports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = root / "recovered" / "demo"
            pkg.mkdir(parents=True)
            (pkg / "A.java").write_text(
                "package recovered.demo;\n"
                "import java.util.List;\n"
                "import com.google.gson.Gson;\n"
                "public class A {\n"
                "    public static class Nested {}\n"
                "}\n",
                encoding="utf-8",
            )
            report = audit_source_workspace(_manifest(root), root)
            self.assertTrue(report["summary"]["static_readiness_pass"])
            self.assertEqual(report["summary"]["java_file_count"], 1)
            self.assertIn("com", report["external_import_roots"])
            self.assertNotIn("java", report["external_import_roots"])
            self.assertEqual(report["issues"], [])

    def test_public_type_filename_mismatch_is_high(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.mkdir(exist_ok=True)
            (root / "Wrong.java").write_text(
                "public class Actual {}\n",
                encoding="utf-8",
            )
            report = audit_source_workspace(_manifest(root), root)
            self.assertFalse(report["summary"]["static_readiness_pass"])
            self.assertEqual(
                report["issue_counts"]["public_type_filename_mismatch"],
                1,
            )

    def test_decompiler_failure_marker_is_high(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "A.java").write_text(
                "public class A { // could not decompile\n}\n",
                encoding="utf-8",
            )
            report = audit_source_workspace(_manifest(root), root)
            self.assertFalse(report["summary"]["static_readiness_pass"])
            self.assertEqual(
                report["issue_counts"]["decompiler_failure_marker"],
                1,
            )


    def test_procyon_inline_failure_marker_is_high(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "A.java").write_text(
                "public class A {\n"
                "    // This method could not be decompiled.\n"
                "}\n",
                encoding="utf-8",
            )
            manifest = _manifest(root)
            manifest["engine"] = "procyon"
            report = audit_source_workspace(manifest, root)
            self.assertFalse(report["summary"]["static_readiness_pass"])
            self.assertEqual(
                report["issue_counts"]["decompiler_failure_marker"],
                1,
            )


    def test_nested_public_types_are_not_top_level(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Outer.java").write_text(
                "public class Outer {\n"
                "    String brace = \"{ not structural }\";\n"
                "    char close = '}';\n"
                "    // } comment brace\n"
                "    /* { block comment brace } */\n"
                "    public enum Nested { A, B }\n"
                "}\n",
                encoding="utf-8",
            )
            report = audit_source_workspace(_manifest(root), root)
            self.assertTrue(report["summary"]["static_readiness_pass"])
            self.assertEqual(report["issues"], [])
            self.assertEqual(
                report["files"][0]["public_types"],
                ["Outer"],
            )
            self.assertEqual(
                report["files"][0]["top_level_types"],
                ["Outer"],
            )


    def test_text_block_braces_do_not_change_top_level_depth(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Outer.java").write_text(
                'public class Outer {\n'
                '    String json = """\n'
                '        { "nested": "} not structural" }\n'
                '        """;\n'
                '    public interface Nested {}\n'
                '}\n',
                encoding="utf-8",
            )
            report = audit_source_workspace(_manifest(root), root)
            self.assertTrue(report["summary"]["static_readiness_pass"])
            self.assertEqual(report["issues"], [])
            self.assertEqual(report["files"][0]["public_types"], ["Outer"])
            self.assertEqual(report["files"][0]["top_level_types"], ["Outer"])

    def test_package_private_outer_with_public_nested_type_has_no_filename_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "o.java").write_text(
                "class o {\n"
                "    public class a {}\n"
                "}\n",
                encoding="utf-8",
            )
            report = audit_source_workspace(_manifest(root), root)
            self.assertTrue(report["summary"]["static_readiness_pass"])
            self.assertEqual(report["issues"], [])
            self.assertEqual(
                report["files"][0]["top_level_types"],
                ["o"],
            )
            self.assertEqual(
                report["files"][0]["public_types"],
                [],
            )

    def test_genuine_multiple_public_top_level_types_remain_high(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "A.java").write_text(
                "public class A {}\n"
                "public class B {}\n",
                encoding="utf-8",
            )
            report = audit_source_workspace(_manifest(root), root)
            self.assertFalse(report["summary"]["static_readiness_pass"])
            self.assertEqual(
                report["issue_counts"]["multiple_public_top_level_types"],
                1,
            )
            self.assertEqual(
                report["files"][0]["public_types"],
                ["A", "B"],
            )


    def test_same_line_multiple_public_top_level_types_remain_high(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "A.java").write_text(
                "public class A {} public class B {}\n",
                encoding="utf-8",
            )
            report = audit_source_workspace(_manifest(root), root)
            self.assertFalse(report["summary"]["static_readiness_pass"])
            self.assertEqual(
                report["issue_counts"]["multiple_public_top_level_types"],
                1,
            )
            self.assertEqual(
                report["files"][0]["public_types"],
                ["A", "B"],
            )
            self.assertEqual(
                report["files"][0]["top_level_types"],
                ["A", "B"],
            )

    def test_source_tree_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "A.java"
            path.write_text("public class A {}\n", encoding="utf-8")
            manifest = _manifest(root)
            path.write_text("public class A { int x; }\n", encoding="utf-8")
            with self.assertRaises(SourceReadinessError):
                audit_source_workspace(manifest, root)


if __name__ == "__main__":
    unittest.main()

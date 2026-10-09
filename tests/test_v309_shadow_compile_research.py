from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from spk_recovery import v309_shadow_compile_research as module


def _sha(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


class JavaPackageShadowResearchTests(unittest.TestCase):
    def test_only_real_binary_imports_can_prove_shadow_prefixes(self):
        names = {
            "demo/api.class",
            "demo/api/widget.class",
            "demo/another/Type.class",
        }
        hits = module._package_shadow_imports([
            "demo.api.widget", "demo.api.widget",
            "demo.api.missing", "demo.another.Type",
        ], names)
        self.assertEqual(dict(hits), {"demo/api.class": 2})
        self.assertNotIn("demo/another/Type.class", hits)

    def test_ambiguous_package_prefix_without_class_target_is_not_suppressed(self):
        self.assertFalse(module._package_shadow_imports(
            ["demo.api.widget"], {"demo/api.class"},
        ))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.original = root / "original.jar"
        self.capsule = root / "capsule.jar"
        self.source = root / "source.zip"
        self.parent = root / "parent.json"
        with ZipFile(self.original, "w") as jar, ZipFile(self.capsule, "w") as cap:
            for path in (
                "demo/api.class",
                "demo/api/widget.class",
                "demo/util/Other.class",
            ):
                jar.writestr(path, ("content " + path).encode())
                cap.writestr(path, ("content " + path).encode())
        self.write_source("import demo.api.widget;")
        self.original_sha = _sha(self.original)
        self.capsule_sha = _sha(self.capsule)
        self.source_sha = _sha(self.source)
        core = {
            "kind": "v309_external_namespace_compile_capsule_research",
            "canonical": False,
            "original_client_sha256": self.original_sha,
            "external_source_archive_sha256": self.source_sha,
            "summary": {
                "exact_compile_capsule_sha256": self.capsule_sha,
                "external_namespace_candidate_classes": 3,
            },
        }
        self.parent_id = "SPKDEPCAPSULE_" + sha256(
            json.dumps(core, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode()
        ).hexdigest()[:20].upper()
        self.parent.write_text(json.dumps({"report_id": self.parent_id, **core}))

    def write_source(self, import_text: str):
        with ZipFile(self.source, "w") as z:
            z.writestr("project/src/main/java/demo/Case.java",
                       "package demo;\n" + import_text + "\nclass Case {}\n")

    def run_builder(self, output: Path, **overrides):
        with patch.object(module, "EXPECTED_PARENT_REPORT_ID", self.parent_id):
            return module.build_v309_shadow_compile_research(
                parent_capsule=self.capsule,
                parent_report=self.parent,
                source_archive=self.source,
                original_jar=self.original,
                out_dir=output,
                expected_capsule_sha256=self.capsule_sha,
                expected_source_sha256=self.source_sha,
                expected_original_sha256=self.original_sha,
                expected_parent_classes=3,
                expected_source_java=1,
                expected_shadow_classes=1,
                expected_shadow_imports=1,
                **overrides,
            )

    def test_byte_determinism_and_bounded_report(self):
        root = self.original.parent
        first = self.run_builder(root / "run1")
        second = self.run_builder(root / "run2")
        self.assertEqual(first, second)
        self.assertFalse(first["canonical"])
        self.assertEqual(first["summary"]["shadow_class_entries_suppressed"], 1)
        self.assertEqual(first["summary"]["remaining_compilation_candidate_classes"], 2)
        self.assertFalse(first["summary"]["clean_java_source_build_passed"])
        first_out = root / "run1" / "shadow-filtered-compile-candidate.jar"
        second_out = root / "run2" / "shadow-filtered-compile-candidate.jar"
        self.assertEqual(_sha(first_out), _sha(second_out))
        with ZipFile(first_out) as jar:
            self.assertNotIn("demo/api.class", jar.namelist())
            self.assertIn("demo/api/widget.class", jar.namelist())
        self.assertNotIn("demo/api.class", json.dumps(first))

    def test_direct_import_of_excluded_class_fails_closed(self):
        self.write_source("import demo.api.widget;\nimport demo.api;")
        self.source_sha = _sha(self.source)
        self.original_sha = _sha(self.original)
        self.capsule_sha = _sha(self.capsule)
        # Re-pin only synthetic inputs and recompute the synthetic parent ID.
        parent = json.loads(self.parent.read_text())
        parent["external_source_archive_sha256"] = self.source_sha
        parent["report_id"] = "SPKDEPCAPSULE_" + sha256(json.dumps(
            {k: v for k, v in parent.items() if k != "report_id"},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()[:20].upper()
        self.parent_id = parent["report_id"]
        self.parent.write_text(json.dumps(parent))
        with self.assertRaises(module.V309ShadowResearchError):
            self.run_builder(self.original.parent / "rejected")
        self.assertFalse((self.original.parent / "rejected").exists())

    def test_wrong_input_hash_never_mutates_originals(self):
        old = self.source.read_bytes()
        self.source.write_bytes(old + b"tampered")
        with self.assertRaises(module.V309ShadowResearchError):
            self.run_builder(self.original.parent / "rejected")
        self.assertFalse((self.original.parent / "rejected").exists())

    def test_existing_output_must_never_be_overwritten(self):
        output = self.original.parent / "existing"
        output.mkdir()
        marker = output / "KEEP.txt"
        marker.write_text("original")
        with self.assertRaises(module.V309ShadowResearchError):
            self.run_builder(output)
        self.assertEqual(marker.read_text(), "original")

    def test_cli_reports_sanitized_failure(self):
        capture = io.StringIO()
        with redirect_stdout(capture):
            status = module.main([
                "--parent-capsule", str(self.capsule),
                "--parent-report", str(self.parent),
                "--source-zip", str(self.source),
                "--original-v309", str(self.original),
                "--out-dir", str(self.original.parent / "none"),
            ])
        self.assertEqual(status, 1)
        self.assertIn("FAIL_CLOSED", capture.getvalue())
        self.assertNotIn(str(self.original.parent), capture.getvalue())


if __name__ == "__main__":
    unittest.main()

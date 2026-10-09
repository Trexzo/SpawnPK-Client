from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.v309_external_compile_capsule import (
    V309CompileCapsuleError,
    build_external_compile_capsule,
    main,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalExternalCompileCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "client.jar"
        self.source = self.root / "candidate.zip"
        self.deob = self.root / "deob.zip"
        self.lombok_bytes = io.BytesIO()
        with ZipFile(self.lombok_bytes, "w") as z:
            z.writestr("lombok/SneakyThrows.class", b"compiler-fixture")
        with ZipFile(self.original, "w") as z:
            z.writestr("com/google/Library.class", b"external-library")
            z.writestr("rs/Client.class", b"never-use-original-project-binary")
            z.writestr("tools/ProjectHelper.class", b"never-project-helper")
            z.writestr("com/apple/eawt/Application.class", b"project-source-shadow")
        with ZipFile(self.source, "w") as z:
            z.writestr(
                "project/src/main/java/rs/Client.java", "package rs; class Client {}")
            z.writestr(
                "project/src/main/java/com/apple/eawt/Application.java",
                "package com.apple.eawt; class Application {}")
        with ZipFile(self.deob, "w") as z:
            z.writestr("tool/lib/lombok-1.18.32.jar", self.lombok_bytes.getvalue())
        self.pins = {
            "expected_client_sha256": sha(self.original),
            "expected_source_sha256": sha(self.source),
            "expected_deob_sha256": sha(self.deob),
        }

    def run_capsule(self, location: Path, **updates):
        return build_external_compile_capsule(
            original_jar=self.original, source_archive=self.source,
            deob_tool_archive=self.deob, out_dir=location,
            expected_external_classes=1, **(self.pins | updates),
        )

    def test_only_external_candidate_classes_enter_capsule(self):
        output = self.root / "capsule"
        report = self.run_capsule(output)
        self.assertFalse(report["canonical"])
        self.assertEqual(report["summary"]["external_namespace_candidate_classes"], 1)
        self.assertEqual(report["summary"]["source_owned_classfile_fallbacks"], 0)
        self.assertFalse(report["summary"]["complete_dependency_authority_verified"])
        with ZipFile(output / "external-namespace-compile-candidate.jar") as z:
            self.assertEqual(z.namelist(), ["com/google/Library.class"])
        self.assertEqual(
            (output / "lombok-1.18.32.jar").read_bytes(),
            self.lombok_bytes.getvalue(),
        )
        self.assertNotIn("rs/Client.class", json.dumps(report))
        self.assertNotIn("com/google/Library.class", json.dumps(report))

    def test_byte_identical_output_from_independent_runs(self):
        first = self.run_capsule(self.root / "first")
        second = self.run_capsule(self.root / "second")
        self.assertEqual(first, second)
        self.assertEqual(sha(self.root / "first" / "external-namespace-compile-candidate.jar"),
                         sha(self.root / "second" / "external-namespace-compile-candidate.jar"))
        self.assertEqual(sha(self.root / "first" / "COMPILE-CAPSULE-RESEARCH.json"),
                         sha(self.root / "second" / "COMPILE-CAPSULE-RESEARCH.json"))

    def test_reject_wrong_original_sha_without_creating_any_output(self):
        output = self.root / "new"
        with self.assertRaises(V309CompileCapsuleError):
            self.run_capsule(output, expected_client_sha256="0" * 64)
        self.assertFalse(output.exists())

    def test_reject_expected_class_count_drift(self):
        with self.assertRaises(V309CompileCapsuleError):
            build_external_compile_capsule(
                original_jar=self.original, source_archive=self.source,
                deob_tool_archive=self.deob, out_dir=self.root / "new",
                expected_external_classes=2, **self.pins)

    def test_reject_incomplete_lombok_dependency(self):
        with ZipFile(self.deob, "w") as z:
            z.writestr("tool/lib/lombok-1.18.32.jar", b"not-zip")
        with self.assertRaises(Exception):
            self.run_capsule(self.root / "new", expected_deob_sha256=sha(self.deob))
        self.assertFalse((self.root / "new").exists())

    def test_source_with_zip_traversal_rejected(self):
        with ZipFile(self.source, "w") as z:
            z.writestr("project/../escape.java", "class Escape {}")
            z.writestr("project/src/main/java/rs/Client.java", "class Client {}")
        with self.assertRaises(V309CompileCapsuleError):
            self.run_capsule(self.root / "new", expected_source_sha256=sha(self.source))

    def test_reject_preexisting_output(self):
        output = self.root / "new"
        output.mkdir()
        marker = output / "KEEP"
        marker.write_text("unchanged")
        with self.assertRaises(V309CompileCapsuleError):
            self.run_capsule(output)
        self.assertEqual(marker.read_text(), "unchanged")

    def test_cli_failure_does_not_disclose_private_paths(self):
        from spk_recovery.v309_external_compile_capsule import main
        captured = io.StringIO()
        with redirect_stdout(captured):
            status = main([
                "--original-v309", str(self.original),
                "--source-zip", str(self.source),
                "--deob-tool-zip", str(self.deob),
                "--out-dir", str(self.root / "nonexistent"),
                "--original-sha256", "0" * 64,
            ])
        self.assertEqual(status, 1)
        self.assertNotIn(str(self.root), captured.getvalue())
        self.assertIn("FAIL_CLOSED", captured.getvalue())


if __name__ == "__main__":
    unittest.main()

"""R389 public synthetic-only cross-host class JAR reproducibility checks."""
from __future__ import annotations
import hashlib
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/r383/verify_private_full_build.py"
ORCHESTRATOR = ROOT / "tools/r386/run_self_contained_acceptance.py"
EXPECTED_RUNNER_SHA = "d09947d5863fc361e7f8362fbcabe5e100452d160ee69fee089f5fb6106944af"
EXPECTED_ORCHESTRATOR_SHA = "cdded0190777c4fc66ef15d56b429384d0307fe0d4bbd07f1487617e71271608"
EXPECTED_SORT = 'classfiles=sorted(classes.rglob("*.class"), key=lambda p: p.relative_to(classes).as_posix())'

spec = importlib.util.spec_from_file_location("r389_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def assemble(classes: Path, out: Path) -> list[str]:
    entries = sorted(classes.rglob("*.class"),
                     key=lambda p: p.relative_to(classes).as_posix())
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in entries:
            name = entry.relative_to(classes).as_posix()
            info = runner.canonical_class_zipinfo(name)
            archive.writestr(info, entry.read_bytes(),
                             compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return [p.relative_to(classes).as_posix() for p in entries]

class R389Tests(unittest.TestCase):
    def test_source_runner_pin_is_exact(self):
        self.assertEqual(sha(RUNNER.read_bytes()), EXPECTED_RUNNER_SHA)

    def test_orchestrator_pin_is_exact(self):
        self.assertEqual(sha(ORCHESTRATOR.read_bytes()), EXPECTED_ORCHESTRATOR_SHA)

    def test_orchestrator_references_correct_runner_pin(self):
        self.assertIn(EXPECTED_RUNNER_SHA, ORCHESTRATOR.read_text("utf-8"))

    def test_explicit_posix_sort_exists_in_real_runner(self):
        self.assertIn(EXPECTED_SORT, RUNNER.read_text("utf-8"))

    def test_mixed_case_and_nested_entries_have_canonical_order(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "classes"
            for path, raw in [
                ("rs/z/Alpha.class", b"z"),
                ("rs/Z/beta.class", b"Z"),
                ("rs/a/Outer$Inner.class", b"a"),
                ("rs/a/Outer.class", b"b"),
            ]:
                file = d / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(raw)
            result = assemble(d, Path(t) / "first.jar")
            self.assertEqual(result, sorted(result))
            with zipfile.ZipFile(Path(t) / "first.jar") as archive:
                self.assertEqual(archive.namelist(), result)
                self.assertTrue(all(i.create_system == 3 for i in archive.infolist()))

    def test_repeated_creation_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "classes"
            for name in ["z/Z.class", "a/A.class", "a/Z.class"]:
                file = d / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(("synthetic:" + name).encode())
            a, b = Path(t)/"a.jar", Path(t)/"b.jar"
            assemble(d, a)
            assemble(d, b)
            self.assertEqual(sha(a.read_bytes()), sha(b.read_bytes()))

    def test_archive_rejects_unsafe_member(self):
        with self.assertRaises(runner.Refused):
            runner.canonical_class_zipinfo("../evil.class")

    def test_canonical_filename_slashes(self):
        with self.assertRaises(runner.Refused):
            runner.canonical_class_zipinfo("rs\\Client.class")

    def test_archive_metadata_is_explicit(self):
        info = runner.canonical_class_zipinfo("rs/Client.class")
        self.assertEqual(info.create_system, 3)
        self.assertEqual(info.date_time, (2026, 10, 18, 0, 0, 0))
        self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)

if __name__ == "__main__":
    unittest.main()

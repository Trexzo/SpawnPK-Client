"""R26 synthetic Java regression tests; no original client bytes in CI."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import warnings
from zipfile import ZipFile

from spk_recovery.exact_class_slice import build_class_slice, ClassSliceError


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ExactClassSliceTests(unittest.TestCase):
    def _source_jar(self, root: Path) -> Path:
        src = root / "src" / "p"
        dest = root / "classes"
        src.mkdir(parents=True)
        dest.mkdir()
        (src / "A.java").write_text(
            "package p; public class A { public static class Inner {} "
            "public int n(){ return 17; } } class AA {}",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "-g:none", "-d", str(dest), str(src / "A.java")],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / "original.jar"
        with ZipFile(jar, "w") as archive:
            for path in sorted(dest.rglob("*.class")):
                archive.write(path, path.relative_to(dest).as_posix())
        return jar

    def test_exact_bytes_and_nested_scope(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            output = root / "slice.jar"
            report = build_class_slice(
                original, output, original_sha256=_digest(original),
                class_entry="p/A.class",
            )
            self.assertEqual(report["included_class_count"], 2)
            self.assertEqual(report["accepted_class_identities"], 0)
            with ZipFile(original) as a, ZipFile(output) as b:
                self.assertEqual(sorted(b.namelist()),
                                 ["p/A$Inner.class", "p/A.class"])
                for name in b.namelist():
                    self.assertEqual(b.read(name), a.read(name))
            self.assertEqual(report["original_jar_sha256"], _digest(original))
            self.assertEqual(report["slice_sha256"], _digest(output))

    def test_deterministic_zip_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            first, second = root / "one.zip", root / "two.zip"
            args = {"original_sha256": _digest(original), "class_entry": "p/A.class"}
            build_class_slice(original, first, **args)
            build_class_slice(original, second, **args)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_exclude_nested(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            output = root / "base.jar"
            result = build_class_slice(
                original, output, original_sha256=_digest(original),
                class_entry="p/A.class", include_nested=False,
            )
            self.assertEqual(result["included_class_count"], 1)
            with ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), ["p/A.class"])

    def test_wrong_hash_refuses_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            output = root / "slice.jar"
            with self.assertRaisesRegex(ClassSliceError, "ORIGINAL_JAR_PIN_MISMATCH"):
                build_class_slice(original, output, original_sha256="0" * 64,
                                  class_entry="p/A.class")
            self.assertFalse(output.exists())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            output = root / "slice.jar"
            output.write_bytes(b"keep me")
            with self.assertRaisesRegex(ClassSliceError, "OUTPUT_ALREADY_EXISTS"):
                build_class_slice(original, output, original_sha256=_digest(original),
                                  class_entry="p/A.class")
            self.assertEqual(output.read_bytes(), b"keep me")

    def test_invalid_class_paths_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            output = root / "slice.jar"
            for name in ("../A.class", "/p/A.class", "p\\A.class",
                         "p/../A.class", "C:/p/A.class", "p//A.class",
                         "p/A.java"):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(ClassSliceError, "INVALID_CLASS_ENTRY"):
                        build_class_slice(original, output,
                                          original_sha256=_digest(original),
                                          class_entry=name)
            self.assertFalse(output.exists())

    def test_missing_class_refuses_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            output = root / "slice.jar"
            with self.assertRaisesRegex(ClassSliceError, "ORIGINAL_CLASS_MISSING"):
                build_class_slice(original, output, original_sha256=_digest(original),
                                  class_entry="p/Unknown.class")
            self.assertFalse(output.exists())

    def test_duplicate_class_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(original, "a") as archive:
                    archive.writestr("p/A.class", b"\xca\xfe\xba\xbe000000")
            output = root / "slice.jar"
            with self.assertRaisesRegex(ClassSliceError, "DUPLICATE_SELECTED_CLASS_ENTRY"):
                build_class_slice(original, output, original_sha256=_digest(original),
                                  class_entry="p/A.class")
            self.assertFalse(output.exists())

    def test_corrupt_selected_class_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = root / "bad.jar"
            with ZipFile(original, "w") as archive:
                archive.writestr("p/A.class", b"wrong")
            output = root / "slice.jar"
            with self.assertRaisesRegex(ClassSliceError, "INVALID_CLASSFILE_MAGIC"):
                build_class_slice(original, output, original_sha256=_digest(original),
                                  class_entry="p/A.class")
            self.assertFalse(output.exists())

    def test_original_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._source_jar(root)
            before = original.read_bytes()
            with self.assertRaisesRegex(ClassSliceError, "OUTPUT_EQUALS_ORIGINAL"):
                build_class_slice(original, original,
                                  original_sha256=_digest(original),
                                  class_entry="p/A.class")
            self.assertEqual(original.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

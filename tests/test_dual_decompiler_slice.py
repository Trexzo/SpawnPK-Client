"""Offline R27 end-to-end tests using synthetic original and fake tool JARs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.dual_decompiler_slice import (
    DualDecompilerError,
    run_targeted_dual_decompilation,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(
    shutil.which("java") and shutil.which("javac") and shutil.which("jar"),
    "Java compiler, runtime and jar tool required",
)
class DualDecompilerSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        src = cls.root / "src"
        build = cls.root / "build"
        src.mkdir()
        build.mkdir()
        pkg = src / "p"
        pkg.mkdir()
        (pkg / "A.java").write_text(
            "package p; public class A {"
            " public static class Nested {}"
            " public int v() { return 7; } }",
            encoding="utf-8",
        )
        (src / "SyntheticDecompiler.java").write_text(
            "import java.nio.file.*;\n"
            "import java.util.zip.*;\n"
            "public class SyntheticDecompiler {\n"
            "public static void main(String[] args) throws Exception {\n"
            "  String out;\n"
            "  if (args.length == 3 && args[1].equals(\"--outputdir\")) out=args[2];\n"
            "  else if (args.length == 2) out=args[1];\n"
            "  else throw new Exception(\"bad adapter syntax\");\n"
            "  try (ZipFile jar = new ZipFile(args[0])) {\n"
            "    if (jar.getEntry(\"p/A.class\") == null ||"
            " jar.getEntry(\"p/A$Nested.class\") == null) throw new Exception(\"bad slice\");\n"
            "  }\n"
            "  Path base=Paths.get(out, \"p\"); Files.createDirectories(base);\n"
            "  Files.writeString(base.resolve(\"A.java\"),"
            " \"package p; class A { int v(){return 7;} }\\n\");\n"
            "}\n"
            "}\n",
            encoding="utf-8",
        )
        (src / "FailDecompiler.java").write_text(
            "public class FailDecompiler {"
            "public static void main(String[] args) { "
            "System.err.println(\"SENSITIVE_ORIGINAL_CLASS_NAME\"); "
            "System.exit(17); }}\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "-g:none", "-d", str(build), str(pkg / "A.java"),
             str(src / "SyntheticDecompiler.java"), str(src / "FailDecompiler.java")],
            capture_output=True, text=True,
        )
        if proc.returncode:
            cls.tmp.cleanup()
            raise AssertionError(proc.stdout + proc.stderr)
        cls.original = cls.root / "synthetic-original.jar"
        with ZipFile(cls.original, "w") as jar:
            for path in sorted((build / "p").rglob("*.class")):
                jar.write(path, path.relative_to(build).as_posix())
        cls.cfr = cls.root / "fake-cfr.jar"
        cls.vine = cls.root / "fake-vineflower.jar"
        cls.fail = cls.root / "fake-failing.jar"
        for jar_path, main_class in (
            (cls.cfr, "SyntheticDecompiler"),
            (cls.vine, "SyntheticDecompiler"),
            (cls.fail, "FailDecompiler"),
        ):
            manifest = cls.root / (jar_path.stem + ".mf")
            manifest.write_text(
                "Manifest-Version: 1.0\nMain-Class: " + main_class + "\n\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                ["jar", "cfm", str(jar_path), str(manifest),
                 "-C", str(build), main_class + ".class"],
                capture_output=True, text=True,
            )
            if proc.returncode:
                cls.tmp.cleanup()
                raise AssertionError(proc.stdout + proc.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _run(self, out: Path, *, original_sha=None, cfr_sha=None,
             vine_sha=None, cfr=None, vine=None, original=None):
        return run_targeted_dual_decompilation(
            original or self.original, cfr or self.cfr, vine or self.vine, out,
            original_sha256=original_sha or _digest(self.original),
            cfr_sha256=cfr_sha or _digest(cfr or self.cfr),
            vineflower_sha256=vine_sha or _digest(vine or self.vine),
            class_entry="p/A.class",
        )

    def test_executes_both_backends_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "run"
            original_sha = _digest(self.original)
            result = self._run(output)
            self.assertEqual(result["included_class_count"], 2)
            self.assertEqual(result["engines_executed"], 2)
            self.assertFalse(result["canonical_identity_accepted"])
            self.assertFalse(result["source_equivalence_certified"])
            self.assertEqual(set(result["engines"]), {"cfr", "vineflower"})
            self.assertEqual(result["engines"]["cfr"]["java_file_count"], 1)
            self.assertEqual(result["engines"]["vineflower"]["java_file_count"], 1)
            self.assertTrue((output / "cfr" / "p" / "A.java").is_file())
            self.assertTrue((output / "vineflower" / "p" / "A.java").is_file())
            self.assertEqual(_digest(self.original), original_sha)
            manifest = json.loads(
                (output / "private-research-manifest.json").read_text()
            )
            self.assertEqual(manifest, result)
            self.assertNotIn("p/A", json.dumps(result))

    def test_manifest_is_deterministic_across_output_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            first = self._run(root / "one")
            second = self._run(root / "two")
            self.assertEqual(first, second)
            self.assertEqual(
                (root / "one" / "private-research-manifest.json").read_bytes(),
                (root / "two" / "private-research-manifest.json").read_bytes(),
            )

    def test_wrong_original_pin_prevents_output_creation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "not-created"
            with self.assertRaisesRegex(DualDecompilerError, "ORIGINAL_SHA256_MISMATCH"):
                self._run(root, original_sha="0" * 64)
            self.assertFalse(root.exists())

    def test_wrong_engine_pin_prevents_output_creation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "not-created"
            with self.assertRaisesRegex(DualDecompilerError, "CFR_SHA256_MISMATCH"):
                self._run(root, cfr_sha="0" * 64)
            self.assertFalse(root.exists())

    def test_output_root_must_not_exist_or_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "exists"
            root.mkdir()
            marker = root / "important.txt"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(DualDecompilerError, "OUTPUT_ROOT_ALREADY_EXISTS"):
                self._run(root)
            self.assertEqual(marker.read_text(), "keep")

    def test_failed_engine_cannot_publish_success_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "failure"
            with self.assertRaisesRegex(DualDecompilerError, "PRIVATE_DUAL_DECOMPILATION_FAILED") as caught:
                self._run(root, vine=self.fail)
            # The legacy decompiler exception includes its raw stderr,
            # but this public-facing wrapper must not print private names.
            self.assertNotIn("SENSITIVE_ORIGINAL_CLASS_NAME", str(caught.exception))
            self.assertTrue((root / "exact-private-slice.jar").is_file())
            self.assertTrue((root / "cfr" / "p" / "A.java").is_file())
            self.assertFalse((root / "private-research-manifest.json").exists())

    def test_missing_decompiler_refused_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "absent"
            with self.assertRaisesRegex(DualDecompilerError, "VINEFLOWER_FILE_MISSING"):
                self._run(root, vine=Path(d) / "missing.jar", vine_sha="0" * 64)
            self.assertFalse(root.exists())

    def test_same_original_as_tool_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "refused"
            with self.assertRaisesRegex(DualDecompilerError, "INPUTS_MUST_BE_SEPARATE"):
                self._run(
                    root, cfr=self.original,
                    cfr_sha=_digest(self.original),
                )
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()

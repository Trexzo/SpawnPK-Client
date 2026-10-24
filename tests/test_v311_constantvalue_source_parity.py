"""Java9 source parity must cover ConstantValue, not merely Code opcodes.

Constant static-final primitive and string values are classfile attributes,
not executable instructions; they must not silently differ in original and
independently compiled candidate classes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)


SOURCE = """package rs.fixture;
import java.awt.Color;
public class ThemeColors {
    public static final int WIDTH = 4;
    public static final int HEIGHT = 129;
    public static final String LABEL = "theme";
    public static final Color SHADE = new Color(70, 61, 50, 156);
}
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("javap"), "Requires Java JDK",
)
class ConstantValueSourceParityTests(unittest.TestCase):
    def fixture(self, root: Path):
        src = root / "source"
        source = src / "rs/fixture/ThemeColors.java"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(SOURCE, encoding="utf-8")
        original_classes = root / "original-classes"
        original_classes.mkdir()
        result = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-sp"),
            "-d", str(original_classes), str(source),
        ], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = "rs/fixture/ThemeColors.class"
        orig = root / "fixture-original.jar"
        with zipfile.ZipFile(orig, "w") as z:
            z.writestr(entry, (original_classes / entry).read_bytes())
        return orig, src, source, entry

    def test_correct_constants_and_color_code_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar, src, source, entry = self.fixture(root)
            with zipfile.ZipFile(jar) as archive:
                expected = sha(archive.read(entry))
            report = verify_standalone_sources(
                jar, src, root / "accepted",
                original_sha256=sha(jar.read_bytes()),
                class_sha256={entry: expected},
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 1)
            self.assertGreater(report["total_ordered_instructions"], 10)
            self.assertEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"
                ], 0,
            )
            self.assertFalse(report["original_game_binary_on_compile_classpath"])

    def test_wrong_compile_time_int_constant_rejected_before_success_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar, src, source, entry = self.fixture(root)
            with zipfile.ZipFile(jar) as archive:
                original_sha = sha(archive.read(entry))
            source.write_text(
                SOURCE.replace("WIDTH = 4", "WIDTH = 5"),
                encoding="utf-8",
            )
            refused_dir = root / "refused"
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, src, refused_dir,
                    original_sha256=sha(jar.read_bytes()),
                    class_sha256={entry: original_sha},
                )
            self.assertFalse(
                (refused_dir / "SOURCE-REBUILD-VERIFY.json").exists()
            )

    def test_wrong_compile_time_string_constant_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar, src, source, entry = self.fixture(root)
            with zipfile.ZipFile(jar) as archive:
                original_sha = sha(archive.read(entry))
            source.write_text(
                SOURCE.replace('LABEL = "theme"', 'LABEL = "other"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, src, root / "refused",
                    original_sha256=sha(jar.read_bytes()),
                    class_sha256={entry: original_sha},
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

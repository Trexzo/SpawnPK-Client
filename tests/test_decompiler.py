from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.decompiler import (
    DecompilerError,
    run_decompiler,
)


@unittest.skipUnless(
    shutil.which("java")
    and shutil.which("javac")
    and shutil.which("jar"),
    "Java toolchain required",
)
class DecompilerAdapterTests(unittest.TestCase):
    def _fake_decompiler(self, root: Path) -> Path:
        src = root / "FakeDecompiler.java"
        src.write_text(
            """
import java.nio.file.*;
public class FakeDecompiler {
    public static void main(String[] args) throws Exception {
        Path out = null;
        for (int i = 0; i < args.length - 1; i++) {
            if (args[i].equals("--outputdir")) {
                out = Paths.get(args[i + 1]);
            }
        }
        if (out == null) {
            out = Paths.get(args[args.length - 1]);
        }
        Files.createDirectories(out);
        Files.writeString(
            out.resolve("Recovered.java"),
            "public class Recovered {}\n"
        );
    }
}
""".strip(),
            encoding="utf-8",
        )
        classes = root / "classes"
        classes.mkdir()
        subprocess.run(
            ["javac", "-d", str(classes), str(src)],
            check=True,
        )
        manifest = root / "MANIFEST.MF"
        manifest.write_text(
            "Manifest-Version: 1.0\nMain-Class: FakeDecompiler\n\n",
            encoding="utf-8",
        )
        jar_path = root / "fake-decompiler.jar"
        subprocess.run(
            [
                "jar",
                "cfm",
                str(jar_path),
                str(manifest),
                "-C",
                str(classes),
                ".",
            ],
            check=True,
        )
        return jar_path

    def _input_jar(self, root: Path) -> Path:
        path = root / "input.jar"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("placeholder.txt", "x")
        return path

    def test_cfr_and_vineflower_shapes_are_supported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tool = self._fake_decompiler(root)
            source = self._input_jar(root)
            sha = hashlib.sha256(tool.read_bytes()).hexdigest()

            cfr = run_decompiler(
                source,
                tool,
                expected_decompiler_sha256=sha,
                engine="cfr",
                out_dir=root / "cfr-out",
            )
            vine = run_decompiler(
                source,
                tool,
                expected_decompiler_sha256=sha,
                engine="vineflower",
                out_dir=root / "vine-out",
            )
            self.assertEqual(cfr["java_file_count"], 1)
            self.assertEqual(vine["java_file_count"], 1)

    def test_wrong_decompiler_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tool = self._fake_decompiler(root)
            source = self._input_jar(root)
            with self.assertRaises(DecompilerError):
                run_decompiler(
                    source,
                    tool,
                    expected_decompiler_sha256="0" * 64,
                    engine="cfr",
                    out_dir=root / "out",
                )

    def test_nonempty_output_requires_explicit_clean(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tool = self._fake_decompiler(root)
            source = self._input_jar(root)
            sha = hashlib.sha256(tool.read_bytes()).hexdigest()
            out = root / "out"
            out.mkdir()
            (out / "stale.txt").write_text("stale", encoding="utf-8")

            with self.assertRaises(DecompilerError):
                run_decompiler(
                    source,
                    tool,
                    expected_decompiler_sha256=sha,
                    engine="vineflower",
                    out_dir=out,
                )

            result = run_decompiler(
                source,
                tool,
                expected_decompiler_sha256=sha,
                engine="vineflower",
                out_dir=out,
                clean_out=True,
            )
            self.assertEqual(result["java_file_count"], 1)
            self.assertFalse((out / "stale.txt").exists())


if __name__ == "__main__":
    unittest.main()

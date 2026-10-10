"""R28: decompiler timeouts must fail closed without exposing private logs."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery.decompiler import DecompilerError, run_decompiler


class DecompilerTimeoutR28Tests(unittest.TestCase):
    @staticmethod
    def _inputs(root: Path) -> tuple[Path, Path, str]:
        original = root / "synthetic-input.jar"
        tool = root / "synthetic-decompiler.jar"
        original.write_bytes(b"synthetic source archive")
        tool.write_bytes(b"synthetic decompiler tool")
        expected = hashlib.sha256(tool.read_bytes()).hexdigest()
        return original, tool, expected

    def test_invalid_timeout_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, tool, pin = self._inputs(root)
            for timeout in (0, -1, True, 0.5, "3", 3601):
                with self.subTest(timeout=timeout):
                    out = root / "output"
                    with self.assertRaisesRegex(DecompilerError, "timeout_seconds"):
                        run_decompiler(
                            src, tool, expected_decompiler_sha256=pin,
                            engine="cfr", out_dir=out, timeout_seconds=timeout,
                        )
                    self.assertFalse(out.exists())

    def test_expiring_process_is_sanitized_and_never_succeeds(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, tool, pin = self._inputs(root)
            out = root / "private-output"
            private_marker = "PRIVATE_OBFUSCATED_MEMBER_COORDINATE"
            expired = subprocess.TimeoutExpired(
                cmd=["java", "-jar", str(tool)], timeout=2,
                output=private_marker.encode(),
                stderr=private_marker.encode(),
            )
            with (
                patch("spk_recovery.decompiler.shutil.which", return_value="java"),
                patch(
                    "spk_recovery.decompiler.subprocess.run",
                    side_effect=expired,
                ) as invoked,
            ):
                with self.assertRaisesRegex(DecompilerError, "DECOMPILER_TIMEOUT") as caught:
                    run_decompiler(
                        src, tool, expected_decompiler_sha256=pin,
                        engine="cfr", out_dir=out, timeout_seconds=2,
                    )
            self.assertNotIn(private_marker, str(caught.exception))
            self.assertEqual(invoked.call_args.kwargs["timeout"], 2)
            self.assertTrue(out.is_dir())
            self.assertFalse(any(out.rglob("*.java")))

    def test_default_none_preserves_existing_success_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, tool, pin = self._inputs(root)
            out = root / "original-behavior"
            def fake_run(*args, **kwargs):
                (out / "p").mkdir(parents=True, exist_ok=True)
                (out / "p" / "Synthetic.java").write_text(
                    "package p; class Synthetic {}",
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(args[0], 0, "ok", "")
            with (
                patch("spk_recovery.decompiler.shutil.which", return_value="java"),
                patch("spk_recovery.decompiler.subprocess.run", side_effect=fake_run) as invoked,
            ):
                result = run_decompiler(
                    src, tool, expected_decompiler_sha256=pin,
                    engine="cfr", out_dir=out,
                )
            self.assertEqual(result["java_file_count"], 1)
            self.assertEqual(result["stdout"], "ok")
            self.assertIsNone(invoked.call_args.kwargs["timeout"])

    def test_upper_bound_is_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, tool, pin = self._inputs(root)
            out = root / "bounded"
            with (
                patch("spk_recovery.decompiler.shutil.which", return_value="java"),
                patch(
                    "spk_recovery.decompiler.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(cmd=["java"], timeout=3600),
                ) as called,
            ):
                with self.assertRaisesRegex(DecompilerError, "DECOMPILER_TIMEOUT"):
                    run_decompiler(
                        src, tool, expected_decompiler_sha256=pin,
                        engine="vineflower", out_dir=out, timeout_seconds=3600,
                    )
            self.assertEqual(called.call_args.kwargs["timeout"], 3600)


if __name__ == "__main__":
    unittest.main()

"""R39: offline, synthetic-only verification of pinned decompiler tool acquisition."""
from __future__ import annotations

from io import BytesIO
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from zipfile import ZipFile

from spk_recovery.decompiler_tool_acquire import (
    DecompilerArtifactError,
    acquire_decompiler_jar,
)


def _mock_jar(*, executable: bool = True) -> bytes:
    buff = BytesIO()
    with ZipFile(buff, "w") as archive:
        archive.writestr(
            "META-INF/MANIFEST.MF",
            ("Manifest-Version: 1.0\r\n"
             + ("Main-Class: example.Main\r\n" if executable else "")
             + "\r\n").encode("utf-8"),
        )
        archive.writestr("example/Main.class", b"\xca\xfe\xba\xbe" + bytes(40))
    return buff.getvalue()


class _Response(BytesIO):
    def __init__(self, data: bytes, url: str):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


class DecompilerArtifactTests(unittest.TestCase):
    def test_hash_pinned_synthetic_executable_artifact(self):
        data = _mock_jar()
        expected = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "cfr.jar"
            calls = []

            def response(req, timeout):
                calls.append((req.full_url, timeout))
                return _Response(data, req.full_url)

            with patch(
                "spk_recovery.decompiler_tool_acquire.urlopen",
                side_effect=response,
            ):
                result = acquire_decompiler_jar(
                    "cfr", out, expected_sha256=expected, timeout_seconds=10,
                )
            self.assertEqual(out.read_bytes(), data)
            self.assertEqual(result["sha256"], expected)
            self.assertTrue(result["validated_executable_jar"])
            self.assertFalse(result["client_source_touched"])
            self.assertFalse(result["canonical_mapping_promoted"])
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], 10)
            self.assertIn("repo.maven.apache.org", calls[0][0])
            self.assertIn("/cfr/0.152/", calls[0][0])
            self.assertNotIn("example/Main", str(result))

    def test_wrong_sha256_removes_untrusted_file(self):
        data = _mock_jar()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bad.jar"
            with patch(
                "spk_recovery.decompiler_tool_acquire.urlopen",
                side_effect=lambda req, timeout: _Response(data, req.full_url),
            ):
                with self.assertRaisesRegex(
                    DecompilerArtifactError, "DECOMPILER_ARTIFACT_SHA256_MISMATCH",
                ):
                    acquire_decompiler_jar(
                        "vineflower", out, expected_sha256="0" * 64,
                    )
            self.assertFalse(out.exists())

    def test_existing_output_never_deleted_or_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "already.jar"
            out.write_bytes(b"KEEP ME")
            with patch("spk_recovery.decompiler_tool_acquire.urlopen") as remote:
                with self.assertRaisesRegex(
                    DecompilerArtifactError, "DECOMPILER_OUTPUT_ALREADY_EXISTS",
                ):
                    acquire_decompiler_jar(
                        "cfr", out, expected_sha256="0" * 64,
                    )
                remote.assert_not_called()
            self.assertEqual(out.read_bytes(), b"KEEP ME")

    def test_invalid_sha_and_timeout_fail_before_network(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "not-created.jar"
            with patch("spk_recovery.decompiler_tool_acquire.urlopen") as remote:
                for bad in (None, "abc", "x" * 64):
                    with self.subTest(bad=bad):
                        with self.assertRaisesRegex(
                            DecompilerArtifactError,
                            "MISSING_OR_INVALID_INDEPENDENT_TOOL_SHA256",
                        ):
                            acquire_decompiler_jar(
                                "cfr", out, expected_sha256=bad,
                            )
                for bad in (0, 121, True, -5, "5"):
                    with self.subTest(timeout=bad):
                        with self.assertRaisesRegex(
                            DecompilerArtifactError, "INVALID_ARTIFACT_NETWORK_TIMEOUT",
                        ):
                            acquire_decompiler_jar(
                                "cfr", out, expected_sha256="0" * 64,
                                timeout_seconds=bad,
                            )
                remote.assert_not_called()
            self.assertFalse(out.exists())

    def test_reject_https_redirect_even_if_bytes_are_correct(self):
        data = _mock_jar()
        expected = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "redirected.jar"
            with patch(
                "spk_recovery.decompiler_tool_acquire.urlopen",
                side_effect=lambda req, timeout: _Response(
                    data, "https://untrusted.invalid/cfr.jar"
                ),
            ):
                with self.assertRaisesRegex(
                    DecompilerArtifactError, "DECOMPILER_ARTIFACT_REDIRECTED",
                ):
                    acquire_decompiler_jar(
                        "cfr", out, expected_sha256=expected,
                    )
            self.assertFalse(out.exists())

    def test_network_failure_is_redacted_and_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "network.jar"
            with patch(
                "spk_recovery.decompiler_tool_acquire.urlopen",
                side_effect=URLError("SECRET_NETWORK_CREDENTIAL"),
            ):
                with self.assertRaisesRegex(
                    DecompilerArtifactError, "DECOMPILER_ARTIFACT_NETWORK_FAILURE",
                ) as failure:
                    acquire_decompiler_jar(
                        "cfr", out, expected_sha256="0" * 64,
                    )
            self.assertNotIn(
                "SECRET_NETWORK_CREDENTIAL", str(failure.exception),
            )
            self.assertFalse(out.exists())

    def test_library_only_jar_is_refused(self):
        data = _mock_jar(executable=False)
        expected = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "library-only.jar"
            with patch(
                "spk_recovery.decompiler_tool_acquire.urlopen",
                side_effect=lambda req, timeout: _Response(data, req.full_url),
            ):
                with self.assertRaisesRegex(
                    DecompilerArtifactError,
                    "DOWNLOADED_JAR_NOT_DIRECTLY_EXECUTABLE",
                ):
                    acquire_decompiler_jar(
                        "vineflower", out, expected_sha256=expected,
                    )
            self.assertFalse(out.exists())

    def test_zip_corruption_fails_closed(self):
        data = b"this is not a JAR"
        expected = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "corrupt.jar"
            with patch(
                "spk_recovery.decompiler_tool_acquire.urlopen",
                side_effect=lambda req, timeout: _Response(data, req.full_url),
            ):
                with self.assertRaisesRegex(
                    DecompilerArtifactError, "DOWNLOADED_JAR_INVALID",
                ):
                    acquire_decompiler_jar(
                        "cfr", out, expected_sha256=expected,
                    )
            self.assertFalse(out.exists())

    def test_unsupported_engine_has_no_network_or_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bad.jar"
            with patch("spk_recovery.decompiler_tool_acquire.urlopen") as remote:
                with self.assertRaisesRegex(
                    DecompilerArtifactError, "UNSUPPORTED_DECOMPILER_ENGINE",
                ):
                    acquire_decompiler_jar(
                        "anything", out, expected_sha256="0" * 64,
                    )
                remote.assert_not_called()
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()

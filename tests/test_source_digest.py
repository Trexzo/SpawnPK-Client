from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from spk_recovery.source_digest import (
    SourceDigestError,
    canonical_source_bytes,
    source_tree_digest,
)


class SourceDigestTests(unittest.TestCase):
    def test_canonical_source_bytes_normalizes_all_line_endings(self):
        self.assertEqual(
            canonical_source_bytes(b"a\r\nb\rc\n"),
            b"a\nb\nc\n",
        )

    def test_lf_and_crlf_trees_have_identical_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lf = root / "lf"
            crlf = root / "crlf"
            (lf / "pkg").mkdir(parents=True)
            (crlf / "pkg").mkdir(parents=True)

            (lf / "pkg" / "A.java").write_bytes(
                b"package pkg;\nclass A {}\n"
            )
            (crlf / "pkg" / "A.java").write_bytes(
                b"package pkg;\r\nclass A {}\r\n"
            )

            lf_digest, lf_files, lf_bytes = source_tree_digest(lf)
            crlf_digest, crlf_files, crlf_bytes = source_tree_digest(crlf)

            self.assertEqual(lf_digest, crlf_digest)
            self.assertEqual(lf_bytes, crlf_bytes)
            self.assertEqual(
                [p.relative_to(lf).as_posix() for p in lf_files],
                ["pkg/A.java"],
            )
            self.assertEqual(
                [p.relative_to(crlf).as_posix() for p in crlf_files],
                ["pkg/A.java"],
            )

    def test_source_tree_rejects_symbolic_linked_java_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            outside = root / "outside.java"
            outside.write_text(
                "class Outside {}\n",
                encoding="utf-8",
            )
            link = source / "A.java"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(
                    f"symbolic links unavailable on this runner: {exc}"
                )

            with self.assertRaisesRegex(
                SourceDigestError,
                "symbolic link",
            ):
                source_tree_digest(source)

    def test_source_tree_rejects_java_fifo_without_reading_it(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO creation is unavailable on this platform")

        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            source.mkdir()
            fifo = source / "A.java"
            try:
                os.mkfifo(fifo)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(
                    f"FIFO creation unavailable on this runner: {exc}"
                )

            with mock.patch.object(
                Path,
                "read_bytes",
                side_effect=AssertionError("FIFO must not be read"),
            ):
                with self.assertRaisesRegex(
                    SourceDigestError,
                    "non-regular file",
                ):
                    source_tree_digest(source)

    def test_relative_path_spelling_is_still_authority_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left = root / "left"
            right = root / "right"
            (left / "pkg").mkdir(parents=True)
            (right / "other").mkdir(parents=True)

            data = b"class A {}\n"
            (left / "pkg" / "A.java").write_bytes(data)
            (right / "other" / "A.java").write_bytes(data)

            self.assertNotEqual(
                source_tree_digest(left)[0],
                source_tree_digest(right)[0],
            )


if __name__ == "__main__":
    unittest.main()

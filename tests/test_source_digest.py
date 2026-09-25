from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from spk_recovery.source_digest import (
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

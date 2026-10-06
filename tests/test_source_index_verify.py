from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.indexer import index_jar, write_index
from spk_recovery.source_index_verify_cli import (
    IndexVerificationError,
    verify_index,
)


class SourceIndexVerifyTests(unittest.TestCase):
    def make_jar(self, path: Path) -> None:
        with zipfile.ZipFile(
            path,
            "w",
            compression=zipfile.ZIP_STORED,
        ) as handle:
            handle.writestr("resource.txt", b"authority\n")

    def test_matching_index_passes_even_if_source_name_differs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar = root / "client.jar"
            self.make_jar(jar)
            index = index_jar(jar)
            index["source_name"] = "historical-client-name.jar"
            path = root / "index.json"
            write_index(index, path)

            verified = verify_index(
                jar,
                path,
                expected_sha256=index["sha256"],
            )

            self.assertEqual(
                verified["sha256"],
                index["sha256"],
            )

    def test_forged_detail_with_correct_top_level_sha_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar = root / "client.jar"
            self.make_jar(jar)
            index = index_jar(jar)
            index["entries"]["resource.txt"]["size"] += 1
            path = root / "index.json"
            write_index(index, path)

            with self.assertRaisesRegex(
                IndexVerificationError,
                "does not exactly match",
            ):
                verify_index(
                    jar,
                    path,
                    expected_sha256=index["sha256"],
                )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar = root / "client.jar"
            self.make_jar(jar)
            index = index_jar(jar)
            path = root / "index.json"
            path.write_text(
                '{"sha256":"'
                + index["sha256"]
                + '","sha256":"'
                + index["sha256"]
                + '"}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                IndexVerificationError,
                "duplicate JSON key",
            ):
                verify_index(
                    jar,
                    path,
                    expected_sha256=index["sha256"],
                )


if __name__ == "__main__":
    unittest.main()

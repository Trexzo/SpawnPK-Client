import tempfile
import unittest
from pathlib import Path
import zipfile

from spk_recovery.cross_version_binary_delta import (
    CrossVersionBinaryDeltaError,
    build_cross_version_binary_delta,
)


def _jar(path: Path, rows: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in rows.items():
            archive.writestr(name, data)


class CrossVersionBinaryDeltaTests(unittest.TestCase):
    def test_exact_entry_delta_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old.jar"
            new = root / "new.jar"
            _jar(
                old,
                {
                    "same.txt": b"same",
                    "rs/f/a.class": b"build-307",
                    "old-only.txt": b"old",
                },
            )
            _jar(
                new,
                {
                    "same.txt": b"same",
                    "rs/f/a.class": b"build-308",
                    "new-only.txt": b"new",
                },
            )

            a = build_cross_version_binary_delta(
                old,
                new,
                old_build_id="v307",
                new_build_id="v308",
            )
            b = build_cross_version_binary_delta(
                old,
                new,
                old_build_id="v307",
                new_build_id="v308",
            )

            self.assertEqual(a, b)
            self.assertTrue(a["report_id"].startswith("XVERBIN_"))
            self.assertEqual(
                a["summary"],
                {
                    "old_entry_count": 3,
                    "new_entry_count": 3,
                    "old_only_entries": 1,
                    "new_only_entries": 1,
                    "changed_entries": 1,
                    "changed_class_entries": 1,
                },
            )
            self.assertEqual(a["old_only"], ["old-only.txt"])
            self.assertEqual(a["new_only"], ["new-only.txt"])
            self.assertEqual(
                [row["path"] for row in a["changed"]],
                ["rs/f/a.class"],
            )
            self.assertTrue(a["changed"][0]["class_entry"])

    def test_duplicate_zip_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old.jar"
            new = root / "new.jar"
            with zipfile.ZipFile(old, "w") as archive:
                archive.writestr("dup.txt", b"a")
                archive.writestr("dup.txt", b"b")
            _jar(new, {"dup.txt": b"c"})
            with self.assertRaises(CrossVersionBinaryDeltaError):
                build_cross_version_binary_delta(
                    old,
                    new,
                    old_build_id="v307",
                    new_build_id="v308",
                )

    def test_same_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = root / "same.jar"
            _jar(jar, {"a.txt": b"a"})
            with self.assertRaises(CrossVersionBinaryDeltaError):
                build_cross_version_binary_delta(
                    jar,
                    jar,
                    old_build_id="v307",
                    new_build_id="v308",
                )

    def test_same_build_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old.jar"
            new = root / "new.jar"
            _jar(old, {"a.txt": b"a"})
            _jar(new, {"a.txt": b"b"})
            with self.assertRaises(CrossVersionBinaryDeltaError):
                build_cross_version_binary_delta(
                    old,
                    new,
                    old_build_id="v308",
                    new_build_id="v308",
                )


if __name__ == "__main__":
    unittest.main()

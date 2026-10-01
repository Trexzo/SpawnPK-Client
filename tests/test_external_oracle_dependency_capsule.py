from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.external_oracle_dependency_capsule_cli import (
    ExternalOracleDependencyCapsuleError,
    build_nonproject_dependency_capsule,
)
from spk_recovery.indexer import sha256_file


class ExternalOracleDependencyCapsuleTests(unittest.TestCase):
    def _fixture_jar(self, path: Path) -> None:
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("rs/a.class", b"project")
            zf.writestr("rs/ui/f.class", b"project-2")
            zf.writestr("com/example/Dep.class", b"dep")
            zf.writestr("org/example/Other.class", b"dep-2")
            zf.writestr("META-INF/MANIFEST.MF", b"ignored")

    def test_builds_deterministic_non_rs_class_capsule(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "v308.jar"
            first = root / "first.jar"
            second = root / "second.jar"
            self._fixture_jar(source)
            sha = sha256_file(source)

            report1 = build_nonproject_dependency_capsule(
                exact_v308_jar=source,
                out_jar=first,
                expected_v308_sha256=sha,
            )
            report2 = build_nonproject_dependency_capsule(
                exact_v308_jar=source,
                out_jar=second,
                expected_v308_sha256=sha,
            )

            self.assertEqual(
                report1["capsule_sha256"],
                report2["capsule_sha256"],
            )
            self.assertEqual(report1["class_count"], 2)
            self.assertEqual(report1["rs_class_count"], 0)
            self.assertEqual(
                report1["project_binary_fallback_count"],
                0,
            )
            self.assertEqual(
                report1["excluded_rs_entry_count"],
                2,
            )

            with zipfile.ZipFile(first, "r") as zf:
                names = set(zf.namelist())
            self.assertEqual(
                names,
                {
                    "com/example/Dep.class",
                    "org/example/Other.class",
                },
            )

    def test_rejects_exact_v308_hash_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "v308.jar"
            out = root / "deps.jar"
            self._fixture_jar(source)

            with self.assertRaisesRegex(
                ExternalOracleDependencyCapsuleError,
                "SHA-256 mismatch",
            ):
                build_nonproject_dependency_capsule(
                    exact_v308_jar=source,
                    out_jar=out,
                    expected_v308_sha256="0" * 64,
                )


if __name__ == "__main__":
    unittest.main()

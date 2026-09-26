from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.class_recovery_plan import (
    build_class_recovery_plan,
)
from spk_recovery.javac_diagnostics import classify_javac_diagnostics


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ClassRecoveryPlanTests(unittest.TestCase):
    def _fixture(self, root: Path):
        src = root / "src"
        t = src / "t"
        p = src / "p"
        t.mkdir(parents=True)
        p.mkdir(parents=True)

        sources = {
            t / "Same.java": "package t; public class Same {}\n",
            t / "Use.java": (
                "package t;\n"
                "import p.Imported;\n"
                "public class Use {}\n"
            ),
            p / "Imported.java": (
                "package p; public class Imported {}\n"
            ),
        }
        for path, text in sources.items():
            path.write_text(text, encoding="utf-8")

        classes = root / "classes"
        classes.mkdir()
        proc = subprocess.run(
            ["javac", "-d", str(classes), *map(str, sources.keys())],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for path in sorted(classes.rglob("*.class")):
                z.write(path, path.relative_to(classes).as_posix())

        return src, t, p, jar

    def _diag(self, source: Path, symbol: str):
        raw = (
            f"{source}:3: error: cannot find symbol\n"
            f"  symbol:   class {symbol}\n"
            "  location: class Use\n"
        )
        return classify_javac_diagnostics(
            raw,
            include_identifiers=True,
        )

    def test_project_missing_source_unit_is_recovery_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, t, _p, jar = self._fixture(root)
            (t / "Same.java").unlink()

            digest = __import__(
                "spk_recovery.source_digest",
                fromlist=["source_tree_digest"],
            ).source_tree_digest(src)[0]

            report = build_class_recovery_plan(
                self._diag(t / "Use.java", "Same"),
                jar,
                src,
                {
                    "source_tree_sha256": digest,
                    "project_source_prefixes": ["t/"],
                },
            )

            self.assertEqual(
                report["summary"]["missing_unique_class_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["responsibility_counts"],
                {"project_source_unit_missing": 1},
            )
            self.assertEqual(
                report["summary"][
                    "safe_source_recovery_candidate_count"
                ],
                1,
            )

    def test_project_identity_mismatch_is_recovery_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, t, _p, jar = self._fixture(root)
            (t / "Same.java").write_text(
                "package t; class Different {}\n",
                encoding="utf-8",
            )

            digest = __import__(
                "spk_recovery.source_digest",
                fromlist=["source_tree_digest"],
            ).source_tree_digest(src)[0]

            report = build_class_recovery_plan(
                self._diag(t / "Use.java", "Same"),
                jar,
                src,
                {
                    "source_tree_sha256": digest,
                    "project_source_prefixes": ["t/"],
                },
            )

            self.assertEqual(
                report["summary"]["responsibility_counts"],
                {"project_expected_source_identity_mismatch": 1},
            )
            self.assertEqual(
                report["summary"][
                    "safe_source_recovery_candidate_count"
                ],
                1,
            )
            self.assertTrue(
                report["candidates"][0]["expected_source_exists"]
            )

    def test_dependency_candidate_is_not_source_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, t, p, jar = self._fixture(root)
            (p / "Imported.java").unlink()

            digest = __import__(
                "spk_recovery.source_digest",
                fromlist=["source_tree_digest"],
            ).source_tree_digest(src)[0]

            report = build_class_recovery_plan(
                self._diag(t / "Use.java", "Imported"),
                jar,
                src,
                {
                    "source_tree_sha256": digest,
                    "project_source_prefixes": ["t/"],
                },
            )

            self.assertEqual(
                report["summary"]["responsibility_counts"],
                {"dependency_binary_responsibility": 1},
            )
            self.assertEqual(
                report["summary"][
                    "safe_source_recovery_candidate_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"]["dependency_responsibility_count"],
                1,
            )

    def test_public_plan_redacts_candidate_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, t, _p, jar = self._fixture(root)
            (t / "Same.java").unlink()

            digest = __import__(
                "spk_recovery.source_digest",
                fromlist=["source_tree_digest"],
            ).source_tree_digest(src)[0]

            public = build_class_recovery_plan(
                self._diag(t / "Use.java", "Same"),
                jar,
                src,
                {
                    "source_tree_sha256": digest,
                    "project_source_prefixes": ["t/"],
                },
            )
            private = build_class_recovery_plan(
                self._diag(t / "Use.java", "Same"),
                jar,
                src,
                {
                    "source_tree_sha256": digest,
                    "project_source_prefixes": ["t/"],
                },
                include_identifiers=True,
            )

            self.assertEqual(public["plan_id"], private["plan_id"])
            self.assertNotIn("t/Same", str(public))
            self.assertIn("t/Same", str(private))


if __name__ == "__main__":
    unittest.main()

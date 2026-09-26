from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.javac_class_triage import (
    analyze_unresolved_classes,
)
from spk_recovery.javac_diagnostics import classify_javac_diagnostics


@unittest.skipUnless(shutil.which("javac"), "javac required")
class JavacClassTriageTests(unittest.TestCase):
    def _fixture(self, root: Path):
        src = root / "src"
        t = src / "t"
        p = src / "p"
        q = src / "q"
        for d in (t, p, q):
            d.mkdir(parents=True)

        sources = {
            t / "Same.java": "package t; public class Same {}\n",
            t / "Outer.java": (
                "package t; public class Outer { "
                "public static class Inner {} }\n"
            ),
            t / "Use.java": (
                "package t;\n"
                "import p.Imported;\n"
                "public class Use {}\n"
            ),
            p / "Imported.java": (
                "package p; public class Imported {}\n"
            ),
            p / "Hidden.java": (
                "package p; public class Hidden {}\n"
            ),
            p / "Dup.java": "package p; public class Dup {}\n",
            q / "Dup.java": "package q; public class Dup {}\n",
        }
        for path, text in sources.items():
            path.write_text(text, encoding="utf-8")

        classes = root / "classes"
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "-d",
                str(classes),
                *[str(path) for path in sorted(sources)],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for path in sorted(classes.rglob("*.class")):
                z.write(path, path.relative_to(classes).as_posix())

        return src, t, jar

    def _run(self, src: Path, t: Path, jar: Path, symbol: str):
        raw = (
            f"{t / 'Use.java'}:3: error: cannot find symbol\n"
            f"  symbol:   class {symbol}\n"
            "  location: class Use\n"
        )
        diagnostic = classify_javac_diagnostics(
            raw,
            include_identifiers=True,
        )
        return analyze_unresolved_classes(
            diagnostic,
            jar,
            src,
            include_identifiers=True,
        )

    def test_same_package_and_explicit_import_are_visible(self):
        with tempfile.TemporaryDirectory() as td:
            src, t, jar = self._fixture(Path(td))

            same = self._run(src, t, jar, "Same")
            imported = self._run(src, t, jar, "Imported")

            self.assertEqual(
                same["summary"]["proof_classes"],
                {"java_visible_exact_class": 1},
            )
            self.assertEqual(
                imported["summary"]["proof_classes"],
                {"java_visible_exact_class": 1},
            )

    def test_same_source_nested_is_visible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src, t, jar = self._fixture(root)

            raw = (
                f"{t / 'Outer.java'}:1: error: cannot find symbol\n"
                "  symbol:   class Inner\n"
                "  location: class Outer\n"
            )
            diagnostic = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )
            report = analyze_unresolved_classes(
                diagnostic,
                jar,
                src,
                include_identifiers=True,
            )

            self.assertEqual(
                report["summary"]["proof_classes"],
                {"java_visible_exact_class": 1},
            )
            self.assertEqual(
                report["diagnostics"][0]["visible_candidates"],
                ["t/Outer$Inner"],
            )

    def test_readable_but_not_visible_is_repair_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            src, t, jar = self._fixture(Path(td))
            report = self._run(src, t, jar, "Hidden")

            self.assertEqual(
                report["summary"]["proof_classes"],
                {"readable_class_not_java_visible": 1},
            )
            self.assertEqual(
                report["summary"]["repair_candidate_diagnostic_count"],
                1,
            )
            self.assertEqual(
                report["diagnostics"][0]["global_candidates"],
                ["p/Hidden"],
            )

    def test_ambiguous_and_absent_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src, t, jar = self._fixture(Path(td))

            ambiguous = self._run(src, t, jar, "Dup")
            absent = self._run(src, t, jar, "NeverThere")

            self.assertEqual(
                ambiguous["summary"]["proof_classes"],
                {"readable_class_name_ambiguous": 1},
            )
            self.assertEqual(
                ambiguous["summary"]["ambiguous_diagnostic_count"],
                1,
            )
            self.assertEqual(
                absent["summary"]["proof_classes"],
                {"class_absent_from_readable": 1},
            )
            self.assertEqual(
                absent["summary"]["absent_diagnostic_count"],
                1,
            )

    def test_public_report_redacts_class_identities(self):
        with tempfile.TemporaryDirectory() as td:
            src, t, jar = self._fixture(Path(td))
            raw = (
                f"{t / 'Use.java'}:3: error: cannot find symbol\n"
                "  symbol:   class Hidden\n"
                "  location: class Use\n"
            )
            diagnostic = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )
            public = analyze_unresolved_classes(
                diagnostic,
                jar,
                src,
            )
            private = analyze_unresolved_classes(
                diagnostic,
                jar,
                src,
                include_identifiers=True,
            )

            self.assertEqual(public["report_id"], private["report_id"])
            self.assertFalse(public["identifiers_included"])
            self.assertTrue(private["identifiers_included"])
            serialized = json.dumps(public, sort_keys=True)
            self.assertNotIn("Hidden", serialized)
            self.assertNotIn("p/Hidden", serialized)
            self.assertNotIn(str(t / "Use.java"), serialized)


if __name__ == "__main__":
    unittest.main()

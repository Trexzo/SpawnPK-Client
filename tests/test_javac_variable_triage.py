from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.javac_diagnostics import classify_javac_diagnostics
from spk_recovery.javac_variable_triage import (
    _relative_source_path,
    analyze_unresolved_variables,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class JavacVariableTriageTests(unittest.TestCase):
    def _fixture(self, root: Path):
        source = root / "src" / "t"
        source.mkdir(parents=True)

        sources = {
            "Own.java": (
                "package t; public class Own { public int ownSecretField; }\n"
            ),
            "Base.java": (
                "package t; public class Base { "
                "protected static int inheritedSecretField; }\n"
            ),
            "Child.java": (
                "package t; public class Child extends Base {}\n"
            ),
            "Iface.java": (
                "package t; public interface Iface { int ifaceSecretField = 1; }\n"
            ),
            "Impl.java": (
                "package t; public class Impl implements Iface {}\n"
            ),
            "I1.java": (
                "package t; public interface I1 { int dupSecretField = 1; }\n"
            ),
            "I2.java": (
                "package t; public interface I2 { int dupSecretField = 2; }\n"
            ),
            "Both.java": (
                "package t; public class Both implements I1, I2 {}\n"
            ),
            "Receiver.java": (
                "package t; public class Receiver { "
                "public int recvSecretField; }\n"
            ),
            "ReceiverChild.java": (
                "package t; public class ReceiverChild extends Receiver {}\n"
            ),
            "UseReceiver.java": (
                "package t; public class UseReceiver { "
                "Receiver receiver; ReceiverChild child; }\n"
            ),
            "Imported.java": (
                "package p; public class Imported { "
                "public int importedSecretField; }\n"
            ),
            "UseImported.java": (
                "package t; import p.Imported; "
                "public class UseImported { Imported imported; }\n"
            ),
        }
        for name, text in sources.items():
            (source / name).write_text(text, encoding="utf-8")

        classes = root / "classes"
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "-d",
                str(classes),
                *[
                    str(source / name)
                    for name in sorted(sources)
                ],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for path in sorted(classes.rglob("*.class")):
                z.write(
                    path,
                    path.relative_to(classes).as_posix(),
                )
        return root / "src", source, jar

    def test_exact_field_proof_classes_and_public_redaction(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, source, jar = self._fixture(root)

            raw = "".join(
                [
                    f"{source / 'Own.java'}:1: error: cannot find symbol\n"
                    "  symbol:   variable ownSecretField\n"
                    "  location: class Own\n",
                    f"{source / 'Child.java'}:1: error: cannot find symbol\n"
                    "  symbol:   variable inheritedSecretField\n"
                    "  location: class Child\n",
                    f"{source / 'Impl.java'}:1: error: cannot find symbol\n"
                    "  symbol:   variable ifaceSecretField\n"
                    "  location: class Impl\n",
                    f"{source / 'Both.java'}:1: error: cannot find symbol\n"
                    "  symbol:   variable dupSecretField\n"
                    "  location: class Both\n",
                    f"{source / 'Child.java'}:2: error: cannot find symbol\n"
                    "  symbol:   variable absentSecretField\n"
                    "  location: class Child\n",
                ]
            )
            diagnostics = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )

            public = analyze_unresolved_variables(
                diagnostics,
                jar,
                source_root,
            )
            private = analyze_unresolved_variables(
                diagnostics,
                jar,
                source_root,
                include_identifiers=True,
            )

            self.assertEqual(
                public["summary"]["proof_classes"],
                {
                    "current_class_exact_field": 1,
                    "hierarchy_exact_field_ambiguous": 1,
                    "inherited_exact_field": 2,
                    "no_exact_field_in_hierarchy": 1,
                },
            )
            self.assertEqual(
                public["summary"]["variable_diagnostic_count"],
                5,
            )
            self.assertEqual(public["report_id"], private["report_id"])
            self.assertFalse(public["identifiers_included"])
            self.assertTrue(private["identifiers_included"])

            serialized = json.dumps(public, sort_keys=True)
            for raw_name in (
                "ownSecretField",
                "inheritedSecretField",
                "ifaceSecretField",
                "absentSecretField",
                "t/Own",
                "t/Base",
            ):
                self.assertNotIn(raw_name, serialized)

            private_by_symbol = {
                row["symbol"]: row
                for row in private["diagnostics"]
            }
            self.assertEqual(
                private_by_symbol["ownSecretField"]["proof_class"],
                "current_class_exact_field",
            )
            self.assertEqual(
                private_by_symbol["inheritedSecretField"]["matches"][0]["owner"],
                "t/Base",
            )
            self.assertEqual(
                private_by_symbol["ifaceSecretField"]["matches"][0]["owner"],
                "t/Iface",
            )
            self.assertEqual(
                private_by_symbol["dupSecretField"]["proof_class"],
                "hierarchy_exact_field_ambiguous",
            )
            self.assertEqual(
                len(private_by_symbol["dupSecretField"]["matches"]),
                2,
            )

    def test_variable_location_resolves_same_package_receiver_and_hierarchy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, source, jar = self._fixture(root)

            raw = "".join(
                [
                    f"{source / 'UseReceiver.java'}:1: error: cannot find symbol\n"
                    "  symbol:   variable recvSecretField\n"
                    "  location: variable receiver of type Receiver\n",
                    f"{source / 'UseReceiver.java'}:2: error: cannot find symbol\n"
                    "  symbol:   variable recvSecretField\n"
                    "  location: variable child of type ReceiverChild\n",
                ]
            )
            diagnostics = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )
            report = analyze_unresolved_variables(
                diagnostics,
                jar,
                source_root,
                include_identifiers=True,
            )

            self.assertEqual(
                report["summary"]["proof_classes"],
                {
                    "current_class_exact_field": 1,
                    "inherited_exact_field": 1,
                },
            )
            rows = report["diagnostics"]
            self.assertEqual(
                rows[0]["owner_resolution"],
                "variable_location_owner_exact",
            )
            self.assertEqual(
                rows[0]["diagnostic_owner"],
                "t/Receiver",
            )
            self.assertEqual(
                rows[1]["diagnostic_owner"],
                "t/ReceiverChild",
            )

    def test_variable_location_resolves_explicit_import(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, source, jar = self._fixture(root)

            raw = (
                f"{source / 'UseImported.java'}:1: error: cannot find symbol\n"
                "  symbol:   variable importedSecretField\n"
                "  location: variable imported of type Imported\n"
            )
            diagnostics = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )
            report = analyze_unresolved_variables(
                diagnostics,
                jar,
                source_root,
                include_identifiers=True,
            )

            row = report["diagnostics"][0]
            self.assertEqual(
                row["proof_class"],
                "current_class_exact_field",
            )
            self.assertEqual(
                row["diagnostic_owner"],
                "p/Imported",
            )
            self.assertEqual(
                row["owner_resolution"],
                "variable_location_owner_exact",
            )

    def test_variable_location_malformed_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, source, jar = self._fixture(root)

            raw = (
                f"{source / 'UseReceiver.java'}:1: error: cannot find symbol\n"
                "  symbol:   variable recvSecretField\n"
                "  location: variable receiver\n"
            )
            diagnostics = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )
            report = analyze_unresolved_variables(
                diagnostics,
                jar,
                source_root,
            )

            self.assertEqual(
                report["summary"]["proof_classes"],
                {"variable_location_malformed": 1},
            )

    def test_triage_id_uses_stable_frontier_not_raw_report_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, source, jar = self._fixture(root)
            raw = (
                f"{source / 'Own.java'}:1: error: cannot find symbol\n"
                "  symbol:   variable ownSecretField\n"
                "  location: class Own\n"
            )

            first_diag = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )
            second_diag = classify_javac_diagnostics(
                raw + "\n",
                include_identifiers=True,
            )

            self.assertNotEqual(
                first_diag["report_id"],
                second_diag["report_id"],
            )
            self.assertEqual(
                first_diag["frontier_id"],
                second_diag["frontier_id"],
            )

            first = analyze_unresolved_variables(
                first_diag,
                jar,
                source_root,
            )
            second = analyze_unresolved_variables(
                second_diag,
                jar,
                source_root,
            )

            self.assertEqual(first["report_id"], second["report_id"])
            self.assertEqual(
                first["diagnostic_frontier_id"],
                second["diagnostic_frontier_id"],
            )

    def test_legacy_private_report_derives_same_stable_frontier(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, source, jar = self._fixture(root)
            raw = (
                f"{source / 'Own.java'}:1: error: cannot find symbol\n"
                "  symbol:   variable ownSecretField\n"
                "  location: class Own\n"
            )
            diagnostic = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )
            expected_frontier = diagnostic["frontier_id"]
            legacy = dict(diagnostic)
            legacy.pop("frontier_id")

            report = analyze_unresolved_variables(
                legacy,
                jar,
                source_root,
            )

            self.assertEqual(
                report["diagnostic_frontier_id"],
                expected_frontier,
            )
            self.assertTrue(
                report[
                    "diagnostic_frontier_derived_from_legacy_report"
                ]
            )

    def test_tampered_frontier_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, source, jar = self._fixture(root)
            raw = (
                f"{source / 'Own.java'}:1: error: cannot find symbol\n"
                "  symbol:   variable ownSecretField\n"
                "  location: class Own\n"
            )
            diagnostic = classify_javac_diagnostics(
                raw,
                include_identifiers=True,
            )
            diagnostic["frontier_id"] = (
                "JAVACFRONTIER_" + "0" * 20
            )

            with self.assertRaisesRegex(
                ValueError,
                "frontier authority is invalid",
            ):
                analyze_unresolved_variables(
                    diagnostic,
                    jar,
                    source_root,
                )

    def test_requires_identifier_opt_in_diagnostic_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, source, jar = self._fixture(root)
            raw = (
                f"{source / 'Own.java'}:1: error: cannot find symbol\n"
                "  symbol:   variable ownSecretField\n"
                "  location: class Own\n"
            )
            diagnostics = classify_javac_diagnostics(raw)
            with self.assertRaisesRegex(
                ValueError,
                "--include-identifiers",
            ):
                analyze_unresolved_variables(
                    diagnostics,
                    jar,
                    source_root,
                )

    def test_windows_spelling_is_bound_without_folding_suffix_case(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "src"
            root.mkdir()
            target = root / "rs" / "A.java"
            target.parent.mkdir()
            target.write_text("class A {}\n", encoding="utf-8")

            windows_spelling = str(target).replace("/", "\\")
            rel = _relative_source_path(
                windows_spelling,
                root,
            )
            self.assertEqual(rel, "rs/A.java")


if __name__ == "__main__":
    unittest.main()

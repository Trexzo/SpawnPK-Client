from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.source_symbol_probe_cli import probe_source_symbols


class SourceSymbolProbeTests(unittest.TestCase):
    def test_correlates_hierarchy_fields_and_exact_invocation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "compile" / "p"
            classes = root / "classes"
            src.mkdir(parents=True)
            classes.mkdir()

            (src / "Base.java").write_text(
                "package p; public class Base { protected int n5 = 4; }\n",
                encoding="utf-8",
            )
            (src / "Target.java").write_text(
                "package p; public class Target extends Base {\n"
                " private int navigationButtonAdded2 = 3;\n"
                " private void clientShutdown() {}\n"
                " public int a(int x) { clientShutdown(); return navigationButtonAdded2 + n5 + x; }\n"
                "}\n",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                ["javac", "-d", str(classes), str(src / "Base.java"), str(src / "Target.java")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)

            jar = root / "readable.jar"
            with zipfile.ZipFile(jar, "w") as zf:
                for class_file in classes.rglob("*.class"):
                    zf.write(class_file, class_file.relative_to(classes).as_posix())

            recovered = root / "recovered"
            target = recovered / "p" / "Target.java"
            target.parent.mkdir(parents=True)
            target.write_text(
                "package p; public class Target extends Base {\n"
                " public int a(int x) { clientShutdown(); return navigationButtonAdded2 + n5 + x; }\n"
                "}\n",
                encoding="utf-8",
            )

            report = probe_source_symbols(
                source_root=recovered,
                readable_jar=jar,
                source_path="p/Target.java",
                symbols=["navigationButtonAdded2", "n5", "clientShutdown"],
            )

            self.assertEqual(report["current_owner"], "p/Target")
            self.assertEqual(
                report["hierarchy_field_declarations"]["navigationButtonAdded2"][0]["declaring_owner"],
                "p/Target",
            )
            self.assertEqual(
                report["hierarchy_field_declarations"]["n5"][0]["declaring_owner"],
                "p/Base",
            )

            method = report["methods"][0]
            self.assertEqual(method["source_method"], "a")
            self.assertEqual(len(method["exact_candidates"]), 1)
            exact = method["exact_candidates"][0]
            self.assertEqual(exact["descriptor"], "(I)I")
            self.assertEqual(
                {row["name"] for row in exact["field_accesses"]},
                {"navigationButtonAdded2", "n5"},
            )
            self.assertEqual(len(exact["method_invocations"]), 1)
            self.assertEqual(exact["method_invocations"][0]["name"], "clientShutdown")
            self.assertEqual(exact["method_invocations"][0]["owner"], "p/Target")

    def test_rejects_invalid_symbol_before_reading_jar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text("package p; class A {}\n", encoding="utf-8")
            jar = root / "empty.jar"
            with zipfile.ZipFile(jar, "w"):
                pass

            with self.assertRaisesRegex(ValueError, "not a Java identifier"):
                probe_source_symbols(
                    source_root=root,
                    readable_jar=jar,
                    source_path="p/A.java",
                    symbols=["bad.name"],
                )


if __name__ == "__main__":
    unittest.main()

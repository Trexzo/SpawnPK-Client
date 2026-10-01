from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.source_owner_probe_cli import probe_source_owner


class SourceOwnerProbeTests(unittest.TestCase):
    def test_reports_alternate_exact_static_owner_without_rewriting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "compile" / "p"
            classes = root / "classes"
            src.mkdir(parents=True)
            classes.mkdir()

            (src / "Ref.java").write_text(
                "package p; public class Ref {}\n",
                encoding="utf-8",
            )
            (src / "b.java").write_text(
                "package p; public class b { "
                "public static int j = 1; public static int f = 2; }\n",
                encoding="utf-8",
            )
            (src / "Real.java").write_text(
                "package p; public class Real { "
                "public static int j = 7; public static int f = 9; }\n",
                encoding="utf-8",
            )
            (src / "A.java").write_text(
                "package p;\n"
                "public class A {\n"
                "    public Ref b;\n"
                "    public int read() { return Real.j + Real.f; }\n"
                "}\n",
                encoding="utf-8",
            )

            compiled = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(classes),
                    str(src / "Ref.java"),
                    str(src / "b.java"),
                    str(src / "Real.java"),
                    str(src / "A.java"),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                compiled.returncode,
                0,
                compiled.stdout + compiled.stderr,
            )

            jar = root / "readable.jar"
            with zipfile.ZipFile(jar, "w") as zf:
                for class_file in classes.rglob("*.class"):
                    zf.write(
                        class_file,
                        class_file.relative_to(classes).as_posix(),
                    )

            recovered = root / "recovered"
            target = recovered / "p" / "A.java"
            target.parent.mkdir(parents=True)
            target.write_text(
                "package p;\n"
                "public class A {\n"
                "    public Ref b;\n"
                "    public int read() { return b.j + b.f; }\n"
                "}\n",
                encoding="utf-8",
            )

            report = probe_source_owner(
                source_root=recovered,
                readable_jar=jar,
                source_path="p/A.java",
                owner_simple="b",
            )

            self.assertTrue(report["same_package_class_exists"])
            self.assertEqual(report["same_package_owner"], "p/b")
            self.assertEqual(len(report["hierarchy_bindings"]), 1)
            self.assertEqual(
                report["hierarchy_bindings"][0]["descriptor"],
                "Lp/Ref;",
            )

            method = report["methods"][0]
            self.assertEqual(
                method["source_field_counts"],
                {"f": 1, "j": 1},
            )
            self.assertFalse(method["reference_parameter_shadow"])
            self.assertEqual(
                method["reference_local_shadow_scope_count"],
                0,
            )

            exact = method["exact_candidates"]
            self.assertEqual(len(exact), 1)
            self.assertEqual(exact[0]["descriptor"], "()I")
            self.assertFalse(exact[0]["same_package_complete_match"])
            owners = {
                row["owner"]
                for row in exact[0]["field_accesses"]
                if row["operation"] == "getstatic"
            }
            self.assertEqual(owners, {"p/Real"})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.bytecode_method_probe_cli import build_report
from spk_recovery.bytecode_profile import BytecodeProfileError


class BytecodeMethodProbeCliTests(unittest.TestCase):
    def test_reports_local_slot_flow_for_dimension_method(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src" / "p"
            classes = root / "classes"
            src.mkdir(parents=True)
            classes.mkdir(parents=True)

            source = src / "A.java"
            source.write_text(
                "package p;\n"
                "import java.awt.Dimension;\n"
                "public class A {\n"
                "    public int bound(int x) {\n"
                "        int y = Math.min(x, 10);\n"
                "        Dimension d = new Dimension(y, 5);\n"
                "        return d.width;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            compiled = subprocess.run(
                ["javac", "-d", str(classes), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                compiled.returncode,
                0,
                compiled.stdout + compiled.stderr,
            )

            jar = root / "fixture.jar"
            with zipfile.ZipFile(jar, "w") as archive:
                for path in sorted(classes.rglob("*.class")):
                    archive.write(
                        path,
                        path.relative_to(classes).as_posix(),
                    )

            report = build_report(
                jar,
                "p/A.class",
                "bound",
                "(I)I",
            )
            instructions = report["instructions"]

            self.assertEqual(report["internal_name"], "p/A")
            self.assertTrue(
                report["probe_id"].startswith("BYTECODEMETHOD_")
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "iload"
                    and row.get("local_index") == 1
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "bipush"
                    and row.get("int_constant") == 10
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "invokestatic"
                    and row.get("owner") == "java/lang/Math"
                    and row.get("name") == "min"
                    and row.get("descriptor") == "(II)I"
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "istore"
                    and row.get("local_index") == 2
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "new"
                    and row.get("type") == "java/awt/Dimension"
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "invokespecial"
                    and row.get("owner") == "java/awt/Dimension"
                    and row.get("name") == "<init>"
                    and row.get("descriptor") == "(II)V"
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "astore"
                    and row.get("local_index") == 3
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "getfield"
                    and row.get("owner") == "java/awt/Dimension"
                    and row.get("name") == "width"
                    for row in instructions
                )
            )

            repeated = build_report(
                jar,
                "p/A.class",
                "bound",
                "(I)I",
            )
            self.assertEqual(
                repeated["probe_id"],
                report["probe_id"],
            )

    def test_requires_exact_method_descriptor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = root / "empty.jar"
            with zipfile.ZipFile(jar, "w"):
                pass
            with self.assertRaises((BytecodeProfileError, KeyError)):
                build_report(
                    jar,
                    "p/A.class",
                    "bound",
                    "()V",
                )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses


class BytecodeMethodInvocationProfileTests(unittest.TestCase):
    def test_profiles_exact_method_invocation_operations_and_owners(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "p"
            classes = root / "classes"
            source.mkdir(parents=True)
            classes.mkdir(parents=True)

            (source / "B.java").write_text(
                "package p;\n"
                "public class B {\n"
                "    public B() {}\n"
                "    public static int s(int x) { return x + 1; }\n"
                "    public int v(int x) { return x + 2; }\n"
                "}\n",
                encoding="utf-8",
            )
            (source / "A.java").write_text(
                "package p;\n"
                "public class A {\n"
                "    public static int run() {\n"
                "        B b = new B();\n"
                "        return B.s(1) + b.v(2);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            compiled = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(classes),
                    str(source / "B.java"),
                    str(source / "A.java"),
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

            profile = profile_class_field_accesses(
                (classes / "p" / "A.class").read_bytes()
            )
            method = next(
                row
                for row in profile["methods"]
                if row["name"] == "run"
                and row["descriptor"] == "()I"
            )
            observed = {
                (
                    row["operation"],
                    row["owner"],
                    row["name"],
                    row["descriptor"],
                )
                for row in method["method_invocations"]
            }

            self.assertIn(
                ("invokespecial", "p/B", "<init>", "()V"),
                observed,
            )
            self.assertIn(
                ("invokestatic", "p/B", "s", "(I)I"),
                observed,
            )
            self.assertIn(
                ("invokevirtual", "p/B", "v", "(I)I"),
                observed,
            )


if __name__ == "__main__":
    unittest.main()

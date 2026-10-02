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

            (source / "I.java").write_text(
                "package p;\n"
                "public interface I { int f(int x); }\n",
                encoding="utf-8",
            )
            (source / "B.java").write_text(
                "package p;\n"
                "public class B implements I {\n"
                "    public B() {}\n"
                "    public static int s(int x) { return x + 1; }\n"
                "    public int v(int x) { return x + 2; }\n"
                "    public int f(int x) { return x + 3; }\n"
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
                "    public static int runInterface(I i) {\n"
                "        return i.f(3);\n"
                "    }\n"
                "    public static String concat(String value) {\n"
                "        return \"value=\" + value;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            compiled = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(classes),
                    str(source / "I.java"),
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

            instructions = method["instructions"]
            self.assertTrue(
                any(
                    row.get("mnemonic") == "new"
                    and row.get("type") == "p/B"
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "astore"
                    and row.get("local_index") == 0
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "aload"
                    and row.get("local_index") == 0
                    for row in instructions
                )
            )
            self.assertTrue(
                any(
                    row.get("mnemonic") == "invokestatic"
                    and row.get("owner") == "p/B"
                    and row.get("name") == "s"
                    for row in instructions
                )
            )

            interface_method = next(
                row
                for row in profile["methods"]
                if row["name"] == "runInterface"
                and row["descriptor"] == "(Lp/I;)I"
            )
            interface_observed = {
                (
                    row["operation"],
                    row["owner"],
                    row["name"],
                    row["descriptor"],
                )
                for row in interface_method["method_invocations"]
            }
            self.assertIn(
                ("invokeinterface", "p/I", "f", "(I)I"),
                interface_observed,
            )

            dynamic_method = next(
                row
                for row in profile["methods"]
                if row["name"] == "concat"
                and row["descriptor"]
                == "(Ljava/lang/String;)Ljava/lang/String;"
            )
            dynamic = [
                row
                for row in dynamic_method["method_invocations"]
                if row["operation"] == "invokedynamic"
            ]
            self.assertEqual(len(dynamic), 1)
            self.assertEqual(
                dynamic[0]["descriptor"],
                "(Ljava/lang/String;)Ljava/lang/String;",
            )
            self.assertIsInstance(
                dynamic[0]["bootstrap_method_attr_index"],
                int,
            )
            self.assertGreaterEqual(
                dynamic[0]["bootstrap_method_attr_index"],
                0,
            )

            dynamic_instructions = [
                row
                for row in dynamic_method["instructions"]
                if row.get("mnemonic") == "invokedynamic"
            ]
            self.assertEqual(len(dynamic_instructions), 1)
            self.assertEqual(
                dynamic_instructions[0]["descriptor"],
                "(Ljava/lang/String;)Ljava/lang/String;",
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from spk_recovery.bytecode_profile import (
    BytecodeProfileError,
    _bootstrap_methods_profile,
    _decoded_instructions,
    _signature_attribute_value,
    profile_class_field_accesses,
    profile_class_utf8_constants,
)


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


    def test_bootstrap_profile_rejects_out_of_range_constant_pool_indices(self):
        method_handle_cp = [
            None,
            (15, 6, 99),
        ]
        payload = bytes.fromhex("000100010000")
        with self.assertRaises(BytecodeProfileError):
            _bootstrap_methods_profile(payload, method_handle_cp)

        argument_cp = [
            None,
            (15, 6, 2),
            (10, 3, 4),
            (7, 5),
            (12, 6, 7),
            (1, "p/A"),
            (1, "impl"),
            (1, "()V"),
        ]
        payload = bytes.fromhex("0001000100010063")
        with self.assertRaises(BytecodeProfileError):
            _bootstrap_methods_profile(payload, argument_cp)

    def test_bootstrap_profile_rejects_invalid_method_handle_kind(self):
        cp = [
            None,
            (15, 0, 2),
            (10, 3, 4),
            (7, 5),
            (12, 6, 7),
            (1, "p/A"),
            (1, "impl"),
            (1, "()V"),
        ]
        payload = bytes.fromhex("000100010000")
        with self.assertRaises(BytecodeProfileError):
            _bootstrap_methods_profile(payload, cp)

    def test_profiles_exact_field_signature_attribute(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "p"
            classes = root / "classes"
            source.mkdir(parents=True)
            classes.mkdir(parents=True)

            (source / "A.java").write_text(
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public List<String> values;\n"
                "    public int plain;\n"
                "}\n",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(classes),
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
            values = next(
                row
                for row in profile["fields"]
                if row["name"] == "values"
            )
            plain = next(
                row
                for row in profile["fields"]
                if row["name"] == "plain"
            )
            self.assertEqual(
                values["descriptor"],
                "Ljava/util/List;",
            )
            self.assertEqual(
                values["signature"],
                "Ljava/util/List<Ljava/lang/String;>;",
            )
            self.assertEqual(plain["descriptor"], "I")
            self.assertIsNone(plain["signature"])

    def test_profiles_exact_method_signature_attribute(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "p"
            classes = root / "classes"
            source.mkdir(parents=True)
            classes.mkdir(parents=True)

            (source / "A.java").write_text(
                "package p;\n"
                "import java.util.Collections;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static List<String> values(String prefix) {\n"
                "        return Collections.singletonList(prefix);\n"
                "    }\n"
                "    public static String plain(String value) {\n"
                "        return value;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(classes),
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
            values = next(
                row
                for row in profile["methods"]
                if row["name"] == "values"
            )
            plain = next(
                row
                for row in profile["methods"]
                if row["name"] == "plain"
            )
            self.assertEqual(
                values["descriptor"],
                "(Ljava/lang/String;)Ljava/util/List;",
            )
            self.assertEqual(
                values["signature"],
                "(Ljava/lang/String;)Ljava/util/List<Ljava/lang/String;>;",
            )
            self.assertIsNone(plain["signature"])

    def test_signature_attribute_profile_fails_closed_on_malformed_payload(self):
        with self.assertRaises(BytecodeProfileError):
            _signature_attribute_value(
                b"\x00",
                [None, (1, "()V")],
                role="test method",
            )
        with self.assertRaises(BytecodeProfileError):
            _signature_attribute_value(
                b"\x00\x02",
                [None, (1, "()V")],
                role="test method",
            )
        with self.assertRaises(BytecodeProfileError):
            _signature_attribute_value(
                b"\x00\x01",
                [None, (3, 7)],
                role="test method",
            )

    def test_profiles_lambda_bootstrap_implementation_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "p"
            classes = root / "classes"
            source.mkdir(parents=True)
            classes.mkdir(parents=True)

            (source / "A.java").write_text(
                "package p;\n"
                "import java.util.function.Predicate;\n"
                "public class A {\n"
                "    public static Predicate<String> make(String prefix) {\n"
                "        return value -> value.startsWith(prefix);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(classes),
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
                if row["name"] == "make"
                and row["descriptor"]
                == "(Ljava/lang/String;)Ljava/util/function/Predicate;"
            )
            dynamic = [
                row
                for row in method["method_invocations"]
                if row["operation"] == "invokedynamic"
            ]
            self.assertEqual(len(dynamic), 1)

            bootstrap_index = dynamic[0][
                "bootstrap_method_attr_index"
            ]
            bootstrap = profile["bootstrap_methods"][
                bootstrap_index
            ]
            self.assertEqual(bootstrap["index"], bootstrap_index)
            self.assertEqual(
                bootstrap["bootstrap_method"]["owner"],
                "java/lang/invoke/LambdaMetafactory",
            )
            self.assertEqual(
                bootstrap["bootstrap_method"]["name"],
                "metafactory",
            )

            method_handles = [
                row["method_handle"]
                for row in bootstrap["arguments"]
                if row["kind"] == "method_handle"
            ]
            implementation = next(
                row
                for row in method_handles
                if row["owner"] == "p/A"
            )
            self.assertEqual(
                implementation["descriptor"],
                "(Ljava/lang/String;Ljava/lang/String;)Z",
            )
            self.assertEqual(
                implementation["target_kind"],
                "method",
            )
            self.assertEqual(
                implementation["reference_kind"],
                6,
            )

            method_types = [
                row["descriptor"]
                for row in bootstrap["arguments"]
                if row["kind"] == "method_type"
            ]
            self.assertIn("(Ljava/lang/Object;)Z", method_types)
            self.assertIn("(Ljava/lang/String;)Z", method_types)

    def test_profiles_exact_utf8_constants(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "p"
            classes = root / "classes"
            source.mkdir(parents=True)
            classes.mkdir(parents=True)
            (source / "A.java").write_text(
                "package p;\n"
                "public class A {\n"
                "    public static final String VALUE = \"marker-value\";\n"
                "}\n",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(classes),
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

            constants = profile_class_utf8_constants(
                (classes / "p" / "A.class").read_bytes()
            )
            self.assertIn("marker-value", constants)
            self.assertIn("Ljava/lang/String;", constants)
            self.assertEqual(constants, sorted(set(constants)))

    def test_profiles_signed_branch_targets_on_instruction_offsets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "p"
            classes = root / "classes"
            source.mkdir(parents=True)
            classes.mkdir(parents=True)

            (source / "A.java").write_text(
                "package p;\n"
                "public class A {\n"
                "    public static int sumEvenDown(int value) {\n"
                "        int total = 0;\n"
                "        while (value > 0) {\n"
                "            if ((value & 1) == 0) {\n"
                "                total += value;\n"
                "            }\n"
                "            value--;\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(classes),
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
                if row["name"] == "sumEvenDown"
                and row["descriptor"] == "(I)I"
            )
            instructions = method["instructions"]
            offsets = {row["offset"] for row in instructions}
            branches = [
                row
                for row in instructions
                if "branch_target_offset" in row
            ]
            self.assertTrue(branches)
            self.assertTrue(
                any(
                    row["branch_target_offset"] > row["offset"]
                    for row in branches
                )
            )
            self.assertTrue(
                any(
                    row["branch_target_offset"] < row["offset"]
                    for row in branches
                )
            )
            self.assertTrue(
                all(
                    row["branch_target_offset"] in offsets
                    for row in branches
                )
            )

    def test_profiles_signed_wide_branch_target_offsets(self):
        forward = _decoded_instructions(
            bytes([0xC8, 0x00, 0x00, 0x00, 0x05, 0xB1]),
            [None],
        )
        self.assertEqual(forward[0]["offset"], 0)
        self.assertEqual(forward[0]["opcode"], "0xc8")
        self.assertEqual(forward[0]["branch_target_offset"], 5)
        self.assertEqual(forward[1]["offset"], 5)

        backward = _decoded_instructions(
            bytes([0x00, 0xC8, 0xFF, 0xFF, 0xFF, 0xFF]),
            [None],
        )
        self.assertEqual(backward[1]["offset"], 1)
        self.assertEqual(backward[1]["branch_target_offset"], 0)

    def test_truncated_branch_target_profiles_fail_closed(self):
        with self.assertRaises(BytecodeProfileError):
            _decoded_instructions(bytes([0x99, 0x00]), [None])
        with self.assertRaises(BytecodeProfileError):
            _decoded_instructions(
                bytes([0xC8, 0x00, 0x00, 0x00]),
                [None],
            )


if __name__ == "__main__":
    unittest.main()

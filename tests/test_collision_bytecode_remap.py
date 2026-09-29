from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.classfile import parse_class
from spk_recovery.collision_bytecode_remap import (
    CollisionBytecodeRemapError,
    remap_class_bytes,
    transform_collision_jar,
)
from spk_recovery.namespace_collision import (
    analyze_namespace_collisions,
)
from spk_recovery.namespace_collision_plan import (
    build_namespace_collision_plan,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class CollisionBytecodeRemapTests(unittest.TestCase):
    def _compile(
        self,
        out: Path,
        sources: dict[Path, str],
    ) -> None:
        for path, text in sources.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(out),
                *[str(path) for path in sources],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )

    def _collision_fixture(self, root: Path):
        classes_a = root / "classes-a"
        classes_b = root / "classes-b"
        classes_a.mkdir()
        classes_b.mkdir()

        self._compile(
            classes_a,
            {
                root / "src-a" / "a" / "b.java": (
                    "package a; "
                    "public class b { "
                    "public static int VALUE = 7; "
                    "public static class Inner {} "
                    "}\n"
                ),
                root / "src-a" / "a" / "Ref.java": (
                    "package a; "
                    "public class Ref { "
                    "public b field; "
                    "public b.Inner nested; "
                    "}\n"
                ),
            },
        )

        self._compile(
            classes_b,
            {
                root / "src-b" / "a" / "b" / "c" / "Target.java": (
                    "package a.b.c; "
                    "public class Target {}\n"
                ),
            },
        )

        jar = root / "collision.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for base in (classes_a, classes_b):
                for path in sorted(base.rglob("*.class")):
                    z.write(path, path.relative_to(base).as_posix())
            z.writestr("config/test.txt", b"resource-authority")

        collision = analyze_namespace_collisions(jar)
        self.assertGreater(
            collision["summary"]["collision_edge_count"],
            0,
        )

        private_plan = build_namespace_collision_plan(
            jar,
            include_identifiers=True,
        )
        plan_path = root / "private-plan.json"
        plan_path.write_text(
            json.dumps(private_plan, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return jar, private_plan, plan_path

    def _javac_probe(
        self,
        root: Path,
        classpath: Path,
        source_text: str,
        name: str,
    ) -> subprocess.CompletedProcess[str]:
        src = root / f"{name}.java"
        out = root / f"{name}-classes"
        out.mkdir(exist_ok=True)
        src.write_text(source_text, encoding="utf-8")
        return subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-classpath",
                str(classpath),
                "-d",
                str(out),
                str(src),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_transform_eliminates_collision_and_restores_javac_addressability(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_jar, plan, plan_path = self._collision_fixture(root)

            before = self._javac_probe(
                root,
                input_jar,
                "import a.b.c.Target; "
                "public class BeforeProbe { Target t; }\n",
                "BeforeProbe",
            )
            self.assertNotEqual(before.returncode, 0)

            output_jar = root / "remapped.jar"
            report = transform_collision_jar(
                input_jar,
                plan_path,
                output_jar,
            )

            self.assertEqual(
                report["summary"]["post_collision_edge_count"],
                0,
            )
            self.assertGreaterEqual(
                report["summary"]["nested_family_added_count"],
                1,
            )
            self.assertGreater(
                report["summary"]["rewritten_class_count"],
                0,
            )
            self.assertTrue(output_jar.is_file())

            after = self._javac_probe(
                root,
                output_jar,
                "import a.b.c.Target; "
                "public class AfterProbe { Target t; }\n",
                "AfterProbe",
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

            with zipfile.ZipFile(output_jar) as z:
                self.assertEqual(
                    z.read("config/test.txt"),
                    b"resource-authority",
                )

            blocker = next(
                row
                for row in plan["remaps"]
                if row["old_internal_name"] == "a/b"
            )
            new_outer = blocker["new_internal_name"]
            new_inner = new_outer + "$Inner"

            with zipfile.ZipFile(output_jar) as z:
                self.assertIn(new_outer + ".class", z.namelist())
                self.assertIn(new_inner + ".class", z.namelist())
                self.assertNotIn("a/b.class", z.namelist())
                self.assertNotIn("a/b$Inner.class", z.namelist())

                ref = parse_class(z.read("a/Ref.class"))
                descriptors = {
                    field["descriptor"]
                    for field in ref.fields
                }
                self.assertIn("L" + new_outer + ";", descriptors)
                self.assertIn("L" + new_inner + ";", descriptors)

            new_simple = new_outer.rsplit("/", 1)[-1]
            nested_probe = self._javac_probe(
                root,
                output_jar,
                (
                    f"import a.{new_simple}; "
                    f"public class NestedProbe {{ "
                    f"{new_simple} outer; "
                    f"{new_simple}.Inner inner; "
                    f"}}\n"
                ),
                "NestedProbe",
            )
            self.assertEqual(
                nested_probe.returncode,
                0,
                nested_probe.stdout + nested_probe.stderr,
            )

    def test_transform_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_jar, _plan, plan_path = self._collision_fixture(root)

            out_a = root / "a.jar"
            out_b = root / "b.jar"

            report_a = transform_collision_jar(
                input_jar,
                plan_path,
                out_a,
            )
            report_b = transform_collision_jar(
                input_jar,
                plan_path,
                out_b,
            )

            sha_a = hashlib.sha256(out_a.read_bytes()).hexdigest()
            sha_b = hashlib.sha256(out_b.read_bytes()).hexdigest()

            self.assertEqual(sha_a, sha_b)
            self.assertEqual(
                report_a["transform_id"],
                report_b["transform_id"],
            )
            self.assertEqual(
                report_a["output_jar_sha256"],
                report_b["output_jar_sha256"],
            )

    def test_signed_jar_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_jar, plan, _plan_path = self._collision_fixture(root)

            signed = root / "signed.jar"
            with zipfile.ZipFile(input_jar) as src, zipfile.ZipFile(
                signed,
                "w",
                zipfile.ZIP_STORED,
            ) as dst:
                for name in src.namelist():
                    dst.writestr(name, src.read(name))
                dst.writestr("META-INF/TEST.SF", b"signature")

            plan["readable_jar_sha256"] = hashlib.sha256(
                signed.read_bytes()
            ).hexdigest()
            plan_path = root / "signed-plan.json"
            plan_path.write_text(
                json.dumps(plan, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CollisionBytecodeRemapError,
                "signed JAR",
            ):
                transform_collision_jar(
                    signed,
                    plan_path,
                    root / "out.jar",
                )

    def test_exact_class_utf8_does_not_rename_shared_method_name(self):
        # A root-level class identity can have the same Utf8 spelling as
        # an ordinary method name. Exact class remapping must retarget the
        # CONSTANT_Class reference without mutating the method name.
        cp = [
            None,
            bytes([1]) + struct.pack(">H", 1) + b"h",
            bytes([7]) + struct.pack(">H", 1),
            bytes([1])
            + struct.pack(">H", len(b"java/lang/Object"))
            + b"java/lang/Object",
            bytes([7]) + struct.pack(">H", 3),
            bytes([1]) + struct.pack(">H", 6) + b"<init>",
            bytes([1]) + struct.pack(">H", 3) + b"()V",
            bytes([1]) + struct.pack(">H", 4) + b"Code",
            bytes([12]) + struct.pack(">HH", 5, 6),
            bytes([10]) + struct.pack(">HH", 4, 8),
        ]

        init_code = (
            struct.pack(">HHI", 1, 1, 5)
            + b"\x2a\xb7\x00\x09\xb1"
            + struct.pack(">H", 0)
            + struct.pack(">H", 0)
        )
        init_method = (
            struct.pack(">HHHH", 0x0001, 5, 6, 1)
            + struct.pack(">HI", 7, len(init_code))
            + init_code
        )

        shared_name_code = (
            struct.pack(">HHI", 0, 0, 1)
            + b"\xb1"
            + struct.pack(">H", 0)
            + struct.pack(">H", 0)
        )
        shared_name_method = (
            struct.pack(">HHHH", 0x0009, 1, 6, 1)
            + struct.pack(">HI", 7, len(shared_name_code))
            + shared_name_code
        )

        data = (
            b"\xca\xfe\xba\xbe"
            + struct.pack(">HHH", 0, 49, len(cp))
            + b"".join(entry for entry in cp[1:] if entry is not None)
            + struct.pack(">HHH", 0x0021, 2, 4)
            + struct.pack(">H", 0)
            + struct.pack(">H", 0)
            + struct.pack(">H", 2)
            + init_method
            + shared_name_method
            + struct.pack(">H", 0)
        )

        parsed = parse_class(data)
        self.assertEqual(parsed.name, "h")
        self.assertIn("h", {method["name"] for method in parsed.methods})

        rewritten, changed_utf8 = remap_class_bytes(
            data,
            {"h": "Recovered_JNSBLOCKER_0076"},
        )

        reparsed = parse_class(rewritten)
        self.assertEqual(
            reparsed.name,
            "Recovered_JNSBLOCKER_0076",
        )
        method_names = {
            method["name"]
            for method in reparsed.methods
        }
        self.assertIn("h", method_names)
        self.assertNotIn(
            "Recovered_JNSBLOCKER_0076",
            method_names,
        )
        self.assertGreaterEqual(changed_utf8, 1)

    def test_constant_string_alias_preserves_literal_and_rewrites_structure(self):
        # Minimal valid class where CONSTANT_Class and CONSTANT_String
        # deliberately share the same Utf8 "a/b". The structural class
        # identity must be rewritten without changing the runtime literal.
        cp = [
            None,
            bytes([1]) + struct.pack(">H", 3) + b"a/b",
            bytes([7]) + struct.pack(">H", 1),
            bytes([1])
            + struct.pack(">H", len(b"java/lang/Object"))
            + b"java/lang/Object",
            bytes([7]) + struct.pack(">H", 3),
            bytes([1]) + struct.pack(">H", 6) + b"<init>",
            bytes([1]) + struct.pack(">H", 3) + b"()V",
            bytes([1]) + struct.pack(">H", 4) + b"Code",
            bytes([12]) + struct.pack(">HH", 5, 6),
            bytes([10]) + struct.pack(">HH", 4, 8),
            bytes([8]) + struct.pack(">H", 1),
        ]

        code = (
            struct.pack(">HHI", 1, 1, 5)
            + b"\x2a\xb7\x00\x09\xb1"
            + struct.pack(">H", 0)
            + struct.pack(">H", 0)
        )
        method = (
            struct.pack(">HHHH", 0x0001, 5, 6, 1)
            + struct.pack(">HI", 7, len(code))
            + code
        )

        data = (
            b"\xca\xfe\xba\xbe"
            + struct.pack(">HHH", 0, 49, len(cp))
            + b"".join(entry for entry in cp[1:] if entry is not None)
            + struct.pack(">HHH", 0x0021, 2, 4)
            + struct.pack(">H", 0)
            + struct.pack(">H", 0)
            + struct.pack(">H", 1)
            + method
            + struct.pack(">H", 0)
        )

        parsed = parse_class(data)
        self.assertEqual(parsed.name, "a/b")
        self.assertEqual(parsed.literal_strings, ["a/b"])

        rewritten, changed_utf8 = remap_class_bytes(
            data,
            {"a/b": "a/Recovered"},
        )

        reparsed = parse_class(rewritten)
        self.assertEqual(reparsed.name, "a/Recovered")
        self.assertEqual(reparsed.literal_strings, ["a/b"])
        self.assertIn("a/Recovered", reparsed.utf8_strings)
        self.assertIn("a/b", reparsed.utf8_strings)
        self.assertGreaterEqual(changed_utf8, 1)


if __name__ == "__main__":
    unittest.main()

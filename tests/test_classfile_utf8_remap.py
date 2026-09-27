from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.classfile import parse_class
from spk_recovery.namespace_alias_plan import (
    build_namespace_alias_plan,
    reverse_alias_mapping,
)
from spk_recovery.classfile_utf8_remap import (
    ClassfileRemapError,
    assert_no_literal_alias_mentions,
    assert_no_utf8_alias_references,
    remap_classfile_utf8,
    remap_jar,
)


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("java"),
    "JDK required",
)
class ClassfileUtf8RemapTests(unittest.TestCase):
    def _compile(
        self,
        *,
        source: Path,
        out: Path,
        classpath: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        out.mkdir(parents=True, exist_ok=True)
        command = [
            "javac",
            "--release",
            "9",
            "-d",
            str(out),
        ]
        if classpath is not None:
            command.extend(
                ["-classpath", str(classpath)]
            )
        command.append(str(source))
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _collision_jar(self, root: Path) -> Path:
        a_src = root / "src-a" / "a.java"
        a_src.parent.mkdir(parents=True)
        a_src.write_text(
            "public class a { public int v = 2; }\n",
            encoding="utf-8",
        )
        a_out = root / "classes-a"
        proc = self._compile(
            source=a_src,
            out=a_out,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )

        c_src = root / "src-c" / "a" / "b" / "C.java"
        c_src.parent.mkdir(parents=True)
        c_src.write_text(
            "package a.b; "
            "public class C { public int w = 3; }\n",
            encoding="utf-8",
        )
        c_out = root / "classes-c"
        proc = self._compile(
            source=c_src,
            out=c_out,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )

        jar = root / "collision.jar"
        with zipfile.ZipFile(
            jar,
            "w",
            zipfile.ZIP_STORED,
        ) as z:
            z.write(
                a_out / "a.class",
                "a.class",
            )
            z.write(
                c_out / "a" / "b" / "C.class",
                "a/b/C.class",
            )
        return jar

    def test_exact_class_remap_does_not_rewrite_package_descendant(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._collision_jar(root)
            alias = (
                "spk_compile_alias/r8s/AliasA"
            )
            out = root / "alias.jar"

            remap_jar(
                jar,
                out,
                {"a": alias},
            )

            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
                self.assertIn(
                    alias + ".class",
                    names,
                )
                self.assertIn(
                    "a/b/C.class",
                    names,
                )
                self.assertNotIn(
                    "spk_compile_alias/r8s/AliasA/b/C.class",
                    names,
                )

                parsed_c = parse_class(
                    z.read("a/b/C.class")
                )
                self.assertEqual(
                    parsed_c.name,
                    "a/b/C",
                )

    def test_jar_remap_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._collision_jar(root)
            mapping = {
                "a": "spk_compile_alias/r8s/AliasA"
            }
            out1 = root / "alias-1.jar"
            out2 = root / "alias-2.jar"

            first = remap_jar(
                jar,
                out1,
                mapping,
            )
            second = remap_jar(
                jar,
                out2,
                mapping,
            )

            self.assertEqual(
                first["destination_sha256"],
                second["destination_sha256"],
            )
            self.assertEqual(
                out1.read_bytes(),
                out2.read_bytes(),
            )

    def test_compile_alias_restore_and_run_with_original_runtime_jar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            collision = self._collision_jar(root)

            bad_source = root / "bad" / "UseBad.java"
            bad_source.parent.mkdir()
            bad_source.write_text(
                "public class UseBad { "
                "public a root; "
                "public a.b.C value; }\n",
                encoding="utf-8",
            )
            bad_out = root / "bad-classes"
            bad = self._compile(
                source=bad_source,
                out=bad_out,
                classpath=collision,
            )
            self.assertNotEqual(
                bad.returncode,
                0,
                "collision fixture must be rejected by javac",
            )

            alias_plan = build_namespace_alias_plan(
                collision,
                include_identifiers=True,
            )
            self.assertEqual(
                set(alias_plan["mapping"]),
                {"a/b/C"},
            )
            alias = alias_plan["mapping"]["a/b/C"]

            alias_jar = root / "alias.jar"
            remap_jar(
                collision,
                alias_jar,
                alias_plan["mapping"],
            )

            with zipfile.ZipFile(alias_jar) as z:
                names = set(z.namelist())
                self.assertIn("a.class", names)
                self.assertIn(alias + ".class", names)
                self.assertNotIn("a/b/C.class", names)

            alias_dotted = alias.replace("/", ".")
            use_source = root / "use" / "Use.java"
            use_source.parent.mkdir()
            use_source.write_text(
                "public class Use {\n"
                "  public static void main(String[] args) {\n"
                "    a x = new a();\n"
                f"    {alias_dotted} y = new {alias_dotted}();\n"
                "    System.out.println(x.v + y.w);\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            compiled = root / "compiled"
            proc = self._compile(
                source=use_source,
                out=compiled,
                classpath=alias_jar,
            )
            self.assertEqual(
                proc.returncode,
                0,
                proc.stdout + proc.stderr,
            )

            generated = (
                compiled / "Use.class"
            ).read_bytes()
            assert_no_literal_alias_mentions(
                [generated],
                [alias],
            )

            restored = remap_classfile_utf8(
                generated,
                reverse_alias_mapping(alias_plan),
            )
            restored_dir = root / "restored"
            restored_dir.mkdir()
            restored_path = restored_dir / "Use.class"
            restored_path.write_bytes(restored.data)

            assert_no_utf8_alias_references(
                [restored.data],
                [alias],
            )

            parsed = parse_class(restored.data)
            self.assertFalse(
                any(
                    alias in value
                    for value in parsed.utf8_strings
                )
            )
            self.assertTrue(
                any(
                    value == "a"
                    or value == "La;"
                    for value in parsed.utf8_strings
                )
            )
            self.assertTrue(
                any(
                    "a/b/C" in value
                    for value in parsed.utf8_strings
                )
            )

            runtime_cp = (
                str(restored_dir)
                + (
                    ";" if shutil.which("java").lower().endswith(".exe")
                    else ":"
                )
                + str(collision)
            )
            run = subprocess.run(
                [
                    "java",
                    "-classpath",
                    runtime_cp,
                    "Use",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                run.returncode,
                0,
                run.stdout + run.stderr,
            )
            self.assertEqual(
                run.stdout.strip(),
                "5",
            )

    def test_missing_alias_source_identity_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            collision = self._collision_jar(root)

            with self.assertRaises(ClassfileRemapError):
                remap_jar(
                    collision,
                    root / "alias.jar",
                    {
                        "not/present/Class":
                            "spk_compile_alias/r8s/Missing"
                    },
                )

    def test_structural_alias_residue_is_refused_and_restore_clears_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            collision = self._collision_jar(root)
            alias = "spk_compile_alias/r8s/AliasA"
            alias_jar = root / "alias.jar"
            remap_jar(
                collision,
                alias_jar,
                {"a": alias},
            )

            source = root / "Use.java"
            source.write_text(
                "public class Use { "
                "public spk_compile_alias.r8s.AliasA value; }\n",
                encoding="utf-8",
            )
            out = root / "classes"
            proc = self._compile(
                source=source,
                out=out,
                classpath=alias_jar,
            )
            self.assertEqual(
                proc.returncode,
                0,
                proc.stdout + proc.stderr,
            )

            generated = (out / "Use.class").read_bytes()
            with self.assertRaises(ClassfileRemapError):
                assert_no_utf8_alias_references(
                    [generated],
                    [alias],
                )

            restored = remap_classfile_utf8(
                generated,
                {alias: "a"},
            ).data
            assert_no_utf8_alias_references(
                [restored],
                [alias],
            )

    def test_literal_alias_mention_is_refused_before_restore(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "Literal.java"
            source.write_text(
                'public class Literal { '
                'public static final String S = '
                '"spk_compile_alias/r8s/AliasA"; }\n',
                encoding="utf-8",
            )
            out = root / "classes"
            proc = self._compile(
                source=source,
                out=out,
            )
            self.assertEqual(
                proc.returncode,
                0,
                proc.stdout + proc.stderr,
            )

            data = (out / "Literal.class").read_bytes()
            with self.assertRaises(ClassfileRemapError):
                assert_no_literal_alias_mentions(
                    [data],
                    ["spk_compile_alias/r8s/AliasA"],
                )


if __name__ == "__main__":
    unittest.main()

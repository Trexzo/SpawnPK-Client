from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.classfile_utf8_remap import (
    assert_no_utf8_alias_references,
    remap_classfile_utf8,
    remap_jar,
)
from spk_recovery.namespace_alias_plan import (
    build_namespace_alias_plan,
    reverse_alias_mapping,
)
from spk_recovery.namespace_source_overlay import (
    build_namespace_source_overlay,
    rewrite_java_source,
)
from spk_recovery.source_digest import source_tree_digest


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("java"),
    "JDK required",
)
class NamespaceSourceOverlayTests(unittest.TestCase):
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
            command.extend(["-classpath", str(classpath)])
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
        proc = self._compile(source=a_src, out=a_out)
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
        proc = self._compile(source=c_src, out=c_out)
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
            z.write(a_out / "a.class", "a.class")
            z.write(
                c_out / "a" / "b" / "C.class",
                "a/b/C.class",
            )
        return jar

    def test_rewrite_import_qualified_and_static_import_only_in_code(self):
        plan = {
            "schema_version": 1,
            "kind": "namespace_alias_plan",
            "plan_id": "NSALIAS_" + "1" * 20,
            "identifiers_included": True,
            "mapping": {
                "a/b/C": "spk_compile_alias/r8s/h123/NODE_0001/b/C"
            },
        }

        source = (
            "package demo;\n"
            "import a.b.C;\n"
            "import static a.b.C.VALUE;\n"
            "public class Use {\n"
            "  a.b.C field;\n"
            "  String s = \"a.b.C\";\n"
            "  // a.b.C must stay in comment\n"
            "  /* import a.b.C; */\n"
            "}\n"
        )

        rewritten, counters = rewrite_java_source(
            source,
            plan,
        )
        alias = "spk_compile_alias.r8s.h123.NODE_0001.b.C"

        self.assertIn(f"import {alias};", rewritten)
        self.assertIn(
            f"import static {alias}.VALUE;",
            rewritten,
        )
        self.assertIn(f"  {alias} field;", rewritten)
        self.assertIn('String s = "a.b.C";', rewritten)
        self.assertIn("// a.b.C must stay in comment", rewritten)
        self.assertIn("/* import a.b.C; */", rewritten)
        self.assertIn("package demo;", rewritten)

        self.assertEqual(
            counters["rewritten_import_count"],
            2,
        )
        self.assertEqual(
            counters["rewritten_qualified_count"],
            1,
        )

    def test_overlay_copies_source_and_preserves_canonical_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "source"
            source_root.mkdir()
            source = source_root / "Use.java"
            source.write_text(
                "import a.b.C; class Use { C value; }\n",
                encoding="utf-8",
            )

            plan = {
                "schema_version": 1,
                "kind": "namespace_alias_plan",
                "plan_id": "NSALIAS_" + "2" * 20,
                "identifiers_included": True,
                "mapping": {
                    "a/b/C":
                        "spk_compile_alias/r8s/h123/NODE_0001/b/C"
                },
            }

            before = source_tree_digest(source_root)
            report = build_namespace_source_overlay(
                plan,
                source_root,
                root / "overlay",
            )
            after = source_tree_digest(source_root)

            self.assertEqual(before, after)
            self.assertFalse(
                report["canonical_source_modified"]
            )
            self.assertEqual(
                report["canonical_source_tree_sha256_after"],
                before[0],
            )
            self.assertEqual(
                report["replacement_count"],
                1,
            )

            overlay = (
                root
                / "overlay"
                / "src"
                / "Use.java"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "spk_compile_alias.r8s.h123.NODE_0001.b.C",
                overlay,
            )
            self.assertEqual(
                source.read_text(encoding="utf-8"),
                "import a.b.C; class Use { C value; }\n",
            )

    def test_collision_import_overlay_compile_restore_and_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            collision = self._collision_jar(root)

            canonical = root / "canonical"
            canonical.mkdir()
            source = canonical / "Use.java"
            source.write_text(
                "import a.b.C;\n"
                "public class Use {\n"
                "  public static void main(String[] args) {\n"
                "    C value = new C();\n"
                "    System.out.println(value.w);\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            bad_out = root / "bad"
            bad = self._compile(
                source=source,
                out=bad_out,
                classpath=collision,
            )
            self.assertNotEqual(
                bad.returncode,
                0,
                "collision fixture must fail before virtualization",
            )

            alias_plan = build_namespace_alias_plan(
                collision,
                include_identifiers=True,
            )
            alias_jar = root / "alias.jar"
            remap_jar(
                collision,
                alias_jar,
                alias_plan["mapping"],
            )

            canonical_before = source_tree_digest(canonical)

            overlay_report = build_namespace_source_overlay(
                alias_plan,
                canonical,
                root / "overlay",
            )
            overlay_source = (
                Path(overlay_report["overlay_root"])
                / "Use.java"
            )

            compiled = root / "compiled"
            proc = self._compile(
                source=overlay_source,
                out=compiled,
                classpath=alias_jar,
            )
            self.assertEqual(
                proc.returncode,
                0,
                proc.stdout + proc.stderr,
            )

            generated = (compiled / "Use.class").read_bytes()
            reverse = reverse_alias_mapping(alias_plan)
            restored = remap_classfile_utf8(
                generated,
                reverse,
            ).data
            assert_no_utf8_alias_references(
                [restored],
                reverse.keys(),
            )

            restored_dir = root / "restored"
            restored_dir.mkdir()
            (restored_dir / "Use.class").write_bytes(restored)

            separator = (
                ";"
                if shutil.which("java").lower().endswith(".exe")
                else ":"
            )
            runtime_cp = (
                str(restored_dir)
                + separator
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
            self.assertEqual(run.stdout.strip(), "3")

            self.assertEqual(
                source_tree_digest(canonical),
                canonical_before,
            )


if __name__ == "__main__":
    unittest.main()

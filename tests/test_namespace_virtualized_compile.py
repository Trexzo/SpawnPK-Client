from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.classfile_utf8_remap import (
    assert_no_utf8_alias_references,
)
from spk_recovery.namespace_alias_plan import (
    build_namespace_alias_plan,
)
from spk_recovery.namespace_virtualized_compile import (
    NamespaceVirtualizedCompileError,
    compile_with_namespace_virtualization,
)
from spk_recovery.source_digest import source_tree_digest


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("java"),
    "JDK required",
)
class NamespaceVirtualizedCompileTests(unittest.TestCase):
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

    def _canonical_source(self, root: Path) -> Path:
        source_root = root / "canonical"
        source_root.mkdir()
        source = source_root / "Use.java"
        source.write_text(
            "public class Use {\n"
            "  public static void main(String[] args) {\n"
            "    a root = new a();\n"
            "    a.b.C value = new a.b.C();\n"
            "    System.out.println(root.v + value.w);\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        return source_root

    def test_orchestrator_compile_restore_runtime_and_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            collision = self._collision_jar(root)
            source_root = self._canonical_source(root)

            original = source_root / "Use.java"
            direct = self._compile(
                source=original,
                out=root / "direct",
                classpath=collision,
            )
            self.assertNotEqual(direct.returncode, 0)

            plan = build_namespace_alias_plan(
                collision,
                include_identifiers=True,
            )
            canonical_before = source_tree_digest(source_root)

            first = compile_with_namespace_virtualization(
                plan,
                source_root,
                collision,
                root / "run-1",
            )
            second = compile_with_namespace_virtualization(
                plan,
                source_root,
                collision,
                root / "run-2",
            )

            self.assertEqual(
                first["compile_id"],
                second["compile_id"],
            )
            self.assertEqual(
                first["compile_only_alias_dependency"]["sha256"],
                second["compile_only_alias_dependency"]["sha256"],
            )
            self.assertEqual(
                first["restored_classes"]["tree_sha256"],
                second["restored_classes"]["tree_sha256"],
            )
            self.assertFalse(first["canonical_source_modified"])
            self.assertFalse(
                first["runtime_alias_dependency_allowed"]
            )
            self.assertGreater(
                first["restored_classes"][
                    "restore_replacement_count"
                ],
                0,
            )

            self.assertEqual(
                source_tree_digest(source_root),
                canonical_before,
            )

            restored = root / "run-1" / "restored-classes"
            restored_data = [
                path.read_bytes()
                for path in restored.rglob("*.class")
            ]
            assert_no_utf8_alias_references(
                restored_data,
                plan["mapping"].values(),
            )

            separator = (
                ";"
                if shutil.which("java").lower().endswith(".exe")
                else ":"
            )
            runtime_cp = (
                str(restored)
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
            self.assertEqual(run.stdout.strip(), "5")

    def test_report_mode_preserves_remaining_javac_frontier(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            collision = self._collision_jar(root)
            source_root = self._canonical_source(root)
            source = source_root / "Use.java"
            sentinel = "missingVirtualizedSentinel"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "root.v + value.w",
                    "root.v + value.w + " + sentinel,
                ),
                encoding="utf-8",
            )
            canonical_before = source_tree_digest(source_root)

            plan = build_namespace_alias_plan(
                collision,
                include_identifiers=True,
            )

            with self.assertRaises(
                NamespaceVirtualizedCompileError
            ):
                compile_with_namespace_virtualization(
                    plan,
                    source_root,
                    collision,
                    root / "fail-fast",
                )

            private_out = root / "private-javac.json"
            first = compile_with_namespace_virtualization(
                plan,
                source_root,
                collision,
                root / "reported-1",
                report_compile_failure=True,
                private_diagnostic_report_out=private_out,
            )
            second = compile_with_namespace_virtualization(
                plan,
                source_root,
                collision,
                root / "reported-2",
                report_compile_failure=True,
            )

            self.assertEqual(first["status"], "compile_failed")
            self.assertEqual(second["status"], "compile_failed")
            self.assertEqual(
                first["compile_id"],
                second["compile_id"],
            )
            self.assertEqual(
                first["restored_classes"]["class_count"],
                0,
            )
            self.assertEqual(
                first["generated_alias_classes"]["class_count"],
                0,
            )
            self.assertFalse(
                first["runtime_alias_dependency_allowed"]
            )

            diagnostic = first["compiler"][
                "diagnostic_classification"
            ]
            self.assertIsNotNone(diagnostic)
            self.assertEqual(
                diagnostic["summary"]["total_errors"],
                1,
            )
            self.assertEqual(
                diagnostic["summary"]["cannot_find_symbol"]["count"],
                1,
            )
            self.assertEqual(
                diagnostic["summary"]["cannot_find_symbol"][
                    "symbol_kinds"
                ],
                {"variable": 1},
            )
            self.assertNotIn(sentinel, str(diagnostic))

            self.assertTrue(private_out.is_file())
            private = json.loads(
                private_out.read_text(encoding="utf-8")
            )
            self.assertTrue(private["identifiers_included"])
            self.assertEqual(
                private["report_id"],
                diagnostic["report_id"],
            )
            self.assertEqual(
                private["frontier_id"],
                diagnostic["frontier_id"],
            )
            self.assertIn(sentinel, str(private))

            self.assertEqual(
                source_tree_digest(source_root),
                canonical_before,
            )
            self.assertFalse(
                (root / "reported-1" / "restored-classes").exists()
            )

    def test_nonempty_output_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            collision = self._collision_jar(root)
            source_root = self._canonical_source(root)
            plan = build_namespace_alias_plan(
                collision,
                include_identifiers=True,
            )

            out = root / "out"
            out.mkdir()
            (out / "existing.txt").write_text(
                "occupied",
                encoding="utf-8",
            )

            with self.assertRaises(
                NamespaceVirtualizedCompileError
            ):
                compile_with_namespace_virtualization(
                    plan,
                    source_root,
                    collision,
                    out,
                )


if __name__ == "__main__":
    unittest.main()

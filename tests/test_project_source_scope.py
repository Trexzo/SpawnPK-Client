from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from spk_recovery.decompiler import DecompilerError, run_decompiler
from spk_recovery.source_workspace import (
    SourceWorkspaceError,
    _selection_digest,
    build_source_workspace,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProjectScopedSourceWorkspaceTests(unittest.TestCase):
    def _readable(self, root: Path) -> tuple[Path, dict]:
        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w") as z:
            z.writestr("rs/A.class", b"a")
            z.writestr("rs/A$Inner.class", b"inner")
            z.writestr("rs/sub/B.class", b"b")
            z.writestr("dep/C.class", b"c")
        manifest = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "status": "complete",
            "verification_pass": True,
            "output_sha256": _sha(jar),
            "source_sha256": "a" * 64,
            "namespace_id": "SEMNS_TEST",
            "class_plan_digest": "b" * 64,
            "member_plan_digest": "c" * 64,
            "build_id": "v308",
            "project_source_prefixes": ["rs/"],
        }
        return jar, manifest

    def test_project_only_selection_is_manifest_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, manifest = self._readable(root)
            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")

            def fake_decompiler(*args, **kwargs):
                selected = kwargs["input_class_files"]
                rel = sorted(
                    path.relative_to(path.parents[1]).as_posix()
                    if path.parent.name == "sub"
                    else path.name
                    for path in selected
                )
                # Dependency and nested classfiles remain resolver context only;
                # neither may become an independent Java source target.
                self.assertEqual(len(selected), 2)
                self.assertTrue(all("/dep/" not in path.as_posix() for path in selected))
                self.assertTrue(all("$" not in path.name for path in selected))
                out = kwargs["out_dir"]
                (out / "rs" / "sub").mkdir(parents=True, exist_ok=True)
                (out / "rs" / "A.java").write_text(
                    "package rs; public class A {}\n",
                    encoding="utf-8",
                )
                (out / "rs" / "sub" / "B.java").write_text(
                    "package rs.sub; public class B {}\n",
                    encoding="utf-8",
                )
                return {
                    "schema_version": 1,
                    "kind": "decompiler_result",
                    "engine": "procyon",
                    "input_sha256": _sha(jar),
                    "decompiler_sha256": "d" * 64,
                    "java_file_count": 2,
                    "output_directory": str(out),
                    "input_mode": "class_files",
                    "selected_class_file_count": 2,
                    "batch_count": 1,
                    "stdout": "",
                    "stderr": "",
                }

            with patch(
                "spk_recovery.source_workspace.run_decompiler",
                side_effect=fake_decompiler,
            ):
                result = build_source_workspace(
                    manifest,
                    jar,
                    tool,
                    expected_decompiler_sha256="d" * 64,
                    engine="procyon",
                    out_dir=root / "out",
                    project_only=True,
                )

            self.assertEqual(result["source_scope"], "project_classes")
            self.assertEqual(result["project_source_prefixes"], ["rs/"])
            self.assertEqual(result["selected_class_count"], 2)
            self.assertEqual(
                result["selected_class_digest"],
                _selection_digest(["rs/A.class", "rs/sub/B.class"]),
            )
            self.assertEqual(result["java_file_count"], 2)


    def test_project_only_refuses_archive_root_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, manifest = self._readable(root)
            manifest["project_source_prefixes"] = ["/"]
            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")
            with self.assertRaises(SourceWorkspaceError):
                build_source_workspace(
                    manifest,
                    jar,
                    tool,
                    expected_decompiler_sha256="d" * 64,
                    engine="procyon",
                    out_dir=root / "out",
                    project_only=True,
                )

    def test_project_only_refuses_parent_traversal_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, manifest = self._readable(root)
            manifest["project_source_prefixes"] = ["../rs/"]
            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")
            with self.assertRaises(SourceWorkspaceError):
                build_source_workspace(
                    manifest,
                    jar,
                    tool,
                    expected_decompiler_sha256="d" * 64,
                    engine="procyon",
                    out_dir=root / "out",
                    project_only=True,
                )

    def test_project_only_refuses_non_procyon_engine(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, manifest = self._readable(root)
            tool = root / "tool.jar"
            tool.write_bytes(b"tool")
            with self.assertRaises(SourceWorkspaceError):
                build_source_workspace(
                    manifest,
                    jar,
                    tool,
                    expected_decompiler_sha256="d" * 64,
                    engine="cfr",
                    out_dir=root / "out",
                    project_only=True,
                )


class ResumableProjectSourceWorkspaceTests(unittest.TestCase):
    def _readable(self, root: Path) -> tuple[Path, dict]:
        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w") as z:
            z.writestr("rs/A.class", b"a")
            z.writestr("rs/B.class", b"b")
            z.writestr("dep/C.class", b"c")
        manifest = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "status": "complete",
            "verification_pass": True,
            "output_sha256": _sha(jar),
            "source_sha256": "a" * 64,
            "namespace_id": "SEMNS_TEST",
            "class_plan_digest": "b" * 64,
            "member_plan_digest": "c" * 64,
            "build_id": "v308",
            "project_source_prefixes": ["rs/"],
        }
        return jar, manifest

    def _fake_decompiler(self, jar: Path):
        def fake(*args, **kwargs):
            selected = kwargs["input_class_files"]
            self.assertEqual(len(selected), 1)
            class_name = selected[0].stem
            out = kwargs["out_dir"]
            (out / "rs").mkdir(parents=True, exist_ok=True)
            (out / "rs" / f"{class_name}.java").write_text(
                f"package rs; public class {class_name} {{}}\n",
                encoding="utf-8",
            )
            return {
                "schema_version": 1,
                "kind": "decompiler_result",
                "engine": "procyon",
                "input_sha256": _sha(jar),
                "decompiler_sha256": kwargs["expected_decompiler_sha256"],
                "java_file_count": 1,
                "output_directory": str(out),
                "input_mode": "class_files",
                "selected_class_file_count": 1,
                "batch_count": 1,
                "stdout": f"stdout-{class_name}\n",
                "stderr": f"stderr-{class_name}\n",
            }
        return fake

    def test_resume_advances_then_emits_final_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, manifest = self._readable(root)
            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")
            out = root / "out"
            with patch(
                "spk_recovery.source_workspace.run_decompiler",
                side_effect=self._fake_decompiler(jar),
            ) as run:
                first = build_source_workspace(
                    manifest,
                    jar,
                    tool,
                    expected_decompiler_sha256=_sha(tool),
                    engine="procyon",
                    out_dir=out,
                    project_only=True,
                    resume_project_only=True,
                    project_batch_size=1,
                    max_batches_per_run=1,
                )
                self.assertEqual(first["kind"], "project_source_resume_checkpoint")
                self.assertEqual(first["status"], "incomplete")
                self.assertEqual(len(first["completed_batches"]), 1)
                self.assertFalse((out / "recovered-source-manifest.json").exists())

                final = build_source_workspace(
                    manifest,
                    jar,
                    tool,
                    expected_decompiler_sha256=_sha(tool),
                    engine="procyon",
                    out_dir=out,
                    project_only=True,
                    resume_project_only=True,
                    project_batch_size=1,
                    max_batches_per_run=1,
                )

            self.assertEqual(run.call_count, 2)
            self.assertEqual(final["kind"], "recovered_source_workspace_manifest")
            self.assertEqual(final["java_file_count"], 2)
            self.assertEqual(final["selected_class_count"], 2)
            checkpoint = json.loads(
                (out / "project-decompile-checkpoint.json").read_text(encoding="utf-8")
            )
            self.assertEqual(checkpoint["status"], "complete")
            self.assertEqual(len(checkpoint["completed_batches"]), 2)
            decompiler_result = json.loads(
                (out / "decompiler-result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                decompiler_result["stdout"],
                "stdout-A\nstdout-B\n",
            )
            self.assertEqual(
                decompiler_result["stderr"],
                "stderr-A\nstderr-B\n",
            )

    def test_resume_rejects_source_tree_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, manifest = self._readable(root)
            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")
            out = root / "out"
            with patch(
                "spk_recovery.source_workspace.run_decompiler",
                side_effect=self._fake_decompiler(jar),
            ):
                build_source_workspace(
                    manifest,
                    jar,
                    tool,
                    expected_decompiler_sha256=_sha(tool),
                    engine="procyon",
                    out_dir=out,
                    project_only=True,
                    resume_project_only=True,
                    project_batch_size=1,
                    max_batches_per_run=1,
                )
                (out / "src" / "rs" / "A.java").write_text(
                    "package rs; public class A { int drift; }\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(SourceWorkspaceError, "source tree has drifted"):
                    build_source_workspace(
                        manifest,
                        jar,
                        tool,
                        expected_decompiler_sha256=_sha(tool),
                        engine="procyon",
                        out_dir=out,
                        project_only=True,
                        resume_project_only=True,
                        project_batch_size=1,
                        max_batches_per_run=1,
                    )

    def test_resume_rejects_batch_policy_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, manifest = self._readable(root)
            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")
            out = root / "out"
            with patch(
                "spk_recovery.source_workspace.run_decompiler",
                side_effect=self._fake_decompiler(jar),
            ):
                build_source_workspace(
                    manifest,
                    jar,
                    tool,
                    expected_decompiler_sha256=_sha(tool),
                    engine="procyon",
                    out_dir=out,
                    project_only=True,
                    resume_project_only=True,
                    project_batch_size=1,
                    max_batches_per_run=1,
                )
                with self.assertRaisesRegex(SourceWorkspaceError, "authority or batch policy"):
                    build_source_workspace(
                        manifest,
                        jar,
                        tool,
                        expected_decompiler_sha256=_sha(tool),
                        engine="procyon",
                        out_dir=out,
                        project_only=True,
                        resume_project_only=True,
                        project_batch_size=2,
                        max_batches_per_run=1,
                    )

    def test_resume_rejects_conflicting_duplicate_java_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, manifest = self._readable(root)
            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")
            out = root / "out"
            calls = 0

            def fake(*args, **kwargs):
                nonlocal calls
                calls += 1
                target = kwargs["out_dir"] / "rs" / "Same.java"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    f"package rs; public class Same {{ int v = {calls}; }}\n",
                    encoding="utf-8",
                )
                return {
                    "schema_version": 1,
                    "kind": "decompiler_result",
                    "engine": "procyon",
                    "input_sha256": _sha(jar),
                    "decompiler_sha256": kwargs["expected_decompiler_sha256"],
                    "java_file_count": 1,
                    "output_directory": str(kwargs["out_dir"]),
                    "input_mode": "class_files",
                    "selected_class_file_count": 1,
                    "batch_count": 1,
                    "stdout": "",
                    "stderr": "",
                }

            with patch(
                "spk_recovery.source_workspace.run_decompiler",
                side_effect=fake,
            ):
                with self.assertRaisesRegex(SourceWorkspaceError, "conflicting Java output"):
                    build_source_workspace(
                        manifest,
                        jar,
                        tool,
                        expected_decompiler_sha256=_sha(tool),
                        engine="procyon",
                        out_dir=out,
                        project_only=True,
                        resume_project_only=True,
                        project_batch_size=1,
                        max_batches_per_run=2,
                    )
            checkpoint = json.loads(
                (out / "project-decompile-checkpoint.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(checkpoint["completed_batches"]), 1)


class SelectiveDecompilerTests(unittest.TestCase):
    def test_procyon_class_inputs_are_deterministically_batched(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_jar = root / "readable.jar"
            input_jar.write_bytes(b"readable")
            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")
            classes = []
            for i in range(24):
                path = root / "classes" / ("package_" + str(i)) / ("Class" + str(i) + ".class")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bytes([i]))
                classes.append(path)
            out = root / "out"

            def fake_run(cmd, **kwargs):
                (out / "rs").mkdir(parents=True, exist_ok=True)
                (out / "rs" / "A.java").write_text(
                    "package rs; public class A {}\n",
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with (
                patch("spk_recovery.decompiler.shutil.which", return_value="/java"),
                patch("spk_recovery.decompiler.subprocess.run", side_effect=fake_run) as run,
            ):
                result = run_decompiler(
                    input_jar,
                    tool,
                    expected_decompiler_sha256=_sha(tool),
                    engine="procyon",
                    out_dir=out,
                    input_class_files=list(reversed(classes)),
                    max_command_chars=1024,
                )

            self.assertEqual(result["input_mode"], "class_files")
            self.assertEqual(result["selected_class_file_count"], 24)
            self.assertGreater(result["batch_count"], 1)
            self.assertEqual(run.call_count, result["batch_count"])

    def test_selective_input_refuses_other_engines(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_jar = root / "readable.jar"
            input_jar.write_bytes(b"readable")
            tool = root / "tool.jar"
            tool.write_bytes(b"tool")
            class_file = root / "A.class"
            class_file.write_bytes(b"a")
            with self.assertRaises(DecompilerError):
                run_decompiler(
                    input_jar,
                    tool,
                    expected_decompiler_sha256=_sha(tool),
                    engine="cfr",
                    out_dir=root / "out",
                    input_class_files=[class_file],
                )


if __name__ == "__main__":
    unittest.main()

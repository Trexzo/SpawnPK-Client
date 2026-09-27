from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.clean_rebuild import (
    _dependency_capsule,
    clean_project_rebuild,
)
from spk_recovery.namespace_alias_plan import (
    build_namespace_alias_plan,
)
from spk_recovery.progressive_compile import _probe_javac
from spk_recovery.source_digest import source_tree_digest


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("java"),
    "JDK required",
)
class CleanRebuildNamespaceVirtualizationTests(unittest.TestCase):
    def _compile(
        self,
        sources: list[Path],
        out: Path,
        *,
        classpath: Path | None = None,
    ) -> None:
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
        command.extend(str(path) for path in sources)
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )

    def _fixture(self, root: Path):
        class_src = root / "class-src" / "x" / "a.java"
        class_src.parent.mkdir(parents=True)
        class_src.write_text(
            "package x; public class a { public int v = 2; }\n",
            encoding="utf-8",
        )
        class_out = root / "class-out"
        self._compile([class_src], class_out)

        package_src = root / "package-src" / "x" / "a" / "b" / "C.java"
        package_src.parent.mkdir(parents=True)
        package_src.write_text(
            "package x.a.b; "
            "public class C { public int w = 3; }\n",
            encoding="utf-8",
        )
        package_out = root / "package-out"
        self._compile([package_src], package_out)

        placeholder_src = root / "placeholder-src" / "rs" / "Use.java"
        placeholder_src.parent.mkdir(parents=True)
        placeholder_src.write_text(
            "package rs; public class Use { public int sum() { return 0; } }\n",
            encoding="utf-8",
        )
        placeholder_out = root / "placeholder-out"
        self._compile([placeholder_src], placeholder_out)

        readable = root / "readable.jar"
        with zipfile.ZipFile(readable, "w", zipfile.ZIP_STORED) as z:
            z.writestr(
                "META-INF/MANIFEST.MF",
                "Manifest-Version: 1.0\r\n\r\n",
            )
            for base in (class_out, package_out, placeholder_out):
                for path in sorted(base.rglob("*.class")):
                    z.write(
                        path,
                        path.relative_to(base).as_posix(),
                    )

        source_root = root / "recovered"
        use = source_root / "rs" / "Use.java"
        use.parent.mkdir(parents=True)
        use.write_text(
            "package rs;\n"
            "public class Use {\n"
            "  public int sum() {\n"
            "    x.a root = new x.a();\n"
            "    x.a.b.C value = new x.a.b.C();\n"
            "    return root.v + value.w;\n"
            "  }\n"
            "  public static void main(String[] args) {\n"
            "    System.out.println(new Use().sum());\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        tree_sha, files, total_bytes = source_tree_digest(source_root)
        readable_sha = _sha(readable)
        probe = _probe_javac("javac")

        recovered = {
            "schema_version": 1,
            "kind": "recovered_source_workspace_manifest",
            "workspace_id": "SRCWS_" + "1" * 20,
            "build_id": "v308",
            "source_authority_sha256": "a" * 64,
            "readable_jar_sha256": readable_sha,
            "namespace_id": "SEMNS_" + "2" * 20,
            "class_plan_digest": "c" * 64,
            "member_plan_digest": "d" * 64,
            "engine": "cfr",
            "decompiler_sha256": "e" * 64,
            "source_tree_sha256": tree_sha,
            "java_file_count": len(files),
            "source_bytes": total_bytes,
            "source_directory": "src",
        }
        readiness = {
            "schema_version": 1,
            "kind": "source_readiness_report",
            "source_tree_sha256": tree_sha,
        }
        readable_manifest = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "status": "complete",
            "verification_pass": True,
            "output_sha256": readable_sha,
            "target_package": "",
            "source_safe_fallback": False,
            "project_source_prefixes": ["rs/"],
            "semantic_summary": {
                "source_safety_fallbacks": 0,
            },
        }
        authority = {
            "schema_version": 1,
            "kind": "build_authority_manifest",
            "authority_id": "BUILDAUTH_" + "3" * 20,
            "source_sha256": "a" * 64,
            "compiler_runtime": {"javac": probe},
            "bytecode": {"dominant_java_release": 9},
        }

        pre_capsule = root / "plan-dependency.jar"
        _dependency_capsule(
            readable,
            ["rs/"],
            pre_capsule,
        )
        plan = build_namespace_alias_plan(
            pre_capsule,
            include_identifiers=True,
        )

        return (
            source_root,
            readable,
            recovered,
            readiness,
            readable_manifest,
            authority,
            plan,
        )

    def test_opt_in_virtualization_recovers_collision_and_preserves_runtime_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                source,
                readable,
                recovered,
                readiness,
                readable_manifest,
                authority,
                plan,
            ) = self._fixture(root)

            direct = clean_project_rebuild(
                recovered,
                readiness,
                readable_manifest,
                readable,
                authority,
                source,
                out_dir=root / "legacy",
                source_prefixes=["rs/"],
            )
            self.assertEqual(direct["status"], "compile_failed")

            canonical_before = source_tree_digest(source)[0]
            virtualized = clean_project_rebuild(
                recovered,
                readiness,
                readable_manifest,
                readable,
                authority,
                source,
                out_dir=root / "virtualized",
                source_prefixes=["rs/"],
                private_namespace_alias_plan=plan,
            )

            self.assertEqual(virtualized["status"], "complete")
            self.assertTrue(virtualized["clean_project_build"])
            self.assertEqual(
                virtualized["project_classes"]["binary_fallback_count"],
                0,
            )
            transport = virtualized["compile_transport"]
            self.assertEqual(
                transport["mode"],
                "namespace_virtualized",
            )
            self.assertTrue(transport["opt_in"])
            self.assertFalse(
                transport["runtime_alias_dependency_allowed"]
            )
            self.assertFalse(
                transport["canonical_source_modified"]
            )
            self.assertEqual(
                source_tree_digest(source)[0],
                canonical_before,
            )

            rebuilt = root / "virtualized" / "rebuilt-client.jar"
            with zipfile.ZipFile(readable) as src, zipfile.ZipFile(rebuilt) as dst:
                for name in ("x/a.class", "x/a/b/C.class"):
                    self.assertEqual(src.read(name), dst.read(name))

                names = set(dst.namelist())
                self.assertIn("rs/Use.class", names)
                for alias in plan["mapping"].values():
                    self.assertNotIn(alias + ".class", names)

            run = subprocess.run(
                [
                    "java",
                    "-classpath",
                    str(rebuilt),
                    "rs.Use",
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

            alias_jar = (
                root
                / "virtualized"
                / "namespace-virtualized-compile"
                / "compile-alias-dependency.jar"
            )
            self.assertTrue(alias_jar.is_file())
            self.assertNotEqual(_sha(alias_jar), _sha(readable))

    def test_virtualization_requires_explicit_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                source,
                readable,
                recovered,
                readiness,
                readable_manifest,
                authority,
                _plan,
            ) = self._fixture(root)

            report = clean_project_rebuild(
                recovered,
                readiness,
                readable_manifest,
                readable,
                authority,
                source,
                out_dir=root / "legacy",
                source_prefixes=["rs/"],
            )

            self.assertNotIn("compile_transport", report)
            self.assertEqual(report["status"], "compile_failed")


if __name__ == "__main__":
    unittest.main()

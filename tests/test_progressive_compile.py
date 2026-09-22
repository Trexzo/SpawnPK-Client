from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.progressive_compile import (
    _probe_javac,
    progressive_compile,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha(root: Path) -> str:
    files = sorted(root.rglob("*.java"))
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ProgressiveCompileTests(unittest.TestCase):
    def _fallback_jar(self, root: Path) -> Path:
        src = root / "dep-src" / "dep"
        src.mkdir(parents=True)
        java = src / "Fallback.java"
        java.write_text(
            "package dep; public class Fallback {}\n",
            encoding="utf-8",
        )
        classes = root / "dep-classes"
        classes.mkdir()
        subprocess.run(
            ["javac", "-d", str(classes), str(java)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for path in sorted(classes.rglob("*.class")):
                z.write(path, path.relative_to(classes).as_posix())
        return jar

    def _authority_docs(self, source: Path, jar: Path):
        tree_sha = _tree_sha(source)
        recovered = {
            "schema_version": 1,
            "kind": "recovered_source_workspace_manifest",
            "workspace_id": "SRCWS_" + "1" * 20,
            "build_id": "v308",
            "source_authority_sha256": "a" * 64,
            "readable_jar_sha256": _sha(jar),
            "namespace_id": "SEMNS_" + "2" * 20,
            "class_plan_digest": "c" * 64,
            "member_plan_digest": "d" * 64,
            "engine": "cfr",
            "decompiler_sha256": "e" * 64,
            "source_tree_sha256": tree_sha,
            "java_file_count": len(list(source.rglob("*.java"))),
            "source_bytes": sum(
                p.stat().st_size for p in source.rglob("*.java")
            ),
            "source_directory": "src",
        }
        readiness = {
            "schema_version": 1,
            "kind": "source_readiness_report",
            "audit_id": "SRCREADY_" + "3" * 20,
            "workspace_id": recovered["workspace_id"],
            "build_id": "v308",
            "source_authority_sha256": "a" * 64,
            "readable_jar_sha256": _sha(jar),
            "namespace_id": recovered["namespace_id"],
            "source_tree_sha256": tree_sha,
            "summary": {},
            "packages": {},
            "external_import_roots": {},
            "external_imports": [],
            "issue_counts": {},
            "issues": [],
            "files": [],
        }
        readable = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "build_id": "v308",
            "namespace_id": recovered["namespace_id"],
            "source_sha256": "a" * 64,
            "target_package": "recovered/spawnpk/client",
            "class_plan_digest": "c" * 64,
            "member_plan_digest": "d" * 64,
            "status": "complete",
            "output_sha256": _sha(jar),
            "verification_pass": True,
            "semantic_summary": {},
            "blocker": None,
            "artifact_names": {},
            "manifest_id": "READABLE_" + "4" * 20,
        }
        probe = _probe_javac("javac")
        authority = {
            "schema_version": 1,
            "kind": "build_authority_manifest",
            "authority_id": "BUILDAUTH_" + "5" * 20,
            "source_sha256": "a" * 64,
            "class_prefix": "rs/",
            "bytecode": {
                "dominant_java_release": None,
            },
            "compiler_runtime": {
                "javac": probe,
            },
            "embedded_maven_metadata": [],
            "root_build_metadata": [],
            "source_dependency_surface": {},
            "interpretation": {},
        }
        return recovered, readiness, readable, authority

    def test_failed_batch_is_bisected_to_file_level(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fallback_jar(root)
            source = root / "src" / "sample"
            source.mkdir(parents=True)
            (source / "A.java").write_text(
                "package sample; import dep.Fallback; "
                "public class A { Fallback value; }\n",
                encoding="utf-8",
            )
            (source / "Bad.java").write_text(
                "package sample; public class Bad { MissingType value; }\n",
                encoding="utf-8",
            )
            source_root = root / "src"
            recovered, readiness, readable, authority = (
                self._authority_docs(source_root, jar)
            )

            report = progressive_compile(
                recovered,
                readiness,
                readable,
                jar,
                authority,
                source_root,
                out_dir=root / "out",
                batch_size=2,
                source_prefixes=["sample/"],
            )

            self.assertEqual(
                report["summary"]["compiled_file_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["failed_file_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["compiler_invocations"],
                3,
            )
            self.assertFalse(
                report["summary"]["full_source_compile_ready"]
            )
            rows = {row["path"]: row for row in report["files"]}
            self.assertEqual(
                rows["sample/A.java"]["status"],
                "compiled_with_readable_fallback",
            )
            self.assertEqual(
                rows["sample/Bad.java"]["status"],
                "compile_failed",
            )
            self.assertIn(
                "MissingType",
                rows["sample/Bad.java"]["diagnostic"],
            )
            self.assertTrue(
                (root / "out" / "classes" / "sample" / "A.class").is_file()
            )
            self.assertTrue(
                (root / "out" / "progressive-compile.json").is_file()
            )


if __name__ == "__main__":
    unittest.main()

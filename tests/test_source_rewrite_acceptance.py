from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.indexer import index_jar
from spk_recovery.source_rewrite_acceptance import (
    SourceRewriteAcceptanceError,
    accept_rewritten_source,
)


def _tree_digest(root: Path) -> tuple[str, int, int]:
    files = sorted(root.rglob("*.java"))
    h = hashlib.sha256()
    total = 0
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
        total += len(data)
    return h.hexdigest(), len(files), total


def _jar(classes: Path, out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for path in sorted(classes.rglob("*.class")):
            z.write(path, path.relative_to(classes).as_posix())


@unittest.skipUnless(
    shutil.which("java") and shutil.which("javac"),
    "Java toolchain required",
)
class SourceRewriteAcceptanceTests(unittest.TestCase):
    def _fixture(self, root: Path):
        authority_src = root / "authority-src"
        dep = authority_src / "lib"
        project = authority_src / "rs"
        dep.mkdir(parents=True)
        project.mkdir(parents=True)

        (dep / "D.java").write_text(
            "package lib; public class D { "
            "public static int value() { return 2; } }\n",
            encoding="utf-8",
        )
        original_text = (
            "package rs; import lib.D; public class A { "
            "public int calc(int x) { "
            "int count = x + D.value(); return count; } }\n"
        )
        (project / "A.java").write_text(
            original_text,
            encoding="utf-8",
        )

        classes = root / "authority-classes"
        classes.mkdir()
        subprocess.run(
            [
                "javac",
                "-d",
                str(classes),
                str(dep / "D.java"),
                str(project / "A.java"),
            ],
            check=True,
        )
        authority_jar = root / "authority.jar"
        _jar(classes, authority_jar)
        authority_index = index_jar(authority_jar)

        original_root = root / "original-source"
        (original_root / "rs").mkdir(parents=True)
        (original_root / "rs" / "A.java").write_text(
            original_text,
            encoding="utf-8",
        )
        input_sha, count, source_bytes = _tree_digest(original_root)

        rewritten_root = root / "rewritten-source"
        (rewritten_root / "rs").mkdir(parents=True)
        rewritten_text = (
            "package rs; import lib.D; public class A { "
            "public int calc(int itemId) { "
            "int total = itemId + D.value(); return total; } }\n"
        )
        (rewritten_root / "rs" / "A.java").write_text(
            rewritten_text,
            encoding="utf-8",
        )
        output_sha, output_count, output_bytes = _tree_digest(
            rewritten_root
        )
        self.assertEqual(count, output_count)

        jar_sha = authority_index["sha256"]
        recovered = {
            "schema_version": 1,
            "kind": "recovered_source_workspace_manifest",
            "workspace_id": "SRCWS_TEST",
            "build_id": "test",
            "source_authority_sha256": jar_sha,
            "readable_jar_sha256": jar_sha,
            "namespace_id": "SEMNS_TEST",
            "class_plan_digest": "a" * 64,
            "member_plan_digest": "b" * 64,
            "engine": "cfr",
            "decompiler_sha256": "c" * 64,
            "source_tree_sha256": input_sha,
            "java_file_count": count,
            "source_bytes": source_bytes,
            "source_directory": "src",
        }
        rewrite = {
            "schema_version": 1,
            "kind": "source_rewrite_manifest",
            "rewrite_id": "SRCREWRITE_0123456789ABCDEF0123",
            "plan_id": "SRCPLAN_0123456789ABCDEF0123",
            "inventory_id": "SRCINV_0123456789ABCDEF0123",
            "review_id": "SRCREVIEW_0123456789ABCDEF0123",
            "workspace_id": "SRCWS_TEST",
            "build_id": "test",
            "input_source_tree_sha256": input_sha,
            "output_source_tree_sha256": output_sha,
            "java_file_count": output_count,
            "input_source_bytes": source_bytes,
            "output_source_bytes": output_bytes,
            "accepted_rename_count": 2,
            "files_changed": 1,
            "identifier_replacements": 4,
            "classpath": [],
            "source_directory": "src",
            "semantic_analysis_pass": True,
            "note": "synthetic rewrite",
        }
        readable = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "build_id": "test",
            "namespace_id": "SEMNS_TEST",
            "source_sha256": jar_sha,
            "target_package": "recovered/spawnpk/client",
            "class_plan_digest": "a" * 64,
            "member_plan_digest": "b" * 64,
            "status": "complete",
            "output_sha256": jar_sha,
            "verification_pass": True,
            "semantic_summary": {},
            "blocker": None,
            "artifact_names": {},
            "manifest_id": "READABLE_TEST",
        }
        return {
            "authority_jar": authority_jar,
            "authority_index": authority_index,
            "original_root": original_root,
            "rewritten_root": rewritten_root,
            "recovered": recovered,
            "rewrite": rewrite,
            "readable": readable,
        }

    def test_rewritten_source_survives_clean_rebuild_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = self._fixture(root)
            report = accept_rewritten_source(
                fixture["recovered"],
                fixture["rewrite"],
                fixture["rewritten_root"],
                fixture["authority_jar"],
                fixture["authority_index"],
                fixture["readable"],
                fixture["authority_jar"],
                out_dir=root / "acceptance",
            )

            self.assertTrue(report["accepted"])
            self.assertTrue(
                report["clean_rebuild"]["clean_project_build"]
            )
            self.assertEqual(
                report["clean_rebuild"][
                    "project_binary_fallback_count"
                ],
                0,
            )
            self.assertTrue(report["roundtrip"]["ready"])
            self.assertEqual(
                report["roundtrip"][
                    "semantic_surface_blockers"
                ],
                0,
            )
            self.assertTrue(
                (
                    root
                    / "acceptance"
                    / "clean-rebuild"
                    / "dependency-capsule.jar"
                ).is_file()
            )
            self.assertTrue(
                (
                    root
                    / "acceptance"
                    / "clean-rebuild"
                    / "rebuilt-client.jar"
                ).is_file()
            )

    def test_stale_rewritten_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = self._fixture(root)
            (
                fixture["rewritten_root"]
                / "rs"
                / "A.java"
            ).write_text(
                "package rs; public class A {}\n",
                encoding="utf-8",
            )
            with self.assertRaises(SourceRewriteAcceptanceError):
                accept_rewritten_source(
                    fixture["recovered"],
                    fixture["rewrite"],
                    fixture["rewritten_root"],
                    fixture["authority_jar"],
                    fixture["authority_index"],
                    fixture["readable"],
                    fixture["authority_jar"],
                    out_dir=root / "acceptance",
                )


if __name__ == "__main__":
    unittest.main()

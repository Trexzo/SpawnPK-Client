"""Synthetic JDK-only original-JAR tests of source-island frontier trust gates."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.source_island_frontier import (
    SourceFrontierError,
    _source_name_collision,
    discover_original_source_frontier,
    write_source_frontier,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "Requires Java compiler")
class OriginalSourceFrontierTests(unittest.TestCase):
    def fixture(self, root: Path):
        source = root / "sources"
        bodies = {
            "rs/demo/Base.java": (
                "package rs.demo; public class Base { public int value=8; }"
            ),
            "rs/demo/Child.java": (
                "package rs.demo; public class Child extends Base {"
                " public int get() { return value; } }"
            ),
            "rs/demo/Grandchild.java": (
                "package rs.demo; public class Grandchild extends Child {"
                " public long value() { return get(); } }"
            ),
            "rs/demo/Independent.java": (
                "package rs.demo; public class Independent {"
                " public boolean ready() { return true; } }"
            ),
        }
        for name, text in bodies.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        dest = root / "original-classes"
        dest.mkdir()
        cmd = [
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-classpath"),
            "-sourcepath", str(root / "empty-sourcepath"),
            "-d", str(dest),
            *[str(source / key) for key in sorted(bodies)],
        ]
        run = subprocess.run(
            cmd, capture_output=True, text=True, timeout=45
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        jar = root / "synthetic-original.jar"
        with zipfile.ZipFile(jar, "w") as z:
            for classfile in sorted(dest.rglob("*.class")):
                z.writestr(
                    classfile.relative_to(dest).as_posix(),
                    classfile.read_bytes(),
                )
        with zipfile.ZipFile(jar) as z:
            pins = {name: sha(z.read(name)) for name in z.namelist()}
        manifest = {
            "original_jar_sha256": sha(jar.read_bytes()),
            "original_class_sha256": {
                "rs/demo/Base.class": pins["rs/demo/Base.class"],
            },
        }
        return jar, manifest, pins

    def test_connected_direct_frontier_excludes_transitive_and_jdk_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar, manifest, pins = self.fixture(root)
            report = discover_original_source_frontier(jar, manifest)
            self.assertTrue(report["explicit_source_island_closure_verified"])
            self.assertEqual(report["selected_classes_attested"], 1)
            self.assertEqual(report["original_project_classes"], 4)
            self.assertEqual(report["direct_dependency_closed_candidate_count"], 1)
            match = report["candidates"][0]
            self.assertEqual(match["original_class_path"], "rs/demo/Child.class")
            self.assertEqual(match["original_class_sha256"], pins[
                "rs/demo/Child.class"
            ])
            self.assertEqual(match["direct_original_project_dependencies"], [
                "rs/demo/Base.class"
            ])
            self.assertFalse(match["source_reconstructed"])
            self.assertFalse(match["compile_or_runtime_parity_proven"])
            self.assertFalse(report["original_class_bytecode_published"])

    def test_frontier_expands_only_after_new_original_dependency_is_attested(self):
        with tempfile.TemporaryDirectory() as temp:
            jar, manifest, pins = self.fixture(Path(temp))
            manifest["original_class_sha256"]["rs/demo/Child.class"] = pins[
                "rs/demo/Child.class"
            ]
            report = discover_original_source_frontier(jar, manifest)
            self.assertEqual(
                [x["original_class_path"] for x in report["candidates"]],
                ["rs/demo/Grandchild.class"],
            )

    def test_sha_and_incomplete_base_refuse_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar, manifest, pins = self.fixture(root)
            wrong = dict(manifest)
            wrong["original_jar_sha256"] = "a" * 64
            with self.assertRaisesRegex(SourceFrontierError, "JAR_SHA_MISMATCH"):
                discover_original_source_frontier(jar, wrong)
            wrong = dict(manifest)
            wrong["original_class_sha256"] = {"rs/demo/Base.class": "a" * 64}
            with self.assertRaisesRegex(SourceFrontierError, "CLASS_SHA_MISMATCH"):
                discover_original_source_frontier(jar, wrong)
            incomplete = dict(manifest)
            incomplete["original_class_sha256"] = {
                "rs/demo/Child.class": pins["rs/demo/Child.class"]
            }
            with self.assertRaisesRegex(SourceFrontierError, "BASE_SELECTION_NOT_CLOSED"):
                discover_original_source_frontier(jar, incomplete)
            out = root / "no-output.json"
            authority = root / "authority.json"
            import json
            authority.write_text(json.dumps(incomplete), encoding="utf-8")
            with self.assertRaisesRegex(SourceFrontierError, "BASE_SELECTION_NOT_CLOSED"):
                write_source_frontier(jar, authority, out)
            self.assertFalse(out.exists())

    def test_nonoverwriting_private_report_and_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar, manifest, pins = self.fixture(root)
            import json
            authority = root / "authority.json"
            authority.write_text(json.dumps(manifest), encoding="utf-8")
            dest = root / "frontier.json"
            report = write_source_frontier(jar, authority, dest, max_candidates=1)
            self.assertEqual(report["direct_dependency_closed_candidate_count"], 1)
            self.assertTrue(dest.is_file())
            with self.assertRaisesRegex(SourceFrontierError, "REFUSE_OVERWRITE"):
                write_source_frontier(jar, authority, dest)
            with self.assertRaisesRegex(SourceFrontierError, "INVALID_LIMIT"):
                discover_original_source_frontier(jar, manifest, max_candidates=101)
            with self.assertRaisesRegex(SourceFrontierError, "INVALID_SELECTED_CLASS_PIN"):
                discover_original_source_frontier(jar, {
                    "original_jar_sha256": manifest["original_jar_sha256"],
                    "original_class_sha256": {"rs/../unsafe.class": "a" * 64},
                })

    def test_report_detects_source_namespace_collision_without_renaming(self):
        self.assertTrue(_source_name_collision(
            "rs/demo/Base/Inner.class", {"rs/demo/Base.class"}
        ))
        self.assertTrue(_source_name_collision(
            "rs/demo/Base.class", {"rs/demo/Base/Inner.class"}
        ))
        self.assertFalse(_source_name_collision(
            "rs/demo/Child.class", {"rs/demo/Base.class"}
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)

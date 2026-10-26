"""Synthetic-JDK-only regression for multi-class original source frontier.

No SpawnPK game binaries, reconstructed Java, or private classfiles are used.
"""
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
    discover_original_source_frontier,
    write_source_frontier,
)


SOURCES = {
    "rs/demo/Base.java": "package rs.demo; public class Base {}",
    "rs/demo/Direct.java":
        "package rs.demo; public class Direct extends Base {}",
    "rs/demo/Chain.java":
        "package rs.demo; public class Chain extends Direct {}",
    "rs/demo/CycleA.java":
        "package rs.demo; public class CycleA { "
        " public CycleB other; public Base anchor; }",
    "rs/demo/CycleB.java":
        "package rs.demo; public class CycleB { public CycleA other; }",
    "rs/demo/FreeA.java":
        "package rs.demo; public class FreeA { public FreeB other; }",
    "rs/demo/FreeB.java":
        "package rs.demo; public class FreeB { public FreeA other; }",
    "rs/demo/NotInJar.java":
        "package rs.demo; public class NotInJar {}",
    "rs/demo/Broken.java":
        "package rs.demo; public class Broken { public NotInJar missing; }",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "Requires javac for real Java 9 fixture")
class ConnectedGroupFrontierTests(unittest.TestCase):
    def fixture(self, root: Path):
        src = root / "sources"
        for relative, body in SOURCES.items():
            path = src / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        classes = root / "classes"
        classes.mkdir()
        command = [
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-encoding", "UTF-8",
            "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-source"),
            "-d", str(classes),
            *[str(src / name) for name in sorted(SOURCES)],
        ]
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=60
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        jar = root / "synthetic-original.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for path in sorted(classes.rglob("*.class")):
                relative = path.relative_to(classes).as_posix()
                if relative == "rs/demo/NotInJar.class":
                    continue  # Broken must NOT become an accepted batch.
                archive.writestr(relative, path.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            pins = {name: digest(archive.read(name)) for name in archive.namelist()}
        manifest = {
            "original_jar_sha256": digest(jar.read_bytes()),
            "original_class_sha256": {
                "rs/demo/Base.class": pins["rs/demo/Base.class"],
            },
        }
        return jar, manifest, pins

    def test_connected_chain_cycle_and_unanchored_pair_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, manifest, pins = self.fixture(Path(directory))
            report = discover_original_source_frontier(jar, manifest)
            self.assertEqual(report["direct_dependency_closed_candidate_count"], 1)
            self.assertEqual(report["candidates"][0]["original_class_path"],
                             "rs/demo/Direct.class")
            self.assertEqual(report["dependency_closed_group_candidate_count"], 3)
            groups = report["dependency_closed_group_candidates"]
            paths = {tuple(group["original_class_paths"]): group for group in groups}
            chain = paths[("rs/demo/Chain.class", "rs/demo/Direct.class")]
            pair = paths[("rs/demo/CycleA.class", "rs/demo/CycleB.class")]
            free = paths[("rs/demo/FreeA.class", "rs/demo/FreeB.class")]
            self.assertTrue(chain["connected_to_selected"])
            self.assertTrue(pair["connected_to_selected"])
            self.assertFalse(free["connected_to_selected"])
            self.assertEqual(pair["internal_explicit_dependency_edges"], 2)
            self.assertEqual(pair["dependencies_to_selected"], ["rs/demo/Base.class"])
            self.assertEqual(chain["additional_class_count"], 2)
            self.assertEqual(chain["original_class_sha256"]["rs/demo/Chain.class"],
                             pins["rs/demo/Chain.class"])
            for group in groups:
                self.assertFalse(group["source_reconstructed"])
                self.assertFalse(group["compile_or_runtime_parity_proven"])
                self.assertFalse(group["class_package_collision_with_selection_or_batch"])
                self.assertNotIn("rs/demo/Broken.class",
                                 group["original_class_paths"])
                self.assertNotIn("rs/demo/NotInJar.class",
                                 group["original_class_paths"])
            self.assertFalse(report["original_class_bytecode_published"])
            self.assertEqual(report["dynamic_or_resource_dependency_closure"],
                             "NOT_PROVEN")

    def test_group_bound_and_limit_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, manifest, _ = self.fixture(Path(directory))
            for size in (1, 33):
                with self.subTest(size=size):
                    with self.assertRaisesRegex(SourceFrontierError,
                                                "INVALID_GROUP_SIZE"):
                        discover_original_source_frontier(
                            jar, manifest, max_group_size=size
                        )
            report = discover_original_source_frontier(
                jar, manifest, max_candidates=1, max_group_size=2
            )
            self.assertEqual(report["dependency_closed_group_candidate_count"], 3)
            self.assertEqual(len(report["dependency_closed_group_candidates"]), 1)
            self.assertEqual(report["max_additional_classes_per_group"], 2)

    def test_existing_sha_and_incomplete_base_gates_apply_to_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, manifest, pins = self.fixture(Path(directory))
            bad_sha = dict(manifest)
            bad_sha["original_jar_sha256"] = "0" * 64
            with self.assertRaisesRegex(SourceFrontierError,
                                        "JAR_SHA_MISMATCH"):
                discover_original_source_frontier(jar, bad_sha)
            unclosed = dict(manifest)
            unclosed["original_class_sha256"] = {
                "rs/demo/Chain.class": pins["rs/demo/Chain.class"],
            }
            with self.assertRaisesRegex(SourceFrontierError,
                                        "BASE_SELECTION_NOT_CLOSED"):
                discover_original_source_frontier(jar, unclosed)

    def test_private_report_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jar, manifest, _ = self.fixture(root)
            import json
            authority = root / "manifest.json"
            authority.write_text(json.dumps(manifest), encoding="utf-8")
            out = root / "frontier-private.json"
            report = write_source_frontier(
                jar, authority, out, max_group_size=2
            )
            self.assertEqual(report["dependency_closed_group_candidate_count"], 3)
            self.assertIn("dependency_closed_group_candidates",
                          json.loads(out.read_text(encoding="utf-8")))
            with self.assertRaisesRegex(SourceFrontierError, "REFUSE_OVERWRITE"):
                write_source_frontier(jar, authority, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

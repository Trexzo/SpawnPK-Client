"""End-to-end original-name parity for Java9 source with node-type aliases."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import verify_standalone_sources


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"), "JDK required")
class NodeCollectionParityTests(unittest.TestCase):
    def test_original_node_package_child_and_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root / "sources"
            bodies = {
                "rs/t.java": (
                    "package rs; public class t { public t next;"
                    " public t() {} public void unlink() { next = null; } }"
                ),
                "rs/t/f.java": (
                    "package rs.t; public final class f {"
                    " public int value() { return 5; } }"
                ),
                "rs/Collection.java": (
                    "package rs; public final class Collection {"
                    " private final t sentinel = new t();"
                    " private t cursor;"
                    " public t first() { t node = sentinel; return node; }"
                    " public void set(t node) { cursor = node; }"
                    " public t current() { return cursor; } }"
                ),
            }
            for name, body in bodies.items():
                path = src / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            out = root / "original-source-built.jar"
            classes = {}
            with zipfile.ZipFile(out, "w") as archive:
                for number, name in enumerate(bodies):
                    dest = root / ("original-build-" + str(number))
                    dest.mkdir()
                    cmd = [
                        "javac", "--release", "9", "-proc:none", "-g:none",
                        "-sourcepath", str(root / "empty-sp"),
                        "-classpath",
                        str(root / "original-build-0")
                        if number == 2 else str(root / "empty-cp"),
                        "-d", str(dest), str(src / name),
                    ]
                    run = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=45
                    )
                    self.assertEqual(run.returncode, 0, run.stderr)
                    member = name[:-5] + ".class"
                    blob = (dest / member).read_bytes()
                    archive.writestr(member, blob)
                    classes[member] = hashlib.sha256(blob).hexdigest()
            report = verify_standalone_sources(
                out, src, root / "accepted",
                original_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                class_sha256=classes,
                compile_aliases={"rs/t.class": "rs/RecoveredNodeV311.class"},
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 3)
            self.assertEqual(report["compile_only_class_alias_count"], 1)
            self.assertEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"
                ], 1,
            )
            self.assertFalse(report["canonical_source_modified"])
            self.assertTrue(
                (root / "accepted" / "restored-classfiles"
                 / "rs/Collection.class").is_file()
            )


if __name__ == "__main__":
    unittest.main()

"""R34: complete staged Java-source closure and drift vetoes."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from spk_recovery.source_tree_fingerprint import (
    SourceTreeError, fingerprint_java_source_tree,
)
from spk_recovery.source_candidate_replay import (
    SourceCandidateReplayError, compile_private_source_candidate,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class JavaSourceTreeFingerprintTests(unittest.TestCase):
    def _tree(self, root: Path) -> Path:
        tree = root / "private-sources"
        pkg = tree / "p"
        pkg.mkdir(parents=True)
        (pkg / "A.java").write_text("package p; class A {}", encoding="utf-8")
        (pkg / "B.java").write_text("package p; class B {}", encoding="utf-8")
        return tree

    def test_stable_across_different_private_roots(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = self._tree(root / "first")
            b = self._tree(root / "second")
            pa = fingerprint_java_source_tree(a)
            pb = fingerprint_java_source_tree(b)
            self.assertEqual(pa, pb)
            self.assertEqual(pa["source_java_file_count"], 2)
            self.assertNotIn(str(a), str(pa))
            self.assertNotIn("A.java", str(pa))

    def test_dependency_edit_addition_deletion_and_rename_change_pin(self):
        with tempfile.TemporaryDirectory() as d:
            tree = self._tree(Path(d))
            before = fingerprint_java_source_tree(tree)["source_tree_sha256"]
            dep = tree / "p" / "B.java"
            dep.write_text("package p; class B { int x=2; }", encoding="utf-8")
            self.assertNotEqual(
                fingerprint_java_source_tree(tree)["source_tree_sha256"], before
            )
            dep.write_text("package p; class B {}", encoding="utf-8")
            self.assertEqual(
                fingerprint_java_source_tree(tree)["source_tree_sha256"], before
            )
            dep.rename(tree / "p" / "Renamed.java")
            self.assertNotEqual(
                fingerprint_java_source_tree(tree)["source_tree_sha256"], before
            )
            (tree / "p" / "Renamed.java").unlink()
            self.assertEqual(fingerprint_java_source_tree(tree)["source_java_file_count"], 1)

    def test_nonjava_content_not_part_of_java_closure(self):
        with tempfile.TemporaryDirectory() as d:
            tree = self._tree(Path(d))
            before = fingerprint_java_source_tree(tree)
            (tree / "README.txt").write_text("ignored data", encoding="utf-8")
            self.assertEqual(before, fingerprint_java_source_tree(tree))

    def test_missing_source_fails(self):
        with tempfile.TemporaryDirectory() as d:
            tree = Path(d) / "empty"
            tree.mkdir()
            with self.assertRaisesRegex(SourceTreeError, "SOURCE_TREE_HAS_NO_JAVA_FILES"):
                fingerprint_java_source_tree(tree)

    def test_symlinked_source_dependency_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            tree = self._tree(Path(d))
            link = tree / "p" / "External.java"
            try:
                link.symlink_to(tree / "p" / "A.java")
            except (OSError, NotImplementedError):
                self.skipTest("Creating symlinks requires platform permissions")
            with self.assertRaisesRegex(SourceTreeError, "SOURCE_TREE_NONREGULAR_OR_SYMLINK_FILE"):
                fingerprint_java_source_tree(tree)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ClosedSourceReplayTests(unittest.TestCase):
    def _fixture(self, root: Path):
        source_root = root / "candidate" / "p"
        original_root = root / "original" / "p"
        classes = root / "original-classes"
        for d in (source_root, original_root, classes):
            d.mkdir(parents=True)
        orig = original_root / "A.java"
        orig.write_text("package p; public class A { public int x(){return 1;} }",
                        encoding="utf-8")
        main = source_root / "A.java"
        main.write_text("package p; public class A { public int x(){return 1;} }",
                        encoding="utf-8")
        subprocess.run(["javac", "-g:none", "--release", "9",
                        "-d", str(classes), str(orig)], check=True,
                       capture_output=True)
        jar = root / "original.jar"
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "A.class", "p/A.class")
        return jar, source_root.parent, main

    def _run(self, jar, root, main, out, tree_pin=None):
        return compile_private_source_candidate(
            jar, root, main, out,
            original_sha256=_sha(jar), source_sha256=_sha(main),
            source_tree_sha256=tree_pin or fingerprint_java_source_tree(root)["source_tree_sha256"],
            class_entry="p/A.class",
        )

    def test_closed_source_tree_success_and_report_pin(self):
        with tempfile.TemporaryDirectory() as d:
            jar, root, main = self._fixture(Path(d))
            result = self._run(jar, root, main, Path(d) / "out")
            self.assertEqual(result["source_java_file_count"], 1)
            self.assertTrue(result["complete_staged_java_tree_pre_and_postflight_verified"])
            self.assertEqual(result["source_tree_sha256"],
                             fingerprint_java_source_tree(root)["source_tree_sha256"])
            self.assertEqual(result["class_method_matrix"]["counts"]["instruction_parity"], 2)

    def test_wrong_secondary_dependency_pin_prevents_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            jar, root, main = self._fixture(Path(d))
            saved = fingerprint_java_source_tree(root)["source_tree_sha256"]
            helper = root / "p" / "Helper.java"
            helper.write_text("package p; class Helper {}", encoding="utf-8")
            out = Path(d) / "none"
            with self.assertRaisesRegex(SourceCandidateReplayError, "SOURCE_TREE_SHA256_MISMATCH"):
                self._run(jar, root, main, out, tree_pin=saved)
            self.assertFalse(out.exists())

    def test_secondary_java_changed_during_compile_refuses_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            jar, root, main = self._fixture(Path(d))
            helper = root / "p" / "Helper.java"
            helper.write_text(
                "package p; class Helper { static int value(){return 2;} }",
                encoding="utf-8",
            )
            main.write_text(
                "package p; public class A { public int x(){return Helper.value();} }",
                encoding="utf-8",
            )
            original_run = subprocess.run
            def mutating_run(*args, **kwargs):
                result = original_run(*args, **kwargs)
                helper.write_text(
                    "package p; class Helper { static int value(){return 3;} }",
                    encoding="utf-8",
                )
                return result
            out = Path(d) / "out"
            with patch("spk_recovery.source_candidate_replay.subprocess.run",
                       side_effect=mutating_run):
                with self.assertRaisesRegex(
                    SourceCandidateReplayError, "SOURCE_TREE_CHANGED_DURING_REPLAY",
                ):
                    self._run(jar, root, main, out)
            self.assertFalse((out / "private-candidate-report.json").exists())

    def test_symlink_root_rejected_before_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            jar, root, main = self._fixture(Path(d))
            linked = Path(d) / "linked"
            try:
                linked.symlink_to(root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Creating symlinks requires platform permissions")
            pin = fingerprint_java_source_tree(root)["source_tree_sha256"]
            with self.assertRaisesRegex(SourceCandidateReplayError, "SOURCE_ROOT_SYMLINK_NOT_ALLOWED"):
                self._run(jar, linked, linked / "p" / "A.java", Path(d) / "out",
                          tree_pin=pin)
            self.assertFalse((Path(d) / "out").exists())


if __name__ == "__main__":
    unittest.main()

"""R33 synthetic Java compilation proof; never uses original SpawnPK bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.source_tree_fingerprint import fingerprint_java_source_tree

from spk_recovery.source_candidate_replay import (
    SourceCandidateReplayError, compile_private_source_candidate,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac must be available")
class SourceCandidateCompileReplayTests(unittest.TestCase):
    def _fixture(self, root: Path, original: str = "return x + 1;",
                 candidate: str = "return x + 1;"):
        original_src = root / "authority-source" / "p"
        candidate_root = root / "candidate-source"
        candidate_src = candidate_root / "p"
        original_src.mkdir(parents=True)
        candidate_src.mkdir(parents=True)
        old = original_src / "A.java"
        source = candidate_src / "A.java"
        old.write_text(
            "package p; public class A { public int get(int x){" + original + "} }",
            encoding="utf-8",
        )
        source.write_text(
            "package p; public class A { public int get(int x){" + candidate + "} }",
            encoding="utf-8",
        )
        (original_src / "Secret.java").write_text(
            "package p; public class Secret { public static int value(){return 42;} }",
            encoding="utf-8",
        )
        classes = root / "classes"
        classes.mkdir()
        compiled = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(old), str(original_src / "Secret.java")],
            capture_output=True, text=True,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        jar = root / "original.jar"
        with ZipFile(jar, "w") as archive:
            archive.write(classes / "p" / "A.class", "p/A.class")
            archive.write(classes / "p" / "Secret.class", "p/Secret.class")
        return jar, candidate_root, source

    def _run(self, base: Path, *, old_code="return x + 1;",
             candidate_code="return x + 1;", out=None,
             old_pin=None, source_pin=None, tree_pin=None, timeout=180):
        original, root, source = self._fixture(
            base, original=old_code, candidate=candidate_code,
        )
        return compile_private_source_candidate(
            original, root, source, out or base / "replay",
            original_sha256=old_pin or _digest(original),
            source_sha256=source_pin or _digest(source),
            source_tree_sha256=tree_pin or fingerprint_java_source_tree(root)["source_tree_sha256"],
            class_entry="p/A.class", timeout_seconds=timeout,
        )

    def test_private_source_compiles_without_original_classpath(self):
        with tempfile.TemporaryDirectory() as d:
            result = self._run(Path(d))
            self.assertEqual(result["compiler_release"], 9)
            self.assertTrue(result["annotation_processors_disabled"])
            self.assertTrue(result["original_client_binary_classpath_disabled"])
            self.assertEqual(result["class_method_matrix"]["counts"]["instruction_parity"], 2)
            self.assertFalse(result["source_equivalence_certified"])
            self.assertFalse(result["canonical_identity_accepted"])
            manifest = Path(d) / "replay" / "private-candidate-report.json"
            self.assertEqual(json.loads(manifest.read_text()), result)
            self.assertTrue((Path(d) / "replay" / "private-candidate.jar").is_file())
            self.assertNotIn("p/A", json.dumps(result))

    def test_source_drift_is_counted_not_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            result = self._run(Path(d), candidate_code="return x + 2;")
            self.assertEqual(result["class_method_matrix"]["counts"]["body_difference"], 1)
            self.assertFalse(result["source_equivalence_certified"])

    def test_output_is_deterministic_between_fresh_runs(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            original, source_root, source = self._fixture(base)
            def call(name):
                return compile_private_source_candidate(
                    original, source_root, source, base / name,
                    original_sha256=_digest(original), source_sha256=_digest(source),
                    source_tree_sha256=fingerprint_java_source_tree(source_root)["source_tree_sha256"],
                    class_entry="p/A.class",
                )
            first, second = call("one"), call("two")
            self.assertEqual(first, second)
            self.assertEqual(
                (base / "one" / "private-candidate.jar").read_bytes(),
                (base / "two" / "private-candidate.jar").read_bytes(),
            )

    def test_mismatched_hash_and_invalid_timeout_create_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            old, root, source = self._fixture(base)
            for overrides, expected in [
                ({"original_sha256": "0" * 64}, "ORIGINAL_JAR_SHA256_MISMATCH"),
                ({"source_sha256": "0" * 64}, "JAVA_SOURCE_SHA256_MISMATCH"),
                ({"timeout_seconds": 0}, "INVALID_COMPILER_TIMEOUT"),
                ({"timeout_seconds": True}, "INVALID_COMPILER_TIMEOUT"),
            ]:
                with self.subTest(overrides=overrides):
                    args = dict(
                        original_sha256=_digest(old),
                        source_sha256=_digest(source),
                        source_tree_sha256=fingerprint_java_source_tree(root)["source_tree_sha256"],
                        class_entry="p/A.class",
                    )
                    args.update(overrides)
                    with self.assertRaisesRegex(SourceCandidateReplayError, expected):
                        compile_private_source_candidate(
                            old, root, source, base / "output", **args,
                        )
                    self.assertFalse((base / "output").exists())

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            old, root, source = self._fixture(base)
            dest = base / "output"
            dest.mkdir()
            marker = dest / "important.txt"
            marker.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                SourceCandidateReplayError, "OUTPUT_ROOT_ALREADY_EXISTS"
            ):
                compile_private_source_candidate(
                    old, root, source, dest,
                    original_sha256=_digest(old), source_sha256=_digest(source),
                    source_tree_sha256=fingerprint_java_source_tree(root)["source_tree_sha256"],
                    class_entry="p/A.class",
                )
            self.assertEqual(marker.read_text(), "KEEP")

    def test_syntax_error_leaves_no_success_manifest_and_redacts_source(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            old, root, source = self._fixture(base)
            source.write_text("SECRET_SOURCE_LITERAL ~~~~~~~~", encoding="utf-8")
            dest = base / "replay"
            with self.assertRaisesRegex(
                SourceCandidateReplayError, "SOURCE_COMPILATION_FAILED"
            ) as failure:
                compile_private_source_candidate(
                    old, root, source, dest,
                    original_sha256=_digest(old), source_sha256=_digest(source),
                    source_tree_sha256=fingerprint_java_source_tree(root)["source_tree_sha256"],
                    class_entry="p/A.class",
                )
            self.assertNotIn("SECRET_SOURCE_LITERAL", str(failure.exception))
            self.assertFalse((dest / "private-candidate-report.json").exists())

    def test_compile_cannot_reuse_original_client_as_binary_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            old, root, source = self._fixture(base)
            # p/Secret.class is present in the original client JAR but not
            # the candidate's staged Java source tree.
            source.write_text(
                "package p; public class A { int x(){return Secret.value();} }",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                SourceCandidateReplayError, "SOURCE_COMPILATION_FAILED"
            ):
                compile_private_source_candidate(
                    old, root, source, base / "out",
                    original_sha256=_digest(old), source_sha256=_digest(source),
                    source_tree_sha256=fingerprint_java_source_tree(root)["source_tree_sha256"],
                    class_entry="p/A.class",
                )
            self.assertFalse((base / "out" / "private-candidate-report.json").exists())

    def test_wrong_class_target_fails_without_publishing_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            old, root, source = self._fixture(base)
            with self.assertRaisesRegex(
                SourceCandidateReplayError, "TARGET_CLASS_NOT_COMPILED"
            ):
                compile_private_source_candidate(
                    old, root, source, base / "out",
                    original_sha256=_digest(old), source_sha256=_digest(source),
                    source_tree_sha256=fingerprint_java_source_tree(root)["source_tree_sha256"],
                    class_entry="p/Wrong.class",
                )
            self.assertFalse((base / "out" / "private-candidate-report.json").exists())


if __name__ == "__main__":
    unittest.main()

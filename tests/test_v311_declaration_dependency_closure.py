"""Real Java9 bytecode regression: own declarations and generic signatures.

These references can be present without any CONSTANT_Class or NameAndType
mention. They must not be silently omitted by a source-closure frontier.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.source_dependency_closure import (
    explicit_class_references,
    require_selected_source_closure,
    SourceClosureError,
)
from spk_recovery.source_island_frontier import discover_original_source_frontier
from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError,
    verify_standalone_sources,
)


SOURCE = {
    "rs/demo/Target.java":
        "package rs.demo; public class Target {}",
    "rs/demo/OwnFieldOnly.java":
        "package rs.demo; public class OwnFieldOnly { public Target value; }",
    "rs/demo/OnlyAbstractMethod.java":
        "package rs.demo; public interface OnlyAbstractMethod { "
        " Target make(Target previous); }",
    "rs/demo/OnlyGeneric.java":
        "package rs.demo; import java.util.List; "
        "public class OnlyGeneric { public List<Target> value; }",
    "rs/demo/LiteralOnly.java":
        'package rs.demo; public class LiteralOnly { '
        'public static final String TEXT = "Lrs/demo/Target;"; }',
}


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "JDK required for actual Java 9 source compilation")
class DeclarationDependencyClosureTests(unittest.TestCase):
    def fixture(self, root: Path):
        src = root / "source"
        for relative, text in SOURCE.items():
            path = src / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        compiled = root / "original-compiled"
        compiled.mkdir()
        process = subprocess.run(
            ["javac", "--release", "9", "-proc:none", "-g:none",
             "-encoding", "UTF-8", "-classpath", str(root / "empty-cp"),
             "-sourcepath", str(root / "empty-sourcepath"), "-d", str(compiled),
             *[str(src / path) for path in sorted(SOURCE)]],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        jar = root / "actual-jdk-original.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for path in sorted(compiled.rglob("*.class")):
                archive.writestr(
                    path.relative_to(compiled).as_posix(),
                    path.read_bytes(),
                )
        with zipfile.ZipFile(jar) as archive:
            pins = {name: sha(archive.read(name)) for name in archive.namelist()}
        self.assertEqual(len(pins), 5)
        return jar, src, pins

    def test_field_declaration_only_reference_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, _, _ = self.fixture(Path(directory))
            with zipfile.ZipFile(jar) as archive:
                deps = explicit_class_references(
                    archive.read("rs/demo/OwnFieldOnly.class")
                )
            self.assertIn("rs/demo/Target.class", deps)

    def test_abstract_method_signature_only_reference_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, _, _ = self.fixture(Path(directory))
            with zipfile.ZipFile(jar) as archive:
                deps = explicit_class_references(
                    archive.read("rs/demo/OnlyAbstractMethod.class")
                )
            self.assertIn("rs/demo/Target.class", deps)

    def test_generic_signature_erased_from_field_descriptor_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, _, _ = self.fixture(Path(directory))
            with zipfile.ZipFile(jar) as archive:
                deps = explicit_class_references(
                    archive.read("rs/demo/OnlyGeneric.class")
                )
            self.assertIn("rs/demo/Target.class", deps)

    def test_literal_descriptor_looking_string_is_not_a_type(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, _, _ = self.fixture(Path(directory))
            with zipfile.ZipFile(jar) as archive:
                deps = explicit_class_references(
                    archive.read("rs/demo/LiteralOnly.class")
                )
            self.assertNotIn("rs/demo/Target.class", deps)

    def test_single_class_without_own_declared_dependency_is_refused_precompile(self):
        for original in ("OwnFieldOnly", "OnlyAbstractMethod", "OnlyGeneric"):
            with self.subTest(original=original):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    jar, src, pins = self.fixture(root)
                    entry = "rs/demo/" + original + ".class"
                    out = root / "must-not-be-created"
                    with self.assertRaisesRegex(
                        StandaloneSourceParityError,
                        "PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION",
                    ):
                        verify_standalone_sources(
                            jar, src, out,
                            original_sha256=sha(jar.read_bytes()),
                            class_sha256={entry: pins[entry]},
                        )
                    self.assertFalse(out.exists())

    def test_frontier_only_admits_declaration_dependent_types_after_target_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jar, _, pins = self.fixture(root)
            manifest = {
                "original_jar_sha256": sha(jar.read_bytes()),
                "original_class_sha256": {
                    "rs/demo/Target.class": pins["rs/demo/Target.class"],
                },
            }
            report = discover_original_source_frontier(jar, manifest)
            actual = {
                c["original_class_path"] for c in report["candidates"]
            }
            self.assertEqual(actual, {
                "rs/demo/OwnFieldOnly.class",
                "rs/demo/OnlyAbstractMethod.class",
                "rs/demo/OnlyGeneric.class",
            })
            self.assertEqual(report["direct_dependency_closed_candidate_count"], 3)

    def test_declared_field_without_target_is_not_closed_even_if_literal_present(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jar, _, pins = self.fixture(root)
            with zipfile.ZipFile(jar) as archive:
                with self.assertRaisesRegex(
                    SourceClosureError,
                    "PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION",
                ):
                    require_selected_source_closure(
                        archive, {"rs/demo/OwnFieldOnly.class"}
                    )
                accepted = require_selected_source_closure(
                    archive, {"rs/demo/Target.class", "rs/demo/OwnFieldOnly.class"}
                )
            self.assertEqual(accepted["source_project_dependency_edges"], 1)
            self.assertTrue(accepted["member_declaration_descriptors_checked"])
            self.assertTrue(accepted["generic_signature_metadata_checked"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

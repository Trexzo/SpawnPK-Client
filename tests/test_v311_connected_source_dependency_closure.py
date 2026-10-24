"""JDK-only tests for fail-closed explicit project dependency closure."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.source_dependency_closure import (
    SourceClosureError, explicit_class_references,
)
from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)


BASE = """package rs.demo;
public class RelatedBase {
    public int value;
    public RelatedBase(int initial) { this.value = initial; }
    public int get() { return this.value; }
}
"""
CHILD = """package rs.demo;
public final class RelatedChild extends RelatedBase {
    public RelatedChild() { super(19); }
    public int read() { return get(); }
}
"""


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("javap"), "Requires Java JDK",
)
class ProjectSourceClosureTests(unittest.TestCase):
    def fixture(self, root: Path):
        src = root / "java"
        for relative, content in [
            ("rs/demo/RelatedBase.java", BASE),
            ("rs/demo/RelatedChild.java", CHILD),
        ]:
            file = src / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content, encoding="utf-8")
        compiled = root / "original-build"
        compiled.mkdir()
        run = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-encoding", "UTF-8",
            "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-sp"),
            "-d", str(compiled),
            str(src / "rs/demo/RelatedBase.java"),
            str(src / "rs/demo/RelatedChild.java"),
        ], capture_output=True, text=True, timeout=45)
        self.assertEqual(run.returncode, 0, run.stderr)
        jar = root / "source-fixture.jar"
        with zipfile.ZipFile(jar, "w") as z:
            for path in sorted(compiled.rglob("*.class")):
                z.writestr(path.relative_to(compiled).as_posix(), path.read_bytes())
        with zipfile.ZipFile(jar) as z:
            hashes = {name: sha(z.read(name)) for name in z.namelist()}
            base = z.read("rs/demo/RelatedBase.class")
            child = z.read("rs/demo/RelatedChild.class")
        return jar, src, hashes, base, child

    def test_original_child_references_original_base_class(self):
        with tempfile.TemporaryDirectory() as d:
            jar, src, hashes, base, child = self.fixture(Path(d))
            self.assertIn("rs/demo/RelatedBase.class", explicit_class_references(child))
            self.assertIn("rs/demo/RelatedBase.class", explicit_class_references(base))
            self.assertEqual(
                explicit_class_references(child) - {"rs/demo/RelatedChild.class"},
                {"rs/demo/RelatedBase.class"},
            )

    def test_connected_real_javac_compile_and_symbolic_parity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            jar, src, hashes, base, child = self.fixture(root)
            report = verify_standalone_sources(
                jar, src, root / "accepted",
                original_sha256=sha(jar.read_bytes()),
                class_sha256=hashes,
            )
            self.assertTrue(report["all_passed"])
            closure = report["explicit_original_project_dependency_closure"]
            self.assertEqual(closure["selected_classes"], 2)
            self.assertEqual(closure["source_project_dependency_edges"], 1)
            self.assertTrue(closure["explicit_project_class_closure"])
            self.assertFalse(closure["dynamic_class_loading_or_reflection_closed"])
            self.assertFalse(closure["resources_or_native_dependencies_closed"])

    def test_real_java9_two_interface_source_only_parity(self):
        # This is not a synthetic fake disassembly: javac emits two actual
        # Java9 interfaces with zero Code instructions and a verified
        # inter-interface type dependency.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "sources"
            definitions = {
                "rs/demo/UiBase.java": (
                    "package rs.demo; public interface UiBase { void open(); }"
                ),
                "rs/demo/UiDerived.java": (
                    "package rs.demo; public interface UiDerived extends UiBase"
                    " { void close(); }"
                ),
            }
            for relative, code in definitions.items():
                file = src / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(code, encoding="utf-8")
            original_classes = root / "original-classes"
            original_classes.mkdir()
            compiled = subprocess.run([
                "javac", "--release", "9", "-proc:none", "-g:none",
                "-classpath", str(root / "empty-classpath"),
                "-sourcepath", str(root / "empty-sourcepath"),
                "-d", str(original_classes),
                *[str(src / name) for name in sorted(definitions)],
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            jar = root / "synthetic-original.jar"
            with zipfile.ZipFile(jar, "w") as archive:
                for classfile in sorted(original_classes.rglob("*.class")):
                    archive.writestr(
                        classfile.relative_to(original_classes).as_posix(),
                        classfile.read_bytes(),
                    )
            with zipfile.ZipFile(jar) as archive:
                hashes = {entry: sha(archive.read(entry))
                          for entry in archive.namelist()}
            report = verify_standalone_sources(
                jar, src, root / "verified",
                original_sha256=sha(jar.read_bytes()),
                class_sha256=hashes,
            )
            self.assertEqual(report["total_classes"], 2)
            self.assertEqual(report["total_ordered_instructions"], 0)
            self.assertEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"
                ], 1,
            )
            self.assertTrue(report["all_passed"])

    def test_truncated_concrete_class_disassembly_does_not_pass_as_interface(self):
        from spk_recovery.standalone_source_parity import _normalize_javap
        text = (
            "public class rs.demo.Fake {\n"
            "  public void run();\n"
            "    descriptor: ()V\n"
            "}\n"
        )
        with self.assertRaisesRegex(
            StandaloneSourceParityError, "DISASSEMBLY_HAS_NO_INSTRUCTIONS"
        ):
            _normalize_javap(text)

    def test_missing_base_refuses_before_output_creation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            jar, src, hashes, base, child = self.fixture(root)
            out = root / "no-output"
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION",
            ):
                verify_standalone_sources(
                    jar, src, out,
                    original_sha256=sha(jar.read_bytes()),
                    class_sha256={"rs/demo/RelatedChild.class": hashes[
                        "rs/demo/RelatedChild.class"
                    ]},
                )
            self.assertFalse(out.exists())

    def test_corrupt_constant_pool_is_not_accepted(self):
        with self.assertRaisesRegex(SourceClosureError, "NOT_CLASSFILE"):
            explicit_class_references(b"not a JVM class")
        with self.assertRaisesRegex(SourceClosureError, "TRUNCATED_CONSTANT_POOL"):
            explicit_class_references(bytes.fromhex("cafebabe00000035") + b"\x00\x02\x01")

    def test_jdk_only_empty_explicit_reference_surface(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            jar, src, hashes, base, child = self.fixture(root)
            self.assertEqual(explicit_class_references(base), {"rs/demo/RelatedBase.class"})


if __name__ == "__main__":
    unittest.main(verbosity=2)

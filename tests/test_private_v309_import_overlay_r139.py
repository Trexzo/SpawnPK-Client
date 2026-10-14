"""R139: real Javac parse-only import spans and R125 classpath remap fixture."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_import_overlay_r139 import (
    PrivateImportOverlayR139Error,
    import_overlay_entries, private_import_overlay, safe_package_only_imports,
)
from spk_recovery.private_v309_compiler_frontier_r137 import (
    _normalize_private_provisional_capsule,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required")
class PrivateImportOverlayR139Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def build_class(self, internal, java_source):
        directory = self.root / ("fixture" + str(len(list(self.root.iterdir()))))
        file = directory / (internal + ".java")
        file.parent.mkdir(parents=True)
        file.write_text(java_source, encoding="utf-8")
        classes = directory / "classes"
        classes.mkdir()
        result = subprocess.run(
            [shutil.which("javac"), "--release", "9", "-g:none",
             "-proc:none", "-d", str(classes), str(file)],
            capture_output=True)
        self.assertEqual(0, result.returncode,
                         result.stderr.decode("utf-8", errors="replace"))
        return (classes / (internal + ".class")).read_bytes()

    def synthetic_original(self):
        source_jar = self.root / "original.jar"
        binaries = {
            "ext/A/Target": self.build_class(
                "ext/A/Target", "package ext.A; public class Target {}"),
            "ext/a/Other": self.build_class(
                "ext/a/Other",
                "package ext.a; public class Other {"
                " public static int value() { return 23; } }"),
            "rs/Game": self.build_class(
                "rs/Game", "package rs; public class Game {}"),
        }
        with ZipFile(source_jar, "w") as archive:
            for key, raw in sorted(binaries.items()):
                archive.writestr(key + ".class", raw)
        return source_jar

    def source_text(self):
        return (
            "package rs;\n"
            "import ext.a.Other;\n"
            "public class RecoveredClient { "
            "public int value() { return Other.value(); } }\n"
        ).encode()

    def test_safe_package_rename_preserves_type_leaf(self):
        allowed, deferred, digest = safe_package_only_imports({
            "ext/A/Target", "ext/a/Other", "ext/n", "ext/n/Child",
        })
        self.assertIn("ext.a.Other", allowed)
        self.assertTrue(allowed["ext.a.Other"].startswith("ext.a__Pkg_"))
        self.assertTrue(allowed["ext.a.Other"].endswith(".Other"))
        self.assertIn("ext.n", deferred)
        self.assertEqual(64, len(digest))

    def test_real_ast_rewrite_and_negative_guards(self):
        eligible, deferred, _ = safe_package_only_imports({
            "ext/A/Target", "ext/a/Other", "ext/n", "ext/n/Child",
        })
        unchanged = ("rs/Other.java", b"package rs; public class Other {}\n")
        source = ("rs/RecoveredClient.java", self.source_text())
        edited, report = import_overlay_entries(
            [unchanged, source], eligible, deferred)
        self.assertEqual(1, report["changed_java_file_count"])
        self.assertEqual(1, report["ast_verified_explicit_import_edits"])
        self.assertEqual(unchanged, edited[0])
        self.assertIn(
            ("import " + eligible["ext.a.Other"] + ";").encode(),
            edited[1][1])
        self.assertIn(b"Other.value()", edited[1][1])
        self.assertNotIn(b"import ext.a.Other;", edited[1][1])

        # Original qualified usages need separate source-symbol proof.
        body = self.source_text() + b"// ext.a.Other\n"
        withheld, counts = import_overlay_entries(
            [("rs/Unsafe.java", body)], eligible, deferred)
        self.assertEqual(body, withheld[0][1])
        self.assertEqual(1, counts["whole_java_files_withheld_for_unresolved_imports"])

        # R125 class/package alias has a different simple name; no edit.
        body = b"package rs;\nimport ext.n;\npublic class X { n value; }\n"
        withheld, counts = import_overlay_entries(
            [("rs/X.java", body)], eligible, deferred)
        self.assertEqual(body, withheld[0][1])
        self.assertEqual(1, counts["withheld_unsafe_import_count"])

        # Malformed source with an affected import must fail, not fall back
        # to text-only replacement.
        with self.assertRaises(PrivateImportOverlayR139Error):
            import_overlay_entries(
                [("rs/Bad.java", b"import ext.a.Other; class Broken {")],
                eligible, deferred)

    def test_private_pinned_zip_overlay_compiles_with_actual_r138_remap(self):
        jar = self.synthetic_original()
        src = self.root / "source.zip"
        with ZipFile(src, "w") as archive:
            archive.writestr("src/main/java/rs/RecoveredClient.java",
                             self.source_text())
        source_sha = hashlib.sha256(src.read_bytes()).hexdigest()
        jar_sha = hashlib.sha256(jar.read_bytes()).hexdigest()
        overlay, report = private_import_overlay(
            src, jar, source_sha256=source_sha, original_sha256=jar_sha)
        self.assertEqual(1, report["changed_java_file_count"])
        self.assertEqual(1, report["ast_verified_explicit_import_edits"])
        self.assertFalse(report["complete_v309_client_compilation_accepted"])
        self.assertEqual(2, report["provisional_non_rs_binary_class_count"])
        self.assertEqual(1, report["source_java_file_count"])

        with ZipFile(jar) as original:
            capsule = self.root / "nonrs.jar"
            with ZipFile(capsule, "w") as stage:
                for name in original.namelist():
                    if name.startswith("ext/"):
                        stage.writestr(name, original.read(name))
        remapped = self.root / "remapped.jar"
        normalized = _normalize_private_provisional_capsule(
            capsule, remapped, self.root)
        self.assertEqual(0, normalized["post_collision_edges"])
        source_file = self.root / "RecoveredClient.java"
        output = self.root / "build"
        output.mkdir()
        cmd = [shutil.which("javac"), "--release", "11",
               "-proc:none", "-implicit:none", "-classpath", str(remapped),
               "-d", str(output), str(source_file)]
        source_file.write_bytes(self.source_text())
        before = subprocess.run(cmd, capture_output=True)
        self.assertNotEqual(0, before.returncode)
        source_file.write_bytes(overlay[0][1])
        after = subprocess.run(cmd, capture_output=True)
        self.assertEqual(0, after.returncode,
                         after.stderr.decode("utf-8", errors="replace"))
        self.assertTrue((output / "rs/RecoveredClient.class").exists())

        with self.assertRaises(Exception):
            private_import_overlay(
                src, jar, source_sha256="0" * 64, original_sha256=jar_sha)


if __name__ == "__main__":
    unittest.main()

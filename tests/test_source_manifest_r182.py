"""Synthetic tests for the private source/dependency manifest guard."""
import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from source_manifest_r182 import inventory_source, inspect_dependencies


class SourceManifestTests(unittest.TestCase):
    def test_source_inventory_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").mkdir()
            (root / "a" / "A.java").write_text("class A {}\n", encoding="utf-8")
            first = inventory_source(root)
            self.assertEqual(1, first["file_count"])
            self.assertEqual(first, inventory_source(root))
            (root / "a" / "A.java").write_text("class A { int x; }\n", encoding="utf-8")
            self.assertNotEqual(first["source_scope_sha256"], inventory_source(root)["source_scope_sha256"])

    def test_windows_casefold_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Foo.java").write_text("class Foo {}", encoding="utf-8")
            (root / "foo.java").write_text("class foo {}", encoding="utf-8")
            # Case-insensitive file systems alias both names; don't assert
            # a false collision when the OS cannot create separate paths.
            if len(list(root.glob("*.java"))) == 2:
                with self.assertRaisesRegex(ValueError, "casefold"):
                    inventory_source(root)

    def test_dependency_hash_and_forbidden_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.jar"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("org/example/Library.class", b"\xca\xfe")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            good = inspect_dependencies([path], {path.name: digest})
            self.assertEqual(1, len(good["dependencies"]))
            with self.assertRaisesRegex(ValueError, "Unapproved"):
                inspect_dependencies([path], {path.name: "0" * 64})
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("rs/x/e.class", b"\xca\xfe")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "Forbidden"):
                inspect_dependencies([path], {path.name: digest})

    def test_duplicate_archive_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.jar"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("org/example/D.class", b"1")
                z.writestr("org/example/D.class", b"2")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                inspect_dependencies([path], {path.name: digest})


if __name__ == "__main__":
    unittest.main()

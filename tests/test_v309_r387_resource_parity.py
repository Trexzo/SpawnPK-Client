"""R387 synthetic-only resource verifier tests. No private Java or JAR bytes."""
import hashlib, stat, sys, tempfile, unittest, warnings
from pathlib import Path
from zipfile import ZipFile, ZipInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.r387.verify_original_resources import Refused, verify

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class ResourceParityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.original = root / "original.jar"
        self.companion = root / "companion.jar"
        self.original_items = [
            ("demo/A.class", b"class A"),
            ("META-INF/MANIFEST.MF", b"Manifest-Version: 1.0\r\n"),
            ("assets/pixel.png", b"abc\x00"),
        ]
        self.companion_items = self.original_items[1:]
        self.pack()

    def pack(self):
        for path, items in ((self.original, self.original_items),
                            (self.companion, self.companion_items)):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(path, "w") as archive:
                    for name, payload in items:
                        archive.writestr(name, payload)

    def check(self, *, osha=None, csha=None):
        return verify(self.original, self.companion,
                      original_sha=osha or digest(self.original),
                      companion_sha=csha or digest(self.companion),
                      expected_classes=1, expected_resources=2)

    def test_exact_preservation(self):
        result = self.check()
        self.assertEqual(result["status"], "R387_RESOURCE_PRESERVATION_PASS")
        self.assertEqual(result["resource_entries_preserved"], 2)
        self.assertFalse(result["runtime_equivalence_proven"])
        self.assertFalse(result["stage_cleanup_authorized"])

    def test_tampered_original_hash(self):
        with self.assertRaisesRegex(Refused, "PIN_MISMATCH"):
            self.check(osha="0" * 64)

    def test_tampered_companion_hash(self):
        with self.assertRaisesRegex(Refused, "PIN_MISMATCH"):
            self.check(csha="0" * 64)

    def test_malformed_pin(self):
        with self.assertRaisesRegex(Refused, "UNSAFE_INPUT_OR_PIN"):
            self.check(osha="bad")

    def test_missing_resource(self):
        self.companion_items.pop()
        self.pack()
        with self.assertRaisesRegex(Refused, "COMPANION_NOT_RESOURCE_ONLY"):
            self.check()

    def test_renamed_resource(self):
        self.companion_items[-1] = ("assets/other.png", b"abc\x00")
        self.pack()
        with self.assertRaisesRegex(Refused, "RESOURCE_NAME_OR_BYTES_DRIFT"):
            self.check()

    def test_changed_bytes(self):
        self.companion_items[-1] = ("assets/pixel.png", b"abc\x01")
        self.pack()
        with self.assertRaisesRegex(Refused, "RESOURCE_NAME_OR_BYTES_DRIFT"):
            self.check()

    def test_companion_with_class(self):
        self.companion_items.append(("demo/B.class", b"class B"))
        self.pack()
        with self.assertRaisesRegex(Refused, "COMPANION_NOT_RESOURCE_ONLY"):
            self.check()

    def test_original_class_count_drift(self):
        self.original_items.append(("demo/B.class", b"class B"))
        self.pack()
        with self.assertRaisesRegex(Refused, "ORIGINAL_ENTRY_COUNT_DRIFT"):
            self.check()

    def test_original_resource_count_drift(self):
        self.original_items.append(("extra.txt", b"hello"))
        self.pack()
        with self.assertRaisesRegex(Refused, "ORIGINAL_ENTRY_COUNT_DRIFT"):
            self.check()

    def test_duplicate_entry(self):
        self.companion_items.append(("assets/pixel.png", b"abc\x00"))
        self.pack()
        with self.assertRaisesRegex(Refused, "DUPLICATE_ARCHIVE_MEMBER"):
            self.check()

    def test_traversal(self):
        self.companion_items[-1] = ("../pixel.png", b"abc")
        self.pack()
        with self.assertRaisesRegex(Refused, "UNSAFE_ARCHIVE_MEMBER"):
            self.check()

    def test_backslash_alias(self):
        # ZIP's writer normalizes path separators on Windows. Patch the raw
        # local/central filename bytes instead, preserving equal ZIP lengths.
        raw = self.companion.read_bytes()
        self.assertEqual(raw.count(b"assets/pixel.png"), 2)
        self.companion.write_bytes(raw.replace(b"assets/pixel.png", b"assets\\pixel.png"))
        with self.assertRaisesRegex(Refused, "UNSAFE_ARCHIVE_MEMBER"):
            self.check()

    def test_symlink_entry(self):
        link = ZipInfo("assets/pixel.png")
        link.create_system = 3
        link.external_attr = ((stat.S_IFLNK | 0o777) << 16)
        self.companion_items[-1] = (link, b"target")
        self.pack()
        with self.assertRaisesRegex(Refused, "UNSAFE_ARCHIVE_MEMBER"):
            self.check()

    def test_same_archive_refused(self):
        with self.assertRaisesRegex(Refused, "IDENTICAL_INPUT_PATHS"):
            verify(self.original, self.original)

    def test_missing_archive(self):
        self.companion.unlink()
        with self.assertRaisesRegex(Refused, "UNSAFE_INPUT_OR_PIN"):
            self.check(csha="0" * 64)

    def test_never_mutates_archives(self):
        old = self.companion.read_bytes()
        self.check()
        self.assertEqual(self.companion.read_bytes(), old)

if __name__ == "__main__":
    unittest.main()

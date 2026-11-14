"""R392 synthetic-only fail-closed source archive + isolation inventory tests."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

TARGET = Path(__file__).resolve().parents[1] / "tools/r392/audit_prelaunch_side_effects.py"
spec = importlib.util.spec_from_file_location("r392_inventory", TARGET)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SOURCE_NAMES = list(audit.CRITICAL_FILES.values())

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SourceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kit = self.root / "kit.zip"
        self.files = {
            "source/rs/gui/Launcher.java": b'public class Launcher { void main(){ File f = null; f.delete(); } }',
            "source/rs/pkg42/Class255.java": b'loadPlugins(); startPlugins(); System.getProperty("user.home");',
            "source/rs/plugins/PluginManager.java": b'void loadPlugins(){} void startPlugins(){}',
            "source/rs/Client.java": b'InetAddress.getLocalHost(); new Socket(); new Thread();',
            "source/rs/cache/updater/AssetUpdater.java": b'Files.write(path, data); new FileOutputStream(file);',
            "source/rs/cache/download/FileDownloader.java": b'new ProcessBuilder("synthetic");',
        }
        self.pack()

    def pack(self, entries=None):
        entries = self.files.items() if entries is None else entries
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.kit, "w") as archive:
                for name, data in entries:
                    archive.writestr(name, data)

    def scan(self):
        audit.verify_kit(self.kit, sha(self.kit.read_bytes()))
        return audit.inventory(self.kit, expected_sources=6)

    def test_expected_categories_and_fail_closed(self):
        result = self.scan()
        self.assertEqual(result["source_count"], 6)
        self.assertEqual(result["flagged_file_counts"]["plugin_load"], 2)
        self.assertEqual(result["flagged_file_counts"]["process_execution"], 1)
        self.assertFalse(result["actual_client_executed"])
        self.assertFalse(result["launch_authorized"])
        self.assertFalse(result["sandbox_verified"])
        self.assertFalse(result["network_egress_blocked_verified"])

    def test_report_does_not_echo_source_bodies(self):
        result = self.scan()
        import json
        public = json.dumps(result)
        self.assertNotIn("synthetic", public)
        self.assertNotIn("System.getProperty", public)
        self.assertNotIn("source/rs/", public)

    def test_correct_pin_accepted(self):
        audit.verify_kit(self.kit, sha(self.kit.read_bytes()))

    def test_wrong_pin_rejected(self):
        with self.assertRaisesRegex(audit.Refused, "KIT_HASH_MISMATCH"):
            audit.verify_kit(self.kit, "0" * 64)

    def test_nonhex_pin_rejected(self):
        with self.assertRaisesRegex(audit.Refused, "INVALID_SHA256_PIN"):
            audit.verify_kit(self.kit, "not-valid")

    def test_missing_critical_source_rejected(self):
        self.files.pop("source/rs/pkg42/Class255.java")
        self.pack()
        with self.assertRaisesRegex(audit.Refused, "CRITICAL_STARTUP_SOURCE_MISSING"):
            audit.inventory(self.kit, expected_sources=5)

    def test_source_count_drift_rejected(self):
        with self.assertRaisesRegex(audit.Refused, "SOURCE_COUNT_DRIFT"):
            audit.inventory(self.kit, expected_sources=7)

    def test_duplicate_member_rejected(self):
        entries = list(self.files.items())
        self.pack(entries + [entries[0]])
        with self.assertRaisesRegex(audit.Refused, "DUPLICATE_ARCHIVE_MEMBER"):
            audit.inventory(self.kit, expected_sources=6)

    def test_traversal_member_rejected(self):
        self.pack(list(self.files.items()) + [("../escaped.txt", b"no")])
        with self.assertRaisesRegex(audit.Refused, "UNSAFE_ARCHIVE_MEMBER"):
            audit.inventory(self.kit, expected_sources=6)

    def test_backslash_member_rejected(self):
        obj = zipfile.ZipInfo("source/dummy.java")
        obj.filename = "source\\dummy.java"
        self.assertFalse(audit.safe_archive_member(obj))

    def test_symlink_member_rejected(self):
        obj = zipfile.ZipInfo("source/evil.java")
        obj.create_system = 3
        obj.external_attr = ((stat.S_IFLNK | 0o777) << 16)
        self.assertFalse(audit.safe_archive_member(obj))

    def test_ordinary_directory_entry_accepted(self):
        obj = zipfile.ZipInfo("source/")
        self.assertTrue(audit.safe_archive_member(obj))

    def test_source_size_limit_rejected(self):
        self.files[SOURCE_NAMES[0]] = b"z" * (audit.MAX_SOURCE_BYTES + 1)
        self.pack()
        with self.assertRaisesRegex(audit.Refused, "SOURCE_SIZE_LIMIT"):
            audit.inventory(self.kit, expected_sources=6)

    def test_non_utf8_source_rejected(self):
        self.files[SOURCE_NAMES[0]] = b"\xff\xfe"
        self.pack()
        with self.assertRaisesRegex(audit.Refused, "KIT_SOURCE_SCAN_FAILED"):
            audit.inventory(self.kit, expected_sources=6)

    def test_syntactically_invalid_archive_rejected(self):
        self.kit.write_bytes(b"not a zip")
        with self.assertRaisesRegex(audit.Refused, "KIT_SOURCE_SCAN_FAILED"):
            audit.inventory(self.kit, expected_sources=6)

    def test_existing_output_refused_without_mutation(self):
        output = self.root / "report.json"
        output.write_text("KEEP", encoding="utf-8")
        rc = audit.main([
            "--kit", str(self.kit), "--kit-sha256", sha(self.kit.read_bytes()),
            "--expected-sources", "6", "--out", str(output),
        ])
        self.assertEqual(rc, 2)
        self.assertEqual(output.read_text(encoding="utf-8"), "KEEP")

    def test_cli_report_has_no_authorization(self):
        output = self.root / "report.json"
        rc = audit.main([
            "--kit", str(self.kit), "--kit-sha256", sha(self.kit.read_bytes()),
            "--expected-sources", "6", "--out", str(output),
        ])
        self.assertEqual(rc, 0)
        text = output.read_text(encoding="utf-8")
        self.assertIn('"launch_authorized": false', text)
        self.assertIn('"actual_client_executed": false', text)

    def test_excessive_expected_sources_rejected(self):
        with self.assertRaisesRegex(audit.Refused, "INVALID_EXPECTED_SOURCE_COUNT"):
            audit.inventory(self.kit, expected_sources=6000)

    def test_side_effects_in_comment_are_not_claimed_as_executed(self):
        self.files[SOURCE_NAMES[0]] += b'\n// this text says new ProcessBuilder("synthetic");'
        self.pack()
        self.assertFalse(self.scan()["interprocedural_reachability_proven"])

if __name__ == "__main__":
    unittest.main()

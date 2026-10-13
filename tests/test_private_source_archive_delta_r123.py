"""Synthetic R123 archive intake and source-delta regression tests."""
import tempfile
import unittest
import warnings
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from spk_recovery.private_source_archive_delta_r123 import (
    audit, safe_entries, internal_outgoing_packet_lengths, PrivateArchiveDeltaError,
)


class ArchiveDeltaR123Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.upload = root / "uploaded.zip"
        self.old = root / "baseline.zip"

    @staticmethod
    def make(path, members):
        with ZipFile(path, "w") as archive:
            for name, content in members:
                archive.writestr(name, content)

    def test_only_real_client_differences_and_server_count_reported(self):
        self.make(self.upload, [
            ("new/client/src/main/java/rs/Client.java", "same"),
            ("new/client/src/main/java/rs/Configuration.java", "new"),
            ("new/server/core/src/main/java/rs/server/World.java", "world"),
            ("new/server/core/src/test/java/rs/server/WorldTest.java", "test"),
            ("new/gradlew", "script"),
        ])
        self.make(self.old, [
            ("old/src/main/java/rs/Client.java", "same"),
            ("old/src/main/java/rs/Configuration.java", "old"),
        ])
        result = audit(self.upload, self.old)
        self.assertEqual(result["client_java_source_files"], 2)
        self.assertEqual(result["byte_identical_shared_client_java_files"], 1)
        self.assertEqual(result["changed_client_java_files"],
                         ["rs/Configuration.java"])
        self.assertEqual(result["server_main_java_files"], 1)
        self.assertEqual(result["server_test_java_files"], 1)
        self.assertFalse(result["original_v309_parity_certified"])
        self.assertFalse(result["server_original_source_certified"])
        self.assertFalse(result["source_executed"])
        self.assertFalse(result["publish_client_or_server_source_to_git"])

    def test_path_traversal_veto(self):
        self.make(self.upload, [("root/../escape", "x")])
        with self.assertRaisesRegex(
                PrivateArchiveDeltaError, "ZIP_ENTRY_UNSAFE_PATH"):
            safe_entries(self.upload)

    def test_zip_duplicate_veto(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.make(self.upload, [
                ("root/a.java", "old"), ("root/a.java", "new")
            ])
        with self.assertRaisesRegex(
                PrivateArchiveDeltaError, "ZIP_DUPLICATE_ENTRY"):
            safe_entries(self.upload)

    def test_zip_symlink_veto(self):
        with ZipFile(self.upload, "w") as archive:
            info = ZipInfo("root/link")
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            archive.writestr(info, "target")
        with self.assertRaisesRegex(
                PrivateArchiveDeltaError, "ZIP_SYMLINK_NOT_ALLOWED"):
            safe_entries(self.upload)

    def test_complete_257_packet_lengths_match_own_decompiler(self):
        client = "\n".join(
            f"incomingLengths[{i}] = {i % 7};" for i in range(257)
        )
        server = (
            "private static final int[] INCOMING_LENGTHS = {"
            + ",".join(str(i % 7) for i in range(257)) + "};"
        )
        self.make(self.upload, [
            ("root/client/src/main/java/rs/io/IncomingPacketLengths.java",
             client),
            ("root/server/core/src/main/java/rs/server/net/codec/"
             "OutgoingPacketLengths.java", server),
        ])
        proof = internal_outgoing_packet_lengths(self.upload)
        self.assertTrue(proof["equal"])
        self.assertEqual(proof["client_values"], 257)
        self.assertEqual(proof["server_values"], 257)
        self.assertEqual(proof["mismatches"], 0)

    def test_changed_packet_length_is_not_original_parity(self):
        client = "\n".join(
            f"incomingLengths[{i}] = 0;" for i in range(257)
        )
        server = (
            "private static final int[] INCOMING_LENGTHS = {"
            + ",".join("1" if i == 81 else "0" for i in range(257))
            + "};"
        )
        self.make(self.upload, [
            ("root/client/src/main/java/rs/io/IncomingPacketLengths.java",
             client),
            ("root/server/core/src/main/java/rs/server/net/codec/"
             "OutgoingPacketLengths.java", server),
        ])
        proof = internal_outgoing_packet_lengths(self.upload)
        self.assertFalse(proof["equal"])
        self.assertEqual(proof["mismatches"], 1)

    def test_missing_client_baseline_veto(self):
        self.make(self.upload, [
            ("new/server/src/main/java/Server.java", "server")
        ])
        self.make(self.old, [
            ("old/src/main/java/rs/Foo.java", "old")
        ])
        with self.assertRaisesRegex(
                PrivateArchiveDeltaError,
                "CLIENT_JAVA_SOURCE_BASELINE_REQUIRED"):
            audit(self.upload, self.old)

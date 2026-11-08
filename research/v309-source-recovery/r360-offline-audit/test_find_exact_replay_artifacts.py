"""R343 synthetic archive and loose-file recovery tests."""
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import find_exact_replay_artifacts as scanner

def sha(data):
    return hashlib.sha256(data).hexdigest()

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.jar=b"test original bytecode"
        self.fixture=b"test gui fixture bytes"
        self.pins={
            "R315_REBUILT_CLASS_ONLY_JAR":(len(self.jar),sha(self.jar)),
            "R328_PRIVATE_GUI_SERVER_FIXTURE_ZIP":(len(self.fixture),sha(self.fixture))
        }
        a=patch.object(scanner,"PINS",self.pins)
        b=patch.object(scanner,"SIZES",{len(self.jar),len(self.fixture)})
        a.start();b.start()
        self.addCleanup(a.stop);self.addCleanup(b.stop)

    def archive(self,files,name="fixture.zip"):
        p=self.root/name
        with zipfile.ZipFile(p,"w",zipfile.ZIP_DEFLATED) as z:
            for n,d in files:z.writestr(n,d)
        return p

    def test_exact_sha_not_extension(self):
        z=self.archive([("unrelated.dat",self.jar),
                        ("old/renamed.bin",self.fixture)])
        r=scanner.scan_zip(z)
        self.assertEqual(r["status"],"COMPLETE")
        self.assertEqual(len(r["matched_artifacts"]),2)
        self.assertTrue(scanner.combine([r])["R328_built_jar_and_fixture_found"])
        self.assertFalse(scanner.combine([r])["approved_R328_cache_verified"])

    def test_same_size_different_content_rejected(self):
        z=self.archive([("old/client.jar",b"X"+self.jar[1:])])
        r=scanner.scan_zip(z)
        self.assertEqual(r["candidate_hashed"],1)
        self.assertEqual(r["matched_artifacts"],[])

    def test_exact_loose_binary(self):
        folder=self.root/"files"
        folder.mkdir()
        (folder/"renamed.bin").write_bytes(self.jar)
        r=scanner.scan_directory(folder)
        self.assertEqual(len(r["matched_artifacts"]),1)
        self.assertFalse(r["original_client_launched"])

    def test_archive_cache_count_not_provenance(self):
        z=self.archive([("b/cache/a",b"a"),("b/cache/b",b"b")])
        with patch.object(scanner,"REFERENCE_CACHE_COUNT",2):
            r=scanner.scan_zip(z)
        self.assertTrue(r["cache_subtrees"][0]["count_matches_R328"])
        self.assertFalse(r["cache_subtrees"][0]["approved_R328_cache_provenance"])

    def test_archive_traversal_rejected(self):
        z=self.archive([("../fake.jar",self.jar)])
        r=scanner.scan_zip(z)
        self.assertEqual(r["candidate_hashed"],0)

    def test_sensitive_member_skipped(self):
        z=self.archive([("secrets/fixture.zip",self.fixture)])
        self.assertEqual(scanner.scan_zip(z)["matched_artifacts"],[])

    def test_zip_entry_limit_is_incomplete(self):
        z=self.archive([("a",b"a"),("b",b"b")])
        self.assertEqual(scanner.scan_zip(z,max_entries=1)["status"],
                         "INCOMPLETE_ENTRY_BUDGET")

    def test_candidate_budget_is_incomplete(self):
        z=self.archive([("fixture.bin",self.jar)])
        self.assertEqual(scanner.scan_zip(z,max_candidate_bytes=2)["status"],
                         "INCOMPLETE_CANDIDATE")

    def test_missing_archive_not_empty_success(self):
        with self.assertRaises(scanner.ScanRefused):
            scanner.scan_zip(self.root/"missing.zip")

    def test_bad_zip_not_empty_success(self):
        p=self.root/"bad.zip"
        p.write_bytes(b"broken")
        with self.assertRaises(zipfile.BadZipFile):
            scanner.scan_zip(p)

    def test_zip_scanning_never_extracts(self):
        z=self.archive([("a/b/c",self.jar)])
        before=set(self.root.rglob("*"))
        scanner.scan_zip(z)
        self.assertEqual(before,set(self.root.rglob("*")))

    def test_partial_scan_not_approved(self):
        report=scanner.combine([{"status":"INCOMPLETE",
                                 "matched_artifacts":[]}])
        self.assertEqual(report["status"],"PARTIAL")
        self.assertEqual(report["original_same_pid_reconnect"],"NOT_TESTED")

    def test_path_normalization_and_blocked_parent(self):
        self.assertEqual(scanner.member_path("backup\\cache\\test.dat"),
                         "backup/cache/test.dat")
        self.assertIsNone(scanner.member_path("tokens/test.dat"))
        self.assertIsNone(scanner.member_path("/root/cache/test.dat"))

if __name__=="__main__":
    unittest.main()

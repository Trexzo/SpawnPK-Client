"""R423 invented negative controls for pinned, read-only legacy cleanup audit."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from tools.r423.audit_private_legacy_cleanup import (
    Refused, audit, inspect_source,
)

SOURCE = """
class LootHistoryStore {
    void deleteStale() {
        r419WithOwner(this::r419DeleteStaleLeased);
    }
    void r419DeleteStaleLeased() {
        if (r411RefuseUnresolvedStage("legacy cleanup")) return;
        if (parts.exists()) {
            deleteTree(parts);
        }
    }
    private static boolean deleteTree(File file) {
        File[] children = file.listFiles();
        if (children != null) {
            for (File child : children) {
                if (!deleteTree(child)) return false;
            }
        }
        Files.deleteIfExists(file.toPath());
        return true;
    }
}
"""


class R423PrivateAuditNegatives(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="r423-fabricated-audit-")
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "LootHistoryStore.java"
        self.path.write_text(SOURCE, encoding="utf-8")

    def check(self, text=SOURCE):
        self.path.write_text(text, encoding="utf-8")
        sha = sha256(self.path.read_bytes()).hexdigest()
        return audit(self.path, sha)

    def refuse_shape(self, old, replacement):
        candidate = SOURCE.replace(old, replacement)
        self.assertNotEqual(candidate, SOURCE)
        with self.assertRaises(Refused):
            inspect_source(candidate)

    def test_01_known_unsafe_recursive_shape_detected(self):
        result = self.check()
        self.assertEqual(
            result["status"],
            "R423_PRIVATE_RECURSIVE_SYMLINK_RISK_REVIEW_REQUIRED")
        self.assertFalse(result["release_authorized"])

    def test_02_exact_source_sha_is_returned(self):
        result = self.check()
        self.assertEqual(result["source_sha256_verified"],
                         sha256(self.path.read_bytes()).hexdigest())

    def test_03_bad_digest_refused(self):
        with self.assertRaises(Refused):
            audit(self.path, "0" * 64)

    def test_04_short_digest_refused(self):
        with self.assertRaises(Refused):
            audit(self.path, "bad")

    def test_05_missing_listfiles_requires_new_review(self):
        self.refuse_shape("file.listFiles()", "safeWalk(file)")

    def test_06_missing_recursion_requires_new_review(self):
        self.refuse_shape("deleteTree(child)", "safeDelete(child)")

    def test_07_missing_delete_call_requires_new_review(self):
        self.refuse_shape("Files.deleteIfExists(file.toPath())", "noop()")

    def test_08_changed_original_caller_requires_new_review(self):
        self.refuse_shape("deleteTree(parts)", "safeDelete(parts)")

    def test_09_missing_stage_guard_refused(self):
        self.refuse_shape("r411RefuseUnresolvedStage(", "false && (")

    def test_10_missing_owner_wrapper_refused(self):
        self.refuse_shape("r419WithOwner(this::r419DeleteStaleLeased)",
                          "r419DeleteStaleLeased()")

    def test_11_comment_does_not_supply_listfiles_evidence(self):
        self.refuse_shape("file.listFiles()", "null /* file.listFiles() */")

    def test_12_nofollow_rewrite_does_not_get_marked_old(self):
        self.refuse_shape("File[] children = file.listFiles();",
                          "LinkOption.NOFOLLOW_LINKS; File[] children = file.listFiles();")

    def test_13_new_walker_requires_fresh_audit(self):
        self.refuse_shape("File[] children = file.listFiles();",
                          "Files.walkFileTree(file.toPath());"
                          " File[] children = file.listFiles();")

    def test_14_wrong_filename_refused(self):
        other = self.path.parent / "Other.java"
        other.write_bytes(self.path.read_bytes())
        with self.assertRaises(Refused):
            audit(other, sha256(other.read_bytes()).hexdigest())

    def test_15_absent_file_refused(self):
        with self.assertRaises(Refused):
            audit(self.path.parent/"Missing.java", "0" * 64)

    def test_16_source_not_modified_by_audit(self):
        baseline = self.path.read_bytes()
        self.check()
        self.assertEqual(self.path.read_bytes(), baseline)

    def test_17_synthetic_symlink_input_refused(self):
        other = self.path.parent / "copy"
        try:
            other.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(Refused):
            audit(other, sha256(self.path.read_bytes()).hexdigest())

    def test_18_invalid_utf8_refused(self):
        self.path.write_bytes(b"\xff\xfe")
        with self.assertRaises(Refused):
            audit(self.path, sha256(self.path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()

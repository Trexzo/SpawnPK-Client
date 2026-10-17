"""Synthetic R184 source tree assembly and no-overwrite tests."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from private_source_tree_r184 import assemble, read_sources, write_private_tree, classify_javac_text, sha

class SourceTree(unittest.TestCase):
    def test_reviewed_replacement_and_addition(self):
        base = {"rs/A.java": b"class A {}"}
        delta = {"rs/A.java": b"class A { int v; }", "rs/B.java": b"class B {}"}
        approvals = {
            "rs/A.java": {"status": "reviewed-private-recovery",
                          "baseline_sha256": sha(base["rs/A.java"]),
                          "replacement_sha256": sha(delta["rs/A.java"])},
            "rs/B.java": {"status": "reviewed-private-recovery",
                          "baseline_sha256": None,
                          "replacement_sha256": sha(delta["rs/B.java"])}
        }
        merged, modifications = assemble(base, delta, approvals)
        self.assertEqual(2, len(merged))
        self.assertEqual(2, len(modifications))
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "private"
            report = write_private_tree(dest, merged, modifications)
            self.assertEqual(2, report["java_count"])
            self.assertEqual(delta["rs/A.java"], (dest / "rs/A.java").read_bytes())
            with self.assertRaises(FileExistsError):
                write_private_tree(dest, merged, modifications)
        approvals["rs/A.java"]["baseline_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Stale"):
            assemble(base, delta, approvals)

    def test_unapproved_source_never_replaced(self):
        with self.assertRaisesRegex(ValueError, "Missing reviewed"):
            assemble({"rs/A.java": b"old"}, {"rs/A.java": b"new"}, {})
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            assemble({}, {"rs/A.java": b"x"},
                     {"rs/A.java": {"status":"unverified", "replacement_sha256":sha(b"x")}})

    def test_zip_member_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("src/rs/A.java", b"1")
                z.writestr("src/rs/a.java", b"2")
            with self.assertRaisesRegex(ValueError, "casefold"):
                read_sources(p, "src/")

    def test_compiler_report_is_not_root_cause_proof(self):
        x = classify_javac_text(
            "/tmp/rs/A.java:10: error: cannot find symbol\n"
            "/tmp/rs/B.java:20: error: package org.example does not exist\n"
            "/tmp/rs/A.java:15: error: cannot find symbol\n")
        self.assertEqual(3, x["reported_error_occurrences"])
        self.assertEqual(2, x["by_reason"]["cannot find symbol"])
        self.assertFalse(x["root_cause_verified"])

if __name__ == "__main__":
    unittest.main()

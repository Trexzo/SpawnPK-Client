"""Synthetic, private-data-free R182 comparison tests."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from javac_frontier_r182 import build_report
from javac_frontier_compare_r182 import compare, _load_pinned

LOCK = dict(
    toolchain_sha256="a" * 64,
    javac_command_sha256="b" * 64,
    dependency_manifest_sha256="c" * 64,
    source_scope_sha256="d" * 64,
    dependency_policy="no-original-client-binary",
)

def report(directory, name, diagnostics):
    file = Path(directory) / name
    rows = [f"X.java:{i+1}:2: compiler.err.doesnt.exist: {value}"
            for i, value in enumerate(diagnostics)]
    file.write_text("\n".join(rows + [f"{len(rows)} errors"]) + "\n", encoding="utf-8")
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    return build_report(file, digest, "pinned-jdk9")

class Compare(unittest.TestCase):
    def test_deltas_are_occurrence_counts(self):
        with tempfile.TemporaryDirectory() as d:
            a = report(d, "a.txt", ["a", "b"])
            b = report(d, "b.txt", ["a"])
            result = compare(a, b, LOCK, LOCK)
            self.assertEqual(-1, result["delta_errors"])
            self.assertEqual(1, result["removed_error_occurrences"])
            self.assertEqual(0, result["added_error_occurrences"])
            self.assertEqual(1, result["unchanged_error_occurrences"])

    def test_changed_input_policy_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a = report(d, "a.txt", ["a"])
            other = dict(LOCK, toolchain_sha256="e" * 64)
            with self.assertRaisesRegex(ValueError, "Different toolchain"):
                compare(a, a, LOCK, other)
            with self.assertRaisesRegex(ValueError, "policy"):
                compare(a, a, LOCK, dict(LOCK, dependency_policy="original-fallback"))

    def test_incomplete_transcript_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a = report(d, "a.txt", ["a"])
            a["complete_error_inventory"] = False
            with self.assertRaisesRegex(ValueError, "incomplete"):
                compare(a, a, LOCK, LOCK)

    def test_wrong_digest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "manifest.json"
            f.write_text('{"a":1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                _load_pinned(f, "0" * 64)

if __name__ == "__main__":
    unittest.main()

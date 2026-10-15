"""Synthetic-only regression checks for R182 transcript ingestion."""
import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from javac_frontier_r182 import build_report, parse_transcript


class Frontiers(unittest.TestCase):
    def test_two_diagnostics_and_unknown_causality(self):
        lines = [
            "B.java:10:4: compiler.err.cant.resolve.location: kindname.class, A",
            "A.java:3: compiler.err.doesnt.exist: example",
            "2 errors",
        ]
        diagnostics, unparsed = parse_transcript(lines)
        self.assertEqual(2, len(diagnostics))
        self.assertEqual([], unparsed)
        self.assertTrue(all(x["root_cause"] == "unknown" for x in diagnostics))
        self.assertEqual(4, diagnostics[0]["column"])

    def test_hash_and_stable_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compiler.txt"
            path.write_text(
                "Z.java:2: compiler.err.doesnt.exist: z\n"
                "A.java:1:1: compiler.err.cant.resolve: a\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            a = build_report(path, digest, "jdk9-only-v1")
            b = build_report(path, digest, "jdk9-only-v1")
            self.assertEqual(a, b)
            self.assertEqual(["A.java", "Z.java"],
                             [x["file"] for x in a["diagnostics"]])
            self.assertEqual(2, a["parsed_diagnostic_count"])
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                build_report(path, "0" * 64, "jdk9-only-v1")

    def test_unparsed_not_silently_dropped(self):
        rows, unparsed = parse_transcript(
            ["private path remains opaque", "1 error"]
        )
        self.assertEqual([], rows)
        self.assertEqual(["private path remains opaque"], unparsed)

    def test_summary_complete_and_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "errors.txt"
            row = "X.java:4: compiler.err.doesnt.exist: xyz\\n"
            path.write_text(row + "1 error\\n", encoding="utf-8")
            a = build_report(path, hashlib.sha256(path.read_bytes()).hexdigest(), "jdk9-a")
            self.assertEqual(1, a["summary_error_count"])
            self.assertTrue(a["complete_error_inventory"])
            path.write_text(row + "2 errors\\n", encoding="utf-8")
            b = build_report(path, hashlib.sha256(path.read_bytes()).hexdigest(), "jdk9-a")
            self.assertFalse(b["complete_error_inventory"])
            self.assertEqual(1, b["parsed_error_count"])

    def test_invalid_profile_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.txt"
            path.write_text("", encoding="utf-8")
            digest = hashlib.sha256(b"").hexdigest()
            with self.assertRaisesRegex(ValueError, "profile"):
                build_report(path, digest, "../../bad")


if __name__ == "__main__":
    unittest.main()

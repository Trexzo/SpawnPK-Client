from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.v309_external_source_corpus_intake import (
    SourceIntakeError, measure, main,
)


class ExternalSourceIntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.zip"
        self.jar = self.root / "client.jar"
        with ZipFile(self.source, "w") as z:
            z.writestr("project/src/main/java/rs/Configuration.java",
                       "package rs; class Configuration { int buildNumber = 309; }")
            z.writestr("project/src/main/java/rs/Client.java",
                       "package rs; class Client {}")
            z.writestr("project/src/main/resources/rs/icon.png", b"png")
            z.writestr("project/docs/LOOT_TRACKER_COMPARISON.md",
                       "| "+chr(96)+"rs.s.l.p"+chr(96)+" | plugin | source |")
        with ZipFile(self.jar, "w") as z:
            z.writestr("rs/Client.class", b"fixture")
            z.writestr("rs/s/l/p.class", b"fixture")
        self.sha_source = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.sha_jar = hashlib.sha256(self.jar.read_bytes()).hexdigest()

    def test_verified_counts_and_research_only(self):
        result = measure(self.source, self.jar, self.sha_source,
                         self.sha_jar, expected_classes=2)
        self.assertEqual(result, measure(self.source, self.jar,
                                         self.sha_source, self.sha_jar,
                                         expected_classes=2))
        self.assertFalse(result["canonical"])
        a = result["summary"]
        self.assertEqual(a["java_source_files"], 2)
        self.assertEqual(a["direct_class_path_overlap_not_identity_proof"], 1)
        self.assertEqual(a["documented_original_paths_found"], 1)
        self.assertEqual(a["new_accepted_class_identities"], 0)
        self.assertFalse(a["clean_rebuild_verified"])
        self.assertNotIn("rs/Client", str(result))

    def test_wrong_archive_hash_refused(self):
        with self.assertRaises(SourceIntakeError):
            measure(self.source, self.jar, "0"*64, self.sha_jar, 2)

    def test_wrong_original_class_count_refused(self):
        with self.assertRaises(SourceIntakeError):
            measure(self.source, self.jar, self.sha_source, self.sha_jar, 3)

    def test_wrong_build_refused(self):
        with ZipFile(self.source, "w") as z:
            z.writestr("project/src/main/java/rs/Configuration.java",
                       "package rs; class Configuration { int buildNumber = 308; }")
        sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaises(SourceIntakeError):
            measure(self.source, self.jar, sha, self.sha_jar, 2)

    def test_no_overwrite_failure_no_private_path(self):
        from contextlib import redirect_stdout
        import io
        target = self.root / "existing.json"
        target.write_text("KEPT")
        captured = io.StringIO()
        with redirect_stdout(captured):
            code = main([
                "--source-zip", str(self.source),
                "--original-jar", str(self.jar),
                "--source-sha256", self.sha_source,
                "--original-sha256", self.sha_jar,
                "--out", str(target),
            ])
        self.assertEqual(code, 1)
        self.assertEqual(target.read_text(), "KEPT")
        self.assertNotIn(str(self.root), captured.getvalue())


if __name__ == "__main__":
    unittest.main()

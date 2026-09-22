from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.cli import main


class UpdateIntakeCliTests(unittest.TestCase):
    def test_update_intake_writes_deterministic_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_index = {
                "schema_version": 1,
                "source_name": "old.jar",
                "sha256": "1" * 64,
                "size_bytes": 0,
                "entries": {},
                "classes": {},
                "summary": {
                    "entry_count": 0,
                    "class_count": 0,
                    "rs_class_count": 0,
                    "class_parse_error_count": 0,
                    "class_parse_errors": {},
                    "class_major_versions": [],
                },
            }
            old_path = root / "old-index.json"
            old_path.write_text(
                json.dumps(old_index),
                encoding="utf-8",
            )

            new_jar = root / "new.jar"
            with zipfile.ZipFile(new_jar, "w", zipfile.ZIP_STORED) as z:
                z.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")

            out_dir = root / "workspace"
            rc = main(
                [
                    "update-intake",
                    str(old_path),
                    str(new_jar),
                    "--old-build-id",
                    "v308",
                    "--new-build-id",
                    "v309",
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((out_dir / "new-index.json").is_file())
            self.assertTrue((out_dir / "migration-report.json").is_file())
            self.assertTrue((out_dir / "analysis-queue.json").is_file())

            report = json.loads(
                (out_dir / "migration-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["old_build_id"], "v308")
            self.assertEqual(report["new_build_id"], "v309")
            self.assertTrue(report["migration_id"].startswith("MIGRATION_"))
            self.assertEqual(report["summary"]["analysis_queue_items"], 0)


if __name__ == "__main__":
    unittest.main()

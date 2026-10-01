from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.historical_lineage_backfill import (
    HistoricalLineageBackfillError,
    backfill_historical_v307_lineage,
)
from spk_recovery.indexer import index_jar
from spk_recovery.lineage import seed_lineage
from spk_recovery.member_lineage import seed_member_lineage


@unittest.skipUnless(shutil.which("javac"), "javac required")
class HistoricalV307LineageBackfillTests(unittest.TestCase):
    def _fixture(self, root: Path):
        src = root / "src" / "rs"
        src.mkdir(parents=True)
        (src / "A.java").write_text(
            "package rs; public class A { "
            "public int x = 1; "
            "public int a(){ return x + 1; } "
            "}",
            encoding="utf-8",
        )

        classes = root / "classes"
        classes.mkdir()
        subprocess.run(
            [
                "javac",
                "-g:none",
                "-d",
                str(classes),
                str(src / "A.java"),
            ],
            check=True,
        )
        class_bytes = (classes / "rs" / "A.class").read_bytes()

        v308 = root / "v308.jar"
        v307 = root / "v307.jar"
        with zipfile.ZipFile(v308, "w", zipfile.ZIP_STORED) as z:
            z.writestr("rs/A.class", class_bytes)
            z.writestr("build.txt", b"308")
        with zipfile.ZipFile(v307, "w", zipfile.ZIP_STORED) as z:
            z.writestr("rs/A.class", class_bytes)
            z.writestr("build.txt", b"307")

        v308_index = index_jar(v308)
        class_lineage = seed_lineage(
            v308_index,
            build_id="v308",
            build_number=308,
            authority="EXACT_CURRENT_CLIENT",
        )
        member_lineage = seed_member_lineage(
            class_lineage,
            v308_index,
            build_id="v308",
        )
        return (
            v308,
            v307,
            v308_index,
            class_lineage,
            member_lineage,
        )

    def test_reverse_migration_derives_release_ready_v307_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                v308,
                v307,
                v308_index,
                class_lineage,
                member_lineage,
            ) = self._fixture(root)

            original_classes = copy.deepcopy(class_lineage)
            original_members = copy.deepcopy(member_lineage)

            report = backfill_historical_v307_lineage(
                v308,
                v307,
                v308_index,
                class_lineage,
                member_lineage,
                out_dir=root / "out",
            )

            self.assertTrue(report["ready_for_authority"])
            self.assertEqual(report["focused_analysis_items"], 0)
            self.assertEqual(
                report["class_transfer_summary"]["trusted_applied"],
                1,
            )
            self.assertGreaterEqual(
                report["member_transfer_summary"][
                    "applied_member_relationships"
                ],
                2,
            )

            derived_classes = json.loads(
                Path(report["paths"]["class_lineage"]).read_text(
                    encoding="utf-8"
                )
            )
            derived_members = json.loads(
                Path(report["paths"]["member_lineage"]).read_text(
                    encoding="utf-8"
                )
            )

            v307_builds = [
                row
                for row in derived_classes["builds"]
                if row["build_id"] == "v307"
            ]
            self.assertEqual(len(v307_builds), 1)
            self.assertEqual(
                v307_builds[0]["authority"],
                "EXACT_HISTORICAL_CLIENT",
            )
            self.assertTrue(
                all(
                    any(
                        entry["build_id"] == "v307"
                        for entry in record["lineage"]
                    )
                    for record in derived_classes["classes"]
                )
            )
            self.assertTrue(
                all(
                    any(
                        entry["build_id"] == "v307"
                        for entry in record["lineage"]
                    )
                    for record in derived_members["members"]
                )
            )

            self.assertEqual(class_lineage, original_classes)
            self.assertEqual(member_lineage, original_members)

    def test_sipush_build_constant_change_reaches_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_src = root / "old-src" / "rs"
            new_src = root / "new-src" / "rs"
            old_src.mkdir(parents=True)
            new_src.mkdir(parents=True)

            (old_src / "A.java").write_text(
                "package rs; public class A { "
                "public static int c = 308; "
                "}",
                encoding="utf-8",
            )
            (new_src / "A.java").write_text(
                "package rs; public class A { "
                "public static int c = 307; "
                "}",
                encoding="utf-8",
            )
            shared = (
                "package rs; public class B { "
                "public static int m(){ return A.c + A.c; } "
                "}"
            )
            (old_src / "B.java").write_text(shared, encoding="utf-8")
            (new_src / "B.java").write_text(shared, encoding="utf-8")

            old_classes = root / "old-classes"
            new_classes = root / "new-classes"
            old_classes.mkdir()
            new_classes.mkdir()
            subprocess.run(
                [
                    "javac",
                    "-g:none",
                    "-d",
                    str(old_classes),
                    str(old_src / "A.java"),
                    str(old_src / "B.java"),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "javac",
                    "-g:none",
                    "-d",
                    str(new_classes),
                    str(new_src / "A.java"),
                    str(new_src / "B.java"),
                ],
                check=True,
            )

            v308 = root / "v308-constant.jar"
            v307 = root / "v307-constant.jar"
            with zipfile.ZipFile(v308, "w", zipfile.ZIP_STORED) as z:
                z.write(old_classes / "rs" / "A.class", "rs/A.class")
                z.write(old_classes / "rs" / "B.class", "rs/B.class")
            with zipfile.ZipFile(v307, "w", zipfile.ZIP_STORED) as z:
                z.write(new_classes / "rs" / "A.class", "rs/A.class")
                z.write(new_classes / "rs" / "B.class", "rs/B.class")

            v308_index = index_jar(v308)
            v307_index = index_jar(v307)
            self.assertNotEqual(
                v308_index["entries"]["rs/A.class"]["sha256"],
                v307_index["entries"]["rs/A.class"]["sha256"],
            )
            self.assertEqual(
                v308_index["classes"]["rs/A.class"]["structural_sha256"],
                v307_index["classes"]["rs/A.class"]["structural_sha256"],
            )
            self.assertEqual(
                v308_index["entries"]["rs/B.class"]["sha256"],
                v307_index["entries"]["rs/B.class"]["sha256"],
            )

            class_lineage = seed_lineage(
                v308_index,
                build_id="v308",
                build_number=308,
                authority="EXACT_CURRENT_CLIENT",
            )
            member_lineage = seed_member_lineage(
                class_lineage,
                v308_index,
                build_id="v308",
            )

            report = backfill_historical_v307_lineage(
                v308,
                v307,
                v308_index,
                class_lineage,
                member_lineage,
                out_dir=root / "constant-out",
            )

            self.assertTrue(report["ready_for_authority"])
            self.assertEqual(
                report["class_transfer_summary"]["trusted_structural"],
                1,
            )
            self.assertEqual(
                report["class_transfer_summary"]["trusted_exact"],
                1,
            )
            self.assertGreaterEqual(
                report["field_proof_summary"]["applied_fields"],
                1,
            )
            self.assertEqual(report["focused_analysis_items"], 0)

    def test_refuses_duplicate_v307_backfill(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                v308,
                v307,
                v308_index,
                class_lineage,
                member_lineage,
            ) = self._fixture(root)

            first = backfill_historical_v307_lineage(
                v308,
                v307,
                v308_index,
                class_lineage,
                member_lineage,
                out_dir=root / "first",
            )

            derived_classes = json.loads(
                Path(first["paths"]["class_lineage"]).read_text(
                    encoding="utf-8"
                )
            )
            derived_members = json.loads(
                Path(first["paths"]["member_lineage"]).read_text(
                    encoding="utf-8"
                )
            )

            with self.assertRaises(HistoricalLineageBackfillError):
                backfill_historical_v307_lineage(
                    v308,
                    v307,
                    v308_index,
                    derived_classes,
                    derived_members,
                    out_dir=root / "second",
                )


if __name__ == "__main__":
    unittest.main()

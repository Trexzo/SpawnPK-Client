from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.generic_historical_lineage import (
    GenericHistoricalLineageBackfillError,
    backfill_historical_lineage,
)
from spk_recovery.indexer import index_jar
from spk_recovery.lineage import seed_lineage
from spk_recovery.member_lineage import seed_member_lineage


@unittest.skipUnless(shutil.which("javac"), "javac required")
class GenericHistoricalLineageBackfillTests(unittest.TestCase):
    def _compile(self, root: Path, name: str, sources: dict[str, str]):
        src = root / f"{name}-src" / "rs"
        classes = root / f"{name}-classes"
        src.mkdir(parents=True)
        classes.mkdir()
        java_files = []
        for filename, body in sources.items():
            path = src / filename
            path.write_text(body, encoding="utf-8")
            java_files.append(str(path))
        subprocess.run(
            ["javac", "-g:none", "-d", str(classes), *java_files],
            check=True,
        )
        return classes

    def _jar(self, path: Path, classes: Path, marker: str):
        with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
            for class_file in sorted((classes / "rs").glob("*.class")):
                z.write(class_file, f"rs/{class_file.name}")
            z.writestr("build.txt", marker.encode("ascii"))

    def _authority(self, jar: Path):
        index = index_jar(jar)
        class_lineage = seed_lineage(
            index,
            build_id="vCurrent",
            build_number=999,
            authority="EXACT_CURRENT_CLIENT",
        )
        member_lineage = seed_member_lineage(
            class_lineage,
            index,
            build_id="vCurrent",
        )
        return index, class_lineage, member_lineage

    def test_full_match_reaches_ordinary_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            classes = self._compile(
                root,
                "shared",
                {
                    "A.java": (
                        "package rs; public class A { "
                        "public int x = 1; "
                        "public int m(){ return x + 1; } "
                        "}"
                    ),
                },
            )
            current = root / "current.jar"
            historical = root / "historical.jar"
            self._jar(current, classes, "current")
            self._jar(historical, classes, "historical")

            (
                current_index,
                class_lineage,
                member_lineage,
            ) = self._authority(current)
            historical_index = index_jar(historical)
            original_classes = copy.deepcopy(class_lineage)
            original_members = copy.deepcopy(member_lineage)

            report = backfill_historical_lineage(
                current,
                historical,
                current_index,
                class_lineage,
                member_lineage,
                current_build_id="vCurrent",
                historical_build_id="vHistorical",
                historical_build_number=998,
                expected_current_sha256=current_index["sha256"],
                expected_historical_sha256=historical_index["sha256"],
                out_dir=root / "out",
                expected_match_summary={
                    "old_class_count": 1,
                    "new_class_count": 1,
                    "matched": 1,
                    "exact_sha256": 1,
                    "ambiguous": 0,
                    "unmatched_old": 0,
                    "unmatched_new": 0,
                },
            )

            self.assertTrue(report["ready_for_authority"])
            self.assertEqual(report["class_match_summary"]["matched"], 1)
            self.assertEqual(report["focused_analysis_items"], 0)
            self.assertEqual(report["blockers"], [])
            self.assertTrue(
                report["backfill_id"].startswith("HISTGEN_")
            )
            self.assertEqual(class_lineage, original_classes)
            self.assertEqual(member_lineage, original_members)

            derived = json.loads(
                Path(report["paths"]["class_lineage"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                len(
                    [
                        row
                        for row in derived["builds"]
                        if row["build_id"] == "vHistorical"
                    ]
                ),
                1,
            )

    def test_partial_lineage_stays_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            current_classes = self._compile(
                root,
                "current",
                {
                    "A.java": (
                        "package rs; public class A { "
                        "public int a(){ return 1; } }"
                    ),
                    "B.java": (
                        "package rs; public final class B { "
                        "public static long b(long x){ return x * 31L; } }"
                    ),
                },
            )
            historical_classes = self._compile(
                root,
                "historical",
                {
                    "A.java": (
                        "package rs; public class A { "
                        "public int a(){ return 1; } }"
                    ),
                    "C.java": (
                        "package rs; public interface C { "
                        "String c(String x); }"
                    ),
                },
            )
            current = root / "current.jar"
            historical = root / "historical.jar"
            self._jar(current, current_classes, "current")
            self._jar(historical, historical_classes, "historical")

            (
                current_index,
                class_lineage,
                member_lineage,
            ) = self._authority(current)
            historical_index = index_jar(historical)

            report = backfill_historical_lineage(
                current,
                historical,
                current_index,
                class_lineage,
                member_lineage,
                current_build_id="vCurrent",
                historical_build_id="vHistorical",
                historical_build_number=998,
                expected_current_sha256=current_index["sha256"],
                expected_historical_sha256=historical_index["sha256"],
                out_dir=root / "out",
            )

            self.assertFalse(report["ready_for_authority"])
            self.assertGreater(report["focused_analysis_items"], 0)
            self.assertGreater(len(report["blockers"]), 0)
            self.assertGreaterEqual(
                report["class_match_summary"]["unmatched_new"],
                1,
            )
            queue = json.loads(
                Path(report["paths"]["focused_analysis_queue"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertGreater(len(queue["items"]), 0)

    def test_refuses_match_expectation_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            classes = self._compile(
                root,
                "shared",
                {
                    "A.java": "package rs; public class A {}",
                },
            )
            current = root / "current.jar"
            historical = root / "historical.jar"
            self._jar(current, classes, "current")
            self._jar(historical, classes, "historical")

            (
                current_index,
                class_lineage,
                member_lineage,
            ) = self._authority(current)
            historical_index = index_jar(historical)

            with self.assertRaisesRegex(
                GenericHistoricalLineageBackfillError,
                "matcher expectation mismatch",
            ):
                backfill_historical_lineage(
                    current,
                    historical,
                    current_index,
                    class_lineage,
                    member_lineage,
                    current_build_id="vCurrent",
                    historical_build_id="vHistorical",
                    historical_build_number=998,
                    expected_current_sha256=current_index["sha256"],
                    expected_historical_sha256=historical_index["sha256"],
                    out_dir=root / "out",
                    expected_match_summary={"matched": 999},
                )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.package_class_remap_plan import (
    build_package_class_remap_plan,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class PackageClassRemapPlanTests(unittest.TestCase):
    def _compile(self, sources: list[Path], out: Path):
        out.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(out),
                *map(str, sources),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )

    def _fixture(self, root: Path):
        blocker_src = root / "blocker-src" / "a"
        candidate_src = root / "candidate-src" / "a" / "b" / "c"
        holder_src = root / "holder-src" / "holder"
        blocker_src.mkdir(parents=True)
        candidate_src.mkdir(parents=True)
        holder_src.mkdir(parents=True)

        blocker = blocker_src / "b.java"
        blocker.write_text(
            "package a; public class b {}\n",
            encoding="utf-8",
        )
        candidate = candidate_src / "One.java"
        candidate.write_text(
            "package a.b.c; public class One {}\n",
            encoding="utf-8",
        )
        holder = holder_src / "UseBlocker.java"
        holder.write_text(
            "package holder; public class UseBlocker { "
            "public a.b value; }\n",
            encoding="utf-8",
        )

        blocker_classes = root / "blocker-classes"
        candidate_classes = root / "candidate-classes"
        holder_classes = root / "holder-classes"

        self._compile([blocker], blocker_classes)
        self._compile([candidate], candidate_classes)

        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-classpath",
                str(blocker_classes),
                "-d",
                str(holder_classes),
                str(holder),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )

        jar = root / "fixture.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for classes in (
                blocker_classes,
                candidate_classes,
                holder_classes,
            ):
                for path in sorted(classes.rglob("*.class")):
                    z.write(
                        path,
                        path.relative_to(classes).as_posix(),
                    )

        plan = {
            "schema_version": 1,
            "kind": "javac_missing_class_recovery_plan",
            "plan_id": "JCLASSPLAN_" + "7" * 20,
            "identifiers_included": True,
            "candidates": [
                {
                    "candidate_id": "JCLASSMISS_001",
                    "candidate_internal_name": "a/b/c/One",
                }
            ],
        }
        plan_path = root / "private-plan.json"
        plan_path.write_text(
            json.dumps(plan, indent=2) + "\n",
            encoding="utf-8",
        )
        return plan_path, jar

    def test_remap_stays_in_same_package_and_tracks_reference_holders(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, jar = self._fixture(root)

            report = build_package_class_remap_plan(
                plan,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                report["summary"]["remap_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["affected_candidate_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["same_package_remap_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["collision_free_target_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["bytecode_reference_holder_count"],
                1,
            )

            remap = report["remaps"][0]
            self.assertEqual(
                remap["old_internal_name"],
                "a/b",
            )
            self.assertTrue(
                remap["new_internal_name"].startswith(
                    "a/RecoveredCollision_"
                )
            )
            self.assertEqual(
                remap["bytecode_reference_holders"],
                ["holder/UseBlocker"],
            )

    def test_public_and_private_share_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, jar = self._fixture(root)

            public = build_package_class_remap_plan(
                plan,
                jar,
            )
            private = build_package_class_remap_plan(
                plan,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["remap_plan_id"],
                private["remap_plan_id"],
            )
            self.assertNotIn("a/b", str(public))
            self.assertNotIn(
                "holder/UseBlocker",
                str(public),
            )
            self.assertIn("a/b", str(private))
            self.assertIn(
                "holder/UseBlocker",
                str(private),
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.package_class_collision import (
    analyze_package_class_collisions,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class PackageClassCollisionTests(unittest.TestCase):
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
        blocker_src.mkdir(parents=True)
        candidate_src.mkdir(parents=True)

        blocker = blocker_src / "b.java"
        blocker.write_text(
            "package a; public class b {}\n",
            encoding="utf-8",
        )

        one = candidate_src / "One.java"
        one.write_text(
            "package a.b.c; public class One {}\n",
            encoding="utf-8",
        )
        two = candidate_src / "Two.java"
        two.write_text(
            "package a.b.c; public class Two {}\n",
            encoding="utf-8",
        )

        blocker_classes = root / "blocker-classes"
        candidate_classes = root / "candidate-classes"
        self._compile([blocker], blocker_classes)
        self._compile([one, two], candidate_classes)

        jar = root / "fixture.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for classes in (blocker_classes, candidate_classes):
                for path in sorted(classes.rglob("*.class")):
                    z.write(
                        path,
                        path.relative_to(classes).as_posix(),
                    )

        plan = {
            "schema_version": 1,
            "kind": "javac_missing_class_recovery_plan",
            "plan_id": "JCLASSPLAN_" + "5" * 20,
            "identifiers_included": True,
            "candidates": [
                {
                    "candidate_id": "JCLASSMISS_001",
                    "candidate_internal_name": "a/b/c/One",
                },
                {
                    "candidate_id": "JCLASSMISS_002",
                    "candidate_internal_name": "a/b/c/Two",
                },
            ],
        }
        plan_path = root / "private-plan.json"
        plan_path.write_text(
            json.dumps(plan, indent=2) + "\n",
            encoding="utf-8",
        )
        return plan_path, jar

    def test_shared_prefix_class_creates_one_collision_component(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, jar = self._fixture(root)

            report = analyze_package_class_collisions(
                plan,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                report["summary"]["candidate_count"],
                2,
            )
            self.assertEqual(
                report["summary"]["colliding_candidate_count"],
                2,
            )
            self.assertEqual(
                report["summary"]["unique_blocker_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["component_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["collision_edge_count"],
                2,
            )
            self.assertEqual(
                report["summary"]["blocking_prefix_counts"],
                {"1": 2},
            )

            blocker = report["blockers"][0]
            self.assertEqual(
                blocker["blocker_internal_name"],
                "a/b",
            )
            self.assertEqual(
                blocker["affected_candidate_count"],
                2,
            )

            component = report["components"][0]
            self.assertEqual(
                component["candidate_count"],
                2,
            )
            self.assertEqual(
                component["blocker_count"],
                1,
            )

    def test_public_report_redacts_names_but_keeps_same_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, jar = self._fixture(root)

            public = analyze_package_class_collisions(
                plan,
                jar,
            )
            private = analyze_package_class_collisions(
                plan,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["collision_topology_id"],
                private["collision_topology_id"],
            )
            self.assertNotIn("a/b/c/One", str(public))
            self.assertNotIn("a/b", str(public))
            self.assertIn("a/b/c/One", str(private))
            self.assertIn("a/b", str(private))

    def test_non_colliding_candidate_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src" / "x" / "y"
            src.mkdir(parents=True)
            source = src / "Plain.java"
            source.write_text(
                "package x.y; public class Plain {}\n",
                encoding="utf-8",
            )
            classes = root / "classes"
            classes.mkdir()
            proc = subprocess.run(
                [
                    "javac",
                    "--release",
                    "9",
                    "-d",
                    str(classes),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)

            jar = root / "plain.jar"
            with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
                z.write(
                    classes / "x" / "y" / "Plain.class",
                    "x/y/Plain.class",
                )

            plan = {
                "schema_version": 1,
                "kind": "javac_missing_class_recovery_plan",
                "plan_id": "JCLASSPLAN_" + "6" * 20,
                "identifiers_included": True,
                "candidates": [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "x/y/Plain",
                    }
                ],
            }
            plan_path = root / "plan.json"
            plan_path.write_text(
                json.dumps(plan),
                encoding="utf-8",
            )

            report = analyze_package_class_collisions(
                plan_path,
                jar,
            )
            self.assertEqual(
                report["summary"]["colliding_candidate_count"],
                0,
            )
            self.assertEqual(
                report["summary"]["non_colliding_candidate_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["unique_blocker_count"],
                0,
            )
            self.assertEqual(
                report["summary"]["component_count"],
                0,
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.classfile import parse_class
from spk_recovery.collision_remap_apply import (
    apply_collision_remap_plan,
)
from spk_recovery.package_class_remap_plan import (
    build_package_class_remap_plan,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class CollisionRemapApplyTests(unittest.TestCase):
    def _compile(
        self,
        sources: list[Path],
        out: Path,
        *,
        classpath: Path | None = None,
    ):
        out.mkdir(parents=True, exist_ok=True)
        command = [
            "javac",
            "--release",
            "9",
        ]
        if classpath is not None:
            command.extend(["-classpath", str(classpath)])
        command.extend(
            [
                "-d",
                str(out),
                *map(str, sources),
            ]
        )
        proc = subprocess.run(
            command,
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
            "package a; "
            "public class b { "
            "public static class Inner {} "
            "}\n",
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
            "public a.b value; "
            "public a.b.Inner inner; "
            "}\n",
            encoding="utf-8",
        )

        blocker_classes = root / "blocker-classes"
        candidate_classes = root / "candidate-classes"
        holder_classes = root / "holder-classes"

        self._compile([blocker], blocker_classes)
        self._compile([candidate], candidate_classes)
        self._compile(
            [holder],
            holder_classes,
            classpath=blocker_classes,
        )

        jar = root / "collision.jar"
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

        recovery_plan = {
            "schema_version": 1,
            "kind": "javac_missing_class_recovery_plan",
            "plan_id": "JCLASSPLAN_" + "8" * 20,
            "identifiers_included": True,
            "candidates": [
                {
                    "candidate_id": "JCLASSMISS_001",
                    "candidate_internal_name": "a/b/c/One",
                }
            ],
        }
        recovery_path = root / "private-recovery-plan.json"
        recovery_path.write_text(
            json.dumps(recovery_plan, indent=2) + "\n",
            encoding="utf-8",
        )

        remap = build_package_class_remap_plan(
            recovery_path,
            jar,
            include_identifiers=True,
        )
        remap_path = root / "private-remap-plan.json"
        remap_path.write_text(
            json.dumps(remap, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return jar, remap_path, remap

    def _javac_probe(
        self,
        root: Path,
        jar: Path,
        source_text: str,
        *,
        name: str,
    ) -> subprocess.CompletedProcess[str]:
        src = root / (name + ".java")
        src.write_text(source_text, encoding="utf-8")
        out = root / (name + "-classes")
        out.mkdir()
        return subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-classpath",
                str(jar),
                "-d",
                str(out),
                str(src),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_apply_remap_removes_collision_and_preserves_candidate_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, remap_path, remap = self._fixture(root)
            transformed = root / "transformed.jar"

            with zipfile.ZipFile(original) as z:
                candidate_before = z.read("a/b/c/One.class")

            before = self._javac_probe(
                root,
                original,
                (
                    "import a.b.c.One; "
                    "public class BeforeProbe { One value; }\n"
                ),
                name="BeforeProbe",
            )
            self.assertNotEqual(before.returncode, 0)

            public = apply_collision_remap_plan(
                remap_path,
                original,
                transformed,
            )
            private = apply_collision_remap_plan(
                remap_path,
                original,
                root / "transformed-private.jar",
                include_identifiers=True,
            )

            self.assertEqual(
                public["application_id"],
                private["application_id"],
            )
            self.assertFalse(public["identifiers_included"])
            self.assertTrue(private["identifiers_included"])
            self.assertNotIn("a/b", str(public))
            self.assertIn("a/b", str(private))

            remap_row = remap["remaps"][0]
            old = remap_row["old_internal_name"]
            new = remap_row["new_internal_name"]

            with zipfile.ZipFile(transformed) as z:
                names = set(z.namelist())
                self.assertNotIn(old + ".class", names)
                self.assertNotIn(old + "$Inner.class", names)
                self.assertIn(new + ".class", names)
                self.assertIn(new + "$Inner.class", names)

                candidate_after = z.read("a/b/c/One.class")
                self.assertEqual(
                    candidate_after,
                    candidate_before,
                )

                holder = parse_class(
                    z.read("holder/UseBlocker.class")
                )
                field_descriptors = {
                    str(row["descriptor"])
                    for row in holder.fields
                }
                self.assertIn(
                    "L" + new + ";",
                    field_descriptors,
                )
                self.assertIn(
                    "L" + new + "$Inner;",
                    field_descriptors,
                )

            after_candidate = self._javac_probe(
                root,
                transformed,
                (
                    "import a.b.c.One; "
                    "public class AfterCandidateProbe { One value; }\n"
                ),
                name="AfterCandidateProbe",
            )
            self.assertEqual(
                after_candidate.returncode,
                0,
                after_candidate.stdout + after_candidate.stderr,
            )

            dotted_new = new.replace("/", ".")
            after_blocker = self._javac_probe(
                root,
                transformed,
                (
                    f"import {dotted_new}; "
                    f"public class AfterBlockerProbe {{ "
                    f"{dotted_new.rsplit('.', 1)[-1]} value; "
                    f"{dotted_new}.Inner inner; "
                    f"}}\n"
                ),
                name="AfterBlockerProbe",
            )
            self.assertEqual(
                after_blocker.returncode,
                0,
                after_blocker.stdout + after_blocker.stderr,
            )

            self.assertEqual(
                public["summary"][
                    "remaining_old_reference_count"
                ],
                0,
            )
            self.assertEqual(
                public["summary"]["verified_target_count"],
                1,
            )

    def test_application_refuses_plan_bound_to_different_jar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, remap_path, _remap = self._fixture(root)
            other = root / "other.jar"
            shutil.copyfile(original, other)

            with zipfile.ZipFile(
                other,
                "a",
                zipfile.ZIP_STORED,
            ) as z:
                z.writestr("extra.txt", b"x")

            with self.assertRaisesRegex(
                ValueError,
                "different input JAR",
            ):
                apply_collision_remap_plan(
                    remap_path,
                    other,
                    root / "out.jar",
                )


if __name__ == "__main__":
    unittest.main()

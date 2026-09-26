from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.namespace_collision_proof import (
    prove_namespace_collisions,
)
from spk_recovery.namespace_remap_impact import (
    plan_namespace_remap_impact,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class NamespaceRemapImpactTests(unittest.TestCase):
    def _compile(
        self,
        sources: list[Path],
        out: Path,
        *,
        classpath: Path | None = None,
    ) -> None:
        command = [
            "javac",
            "--release",
            "9",
            "-d",
            str(out),
        ]
        if classpath is not None:
            command.extend(["-classpath", str(classpath)])
        command.extend(str(source) for source in sources)

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

    def _fixture(
        self,
        root: Path,
        *,
        include_reflective_literal: bool = False,
    ) -> tuple[Path, dict]:
        owner_src = root / "owner-src"
        package_src = root / "package-src"
        ref_src = root / "ref-src"
        owner_classes = root / "owner-classes"
        package_classes = root / "package-classes"
        ref_classes = root / "ref-classes"

        for path in (
            owner_src,
            package_src,
            ref_src,
            owner_classes,
            package_classes,
            ref_classes,
        ):
            path.mkdir(parents=True)

        owner_file = owner_src / "b.java"
        owner_file.write_text(
            "package a; public class b { "
            "public static class Inner {} }\n",
            encoding="utf-8",
        )
        self._compile([owner_file], owner_classes)

        target_dir = package_src / "a" / "b" / "c"
        target_dir.mkdir(parents=True)
        target_file = target_dir / "Target.java"
        target_file.write_text(
            "package a.b.c; public class Target {}\n",
            encoding="utf-8",
        )
        self._compile([target_file], package_classes)

        ref_dir = ref_src / "x"
        ref_dir.mkdir(parents=True)
        ref_file = ref_dir / "Ref.java"
        literal = (
            ' public String reflected = "a.b";'
            if include_reflective_literal
            else ""
        )
        ref_file.write_text(
            "package x; public class Ref { "
            "public a.b value;"
            + literal
            + " }\n",
            encoding="utf-8",
        )
        self._compile(
            [ref_file],
            ref_classes,
            classpath=owner_classes,
        )

        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as archive:
            for classes in (
                owner_classes,
                package_classes,
                ref_classes,
            ):
                for path in sorted(classes.rglob("*.class")):
                    archive.write(
                        path,
                        path.relative_to(classes).as_posix(),
                    )

        private_plan = {
            "schema_version": 1,
            "kind": "javac_missing_class_recovery_plan",
            "plan_id": "JCLASSPLAN_" + "6" * 20,
            "identifiers_included": True,
            "candidates": [
                {
                    "candidate_id": "JCLASSMISS_001",
                    "candidate_internal_name": "a/b/c/Target",
                }
            ],
        }

        collision = prove_namespace_collisions(
            private_plan,
            jar,
            include_identifiers=True,
        )
        return jar, collision

    def test_real_classfiles_expose_hard_and_descriptor_rewrite_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, collision = self._fixture(root)

            public = plan_namespace_remap_impact(
                collision,
                jar,
            )
            private = plan_namespace_remap_impact(
                collision,
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["impact_plan_id"],
                private["impact_plan_id"],
            )
            self.assertEqual(
                public["summary"][
                    "planned_binary_class_rename_count"
                ],
                2,
            )
            self.assertEqual(
                public["summary"][
                    "planned_nested_binary_class_rename_count"
                ],
                1,
            )
            self.assertGreater(
                public["summary"]["hard_class_reference_count"],
                0,
            )
            self.assertGreater(
                public["summary"][
                    "descriptor_signature_reference_count"
                ],
                0,
            )
            self.assertEqual(
                public["summary"]["reflective_literal_risk_count"],
                0,
            )
            self.assertEqual(
                public["summary"]["unclassified_utf8_risk_count"],
                0,
            )
            self.assertTrue(
                public["summary"]["automatic_bytecode_rewrite_safe"]
            )
            self.assertTrue(
                public["summary"]["source_reference_rewrite_required"]
            )
            self.assertNotIn("a/b", str(public))
            self.assertIn("a/b", str(private))

    def test_reflective_literal_blocks_automatic_rewrite_safety(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, collision = self._fixture(
                root,
                include_reflective_literal=True,
            )

            report = plan_namespace_remap_impact(
                collision,
                jar,
            )

            self.assertGreater(
                report["summary"]["reflective_literal_risk_count"],
                0,
            )
            self.assertFalse(
                report["summary"]["automatic_bytecode_rewrite_safe"]
            )


if __name__ == "__main__":
    unittest.main()

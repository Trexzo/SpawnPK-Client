from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_closure import (
    DependencyRuntimeClosureError,
    build_dependency_runtime_closure,
)
from spk_recovery.dependency_runtime_frontier import (
    build_dependency_runtime_frontier,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyRuntimeClosureTests(unittest.TestCase):
    def _compile(
        self,
        root: Path,
        package: str,
        sources: dict[str, str],
        out_name: str,
    ) -> Path:
        src = root / (out_name + "-src") / package
        src.mkdir(parents=True)
        paths: list[Path] = []
        for name, body in sources.items():
            path = src / name
            path.write_text(body, encoding="utf-8")
            paths.append(path)

        classes = root / (out_name + "-classes")
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(classes),
                *[str(path) for path in sorted(paths)],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return classes

    def _fixture(self, root: Path) -> dict:
        bundled_classes = self._compile(
            root,
            "old",
            {
                "A.java": (
                    "package old; public class A { "
                    "public B make() { return new B(); } }\n"
                ),
                "B.java": "package old; public class B {}\n",
            },
            "bundled",
        )
        official_classes = self._compile(
            root,
            "official",
            {
                "A.java": "package official; public class A {}\n",
            },
            "official",
        )

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for name in ("A", "B"):
                archive.write(
                    bundled_classes / "old" / f"{name}.class",
                    f"old/{name}.class",
                )

        official = root / "official.jar"
        with zipfile.ZipFile(
            official,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.write(
                official_classes / "official" / "A.class",
                "official/A.class",
            )
            archive.writestr(
                "META-INF/services/example.Service",
                b"official.A\n",
            )
            archive.writestr(
                "natives/example.dll",
                b"native-bytes",
            )

        replacement = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": "DEPREPLACE_" + "1" * 20,
            "bundled_jar_sha256": _sha(bundled),
            "java_release": 9,
            "project_prefixes": ["rs/"],
            "official_artifact_set_sha256": "f" * 64,
            "official_artifacts": [
                {
                    "artifact": "official.jar",
                    "sha256": _sha(official),
                    "multi_release_class_count": 0,
                    "java_release": 9,
                }
            ],
            "artifact_ids": {
                "official.jar": "DEPARTIFACT_0001",
            },
            "owners": [
                {
                    "owner_id": "DEPOWNER_00001",
                    "classification": "official_replaceable",
                    "old_owner": "old/A",
                    "new_owner": "official/A",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "residual_bundled",
                    "old_owner": "old/B",
                    "new_owner": None,
                    "artifact": None,
                },
            ],
            "identifiers_included": True,
        }
        plan = root / "replacement.json"
        plan.write_text(
            json.dumps(replacement, indent=2) + "\n",
            encoding="utf-8",
        )

        frontier = build_dependency_runtime_frontier(
            plan,
            bundled,
            [official],
        )
        frontier_path = root / "frontier.json"
        frontier_path.write_text(
            json.dumps(frontier, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "bundled": bundled,
            "official": official,
            "plan": plan,
            "frontier": frontier_path,
            "frontier_report": frontier,
        }

    def test_closure_surfaces_residual_and_resource_blockers(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_closure(
                fx["plan"],
                fx["frontier"],
                fx["bundled"],
                [fx["official"]],
            )

            self.assertEqual(
                report["kind"],
                "dependency_runtime_closure",
            )
            self.assertEqual(report["summary"]["root_count"], 1)
            self.assertGreaterEqual(
                report["summary"]["status_counts"].get(
                    "official_closure_mapped",
                    0,
                ),
                1,
            )
            self.assertGreaterEqual(
                report["summary"]["status_counts"].get(
                    "residual_bundled",
                    0,
                ),
                1,
            )
            self.assertGreaterEqual(
                report["summary"]["status_counts"].get(
                    "platform_runtime",
                    0,
                ),
                1,
            )
            self.assertGreaterEqual(
                report["summary"]["class_closure_blocker_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["service_entry_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["native_entry_count"],
                1,
            )
            self.assertTrue(
                report["summary"][
                    "reflection_dynamic_loading_unproven"
                ]
            )
            self.assertFalse(
                report["summary"]["runtime_capsule_mutation_ready"]
            )
            self.assertFalse(report["identifiers_included"])
            self.assertNotIn(
                '"owner": "old/',
                json.dumps(report),
            )

    def test_public_and_private_reports_share_closure_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = build_dependency_runtime_closure(
                fx["plan"],
                fx["frontier"],
                fx["bundled"],
                [fx["official"]],
            )
            private = build_dependency_runtime_closure(
                fx["plan"],
                fx["frontier"],
                fx["bundled"],
                [fx["official"]],
                include_identifiers=True,
            )
            self.assertEqual(
                public["runtime_closure_id"],
                private["runtime_closure_id"],
            )
            self.assertTrue(private["identifiers_included"])
            self.assertIn(
                "old/A",
                {row.get("owner") for row in private["owners"]},
            )

    def test_frontier_replacement_plan_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            frontier = fx["frontier_report"]
            frontier["replacement_plan_id"] = (
                "DEPREPLACE_" + "9" * 20
            )
            fx["frontier"].write_text(
                json.dumps(frontier) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeClosureError,
                "different DEPREPLACE",
            ):
                build_dependency_runtime_closure(
                    fx["plan"],
                    fx["frontier"],
                    fx["bundled"],
                    [fx["official"]],
                )

    def test_official_artifact_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            fx["official"].write_bytes(b"drift")
            with self.assertRaises(DependencyRuntimeClosureError):
                build_dependency_runtime_closure(
                    fx["plan"],
                    fx["frontier"],
                    fx["bundled"],
                    [fx["official"]],
                )


if __name__ == "__main__":
    unittest.main()

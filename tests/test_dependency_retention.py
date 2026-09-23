from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_remap_proof import prove_dependency_remaps
from spk_recovery.dependency_reference_surface import (
    scan_project_reference_surface,
)
from spk_recovery.dependency_retention import (
    classify_project_coupled_retention,
)


class DependencyRetentionTests(unittest.TestCase):
    def _compile_jar(
        self,
        root: Path,
        name: str,
        sources: dict[str, str],
    ) -> Path:
        src = root / (name + "-src")
        classes = root / (name + "-classes")
        src.mkdir()
        classes.mkdir()
        paths = []
        for rel, content in sources.items():
            path = src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(str(path))
        proc = subprocess.run(
            ["javac", "-d", str(classes), *paths],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError(proc.stderr)
        jar = root / (name + ".jar")
        with zipfile.ZipFile(jar, "w") as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(
                    path,
                    path.relative_to(classes).as_posix(),
                )
        return jar

    def _write_json(self, path: Path, value: dict) -> Path:
        path.write_text(
            json.dumps(value, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def test_bidirectional_unmapped_seed_and_peer_closure_are_retained(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "project/Main.java": (
                        "package project; public class Main { "
                        "public int run(vendor.b value) { return value.use(); } "
                        "}"
                    ),
                    "vendor/b.java": (
                        "package vendor; public class b { "
                        "public int use() { return project.Main.class.getName().length() + "
                        "new vendor.c().value(); } }"
                    ),
                    "vendor/c.java": (
                        "package vendor; public class c { "
                        "public int value() { return 7; } }"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "official/Api.java": (
                        "package official; public class Api { "
                        "public long unrelated() { return 1L; } }"
                    )
                },
            )
            surface = scan_project_reference_surface(
                bundled,
                project_prefixes=("project/",),
            )
            surface_path = self._write_json(
                root / "depref.json",
                surface,
            )
            remap = prove_dependency_remaps(
                surface_path,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )
            remap_path = self._write_json(
                root / "remap.json",
                remap,
            )

            report = classify_project_coupled_retention(
                surface_path,
                remap_path,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
                lineage_jar=bundled,
            )

            statuses = {
                row["class"]: row["status"]
                for row in report["classifications"]
            }
            self.assertEqual(
                statuses["vendor/b"],
                "project_coupled_non_pom",
            )
            self.assertEqual(
                statuses["vendor/c"],
                "source_retention_closure",
            )
            self.assertEqual(
                report["summary"][
                    "lineage_byte_identical_retained_class_count"
                ],
                2,
            )

    def test_consumed_unmapped_class_without_reverse_edge_is_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "project/Main.java": (
                        "package project; public class Main { "
                        "public int run(vendor.x value) { return value.use(); } "
                        "}"
                    ),
                    "vendor/x.java": (
                        "package vendor; public class x { "
                        "public int use() { return 1; } }"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {"official/Api.java": "package official; public class Api {}"},
            )
            surface = scan_project_reference_surface(
                bundled,
                project_prefixes=("project/",),
            )
            surface_path = self._write_json(root / "depref.json", surface)
            remap = prove_dependency_remaps(
                surface_path,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )
            remap_path = self._write_json(root / "remap.json", remap)

            report = classify_project_coupled_retention(
                surface_path,
                remap_path,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            self.assertEqual(
                report["classifications"][0]["status"],
                "project_consumed_non_pom",
            )

    def test_closure_does_not_cross_accepted_official_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "project/Main.java": (
                        "package project; public class Main { "
                        "public int run(vendor.b value) { return value.use(); } }"
                    ),
                    "vendor/b.java": (
                        "package vendor; public class b { "
                        "public int use() { "
                        "return project.Main.class.getName().length() + "
                        "new dep.a().value(); } }"
                    ),
                    "dep/a.java": (
                        "package dep; public class a { "
                        "public int value() { return 7; } }"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public int value() { return 7; } }"
                    )
                },
            )
            surface = scan_project_reference_surface(
                bundled,
                project_prefixes=("project/",),
            )
            surface_path = self._write_json(root / "depref.json", surface)
            remap = prove_dependency_remaps(
                surface_path,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )
            remap_path = self._write_json(root / "remap.json", remap)

            report = classify_project_coupled_retention(
                surface_path,
                remap_path,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            retained = {
                row["class"] for row in report["classifications"]
            }
            self.assertIn("vendor/b", retained)
            self.assertNotIn("dep/a", retained)


if __name__ == "__main__":
    unittest.main()

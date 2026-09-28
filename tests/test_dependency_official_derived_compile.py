from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_official_derived_compile import (
    DependencyOfficialDerivedCompileError,
    compile_official_overlay_and_restore,
)
from spk_recovery.dependency_reference_surface import (
    scan_project_reference_surface,
)
from spk_recovery.source_digest import source_tree_digest


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("java"),
    "JDK required",
)
class DependencyOfficialDerivedCompileTests(unittest.TestCase):
    def _compile(
        self,
        root: Path,
        sources: dict[str, str],
    ) -> Path:
        src = root / "src"
        out = root / "classes"
        src.mkdir(parents=True)
        out.mkdir()
        paths = []
        for rel, text in sources.items():
            path = src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            paths.append(path)

        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(out),
                *[str(path) for path in paths],
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
        return out

    def _jar(self, classes: Path, out: Path) -> Path:
        with zipfile.ZipFile(
            out,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(
                    path,
                    path.relative_to(classes).as_posix(),
                )
        return out

    def _sha(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _fixture(self, root: Path):
        official_classes = self._compile(
            root / "official",
            {
                "official/T.java": (
                    "package official; public class T {}\n"
                ),
                "official/I.java": (
                    "package official; "
                    "public interface I { void call(T t); }\n"
                ),
                "official/Api.java": (
                    "package official; "
                    "public class Api { "
                    "public T value; "
                    "public void run(T t) { value = t; } "
                    "}\n"
                ),
            },
        )
        official_jar = self._jar(
            official_classes,
            root / "official.jar",
        )

        bundled_classes = self._compile(
            root / "bundled",
            {
                "bundled/T.java": (
                    "package bundled; public class T {}\n"
                ),
                "bundled/I.java": (
                    "package bundled; "
                    "public interface I { void z(T t); }\n"
                ),
                "bundled/Api.java": (
                    "package bundled; "
                    "public class Api { "
                    "public T b; "
                    "public void x(T t) { b = t; } "
                    "}\n"
                ),
                "app/LegacyOnly.java": (
                    "package app; public class LegacyOnly {}\n"
                ),
            },
        )
        bundled_jar = self._jar(
            bundled_classes,
            root / "bundled.jar",
        )

        canonical = root / "canonical"
        canonical.mkdir()
        app = canonical / "app"
        app.mkdir()
        (app / "Use.java").write_text(
            "package app; "
            "public class Use { "
            "public static official.T use("
            "official.Api a, official.I i, official.T t) { "
            "a.value = t; a.run(t); i.call(t); "
            "return a.value; "
            "} "
            "public static official.Api make() { "
            "return new official.Api(); "
            "} "
            "}\n",
            encoding="utf-8",
        )

        overlay = root / "overlay"
        shutil.copytree(canonical, overlay)

        source_sha, source_files, source_bytes = source_tree_digest(
            canonical
        )
        overlay_sha, overlay_files, overlay_bytes = source_tree_digest(
            overlay
        )
        self.assertEqual(source_sha, overlay_sha)

        replacement_id = "DEPREPLACE_" + "A" * 20
        remap_id = "DEPREMAP_" + "B" * 20
        bundled_sha = self._sha(bundled_jar)
        official_sha = self._sha(official_jar)

        overlay_manifest = {
            "schema_version": 1,
            "kind": "dependency_source_overlay_manifest",
            "overlay_id": "DEPSRCOVERLAY_" + "C" * 20,
            "edit_plan_id": "DEPSRCEDIT_" + "D" * 20,
            "binding_inventory_id": "DEPSRCBIND_" + "E" * 20,
            "replacement_plan_id": replacement_id,
            "dependency_remap_proof_id": remap_id,
            "input_source_tree_sha256": source_sha,
            "output_source_tree_sha256": overlay_sha,
            "java_file_count": len(overlay_files),
            "input_source_bytes": source_bytes,
            "output_source_bytes": overlay_bytes,
            "bundled_jar_sha256": bundled_sha,
            "java_release": 9,
            "official_artifact_sha256": [official_sha],
            "summary": {
                "direct_edit_count": 0,
                "files_changed": 0,
                "canonical_input_unchanged": True,
            },
            "source_directory": "src",
        }
        overlay_manifest_path = root / "overlay-manifest.json"
        overlay_manifest_path.write_text(
            json.dumps(overlay_manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        replacement = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": replacement_id,
            "dependency_remap_proof_id": remap_id,
            "bundled_jar_sha256": bundled_sha,
            "java_release": 9,
            "official_artifacts": [
                {
                    "artifact": "official.jar",
                    "sha256": official_sha,
                    "java_release": 9,
                }
            ],
            "owners": [],
            "identifiers_included": True,
        }
        replacement_path = root / "replacement.json"
        replacement_path.write_text(
            json.dumps(replacement, indent=2) + "\n",
            encoding="utf-8",
        )

        reverse = {
            "schema_version": 1,
            "kind": "dependency_reverse_compile_transport_plan",
            "reverse_plan_id": "DEPREVERSE_" + "F" * 20,
            "dependency_remap_proof_id": remap_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": bundled_sha,
            "summary": {
                "ready_for_bytecode_restore": True,
                "blocker_count": 0,
            },
            "blockers": [],
            "class_reverse": [
                {
                    "class_reverse_id": "C1",
                    "official_owner": "official/Api",
                    "bundled_owner": "bundled/Api",
                },
                {
                    "class_reverse_id": "C2",
                    "official_owner": "official/I",
                    "bundled_owner": "bundled/I",
                },
                {
                    "class_reverse_id": "C3",
                    "official_owner": "official/T",
                    "bundled_owner": "bundled/T",
                },
            ],
            "member_reverse": [
                {
                    "member_reverse_id": "M1",
                    "reference_kind": "field",
                    "transport_kind": "field",
                    "official_owner": "official/Api",
                    "official_name": "value",
                    "official_descriptor": "Lofficial/T;",
                    "bundled_owner": "bundled/Api",
                    "bundled_name": "b",
                    "bundled_descriptor": "Lbundled/T;",
                },
                {
                    "member_reverse_id": "M2",
                    "reference_kind": "method",
                    "transport_kind": "method",
                    "official_owner": "official/Api",
                    "official_name": "run",
                    "official_descriptor": "(Lofficial/T;)V",
                    "bundled_owner": "bundled/Api",
                    "bundled_name": "x",
                    "bundled_descriptor": "(Lbundled/T;)V",
                },
                {
                    "member_reverse_id": "M3",
                    "reference_kind": "interface_method",
                    "transport_kind": "method",
                    "official_owner": "official/I",
                    "official_name": "call",
                    "official_descriptor": "(Lofficial/T;)V",
                    "bundled_owner": "bundled/I",
                    "bundled_name": "z",
                    "bundled_descriptor": "(Lbundled/T;)V",
                },
            ],
            "identifiers_included": True,
        }
        reverse_path = root / "reverse.json"
        reverse_path.write_text(
            json.dumps(reverse, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "overlay_manifest": overlay_manifest_path,
            "overlay": overlay,
            "canonical": canonical,
            "replacement": replacement_path,
            "reverse": reverse_path,
            "bundled": bundled_jar,
            "official": official_jar,
            "canonical_sha": source_sha,
            "bundled_sha": bundled_sha,
            "official_sha": official_sha,
        }

    def test_official_first_compile_restores_bundled_runtime_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)
            out = root / "derived"

            report = compile_official_overlay_and_restore(
                fx["overlay_manifest"],
                fx["overlay"],
                fx["canonical"],
                fx["replacement"],
                fx["reverse"],
                fx["bundled"],
                [fx["official"]],
                out,
                project_prefixes=("app/",),
            )

            self.assertEqual(report["status"], "complete")
            self.assertTrue(
                report["summary"][
                    "reverse_reference_surface_match"
                ]
            )
            self.assertEqual(
                report["summary"][
                    "project_binary_fallback_count"
                ],
                0,
            )
            self.assertFalse(
                report["summary"][
                    "compile_dependency_contains_project_classes"
                ]
            )
            self.assertEqual(
                report["summary"][
                    "compile_dependency_capsule_class_count"
                ],
                3,
            )
            self.assertFalse(
                report["summary"]["canonical_source_modified"]
            )
            self.assertFalse(
                report["summary"][
                    "bundled_runtime_dependency_modified"
                ]
            )
            self.assertFalse(
                report["summary"][
                    "official_compile_artifacts_modified"
                ]
            )
            self.assertTrue(
                report["summary"][
                    "restored_project_bytecode_ready_for_runtime_assembly"
                ]
            )

            self.assertEqual(
                source_tree_digest(fx["canonical"])[0],
                fx["canonical_sha"],
            )
            self.assertEqual(
                self._sha(fx["bundled"]),
                fx["bundled_sha"],
            )
            self.assertEqual(
                self._sha(fx["official"]),
                fx["official_sha"],
            )

            restored = out / "restored-bundled-project.jar"
            surface = scan_project_reference_surface(
                restored,
                project_prefixes=("app/",),
            )
            encoded = json.dumps(surface)
            self.assertNotIn("official/", encoded)
            self.assertIn("bundled/Api", encoded)
            self.assertIn("bundled/I", encoded)

    def test_official_first_compile_cannot_fallback_to_project_binary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)

            source_text = (
                "package app; "
                "public class Use { "
                "public LegacyOnly legacy; "
                "public official.Api api; "
                "}\n"
            )
            for source_root in (
                fx["canonical"],
                fx["overlay"],
            ):
                (source_root / "app" / "Use.java").write_text(
                    source_text,
                    encoding="utf-8",
                )

            canonical_sha, _files, _bytes = source_tree_digest(
                fx["canonical"]
            )
            overlay_sha, overlay_files, _overlay_bytes = (
                source_tree_digest(fx["overlay"])
            )
            self.assertEqual(canonical_sha, overlay_sha)

            manifest = json.loads(
                fx["overlay_manifest"].read_text(
                    encoding="utf-8"
                )
            )
            manifest["input_source_tree_sha256"] = canonical_sha
            manifest["output_source_tree_sha256"] = overlay_sha
            manifest["java_file_count"] = len(overlay_files)
            fx["overlay_manifest"].write_text(
                json.dumps(manifest) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DependencyOfficialDerivedCompileError,
                "official-first overlay javac failed",
            ):
                compile_official_overlay_and_restore(
                    fx["overlay_manifest"],
                    fx["overlay"],
                    fx["canonical"],
                    fx["replacement"],
                    fx["reverse"],
                    fx["bundled"],
                    [fx["official"]],
                    root / "derived",
                    project_prefixes=("app/",),
                )

    def test_authority_mismatch_refuses_before_compile(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)

            manifest = json.loads(
                fx["overlay_manifest"].read_text(
                    encoding="utf-8"
                )
            )
            manifest["replacement_plan_id"] = (
                "DEPREPLACE_" + "0" * 20
            )
            fx["overlay_manifest"].write_text(
                json.dumps(manifest) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                DependencyOfficialDerivedCompileError
            ):
                compile_official_overlay_and_restore(
                    fx["overlay_manifest"],
                    fx["overlay"],
                    fx["canonical"],
                    fx["replacement"],
                    fx["reverse"],
                    fx["bundled"],
                    [fx["official"]],
                    root / "derived",
                    project_prefixes=("app/",),
                )


if __name__ == "__main__":
    unittest.main()

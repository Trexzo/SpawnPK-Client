from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.clean_rebuild import (
    CleanRebuildError,
    clean_project_rebuild,
)
from spk_recovery.dependency_reference_surface import (
    scan_project_reference_surface,
)
from spk_recovery.progressive_compile import _probe_javac
from spk_recovery.source_digest import source_tree_digest


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("java"),
    "JDK required",
)
class CleanRebuildOfficialFirstTests(unittest.TestCase):
    def _compile(
        self,
        root: Path,
        sources: dict[str, str],
        *,
        classpath: Path | None = None,
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
                *[str(path) for path in paths],
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
        return out

    def _jar(
        self,
        out: Path,
        *class_roots: Path,
    ) -> Path:
        with zipfile.ZipFile(
            out,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr(
                "META-INF/MANIFEST.MF",
                "Manifest-Version: 1.0\r\n\r\n",
            )
            for class_root in class_roots:
                for path in sorted(class_root.rglob("*.class")):
                    archive.write(
                        path,
                        path.relative_to(class_root).as_posix(),
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
                "official/Api.java": (
                    "package official; public class Api { "
                    "public T value; "
                    "public void run(T t) { value = t; } "
                    "}\n"
                ),
            },
        )
        official_jar = self._jar(
            root / "official.jar",
            official_classes,
        )

        bundled_classes = self._compile(
            root / "bundled",
            {
                "bundled/T.java": (
                    "package bundled; public class T {}\n"
                ),
                "bundled/Api.java": (
                    "package bundled; public class Api { "
                    "public T b; "
                    "public void x(T t) { b = t; } "
                    "}\n"
                ),
            },
        )
        bundled_only_jar = self._jar(
            root / "bundled-only.jar",
            bundled_classes,
        )
        runtime_project_classes = self._compile(
            root / "runtime-project",
            {
                "app/Use.java": (
                    "package app; "
                    "public class Use { "
                    "public static bundled.T use("
                    "bundled.Api a, bundled.T t) { "
                    "a.b = t; a.x(t); return a.b; "
                    "} "
                    "}\n"
                ),
            },
            classpath=bundled_only_jar,
        )

        readable = self._jar(
            root / "readable.jar",
            bundled_classes,
            runtime_project_classes,
        )
        readable_sha = self._sha(readable)

        canonical = root / "canonical"
        app = canonical / "app"
        app.mkdir(parents=True)
        (app / "Use.java").write_text(
            "package app; "
            "public class Use { "
            "public static official.T use("
            "official.Api a, official.T t) { "
            "a.value = t; a.run(t); return a.value; "
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

        source_authority = "a" * 64
        recovered = {
            "schema_version": 1,
            "kind": "recovered_source_workspace_manifest",
            "workspace_id": "SRCWS_" + "1" * 20,
            "build_id": "v308",
            "source_authority_sha256": source_authority,
            "readable_jar_sha256": readable_sha,
            "namespace_id": "SEMNS_" + "2" * 20,
            "class_plan_digest": "c" * 64,
            "member_plan_digest": "d" * 64,
            "engine": "cfr",
            "decompiler_sha256": "e" * 64,
            "source_tree_sha256": source_sha,
            "java_file_count": len(source_files),
            "source_bytes": source_bytes,
            "source_directory": "src",
        }
        readiness = {
            "schema_version": 1,
            "kind": "source_readiness_report",
            "source_tree_sha256": source_sha,
        }
        readable_manifest = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "status": "complete",
            "verification_pass": True,
            "output_sha256": readable_sha,
            "target_package": "",
            "source_safe_fallback": False,
            "project_source_prefixes": ["app/"],
            "semantic_summary": {
                "source_safety_fallbacks": 0,
            },
        }
        authority = {
            "schema_version": 1,
            "kind": "build_authority_manifest",
            "authority_id": "BUILDAUTH_" + "3" * 20,
            "source_sha256": source_authority,
            "compiler_runtime": {
                "javac": _probe_javac("javac"),
            },
            "bytecode": {
                "dominant_java_release": 9,
            },
        }

        replacement_id = "DEPREPLACE_" + "4" * 20
        remap_id = "DEPREMAP_" + "5" * 20
        reverse_id = "DEPREVERSE_" + "6" * 20
        official_sha = self._sha(official_jar)

        overlay_manifest = {
            "schema_version": 1,
            "kind": "dependency_source_overlay_manifest",
            "overlay_id": "DEPSRCOVERLAY_" + "7" * 20,
            "edit_plan_id": "DEPSRCEDIT_" + "8" * 20,
            "binding_inventory_id": "DEPSRCBIND_" + "9" * 20,
            "replacement_plan_id": replacement_id,
            "dependency_remap_proof_id": remap_id,
            "input_source_tree_sha256": source_sha,
            "output_source_tree_sha256": overlay_sha,
            "java_file_count": len(overlay_files),
            "input_source_bytes": source_bytes,
            "output_source_bytes": overlay_bytes,
            "bundled_jar_sha256": readable_sha,
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
            "bundled_jar_sha256": readable_sha,
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
            "reverse_plan_id": reverse_id,
            "dependency_remap_proof_id": remap_id,
            "replacement_plan_id": replacement_id,
            "bundled_jar_sha256": readable_sha,
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
            ],
            "identifiers_included": True,
        }
        reverse_path = root / "reverse.json"
        reverse_path.write_text(
            json.dumps(reverse, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "canonical": canonical,
            "overlay": overlay,
            "readable": readable,
            "recovered": recovered,
            "readiness": readiness,
            "readable_manifest": readable_manifest,
            "authority": authority,
            "overlay_manifest": overlay_manifest_path,
            "replacement": replacement_path,
            "reverse": reverse_path,
            "official": official_jar,
            "canonical_sha": source_sha,
            "readable_sha": readable_sha,
            "official_sha": official_sha,
        }

    def _run(self, root: Path, fx: dict):
        return clean_project_rebuild(
            fx["recovered"],
            fx["readiness"],
            fx["readable_manifest"],
            fx["readable"],
            fx["authority"],
            fx["canonical"],
            out_dir=root / "out",
            source_prefixes=["app/"],
            official_first_restored=True,
            official_overlay_manifest_path=fx[
                "overlay_manifest"
            ],
            official_overlay_source_root=fx["overlay"],
            private_dependency_replacement_plan_path=fx[
                "replacement"
            ],
            private_dependency_reverse_plan_path=fx["reverse"],
            official_artifacts=[fx["official"]],
        )

    def test_official_first_restored_clean_rebuild_assembles_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)

            report = self._run(root, fx)

            self.assertEqual(report["status"], "complete")
            self.assertTrue(report["clean_project_build"])
            self.assertEqual(
                report["compile_transport"]["mode"],
                "official_first_restored",
            )
            self.assertTrue(
                report["compile_transport"]["opt_in"]
            )
            self.assertFalse(
                report["compile_transport"][
                    "runtime_official_dependencies_allowed"
                ]
            )
            self.assertEqual(
                report["project_classes"]["binary_fallback_count"],
                0,
            )
            self.assertEqual(
                report["project_classes"]["expected_count"],
                1,
            )
            self.assertEqual(
                report["project_classes"]["generated_count"],
                1,
            )
            self.assertEqual(
                source_tree_digest(fx["canonical"])[0],
                fx["canonical_sha"],
            )
            self.assertEqual(
                self._sha(fx["readable"]),
                fx["readable_sha"],
            )
            self.assertEqual(
                self._sha(fx["official"]),
                fx["official_sha"],
            )

            rebuilt = root / "out" / "rebuilt-client.jar"
            self.assertTrue(rebuilt.is_file())

            with zipfile.ZipFile(fx["readable"]) as original:
                original_api = original.read("bundled/Api.class")
                original_t = original.read("bundled/T.class")

            with zipfile.ZipFile(rebuilt) as runtime:
                names = set(runtime.namelist())
                self.assertIn("bundled/Api.class", names)
                self.assertIn("bundled/T.class", names)
                self.assertIn("app/Use.class", names)
                self.assertNotIn("official/Api.class", names)
                self.assertNotIn("official/T.class", names)
                self.assertEqual(
                    runtime.read("bundled/Api.class"),
                    original_api,
                )
                self.assertEqual(
                    runtime.read("bundled/T.class"),
                    original_t,
                )

            surface = scan_project_reference_surface(
                rebuilt,
                project_prefixes=("app/",),
            )
            encoded = json.dumps(surface)
            self.assertNotIn("official/", encoded)
            self.assertIn("bundled/Api", encoded)
            self.assertIn("bundled/T", encoded)

    def test_official_inputs_require_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)

            with self.assertRaisesRegex(
                CleanRebuildError,
                "require explicit official_first_restored opt-in",
            ):
                clean_project_rebuild(
                    fx["recovered"],
                    fx["readiness"],
                    fx["readable_manifest"],
                    fx["readable"],
                    fx["authority"],
                    fx["canonical"],
                    out_dir=root / "out",
                    source_prefixes=["app/"],
                    official_overlay_manifest_path=fx[
                        "overlay_manifest"
                    ],
                )

    def test_official_first_requires_complete_authority_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)

            with self.assertRaisesRegex(
                CleanRebuildError,
                "requires overlay manifest/source",
            ):
                clean_project_rebuild(
                    fx["recovered"],
                    fx["readiness"],
                    fx["readable_manifest"],
                    fx["readable"],
                    fx["authority"],
                    fx["canonical"],
                    out_dir=root / "out",
                    source_prefixes=["app/"],
                    official_first_restored=True,
                )

    def test_official_first_authority_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx = self._fixture(root)

            manifest = json.loads(
                fx["overlay_manifest"].read_text(
                    encoding="utf-8"
                )
            )
            manifest["bundled_jar_sha256"] = "0" * 64
            fx["overlay_manifest"].write_text(
                json.dumps(manifest) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                CleanRebuildError,
                "bundled JAR authority differs",
            ):
                self._run(root, fx)


if __name__ == "__main__":
    unittest.main()

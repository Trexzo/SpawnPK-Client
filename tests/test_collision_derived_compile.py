from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.classfile import parse_class
from spk_recovery.clean_rebuild import (
    CleanRebuildError,
    clean_project_rebuild,
)
from spk_recovery.progressive_compile import _probe_javac
from spk_recovery.collision_bytecode_remap import (
    transform_collision_jar,
)
from spk_recovery.collision_derived_compile import (
    CollisionDerivedCompileError,
    compile_collision_derived_source,
)
from spk_recovery.namespace_collision_plan import (
    build_namespace_collision_plan,
)
from spk_recovery.source_digest import source_tree_digest


@unittest.skipUnless(shutil.which("javac"), "javac required")
class CollisionDerivedCompileTests(unittest.TestCase):
    def _fixture(self, root: Path):
        blocker_src = root / "blocker-src" / "dep"
        target_src = root / "target-src" / "dep" / "clash"
        project_src = root / "project-src" / "rs"
        blocker_src.mkdir(parents=True)
        target_src.mkdir(parents=True)
        project_src.mkdir(parents=True)

        blocker_java = blocker_src / "clash.java"
        blocker_java.write_text(
            "package dep; public class clash {}\n",
            encoding="utf-8",
        )
        target_java = target_src / "Target.java"
        target_java.write_text(
            "package dep.clash; public class Target {}\n",
            encoding="utf-8",
        )
        project_java = project_src / "A.java"
        project_java.write_text(
            "package rs; public class A { "
            "public dep.clash value; }\n",
            encoding="utf-8",
        )

        blocker_classes = root / "blocker-classes"
        target_classes = root / "target-classes"
        project_classes = root / "project-classes"
        for path in (
            blocker_classes,
            target_classes,
            project_classes,
        ):
            path.mkdir()

        def run(args):
            proc = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                proc.returncode,
                0,
                proc.stdout + proc.stderr,
            )

        run([
            "javac",
            "--release",
            "9",
            "-d",
            str(blocker_classes),
            str(blocker_java),
        ])
        run([
            "javac",
            "--release",
            "9",
            "-d",
            str(target_classes),
            str(target_java),
        ])
        run([
            "javac",
            "--release",
            "9",
            "-classpath",
            str(blocker_classes),
            "-d",
            str(project_classes),
            str(project_java),
        ])

        readable = root / "readable.jar"
        with zipfile.ZipFile(
            readable,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for classes in (
                blocker_classes,
                target_classes,
                project_classes,
            ):
                for path in sorted(classes.rglob("*.class")):
                    archive.write(
                        path,
                        path.relative_to(classes).as_posix(),
                    )

        plan = build_namespace_collision_plan(
            readable,
            include_identifiers=True,
        )
        self.assertEqual(
            plan["summary"]["post_collision_edge_count"],
            0,
        )
        self.assertEqual(
            plan["summary"]["blocker_remap_count"],
            1,
        )
        old_name = plan["remaps"][0]["old_internal_name"]
        new_name = plan["remaps"][0]["new_internal_name"]
        self.assertEqual(old_name, "dep/clash")

        plan_path = root / "private-plan.json"
        plan_path.write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        transformed = root / "transformed.jar"
        transform = transform_collision_jar(
            readable,
            plan_path,
            transformed,
        )

        recovered = root / "recovered"
        (recovered / "rs").mkdir(parents=True)
        (recovered / "rs" / "A.java").write_text(
            "package rs; public class A { "
            f"public {new_name.replace('/', '.')} value; }}\n",
            encoding="utf-8",
        )
        tree_sha = source_tree_digest(recovered)[0]

        manifest = {
            "schema_version": 1,
            "kind": "recovered_source_workspace_manifest",
            "workspace_id": "SRCWS_" + "7" * 20,
            "source_tree_sha256": tree_sha,
            "readable_jar_sha256": transform[
                "output_jar_sha256"
            ],
            "collision_transform_id": transform["transform_id"],
            "collision_plan_id": transform["plan_id"],
            "collision_report_id": transform[
                "collision_report_id"
            ],
            "collision_mapping_sha256": transform[
                "private_mapping_sha256"
            ],
            "base_readable_jar_sha256": transform[
                "input_jar_sha256"
            ],
        }

        return (
            readable,
            plan_path,
            recovered,
            manifest,
            old_name,
            new_name,
            transform,
        )

    def test_compile_uses_matching_transform_and_restores_runtime_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                plan_path,
                recovered,
                manifest,
                old_name,
                new_name,
                transform,
            ) = self._fixture(root)

            report = compile_collision_derived_source(
                manifest,
                recovered,
                readable,
                plan_path,
                ["rs/"],
                root / "compile",
                javac_command="javac",
                release=9,
            )

            self.assertEqual(report["status"], "complete")
            self.assertFalse(report["canonical_source_modified"])
            self.assertEqual(
                report["compiler"]["source_transport"],
                "case_unique_explicit_inputs",
            )
            self.assertEqual(
                report["compiler"]["staged_source_count"],
                report["compiler"]["source_count"],
            )

            javac_args = (
                root / "compile" / "javac.args"
            ).read_text(encoding="utf-8").replace("\\", "/")
            self.assertIn(
                "/source-inputs/000000/A.java",
                javac_args,
            )
            self.assertIn("/empty-sourcepath", javac_args)
            self.assertNotIn(
                (recovered / "rs" / "A.java").resolve().as_posix(),
                javac_args,
            )
            staged_source = (
                root
                / "compile"
                / "source-inputs"
                / "000000"
                / "A.java"
            )
            self.assertEqual(
                staged_source.read_bytes(),
                (recovered / "rs" / "A.java").read_bytes(),
            )
            self.assertEqual(
                report["collision_transform_id"],
                transform["transform_id"],
            )
            self.assertFalse(
                report["runtime_transformed_dependency_allowed"]
            )
            self.assertGreater(
                report["restored_classes"][
                    "restore_replacement_count"
                ],
                0,
            )
            self.assertEqual(
                report["restored_classes"][
                    "transformed_reference_count"
                ],
                0,
            )

            restored = (
                root
                / "compile"
                / "restored-classes"
                / "rs"
                / "A.class"
            ).read_bytes()
            parsed = parse_class(restored)
            descriptors = {
                str(field["descriptor"])
                for field in parsed.fields
            }
            self.assertIn(
                "L" + old_name + ";",
                descriptors,
            )
            self.assertNotIn(
                "L" + new_name + ";",
                descriptors,
            )

            transformed_dependency = (
                root
                / "compile"
                / "compile-transformed-dependency.jar"
            )
            with zipfile.ZipFile(transformed_dependency) as archive:
                names = set(archive.namelist())
                self.assertIn(new_name + ".class", names)
                self.assertNotIn(old_name + ".class", names)
                self.assertNotIn("rs/A.class", names)

    def test_java9_eawt_bridge_is_compile_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                plan_path,
                recovered,
                manifest,
                _old_name,
                _new_name,
                _transform,
            ) = self._fixture(root)

            source = recovered / "rs" / "A.java"
            source.write_text(
                "package rs; "
                "import com.apple.eawt.Application; "
                "import com.apple.eawt.FullScreenAdapter; "
                "import com.apple.eawt.FullScreenListener; "
                "import com.apple.eawt.FullScreenUtilities; "
                "import com.apple.eawt.event.FullScreenEvent; "
                "import java.awt.Window; "
                "public class A extends FullScreenAdapter { "
                "public void a(FullScreenEvent event) {} "
                "public static void install(Window window) { "
                "FullScreenUtilities.setWindowCanFullScreen(window, true); "
                "FullScreenUtilities.addFullScreenListenerTo("
                "window, (FullScreenListener)new A()); "
                "Application.getApplication().requestForeground(true); "
                "Application.getApplication().requestUserAttention(true); "
                "} }\n",
                encoding="utf-8",
            )
            manifest = dict(manifest)
            manifest["source_tree_sha256"] = source_tree_digest(
                recovered
            )[0]

            report = compile_collision_derived_source(
                manifest,
                recovered,
                readable,
                plan_path,
                ["rs/"],
                root / "compile-eawt",
                javac_command="javac",
                release=9,
                java9_macos_eawt_compile_bridge=True,
            )

            self.assertEqual(report["status"], "complete")
            self.assertEqual(
                report["compiler"]["classpath_entry_count"],
                2,
            )
            self.assertEqual(
                len(report["compile_only_platform_bridges"]),
                1,
            )
            self.assertFalse(
                report["compile_only_platform_bridges"][0][
                    "runtime_allowed"
                ]
            )
            self.assertFalse(
                report["runtime_platform_bridges_allowed"]
            )
            self.assertFalse(
                any(
                    (root / "compile-eawt" / "restored-classes")
                    .rglob("com/apple/eawt/*.class")
                )
            )

            javac_args = (
                root / "compile-eawt" / "javac.args"
            ).read_text(encoding="utf-8").replace("\\", "/")
            self.assertIn(
                "/java9-macos-eawt-bridge/classes",
                javac_args,
            )
            self.assertNotIn(
                "/java9-macos-eawt-bridge/source/",
                javac_args,
            )

    def test_mapping_commitment_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                plan_path,
                recovered,
                manifest,
                _old_name,
                _new_name,
                _transform,
            ) = self._fixture(root)
            manifest["collision_mapping_sha256"] = "0" * 64

            with self.assertRaisesRegex(
                CollisionDerivedCompileError,
                "collision_mapping_sha256",
            ):
                compile_collision_derived_source(
                    manifest,
                    recovered,
                    readable,
                    plan_path,
                    ["rs/"],
                    root / "compile",
                    javac_command="javac",
                    release=9,
                )

    def test_compile_failure_restores_canonical_diagnostic_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                plan_path,
                recovered,
                manifest,
                _old_name,
                _new_name,
                _transform,
            ) = self._fixture(root)

            bad_source = recovered / "rs" / "A.java"
            bad_source.write_text(
                "package rs; public class A { MissingType value; }\n",
                encoding="utf-8",
            )
            manifest = dict(manifest)
            manifest["source_tree_sha256"] = source_tree_digest(
                recovered
            )[0]

            private_diagnostic = root / "private-diagnostic.json"
            report = compile_collision_derived_source(
                manifest,
                recovered,
                readable,
                plan_path,
                ["rs/"],
                root / "compile-fail",
                javac_command="javac",
                release=9,
                report_compile_failure=True,
                private_diagnostic_report_out=private_diagnostic,
            )

            self.assertEqual(report["status"], "compile_failed")
            self.assertEqual(
                report["compiler"]["source_transport"],
                "case_unique_explicit_inputs",
            )

            diagnostic = json.loads(
                private_diagnostic.read_text(encoding="utf-8")
            )
            source_paths = {
                str(row.get("source_path", "")).replace("\\", "/")
                for row in diagnostic.get("diagnostics", [])
            }
            self.assertIn(
                bad_source.resolve().as_posix(),
                source_paths,
            )
            self.assertFalse(
                any(
                    "/source-inputs/" in path
                    for path in source_paths
                )
            )


    def _clean_rebuild_authorities(
        self,
        manifest,
        transform,
    ):
        manifest = dict(manifest)
        manifest.update(
            {
                "build_id": "v308",
                "source_authority_sha256": "a" * 64,
                "namespace_id": "SEMNS_" + "b" * 20,
            }
        )
        readiness = {
            "schema_version": 1,
            "kind": "source_readiness_report",
            "source_tree_sha256": manifest[
                "source_tree_sha256"
            ],
        }
        readable_manifest = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "status": "complete",
            "verification_pass": True,
            "output_sha256": transform[
                "input_jar_sha256"
            ],
            "project_source_prefixes": ["rs/"],
            "semantic_summary": {
                "source_safety_fallbacks": 0,
            },
        }
        authority = {
            "schema_version": 1,
            "kind": "build_authority_manifest",
            "authority_id": "BUILDAUTH_" + "c" * 20,
            "source_sha256": "a" * 64,
            "compiler_runtime": {
                "javac": _probe_javac("javac"),
            },
            "bytecode": {
                "dominant_java_release": 9,
            },
        }
        return (
            manifest,
            readiness,
            readable_manifest,
            authority,
        )

    def test_clean_rebuild_packages_original_runtime_dependency_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                plan_path,
                recovered,
                manifest,
                old_name,
                new_name,
                transform,
            ) = self._fixture(root)

            (
                manifest,
                readiness,
                readable_manifest,
                authority,
            ) = self._clean_rebuild_authorities(
                manifest,
                transform,
            )

            report = clean_project_rebuild(
                manifest,
                readiness,
                readable_manifest,
                readable,
                authority,
                recovered,
                out_dir=root / "clean",
                source_prefixes=["rs/"],
                private_collision_plan_path=plan_path,
                java9_macos_eawt_compile_bridge=True,
            )

            self.assertEqual(report["status"], "complete")
            self.assertEqual(
                report["compile_transport"]["mode"],
                "collision_derived_remap",
            )
            self.assertFalse(
                report["compile_transport"][
                    "runtime_transformed_dependency_allowed"
                ]
            )
            self.assertFalse(
                report["compile_transport"][
                    "runtime_platform_bridges_allowed"
                ]
            )
            self.assertEqual(
                len(
                    report["compile_transport"][
                        "compile_only_platform_bridges"
                    ]
                ),
                1,
            )
            self.assertEqual(
                report["dependency_capsule"]["source"],
                "verified_base_readable_non_project_classes",
            )

            rebuilt = root / "clean" / "rebuilt-client.jar"
            with zipfile.ZipFile(readable) as original_archive:
                original_blocker = original_archive.read(
                    old_name + ".class"
                )
            with zipfile.ZipFile(rebuilt) as archive:
                names = set(archive.namelist())
                self.assertIn(old_name + ".class", names)
                self.assertIn(
                    "dep/clash/Target.class",
                    names,
                )
                self.assertNotIn(new_name + ".class", names)
                self.assertNotIn(
                    "com/apple/eawt/Application.class",
                    names,
                )
                self.assertEqual(
                    archive.read(old_name + ".class"),
                    original_blocker,
                )
                project_bytes = archive.read("rs/A.class")

            parsed = parse_class(project_bytes)
            descriptors = {
                str(field["descriptor"])
                for field in parsed.fields
            }
            self.assertIn(
                "L" + old_name + ";",
                descriptors,
            )
            self.assertNotIn(
                "L" + new_name + ";",
                descriptors,
            )

    def test_collision_derived_workspace_refuses_namespace_alias_transport(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                _plan_path,
                recovered,
                manifest,
                _old_name,
                _new_name,
                transform,
            ) = self._fixture(root)
            (
                manifest,
                readiness,
                readable_manifest,
                authority,
            ) = self._clean_rebuild_authorities(
                manifest,
                transform,
            )

            with self.assertRaisesRegex(
                CleanRebuildError,
                "matching blocker-remap compile transport",
            ):
                clean_project_rebuild(
                    manifest,
                    readiness,
                    readable_manifest,
                    readable,
                    authority,
                    recovered,
                    out_dir=root / "clean",
                    source_prefixes=["rs/"],
                    auto_namespace_alias=True,
                )

    def test_collision_derived_workspace_requires_private_collision_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                _plan_path,
                recovered,
                manifest,
                _old_name,
                _new_name,
                transform,
            ) = self._fixture(root)
            (
                manifest,
                readiness,
                readable_manifest,
                authority,
            ) = self._clean_rebuild_authorities(
                manifest,
                transform,
            )

            with self.assertRaisesRegex(
                CleanRebuildError,
                "requires an explicit private collision plan path",
            ):
                clean_project_rebuild(
                    manifest,
                    readiness,
                    readable_manifest,
                    readable,
                    authority,
                    recovered,
                    out_dir=root / "clean",
                    source_prefixes=["rs/"],
                )

    def test_derivation_transform_id_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                plan_path,
                recovered,
                manifest,
                _old_name,
                _new_name,
                _transform,
            ) = self._fixture(root)

            manifest["collision_transform_id"] = (
                "JNSREWRITE_" + "0" * 20
            )
            with self.assertRaisesRegex(
                CollisionDerivedCompileError,
                "collision_transform_id",
            ):
                compile_collision_derived_source(
                    manifest,
                    recovered,
                    readable,
                    plan_path,
                    ["rs/"],
                    root / "compile",
                    javac_command="javac",
                    release=9,
                )

    def test_project_blocker_mapping_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                readable,
                plan_path,
                recovered,
                manifest,
                _old_name,
                _new_name,
                _transform,
            ) = self._fixture(root)

            plan = json.loads(
                plan_path.read_text(encoding="utf-8")
            )
            plan["remaps"][0]["old_internal_name"] = "rs/A"
            plan["remaps"][0]["new_internal_name"] = (
                "rs/RecoveredCollision_Test"
            )
            plan_path.write_text(
                json.dumps(plan, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                CollisionDerivedCompileError
            ):
                compile_collision_derived_source(
                    manifest,
                    recovered,
                    readable,
                    plan_path,
                    ["rs/"],
                    root / "compile",
                    javac_command="javac",
                    release=9,
                )


if __name__ == "__main__":
    unittest.main()

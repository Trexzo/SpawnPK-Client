from __future__ import annotations

import hashlib
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
from spk_recovery.progressive_compile import _probe_javac


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha(root: Path) -> str:
    files = sorted(root.rglob("*.java"))
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class CleanRebuildTests(unittest.TestCase):
    def _fixture(self, root: Path):
        dep_src = root / "orig-src" / "dep"
        rs_src = root / "orig-src" / "rs"
        fallback_src = rs_src
        dep_src.mkdir(parents=True)
        rs_src.mkdir(parents=True)
        (dep_src / "Fallback.java").write_text(
            "package dep; public class Fallback { "
            "public String value() { return \"ok\"; } }\n",
            encoding="utf-8",
        )
        (rs_src / "A.java").write_text(
            "package rs; import dep.Fallback; "
            "public class A { public Fallback dep = new Fallback(); }\n",
            encoding="utf-8",
        )
        (rs_src / "B.java").write_text(
            "package rs; public class B { public int value = 1; }\n",
            encoding="utf-8",
        )
        (fallback_src / "Recovered_CLIENT_CLASS_000001.java").write_text(
            "package rs; "
            "public class Recovered_CLIENT_CLASS_000001 { "
            "public int value = 2; }\n",
            encoding="utf-8",
        )

        dep_classes = root / "dep-classes"
        dep_classes.mkdir()
        subprocess.run(
            [
                "javac",
                "-d",
                str(dep_classes),
                str(dep_src / "Fallback.java"),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        project_classes = root / "project-classes"
        project_classes.mkdir()
        subprocess.run(
            [
                "javac",
                "-classpath",
                str(dep_classes),
                "-d",
                str(project_classes),
                str(rs_src / "A.java"),
                str(rs_src / "B.java"),
                str(fallback_src / "Recovered_CLIENT_CLASS_000001.java"),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        readable = root / "readable.jar"
        with zipfile.ZipFile(
            readable,
            "w",
            zipfile.ZIP_STORED,
        ) as z:
            z.writestr(
                "META-INF/MANIFEST.MF",
                "Manifest-Version: 1.0\r\n\r\n",
            )
            z.writestr("rs/resource.txt", "keep me")
            for classes in (dep_classes, project_classes):
                for path in sorted(classes.rglob("*.class")):
                    z.write(
                        path,
                        path.relative_to(classes).as_posix(),
                    )

        recovered_root = root / "recovered"
        (recovered_root / "rs").mkdir(parents=True)
        shutil.copy2(rs_src / "A.java", recovered_root / "rs" / "A.java")
        shutil.copy2(rs_src / "B.java", recovered_root / "rs" / "B.java")
        shutil.copy2(
            fallback_src / "Recovered_CLIENT_CLASS_000001.java",
            recovered_root / "rs" / "Recovered_CLIENT_CLASS_000001.java",
        )
        tree_sha = _tree_sha(recovered_root)
        readable_sha = _sha(readable)

        recovered = {
            "schema_version": 1,
            "kind": "recovered_source_workspace_manifest",
            "workspace_id": "SRCWS_" + "1" * 20,
            "build_id": "v308",
            "source_authority_sha256": "a" * 64,
            "readable_jar_sha256": readable_sha,
            "namespace_id": "SEMNS_" + "2" * 20,
            "class_plan_digest": "c" * 64,
            "member_plan_digest": "d" * 64,
            "engine": "cfr",
            "decompiler_sha256": "e" * 64,
            "source_tree_sha256": tree_sha,
            "java_file_count": 3,
            "source_bytes": sum(
                p.stat().st_size
                for p in recovered_root.rglob("*.java")
            ),
            "source_directory": "src",
        }
        readiness = {
            "schema_version": 1,
            "kind": "source_readiness_report",
            "source_tree_sha256": tree_sha,
        }
        readable_manifest = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "status": "complete",
            "verification_pass": True,
            "output_sha256": readable_sha,
            "target_package": "recovered/spawnpk/client",
            "source_safe_fallback": True,
            "fallback_name_prefix": "Recovered_",
            "project_source_prefixes": [
                "recovered/spawnpk/client/",
                "rs/",
            ],
            "semantic_summary": {
                "source_safety_fallbacks": 1,
            },
        }
        authority = {
            "schema_version": 1,
            "kind": "build_authority_manifest",
            "authority_id": "BUILDAUTH_" + "3" * 20,
            "source_sha256": "a" * 64,
            "compiler_runtime": {
                "javac": _probe_javac("javac"),
            },
            "bytecode": {
                "dominant_java_release": None,
            },
        }
        return (
            recovered_root,
            readable,
            recovered,
            readiness,
            readable_manifest,
            authority,
        )

    def test_project_rebuild_has_zero_project_binary_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                source,
                readable,
                recovered,
                readiness,
                readable_manifest,
                authority,
            ) = self._fixture(root)

            report = clean_project_rebuild(
                recovered,
                readiness,
                readable_manifest,
                readable,
                authority,
                source,
                out_dir=root / "out",
                source_prefixes=["rs/"],
            )

            self.assertEqual(report["status"], "complete")
            self.assertTrue(report["clean_project_build"])
            self.assertEqual(
                report["project_classes"]["binary_fallback_count"],
                0,
            )
            self.assertEqual(
                report["project_classes"]["expected_count"],
                3,
            )
            self.assertEqual(
                report["project_classes"]["generated_count"],
                3,
            )
            self.assertFalse(
                report["all_dependencies_rebuilt_from_source"]
            )

            capsule = root / "out" / "dependency-capsule.jar"
            rebuilt = root / "out" / "rebuilt-client.jar"
            with zipfile.ZipFile(capsule) as z:
                names = set(z.namelist())
                self.assertIn("dep/Fallback.class", names)
                self.assertNotIn("rs/A.class", names)
                self.assertNotIn("rs/B.class", names)
                self.assertNotIn(
                    "rs/Recovered_CLIENT_CLASS_000001.class",
                    names,
                )

            with zipfile.ZipFile(rebuilt) as z:
                names = set(z.namelist())
                self.assertIn("dep/Fallback.class", names)
                self.assertIn("rs/A.class", names)
                self.assertIn("rs/B.class", names)
                self.assertIn(
                    "rs/Recovered_CLIENT_CLASS_000001.class",
                    names,
                )
                self.assertIn("rs/resource.txt", names)


    def test_default_project_prefixes_rebuild_fallback_class(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                source,
                readable,
                recovered,
                readiness,
                readable_manifest,
                authority,
            ) = self._fixture(root)

            report = clean_project_rebuild(
                recovered,
                readiness,
                readable_manifest,
                readable,
                authority,
                source,
                out_dir=root / "out",
            )

            self.assertEqual(report["status"], "complete")
            self.assertEqual(
                report["project_classes"]["expected_count"],
                3,
            )
            self.assertEqual(
                report["project_classes"]["generated_count"],
                3,
            )
            self.assertEqual(
                report["project_classes"]["binary_fallback_count"],
                0,
            )

            fallback_class = "rs/Recovered_CLIENT_CLASS_000001.class"
            with zipfile.ZipFile(
                root / "out" / "dependency-capsule.jar"
            ) as z:
                self.assertNotIn(fallback_class, set(z.namelist()))
            with zipfile.ZipFile(
                root / "out" / "rebuilt-client.jar"
            ) as z:
                self.assertIn(fallback_class, set(z.namelist()))

    def test_compile_failure_embeds_redacted_javac_classification(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                source,
                readable,
                recovered,
                readiness,
                readable_manifest,
                authority,
            ) = self._fixture(root)

            target = source / "rs" / "A.java"
            target.write_text(
                "package rs; public class A { "
                "public int value() { return missingValue; } }\n",
                encoding="utf-8",
            )
            tree_sha = _tree_sha(source)
            recovered["source_tree_sha256"] = tree_sha
            readiness["source_tree_sha256"] = tree_sha

            report = clean_project_rebuild(
                recovered,
                readiness,
                readable_manifest,
                readable,
                authority,
                source,
                out_dir=root / "out",
                source_prefixes=["rs/"],
            )

            self.assertEqual(report["status"], "compile_failed")
            self.assertEqual(
                report["project_classes"]["binary_fallback_count"],
                0,
            )
            classified = report["compiler"]["diagnostic_classification"]
            self.assertIsNotNone(classified)
            self.assertFalse(classified["identifiers_included"])
            self.assertTrue(
                classified["report_id"].startswith("JAVACDIAG_")
            )
            self.assertEqual(
                classified["summary"]["cannot_find_symbol"]["count"],
                1,
            )
            serialized = str(classified)
            self.assertNotIn("missingValue", serialized)
            self.assertNotIn(str(target), serialized)

    def test_cleanbuild_id_is_independent_of_diagnostic_absolute_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                source,
                readable,
                recovered,
                readiness,
                readable_manifest,
                authority,
            ) = self._fixture(root)

            failing = (
                "package rs; public class A { "
                "public int value() { return missingValue; } }\n"
            )
            (source / "rs" / "A.java").write_text(
                failing,
                encoding="utf-8",
            )
            tree_sha = _tree_sha(source)
            recovered["source_tree_sha256"] = tree_sha
            readiness["source_tree_sha256"] = tree_sha

            source2 = root / "other-absolute-source-root"
            shutil.copytree(source, source2)

            first = clean_project_rebuild(
                recovered,
                readiness,
                readable_manifest,
                readable,
                authority,
                source,
                out_dir=root / "out-1",
                source_prefixes=["rs/"],
            )
            second = clean_project_rebuild(
                recovered,
                readiness,
                readable_manifest,
                readable,
                authority,
                source2,
                out_dir=root / "out-2",
                source_prefixes=["rs/"],
            )

            self.assertEqual(first["status"], "compile_failed")
            self.assertEqual(second["status"], "compile_failed")
            self.assertEqual(first["rebuild_id"], second["rebuild_id"])
            self.assertNotEqual(
                first["compiler"]["diagnostic_classification"][
                    "input_sha256"
                ],
                second["compiler"]["diagnostic_classification"][
                    "input_sha256"
                ],
            )

    def test_old_fallback_manifest_without_project_prefixes_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                source,
                readable,
                recovered,
                readiness,
                readable_manifest,
                authority,
            ) = self._fixture(root)
            readable_manifest.pop("project_source_prefixes")

            with self.assertRaises(CleanRebuildError):
                clean_project_rebuild(
                    recovered,
                    readiness,
                    readable_manifest,
                    readable,
                    authority,
                    source,
                    out_dir=root / "out",
                )



if __name__ == "__main__":
    unittest.main()

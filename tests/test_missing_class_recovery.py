from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from spk_recovery.javac_diagnostics import classify_javac_diagnostics
from spk_recovery.missing_class_recovery import (
    MissingClassRecoveryError,
    build_missing_class_recovery_plan,
    stage_missing_class_recovery,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class MissingClassRecoveryTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        dependency_candidate: bool = False,
    ):
        src = root / "src"
        rs = src / "rs"
        dep = src / "dep"
        rs.mkdir(parents=True)
        dep.mkdir(parents=True)

        use = rs / "Use.java"
        use.write_text(
            (
                "package rs;\n"
                "import dep.Missing;\n"
                "public class Use {}\n"
            )
            if dependency_candidate
            else "package rs; public class Use {}\n",
            encoding="utf-8",
        )

        missing = (
            dep / "Missing.java"
            if dependency_candidate
            else rs / "Missing.java"
        )
        missing.write_text(
            (
                "package dep; public class Missing {}\n"
                if dependency_candidate
                else "package rs; public class Missing {}\n"
            ),
            encoding="utf-8",
        )

        classes = root / "classes"
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "-d",
                str(classes),
                str(use),
                str(missing),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        jar = root / "readable.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for path in sorted(classes.rglob("*.class")):
                z.write(
                    path,
                    path.relative_to(classes).as_posix(),
                )

        missing.unlink()

        raw = (
            f"{use}:2: error: cannot find symbol\n"
            "  symbol:   class Missing\n"
            "  location: class Use\n"
        )
        diagnostic = classify_javac_diagnostics(
            raw,
            include_identifiers=True,
        )
        manifest = {
            "schema_version": 1,
            "kind": "readable_client_build_manifest",
            "status": "complete",
            "verification_pass": True,
            "output_sha256": _sha(jar),
            "source_sha256": "a" * 64,
            "namespace_id": "SEMNS_TEST",
            "class_plan_digest": "b" * 64,
            "member_plan_digest": "c" * 64,
            "build_id": "v308",
            "project_source_prefixes": ["rs/"],
        }
        return src, use, missing, jar, diagnostic, manifest

    def test_plan_binds_one_project_missing_class(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                src,
                _use,
                _missing,
                jar,
                diagnostic,
                manifest,
            ) = self._fixture(root)

            public = build_missing_class_recovery_plan(
                diagnostic,
                manifest,
                jar,
                src,
                expected_candidate_count=1,
            )
            private = build_missing_class_recovery_plan(
                diagnostic,
                manifest,
                jar,
                src,
                expected_candidate_count=1,
                include_identifiers=True,
            )

            self.assertEqual(public["plan_id"], private["plan_id"])
            self.assertEqual(
                public["summary"],
                {
                    "candidate_count": 1,
                    "project_candidate_count": 1,
                    "nonproject_candidate_count": 0,
                    "target_states": {"absent": 1},
                    "kinds": {"class": 1},
                    "synthetic_count": 0,
                    "diagnostic_count": 1,
                },
            )
            self.assertFalse(public["identifiers_included"])
            self.assertTrue(private["identifiers_included"])
            self.assertEqual(
                private["candidates"][0]["internal_name"],
                "rs/Missing",
            )
            self.assertEqual(
                private["candidates"][0]["expected_target_path"],
                "rs/Missing.java",
            )
            self.assertNotIn("rs/Missing", json.dumps(public))

    def test_plan_detects_occupied_mismaterialized_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                src,
                _use,
                missing,
                jar,
                diagnostic,
                manifest,
            ) = self._fixture(root)

            missing.write_text(
                "package rs; class Different {}\n",
                encoding="utf-8",
            )

            plan = build_missing_class_recovery_plan(
                diagnostic,
                manifest,
                jar,
                src,
                expected_candidate_count=1,
                include_identifiers=True,
            )
            self.assertEqual(
                plan["summary"]["target_states"],
                {"occupied_missing_exact_declaration": 1},
            )
            self.assertIsNotNone(
                plan["candidates"][0]["target_sha256"]
            )

    def test_plan_marks_nonproject_dependency_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                src,
                _use,
                _missing,
                jar,
                diagnostic,
                manifest,
            ) = self._fixture(
                root,
                dependency_candidate=True,
            )

            plan = build_missing_class_recovery_plan(
                diagnostic,
                manifest,
                jar,
                src,
                expected_candidate_count=1,
            )
            self.assertEqual(
                plan["summary"]["project_candidate_count"],
                0,
            )
            self.assertEqual(
                plan["summary"]["nonproject_candidate_count"],
                1,
            )

            with self.assertRaisesRegex(
                MissingClassRecoveryError,
                "non-project candidates",
            ):
                stage_missing_class_recovery(
                    diagnostic,
                    manifest,
                    jar,
                    src,
                    root / "procyon.jar",
                    expected_decompiler_sha256="d" * 64,
                    stage_dir=root / "stage",
                    expected_candidate_count=1,
                )

    def test_stage_uses_full_context_but_only_candidate_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                src,
                _use,
                _missing,
                jar,
                diagnostic,
                manifest,
            ) = self._fixture(root)

            tool = root / "procyon.jar"
            tool.write_bytes(b"tool")

            def fake_decompiler(
                input_jar,
                decompiler_jar,
                **kwargs,
            ):
                selected = kwargs["input_class_files"]
                self.assertEqual(len(selected), 1)
                self.assertEqual(
                    selected[0].name,
                    "Missing.class",
                )

                context = selected[0].parents[1]
                self.assertTrue(
                    (context / "rs" / "Use.class").is_file()
                )
                self.assertTrue(
                    (context / "rs" / "Missing.class").is_file()
                )

                out = kwargs["out_dir"]
                target = out / "rs" / "Missing.java"
                target.parent.mkdir(parents=True)
                target.write_text(
                    "package rs; public class Missing {}\n",
                    encoding="utf-8",
                )
                return {
                    "schema_version": 1,
                    "kind": "decompiler_result",
                    "engine": "procyon",
                    "input_sha256": _sha(jar),
                    "decompiler_sha256": "d" * 64,
                    "java_file_count": 1,
                    "output_directory": str(out),
                    "input_mode": "class_files",
                    "selected_class_file_count": 1,
                    "batch_count": 1,
                    "stdout": "",
                    "stderr": "",
                }

            fake_norm = {
                "schema_version": 1,
                "kind": "source_normalization_report",
                "normalization_id": "SRCNORM_TEST",
                "summary": {
                    "action_count": 0,
                },
            }

            with (
                patch(
                    "spk_recovery.missing_class_recovery."
                    "run_decompiler",
                    side_effect=fake_decompiler,
                ),
                patch(
                    "spk_recovery.missing_class_recovery."
                    "normalize_procyon_source",
                    return_value=fake_norm,
                ),
            ):
                report = stage_missing_class_recovery(
                    diagnostic,
                    manifest,
                    jar,
                    src,
                    tool,
                    expected_decompiler_sha256="d" * 64,
                    stage_dir=root / "stage",
                    expected_candidate_count=1,
                )

            self.assertEqual(
                report["summary"]["candidate_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["materialized_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["java_file_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["decompiler_batch_count"],
                1,
            )
            self.assertFalse(report["identifiers_included"])


if __name__ == "__main__":
    unittest.main()

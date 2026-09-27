from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.r8q_source_entry_gate_cli import main


@unittest.skipUnless(shutil.which("javac"), "javac required")
class R8QSourceEntryGateCliTests(unittest.TestCase):
    def test_exact_gate_binds_authorities_and_writes_public_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            src = root / "src" / "dep"
            src.mkdir(parents=True)
            source = src / "Fallback.java"
            source.write_text(
                "package dep; public class Fallback {}\n",
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
            self.assertEqual(
                proc.returncode,
                0,
                proc.stdout + proc.stderr,
            )

            entry = "dep/Fallback.class"
            data = (classes / entry).read_bytes()

            readable = root / "readable.jar"
            capsule = root / "dependency-capsule.jar"
            for jar in (readable, capsule):
                with zipfile.ZipFile(
                    jar,
                    "w",
                    zipfile.ZIP_STORED,
                ) as z:
                    z.writestr(entry, data)

            plan_id = "JCLASSPLAN_" + "4" * 20
            plan = {
                "schema_version": 1,
                "kind": "javac_missing_class_recovery_plan",
                "plan_id": plan_id,
                "identifiers_included": True,
                "candidates": [
                    {
                        "candidate_id": "JCLASSMISS_001",
                        "candidate_internal_name": "dep/Fallback",
                    }
                ],
            }
            plan_path = root / "private-plan.json"
            plan_path.write_text(
                json.dumps(plan, indent=2) + "\n",
                encoding="utf-8",
            )

            def sha(path: Path) -> str:
                return hashlib.sha256(path.read_bytes()).hexdigest()

            out = root / "audit.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = main(
                    [
                        str(plan_path),
                        str(readable),
                        str(capsule),
                        "--javac-command",
                        "javac",
                        "--release",
                        "9",
                        "--expected-plan-id",
                        plan_id,
                        "--expected-readable-sha256",
                        sha(readable),
                        "--expected-capsule-sha256",
                        sha(capsule),
                        "--expected-candidates",
                        "1",
                        "--out",
                        str(out),
                    ]
                )

            self.assertEqual(rc, 0)
            self.assertTrue(out.is_file())

            text = stdout.getvalue()
            self.assertIn(
                "R8Q_EXACT_SOURCE_ENTRY_GATE_PASS",
                text,
            )
            self.assertIn(
                "default_package_count=0",
                text,
            )
            self.assertIn(
                "javap_resolved_count=1",
                text,
            )

            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(report["identifiers_included"])
            self.assertEqual(
                report["summary"]["candidate_count"],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "source_form_target_loaded_counts"
                ]["qualified_type"]["capsule_release"],
                1,
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_source_binding import (
    bind_dependency_source_references,
)
from spk_recovery.dependency_source_edit_plan import (
    build_dependency_source_edit_plan,
)
from spk_recovery.dependency_source_overlay import (
    apply_dependency_source_overlay,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
@unittest.skipUnless(shutil.which("java"), "java required")
class DependencySourceOverlayTests(unittest.TestCase):
    def _compile(
        self,
        sources: list[Path],
        out: Path,
    ) -> None:
        out.mkdir(parents=True)
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(out),
                *map(str, sources),
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

    def test_end_to_end_overlay_rewrites_class_method_and_method_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            old_src = root / "old-src" / "old"
            old_src.mkdir(parents=True)
            old_java = old_src / "A.java"
            old_java.write_text(
                """
package old;
public class A {
    public A() {}
    public String x() { return "old"; }
}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            old_classes = root / "old-classes"
            self._compile([old_java], old_classes)

            new_src = root / "new-src" / "newpkg"
            new_src.mkdir(parents=True)
            new_java = new_src / "A.java"
            new_java.write_text(
                """
package newpkg;
public class A {
    public A() {}
    public String run() { return "new"; }
}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            new_classes = root / "new-classes"
            self._compile([new_java], new_classes)

            bundled = root / "bundled.jar"
            with zipfile.ZipFile(
                bundled,
                "w",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr(
                    "old/A.class",
                    (old_classes / "old" / "A.class").read_bytes(),
                )

            official = root / "official.jar"
            with zipfile.ZipFile(
                official,
                "w",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr(
                    "newpkg/A.class",
                    (
                        new_classes
                        / "newpkg"
                        / "A.class"
                    ).read_bytes(),
                )

            source_root = root / "source"
            app = source_root / "app"
            app.mkdir(parents=True)
            use = app / "Use.java"
            original_text = """
package app;

import old.A;
import java.util.function.Supplier;

public class Use {
    private final A value = new A();

    public String call() {
        return value.x();
    }

    public Supplier<String> reference() {
        return value::x;
    }
}
""".strip() + "\n"
            use.write_text(
                original_text,
                encoding="utf-8",
            )

            bundled_sha = hashlib.sha256(
                bundled.read_bytes()
            ).hexdigest()
            official_sha = hashlib.sha256(
                official.read_bytes()
            ).hexdigest()
            artifact_rows = [
                {
                    "artifact": "official.jar",
                    "sha256": official_sha,
                    "multi_release_class_count": 0,
                    "java_release": 9,
                }
            ]

            remap = {
                "schema_version": 1,
                "kind": "dependency_structural_remap_proof",
                "dependency_remap_proof_id": (
                    "DEPREMAP_" + "A" * 20
                ),
                "reference_surface_id": (
                    "DEPREF_" + "B" * 20
                ),
                "bundled_jar_sha256": bundled_sha,
                "java_release": 9,
                "project_prefixes": ["app/"],
                "official_artifacts": artifact_rows,
                "member_results": [
                    {
                        "kind": "method",
                        "old_owner": "old/A",
                        "old_name": "<init>",
                        "old_descriptor": "()V",
                        "reference_count": 1,
                        "status": "accepted_remap",
                        "new_owner": "newpkg/A",
                        "new_name": "<init>",
                        "new_descriptor": "()V",
                        "artifact": "official.jar",
                    },
                    {
                        "kind": "method",
                        "old_owner": "old/A",
                        "old_name": "x",
                        "old_descriptor": (
                            "()Ljava/lang/String;"
                        ),
                        "reference_count": 2,
                        "status": "accepted_remap",
                        "new_owner": "newpkg/A",
                        "new_name": "run",
                        "new_descriptor": (
                            "()Ljava/lang/String;"
                        ),
                        "artifact": "official.jar",
                    },
                ],
            }
            remap_path = root / "depremap.json"
            remap_path.write_text(
                json.dumps(remap, indent=2) + "\n",
                encoding="utf-8",
            )

            replacement = {
                "schema_version": 1,
                "kind": "dependency_replacement_boundary_plan",
                "replacement_plan_id": (
                    "DEPREPLACE_" + "C" * 20
                ),
                "reference_surface_id": remap[
                    "reference_surface_id"
                ],
                "dependency_remap_proof_id": remap[
                    "dependency_remap_proof_id"
                ],
                "retention_report_id": None,
                "bundled_jar_sha256": bundled_sha,
                "java_release": 9,
                "project_prefixes": ["app/"],
                "official_artifact_set_sha256": "D" * 64,
                "summary": {},
                "artifact_usage": {},
                "owners": [
                    {
                        "owner_id": "DEPOWNER_00001",
                        "classification": "official_replaceable",
                        "old_owner": "old/A",
                        "new_owner": "newpkg/A",
                        "artifact": "official.jar",
                    }
                ],
                "identifiers_included": True,
                "official_artifacts": artifact_rows,
                "artifact_ids": {
                    "official.jar": "DEPARTIFACT_0001"
                },
            }
            replacement_path = root / "depreplace.json"
            replacement_path.write_text(
                json.dumps(replacement, indent=2) + "\n",
                encoding="utf-8",
            )

            binding = bind_dependency_source_references(
                source_root,
                remap_path,
                replacement_path,
                bundled,
                [official],
                include_identifiers=True,
            )
            self.assertEqual(
                binding["summary"][
                    "javac_diagnostic_error_count"
                ],
                0,
            )
            self.assertTrue(
                any(
                    row["syntax_kind"]
                    == "member_reference"
                    and row["old_name"] == "x"
                    and row["match_status"]
                    == "exact_approved_member"
                    for row in binding["bindings"]
                )
            )

            binding_path = root / "binding.json"
            binding_path.write_text(
                json.dumps(binding, indent=2) + "\n",
                encoding="utf-8",
            )

            edit_plan = build_dependency_source_edit_plan(
                binding_path,
                remap_path,
                replacement_path,
                include_identifiers=True,
            )
            self.assertTrue(
                edit_plan["summary"][
                    "ready_for_source_overlay"
                ]
            )
            self.assertGreater(
                edit_plan["summary"][
                    "class_type_rename_required_count"
                ],
                0,
            )
            self.assertEqual(
                edit_plan["summary"][
                    "member_name_rename_required_count"
                ],
                2,
            )

            edit_path = root / "edit-plan.json"
            edit_path.write_text(
                json.dumps(edit_plan, indent=2) + "\n",
                encoding="utf-8",
            )

            out = root / "overlay"
            manifest = apply_dependency_source_overlay(
                source_root,
                edit_path,
                replacement_path,
                bundled,
                [official],
                out_dir=out,
            )

            self.assertEqual(
                use.read_text(encoding="utf-8"),
                original_text,
            )
            rewritten = (
                out / "src" / "app" / "Use.java"
            ).read_text(encoding="utf-8")
            self.assertIn("newpkg.A", rewritten)
            self.assertIn(".run()", rewritten)
            self.assertIn("::run", rewritten)
            self.assertNotIn("old.A", rewritten)
            self.assertNotIn(".x()", rewritten)
            self.assertNotIn("::x", rewritten)

            self.assertTrue(
                manifest["summary"][
                    "canonical_input_unchanged"
                ]
            )
            self.assertEqual(
                manifest["summary"][
                    "pre_diagnostic_error_count"
                ],
                0,
            )
            self.assertEqual(
                manifest["summary"][
                    "post_diagnostic_error_count"
                ],
                0,
            )
            self.assertGreater(
                manifest["summary"]["direct_edit_count"],
                2,
            )


if __name__ == "__main__":
    unittest.main()

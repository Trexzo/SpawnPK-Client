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


@unittest.skipUnless(shutil.which("javac"), "javac required")
@unittest.skipUnless(shutil.which("java"), "java required")
class DependencySourceBindingTests(unittest.TestCase):
    def _fixture(self, root: Path):
        dep_src = root / "dep-src" / "dep"
        dep_src.mkdir(parents=True)

        (dep_src / "A.java").write_text(
            """
package dep;
public class A {
    public int[] values = new int[0];
    public A() {}
    public String x(int n, String[] values) {
        return values.length == n ? "" : "x";
    }
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        (dep_src / "B.java").write_text(
            "package dep; public class B {}\n",
            encoding="utf-8",
        )

        classes = root / "dep-classes"
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(classes),
                str(dep_src / "A.java"),
                str(dep_src / "B.java"),
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

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for name in ("A", "B"):
                archive.writestr(
                    f"dep/{name}.class",
                    (
                        classes
                        / "dep"
                        / f"{name}.class"
                    ).read_bytes(),
                )

        official = root / "official.jar"
        with zipfile.ZipFile(
            official,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr(
                "dep/A.class",
                (classes / "dep" / "A.class").read_bytes(),
            )

        source = root / "source" / "app"
        source.mkdir(parents=True)
        (source / "Use.java").write_text(
            """
package app;

import dep.A;
import dep.B;
import java.util.List;

public class Use {
    private final A a = new A();
    private B b;
    private List<String> list;

    public int[] fieldUse() {
        return a.values;
    }

    public String methodUse() {
        return a.x(1, new String[] {"a"});
    }
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        source_root = root / "source"

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

        remap_id = "DEPREMAP_" + "A" * 20
        remap = {
            "schema_version": 1,
            "kind": "dependency_structural_remap_proof",
            "dependency_remap_proof_id": remap_id,
            "reference_surface_id": "DEPREF_" + "B" * 20,
            "bundled_jar_sha256": bundled_sha,
            "java_release": 9,
            "project_prefixes": ["app/"],
            "official_artifacts": artifact_rows,
            "member_results": [
                {
                    "kind": "method",
                    "old_owner": "dep/A",
                    "old_name": "<init>",
                    "old_descriptor": "()V",
                    "reference_count": 1,
                    "status": "accepted_identity",
                    "new_owner": "dep/A",
                    "new_name": "<init>",
                    "new_descriptor": "()V",
                    "artifact": "official.jar",
                },
                {
                    "kind": "field",
                    "old_owner": "dep/A",
                    "old_name": "values",
                    "old_descriptor": "[I",
                    "reference_count": 1,
                    "status": "accepted_identity",
                    "new_owner": "dep/A",
                    "new_name": "values",
                    "new_descriptor": "[I",
                    "artifact": "official.jar",
                },
                {
                    "kind": "method",
                    "old_owner": "dep/A",
                    "old_name": "x",
                    "old_descriptor": (
                        "(I[Ljava/lang/String;)"
                        "Ljava/lang/String;"
                    ),
                    "reference_count": 1,
                    "status": "accepted_identity",
                    "new_owner": "dep/A",
                    "new_name": "x",
                    "new_descriptor": (
                        "(I[Ljava/lang/String;)"
                        "Ljava/lang/String;"
                    ),
                    "artifact": "official.jar",
                },
                {
                    "kind": "method",
                    "old_owner": "java/util/List",
                    "old_name": "size",
                    "old_descriptor": "()I",
                    "reference_count": 0,
                    "status": "platform_runtime",
                    "new_owner": None,
                    "new_name": None,
                    "new_descriptor": None,
                    "artifact": None,
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
            "replacement_plan_id": "DEPREPLACE_" + "C" * 20,
            "reference_surface_id": remap["reference_surface_id"],
            "dependency_remap_proof_id": remap_id,
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
                    "old_owner": "dep/A",
                    "new_owner": "dep/A",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "residual_bundled",
                    "old_owner": "dep/B",
                    "new_owner": None,
                    "artifact": None,
                },
                {
                    "owner_id": "DEPOWNER_00003",
                    "classification": "platform_runtime",
                    "old_owner": "java/util/List",
                    "new_owner": None,
                    "artifact": None,
                },
            ],
            "identifiers_included": True,
            "official_artifacts": artifact_rows,
            "artifact_ids": {
                "official.jar": "DEPARTIFACT_0001"
            },
        }
        replacement_path = root / "depreplace-private.json"
        replacement_path.write_text(
            json.dumps(replacement, indent=2) + "\n",
            encoding="utf-8",
        )

        return (
            source_root,
            remap_path,
            replacement_path,
            bundled,
            official,
        )

    def test_binds_exact_classes_fields_methods_and_constructor(self):
        with tempfile.TemporaryDirectory() as td:
            (
                source,
                remap,
                replacement,
                bundled,
                official,
            ) = self._fixture(Path(td))

            report = bind_dependency_source_references(
                source,
                remap,
                replacement,
                bundled,
                [official],
                include_identifiers=True,
            )

            rows = report["bindings"]

            exact_classes = [
                row
                for row in rows
                if (
                    row["old_owner"] == "dep/A"
                    and row["element_kind"] == "class"
                    and row["match_status"]
                    == "exact_approved_class"
                )
            ]
            self.assertTrue(exact_classes)

            constructor = [
                row
                for row in rows
                if (
                    row["old_owner"] == "dep/A"
                    and row["old_name"] == "<init>"
                    and row["old_descriptor"] == "()V"
                    and row["match_status"]
                    == "exact_approved_member"
                )
            ]
            self.assertEqual(len(constructor), 1)

            fields = [
                row
                for row in rows
                if (
                    row["old_owner"] == "dep/A"
                    and row["old_name"] == "values"
                    and row["old_descriptor"] == "[I"
                    and row["match_status"]
                    == "exact_approved_member"
                )
            ]
            self.assertEqual(len(fields), 1)

            methods = [
                row
                for row in rows
                if (
                    row["old_owner"] == "dep/A"
                    and row["old_name"] == "x"
                    and row["old_descriptor"]
                    == "(I[Ljava/lang/String;)Ljava/lang/String;"
                    and row["match_status"]
                    == "exact_approved_member"
                )
            ]
            self.assertEqual(len(methods), 1)

            residual = [
                row
                for row in rows
                if (
                    row["old_owner"] == "dep/B"
                    and row["match_status"]
                    == "non_replaceable_owner"
                )
            ]
            self.assertTrue(residual)

            platform = [
                row
                for row in rows
                if (
                    row["old_owner"] == "java/util/List"
                    and row["match_status"]
                    == "non_replaceable_owner"
                )
            ]
            self.assertTrue(platform)

            self.assertEqual(
                report["summary"]["javac_diagnostic_error_count"],
                0,
            )
            self.assertGreater(
                report["summary"]["exact_approved_binding_count"],
                3,
            )

    def test_public_private_authority_matches_and_redacts(self):
        with tempfile.TemporaryDirectory() as td:
            (
                source,
                remap,
                replacement,
                bundled,
                official,
            ) = self._fixture(Path(td))

            public = bind_dependency_source_references(
                source,
                remap,
                replacement,
                bundled,
                [official],
            )
            private = bind_dependency_source_references(
                source,
                remap,
                replacement,
                bundled,
                [official],
                include_identifiers=True,
            )

            self.assertEqual(
                public["binding_inventory_id"],
                private["binding_inventory_id"],
            )
            encoded_public = json.dumps(public)
            self.assertNotIn("dep/A", encoded_public)
            self.assertNotIn("dep/B", encoded_public)
            self.assertNotIn("Use.java", encoded_public)
            self.assertNotIn("official.jar", encoded_public)
            self.assertIn("dep/A", json.dumps(private))
            self.assertIn("Use.java", json.dumps(private))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_runtime_dynamic import (
    build_dependency_runtime_dynamic_inventory,
)
from spk_recovery.dependency_runtime_dynamic_target import (
    DependencyRuntimeDynamicTargetError,
    build_dependency_runtime_dynamic_target_classification,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyRuntimeDynamicTargetTests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict:
        src = root / "src"
        (src / "rs" / "pkg").mkdir(parents=True)
        (src / "dep").mkdir(parents=True)

        for name in (
            "Replaceable",
            "Residual",
            "Unclassified",
            "VersionOnly",
        ):
            (src / "dep" / f"{name}.java").write_text(
                f"package dep; public class {name} {{}}\n",
                encoding="utf-8",
            )

        (src / "rs" / "pkg" / "DynamicTargets.java").write_text(
            """
package rs.pkg;

import java.net.URL;
import java.util.ServiceLoader;

public class DynamicTargets {
    public void replaceable() throws Exception {
        Class.forName("dep.Replaceable");
    }

    public void residual() throws Exception {
        Class.forName("dep.Residual");
    }

    public void unclassified() throws Exception {
        Class.forName("dep.Unclassified");
    }

    public void projectTarget() throws Exception {
        Class.forName("rs.Client");
    }

    public void platformTarget() throws Exception {
        Class.forName("java.lang.String");
    }

    public void versionOnly() throws Exception {
        Class.forName("dep.VersionOnly");
    }

    public void malformed() throws Exception {
        Class.forName("bad/name");
    }

    public void serviceTarget() {
        ServiceLoader.load(dep.Residual.class);
    }

    public URL absoluteResource() {
        return DynamicTargets.class.getResource("/config/exact.txt");
    }

    public URL relativeResource() {
        return DynamicTargets.class.getResource("rel.txt");
    }

    public URL loaderLeadingSlash() {
        return ClassLoader.getSystemClassLoader().getResource("/leading.txt");
    }

    public void nativeTarget() {
        System.loadLibrary("lwjgl");
    }

    public void unresolved(String name) throws Exception {
        Class.forName(name);
    }
}
""".strip()
            + "\n",
            encoding="utf-8",
        )

        classes = root / "classes"
        classes.mkdir()
        sources = sorted(str(path) for path in src.rglob("*.java"))
        proc = subprocess.run(
            [
                "javac",
                "--release",
                "9",
                "-d",
                str(classes),
                *sources,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for internal in (
                "dep/Replaceable",
                "dep/Residual",
                "dep/Unclassified",
                "rs/pkg/DynamicTargets",
            ):
                archive.write(
                    classes / (internal + ".class"),
                    internal + ".class",
                )
            archive.write(
                classes / "dep" / "VersionOnly.class",
                "META-INF/versions/9/dep/VersionOnly.class",
            )
            archive.writestr("rs/pkg/rel.txt", b"rel")
            archive.writestr("config/exact.txt", b"exact")

        bundled_sha = _sha(bundled)

        replacement = {
            "schema_version": 1,
            "kind": "dependency_replacement_boundary_plan",
            "replacement_plan_id": "DEPREPLACE_" + "1" * 20,
            "bundled_jar_sha256": bundled_sha,
            "project_prefixes": ["rs/"],
            "owners": [
                {
                    "owner_id": "DEPOWNER_00001",
                    "classification": "official_replaceable",
                    "old_owner": "dep/Replaceable",
                    "new_owner": "official/Replaceable",
                    "artifact": "official.jar",
                },
                {
                    "owner_id": "DEPOWNER_00002",
                    "classification": "residual_bundled",
                    "old_owner": "dep/Residual",
                    "new_owner": None,
                    "artifact": None,
                },
            ],
            "identifiers_included": True,
        }
        replacement_path = root / "replacement.json"
        replacement_path.write_text(
            json.dumps(replacement, indent=2) + "\n",
            encoding="utf-8",
        )

        resource_id = "DEPRUNTIMERESOURCE_" + "2" * 20
        resource = {
            "schema_version": 1,
            "kind": "dependency_runtime_resource_equivalence",
            "runtime_resource_id": resource_id,
            "bundled_jar_sha256": bundled_sha,
            "resources": [
                {
                    "resource_id": "DEPRUNTIME_RESOURCE_00001",
                    "entry": "config/exact.txt",
                    "status": "exact_byte_match",
                },
                {
                    "resource_id": "DEPRUNTIME_RESOURCE_00002",
                    "entry": "config/bad.txt",
                    "status": "byte_mismatch",
                },
            ],
            "identifiers_included": True,
        }
        resource_path = root / "resource.json"
        resource_path.write_text(
            json.dumps(resource, indent=2) + "\n",
            encoding="utf-8",
        )

        dynamic = build_dependency_runtime_dynamic_inventory(
            resource_path,
            bundled,
            include_identifiers=True,
        )
        dynamic_path = root / "dynamic.json"
        dynamic_path.write_text(
            json.dumps(dynamic, indent=2) + "\n",
            encoding="utf-8",
        )

        return {
            "bundled": bundled,
            "replacement": replacement_path,
            "resource": resource_path,
            "resource_report": resource,
            "dynamic": dynamic_path,
            "dynamic_report": dynamic,
        }

    def _build(self, fx: dict, *, private: bool = False):
        return build_dependency_runtime_dynamic_target_classification(
            fx["dynamic"],
            fx["replacement"],
            fx["resource"],
            fx["bundled"],
            include_identifiers=private,
        )

    def test_classifies_proven_class_targets(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = self._build(fx)
            counts = report["summary"]["classification_counts"]

            self.assertEqual(
                counts["dependency_official_replaceable"],
                1,
            )
            self.assertEqual(
                counts["dependency_residual_bundled"],
                1,
            )
            self.assertEqual(
                counts["bundled_unclassified"],
                1,
            )
            self.assertEqual(counts["project_class"], 1)
            self.assertEqual(counts["platform_runtime"], 1)
            self.assertEqual(
                counts["bundled_multi_release_unresolved"],
                1,
            )
            self.assertEqual(
                counts["class_target_malformed"],
                1,
            )

    def test_classifies_service_resource_native_and_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = self._build(fx)
            counts = report["summary"]["classification_counts"]

            self.assertEqual(
                counts["service_dependency_residual_bundled"],
                1,
            )
            self.assertEqual(
                counts["resource_official_equivalent"],
                1,
            )
            self.assertEqual(
                counts["resource_bundled_only"],
                1,
            )
            self.assertEqual(
                counts["resource_semantics_unresolved"],
                1,
            )
            self.assertEqual(
                counts["native_runtime_requirement"],
                1,
            )
            self.assertEqual(
                counts["dynamic_target_unresolved"],
                1,
            )
            self.assertTrue(
                report["summary"][
                    "service_provider_discovery_unproven"
                ]
            )
            self.assertTrue(
                report["summary"][
                    "native_artifact_equivalence_unproven"
                ]
            )
            self.assertFalse(
                report["summary"][
                    "runtime_capsule_mutation_ready"
                ]
            )
            self.assertEqual(
                report["summary"]["unresolved_or_blocked_count"],
                9,
            )

    def test_private_rows_preserve_exact_normalization(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = self._build(fx, private=True)

            replaceable = next(
                row
                for row in report["targets"]
                if row["literal_target"] == "dep.Replaceable"
            )
            absolute_resource = next(
                row
                for row in report["targets"]
                if row["literal_target"] == "/config/exact.txt"
            )
            relative_resource = next(
                row
                for row in report["targets"]
                if row["literal_target"] == "rel.txt"
            )

            self.assertEqual(
                replaceable["normalized_class_target"],
                "dep/Replaceable",
            )
            self.assertEqual(
                absolute_resource["resource_entry"],
                "config/exact.txt",
            )
            self.assertEqual(
                relative_resource["resource_entry"],
                "rs/pkg/rel.txt",
            )

    def test_public_and_private_reports_share_id_and_redact_targets(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = self._build(fx)
            private = self._build(fx, private=True)
            self.assertEqual(
                public["runtime_dynamic_target_id"],
                private["runtime_dynamic_target_id"],
            )
            rendered = json.dumps(public)
            self.assertNotIn("dep.Replaceable", rendered)
            self.assertNotIn("config/exact.txt", rendered)
            self.assertNotIn("lwjgl", rendered)

    def test_authority_linkage_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            dynamic = fx["dynamic_report"]
            dynamic["runtime_resource_id"] = (
                "DEPRUNTIMERESOURCE_" + "9" * 20
            )
            fx["dynamic"].write_text(
                json.dumps(dynamic) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeDynamicTargetError,
                "different runtime resource authority",
            ):
                self._build(fx)

    def test_tampered_dynamic_callsites_fail_reproduction(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            dynamic = fx["dynamic_report"]
            dynamic["callsites"][0]["literal_target"] = "tampered.Target"
            fx["dynamic"].write_text(
                json.dumps(dynamic) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DependencyRuntimeDynamicTargetError,
                "callsite authority does not reproduce",
            ):
                self._build(fx)


if __name__ == "__main__":
    unittest.main()

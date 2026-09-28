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
    DependencyRuntimeDynamicError,
    build_dependency_runtime_dynamic_inventory,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DependencyRuntimeDynamicTests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict:
        src = root / "src" / "sample"
        src.mkdir(parents=True)
        source = src / "DynamicCalls.java"
        source.write_text(
            """
package sample;

import java.io.InputStream;
import java.net.URL;
import java.util.ServiceLoader;

public class DynamicCalls {
    public void classForName() throws Exception {
        Class.forName("example.Target");
    }

    public void loadClass(ClassLoader loader) throws Exception {
        loader.loadClass("example.Target2");
    }

    public void serviceLoad() {
        ServiceLoader.load(Runnable.class);
    }

    public void nativeLoad() {
        System.loadLibrary("example");
    }

    public URL classResource() {
        return DynamicCalls.class.getResource("/example.txt");
    }

    public InputStream loaderResource(ClassLoader loader) {
        return loader.getResourceAsStream("example.txt");
    }

    public void conditionalTarget(boolean flag) throws Exception {
        Class.forName(flag ? "example.Left" : "example.Right");
    }

    public void localTarget() throws Exception {
        String name = "example.Local";
        Class.forName(name);
    }
}
""".strip()
            + "\n",
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
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        bundled = root / "bundled.jar"
        with zipfile.ZipFile(
            bundled,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            archive.write(
                classes / "sample" / "DynamicCalls.class",
                "sample/DynamicCalls.class",
            )

        resource = {
            "schema_version": 1,
            "kind": "dependency_runtime_resource_equivalence",
            "runtime_resource_id": (
                "DEPRUNTIMERESOURCE_" + "1" * 20
            ),
            "bundled_jar_sha256": _sha(bundled),
            "summary": {
                "runtime_capsule_mutation_ready": False,
            },
        }
        authority = root / "runtime-resource.json"
        authority.write_text(
            json.dumps(resource, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "bundled": bundled,
            "authority": authority,
            "resource": resource,
        }

    def test_inventory_finds_known_dynamic_loading_apis(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_dynamic_inventory(
                fx["authority"],
                fx["bundled"],
                include_identifiers=True,
            )

            self.assertEqual(
                report["kind"],
                "dependency_runtime_dynamic_inventory",
            )
            self.assertGreaterEqual(
                report["summary"]["dynamic_callsite_count"],
                6,
            )
            categories = report["summary"]["category_counts"]
            self.assertGreaterEqual(
                categories.get("class_loading", 0),
                2,
            )
            self.assertGreaterEqual(
                categories.get("service_loading", 0),
                1,
            )
            self.assertGreaterEqual(
                categories.get("native_loading", 0),
                1,
            )
            self.assertGreaterEqual(
                categories.get("resource_loading", 0),
                2,
            )
            self.assertGreaterEqual(
                report["summary"]["native_load_callsite_count"],
                1,
            )
            self.assertFalse(
                report["summary"]["runtime_capsule_mutation_ready"]
            )

    def test_proves_only_control_flow_safe_immediate_literals(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_dynamic_inventory(
                fx["authority"],
                fx["bundled"],
                include_identifiers=True,
            )

            proven = [
                row
                for row in report["callsites"]
                if row["literal_target_proven"]
            ]
            unresolved = [
                row
                for row in report["callsites"]
                if not row["literal_target_proven"]
            ]

            self.assertGreaterEqual(len(proven), 6)
            self.assertGreaterEqual(len(unresolved), 2)

            proven_targets = {
                row["literal_target"]
                for row in proven
            }
            self.assertIn("example.Target", proven_targets)
            self.assertIn("example.Target2", proven_targets)
            self.assertIn("java/lang/Runnable", proven_targets)
            self.assertIn("example", proven_targets)
            self.assertIn("/example.txt", proven_targets)
            self.assertIn("example.txt", proven_targets)

            unresolved_methods = {
                row["caller_method"]
                for row in unresolved
            }
            self.assertIn(
                "conditionalTarget",
                unresolved_methods,
            )
            self.assertIn("localTarget", unresolved_methods)

            self.assertEqual(
                report["summary"][
                    "dynamic_target_unresolved_count"
                ],
                len(unresolved),
            )

    def test_native_calls_are_classified_separately(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_dynamic_inventory(
                fx["authority"],
                fx["bundled"],
                include_identifiers=True,
            )
            native = [
                row
                for row in report["callsites"]
                if row["category"] == "native_loading"
            ]
            self.assertGreaterEqual(len(native), 1)
            self.assertTrue(
                all(
                    row["classification"]
                    in {
                        "native_load_dynamic",
                        "native_load_literal",
                    }
                    for row in native
                )
            )
            self.assertTrue(
                any(
                    row["classification"]
                    == "native_load_literal"
                    and row["literal_target"] == "example"
                    for row in native
                )
            )

    def test_service_loader_class_token_is_proven(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_dynamic_inventory(
                fx["authority"],
                fx["bundled"],
                include_identifiers=True,
            )
            service = [
                row
                for row in report["callsites"]
                if row["category"] == "service_loading"
            ]
            self.assertGreaterEqual(len(service), 1)
            self.assertTrue(
                any(
                    row["classification"]
                    == "service_loader_class_token"
                    and row["literal_target"]
                    == "java/lang/Runnable"
                    for row in service
                )
            )

    def test_public_report_redacts_caller_identity_and_shares_id(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            public = build_dependency_runtime_dynamic_inventory(
                fx["authority"],
                fx["bundled"],
            )
            private = build_dependency_runtime_dynamic_inventory(
                fx["authority"],
                fx["bundled"],
                include_identifiers=True,
            )

            self.assertEqual(
                public["runtime_dynamic_id"],
                private["runtime_dynamic_id"],
            )
            rendered = json.dumps(public)
            self.assertNotIn("sample/DynamicCalls", rendered)
            self.assertNotIn("example.Target", rendered)
            self.assertFalse(public["identifiers_included"])

    def test_duplicate_class_entry_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            with zipfile.ZipFile(
                fx["bundled"],
                "a",
                zipfile.ZIP_STORED,
            ) as archive:
                original = archive.read(
                    "sample/DynamicCalls.class"
                )
                archive.writestr(
                    "sample/DynamicCalls.class",
                    original,
                )

            resource = fx["resource"]
            resource["bundled_jar_sha256"] = _sha(
                fx["bundled"]
            )
            fx["authority"].write_text(
                json.dumps(resource) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DependencyRuntimeDynamicError,
                "duplicate class entry",
            ):
                build_dependency_runtime_dynamic_inventory(
                    fx["authority"],
                    fx["bundled"],
                )

    def test_resource_authority_jar_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            with zipfile.ZipFile(
                fx["bundled"],
                "a",
                zipfile.ZIP_STORED,
            ) as archive:
                archive.writestr("drift.txt", b"drift")

            with self.assertRaisesRegex(
                DependencyRuntimeDynamicError,
                "different bundled JAR",
            ):
                build_dependency_runtime_dynamic_inventory(
                    fx["authority"],
                    fx["bundled"],
                )


if __name__ == "__main__":
    unittest.main()

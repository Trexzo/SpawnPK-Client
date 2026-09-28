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

    def test_does_not_guess_literal_targets_from_nearby_constants(self):
        with tempfile.TemporaryDirectory() as td:
            fx = self._fixture(Path(td))
            report = build_dependency_runtime_dynamic_inventory(
                fx["authority"],
                fx["bundled"],
                include_identifiers=True,
            )

            for row in report["callsites"]:
                self.assertFalse(row["literal_target_proven"])
                self.assertIsNone(row["literal_target"])

            self.assertEqual(
                report["summary"]["literal_target_proven_count"],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "dynamic_target_unresolved_count"
                ],
                report["summary"]["dynamic_callsite_count"],
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
                    == "native_load_dynamic"
                    for row in native
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

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from spk_recovery.build_authority import (
    BuildAuthorityError,
    build_build_authority,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jar(root: Path) -> Path:
    path = root / "client.jar"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.writestr(
            "META-INF/maven/com.google.code.gson/gson/pom.properties",
            "groupId=com.google.code.gson\n"
            "artifactId=gson\n"
            "version=2.8.5\n",
        )
        z.writestr(
            "META-INF/maven/com.google.code.gson/gson/pom.xml",
            "<project><artifactId>gson</artifactId></project>\n",
        )
        z.writestr("pom.xml", "<project/>\n")
        z.writestr("rs/A.class", b"not parsed here")
    return path


def _index(jar: Path) -> dict:
    return {
        "sha256": _sha(jar),
        "classes": {
            "rs/A.class": {"major": 53},
            "rs/B.class": {"major": 53},
            "other/C.class": {"major": 52},
        },
    }


def _probe(name, args):
    return {
        "requested_command": name,
        "resolved_path": f"/tool/{name}",
        "binary_sha256": "f" * 64,
        "version_output": (
            "javac 21.0.1"
            if name == "javac"
            else 'openjdk version "21.0.1"'
        ),
    }


class BuildAuthorityTests(unittest.TestCase):
    @patch("spk_recovery.build_authority._probe_executable", side_effect=_probe)
    def test_embedded_metadata_is_exact_but_not_original_build_claim(self, _):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _jar(root)
            readiness = {
                "schema_version": 1,
                "kind": "source_readiness_report",
                "source_authority_sha256": _sha(jar),
                "external_import_roots": {"com": 12},
            }
            manifest = build_build_authority(
                jar,
                _index(jar),
                source_readiness=readiness,
            )

            self.assertEqual(
                manifest["bytecode"]["dominant_java_release"],
                9,
            )
            self.assertEqual(
                manifest["bytecode"]["major_versions"],
                {"53": 2},
            )
            self.assertEqual(
                manifest["embedded_maven_metadata"][0]["group_id"],
                "com.google.code.gson",
            )
            self.assertEqual(
                manifest["embedded_maven_metadata"][0]["version"],
                "2.8.5",
            )
            self.assertFalse(
                manifest["interpretation"][
                    "embedded_maven_metadata_is_original_build_file"
                ]
            )
            self.assertFalse(
                manifest["interpretation"]["compiler_runtime_is_original_jdk"]
            )
            self.assertEqual(
                manifest["source_dependency_surface"][
                    "external_import_roots"
                ],
                {"com": 12},
            )
            self.assertEqual(
                manifest["root_build_metadata"][0]["entry"],
                "pom.xml",
            )

    @patch("spk_recovery.build_authority._probe_executable", side_effect=_probe)
    def test_class_prefix_scopes_bytecode_evidence(self, _):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _jar(root)
            manifest = build_build_authority(
                jar,
                _index(jar),
                class_prefix="other/",
            )
            self.assertEqual(
                manifest["bytecode"]["major_versions"],
                {"52": 1},
            )
            self.assertEqual(
                manifest["bytecode"]["dominant_java_release"],
                8,
            )

    @patch("spk_recovery.build_authority._probe_executable", side_effect=_probe)
    def test_readiness_authority_mismatch_is_rejected(self, _):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _jar(root)
            readiness = {
                "schema_version": 1,
                "kind": "source_readiness_report",
                "source_authority_sha256": "0" * 64,
                "external_import_roots": {},
            }
            with self.assertRaises(BuildAuthorityError):
                build_build_authority(
                    jar,
                    _index(jar),
                    source_readiness=readiness,
                )


if __name__ == "__main__":
    unittest.main()

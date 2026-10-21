"""Public-only regression gates for the actual v311 project-class inventory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from spk_recovery.indexer import project_class_surface


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "authority" / "v311.json"


def index_fixture():
    return {
        "entries": {
            "rs/a.class": {"sha256": "a" * 64},
            "rs/gui/Launcher.class": {"sha256": "b" * 64},
            "some/library/Class.class": {"sha256": "c" * 64},
        },
        "classes": {
            "rs/a.class": {"internal_name": "rs/a", "major": 53},
            "rs/gui/Launcher.class": {
                "internal_name": "rs/gui/Launcher", "major": 53
            },
        },
    }


class ProjectSurfaceTests(unittest.TestCase):
    def test_path_and_sha_witness_order_independent(self):
        doc = index_fixture()
        result = project_class_surface(doc)
        material = (
            "rs/a.class\\0" + "a" * 64 + "\\n"
            + "rs/gui/Launcher.class\\0" + "b" * 64 + "\\n"
        ).replace("\\0", "\0").replace("\\n", "\n").encode("utf-8")
        self.assertEqual(
            result["path_sha256_manifest_digest"],
            hashlib.sha256(material).hexdigest(),
        )
        self.assertEqual(result["class_count"], 2)
        self.assertEqual(result["class_major_versions"], {"53": 2})
        self.assertEqual(
            result["package_class_counts"], {"[root]": 1, "gui": 1},
        )
        self.assertTrue(result["full_jvm_class_parse"])
        self.assertFalse(result["cross_build_identity_proven"])
        self.assertEqual(
            result,
            project_class_surface({
                "entries": dict(reversed(list(doc["entries"].items()))),
                "classes": dict(reversed(list(doc["classes"].items()))),
            }),
        )

    def test_unparsed_class_fails_closed(self):
        doc = index_fixture()
        del doc["classes"]["rs/a.class"]
        with self.assertRaisesRegex(ValueError, "UNPARSED_CLASS"):
            project_class_surface(doc)

    def test_mismatched_internal_name_fails_closed(self):
        doc = index_fixture()
        doc["classes"]["rs/a.class"]["internal_name"] = "rs/other"
        with self.assertRaisesRegex(ValueError, "CLASS_PATH_MISMATCH"):
            project_class_surface(doc)

    def test_corrupt_class_digest_fails_closed(self):
        doc = index_fixture()
        doc["entries"]["rs/a.class"]["sha256"] = "ABC"
        with self.assertRaisesRegex(ValueError, "INVALID_CLASS_SHA"):
            project_class_surface(doc)

    def test_invalid_class_version_fails_closed(self):
        doc = index_fixture()
        doc["classes"]["rs/a.class"]["major"] = True
        with self.assertRaisesRegex(ValueError, "INVALID_CLASS_VERSION"):
            project_class_surface(doc)

    def test_scope_does_not_accept_external_classes(self):
        doc = index_fixture()
        del doc["entries"]["rs/a.class"]
        del doc["entries"]["rs/gui/Launcher.class"]
        with self.assertRaisesRegex(ValueError, "PROJECT_SURFACE_EMPTY"):
            project_class_surface(doc)

    def test_v311_authority_preserves_original_bytecode_boundary(self):
        doc = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        self.assertEqual(doc["sha256"], "5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268")
        project = doc["project_class_surface"]
        self.assertEqual(project["scope"], "rs/")
        self.assertEqual(project["class_count"], 1184)
        self.assertEqual(project["class_major_versions"], {"53": 1184})
        self.assertEqual(project["path_sha256_manifest_digest"],
            "c9a88342e8f1d3eed57d113d0691b8ffb0014c46947637437705e03159e4d535")
        self.assertEqual(project["full_jvm_class_parse"], "NOT_YET_REPLAYED_WITH_PROJECT_INDEXER")
        self.assertEqual(doc["verification"]["v309_to_v311_class_delta"], "NOT_COMPUTED")
        self.assertEqual(doc["verification"]["recovered_v311_source_rebuild"], "NOT_TESTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)

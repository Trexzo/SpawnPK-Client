"""Public-only v311 scene/tile role identification regressions.

No real game binary, proprietary cache or source is required for hosted CI.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from spk_recovery.indexer import project_class_surface
from spk_recovery.scene_role_candidates import (
    SceneRoleProbeError,
    discover_scene_role,
)


JAR_SHA = "f" * 64


def member(path, fields, methods, digest):
    return (
        path,
        {"internal_name": path[:-6], "major": 53,
         "fields": fields, "methods": methods},
        {"sha256": digest},
    )


def field(desc):
    return {"descriptor": desc}


def method(name, desc):
    return {"name": name, "descriptor": desc}


def fixture():
    scene, klass, entry = member(
        "rs/V.class",
        [field("[[[Lrs/H;"), field("[[[[Z"), field("[[[I")]
        + [field("I") for _ in range(74)],
        [method("<init>", "([[[I)V")] + [method("a", "(III)V")
                                         for _ in range(65)],
        "a" * 64,
    )
    tile, tile_klass, tile_entry = member(
        "rs/H.class",
        [field("Lrs/H;"), field("[Lrs/l;")]
        + [field("I") for _ in range(22)],
        [method("<init>", "(III)V")]+[method("a", "()I")
                                      for _ in range(11)],
        "b" * 64,
    )
    client, client_klass, client_entry = member(
        "rs/Client.class",
        [field("Lrs/V;")],
        [method("<init>", "()V")],
        "c" * 64,
    )
    index = {
        "sha256": JAR_SHA,
        "entries": {
            scene: entry, tile: tile_entry,
            client: client_entry,
        },
        "classes": {
            scene: klass, tile: tile_klass,
            client: client_klass,
        },
    }
    authority = {
        "sha256": JAR_SHA,
        "build": 311,
        "project_class_surface": project_class_surface(index),
    }
    return index, authority


class SceneRoleProofTests(unittest.TestCase):
    def test_actual_v311_role_shape_has_unique_candidates(self):
        index, authority = fixture()
        result = discover_scene_role(index, authority)
        self.assertEqual(result["kind"], "v311_original_scene_role_candidate")
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["scene_class_path"], "rs/V.class")
        self.assertEqual(candidate["tile_class_path"], "rs/H.class")
        self.assertEqual(candidate["client_class_path"], "rs/Client.class")
        self.assertEqual(candidate["scene_methods"], 66)
        self.assertEqual(candidate["tile_methods"], 12)
        self.assertEqual(len(candidate["witnesses"]), 6)
        self.assertEqual(candidate["semantic_name_promotion"], "NOT_AUTHORIZED")
        self.assertEqual(candidate["historical_v308_class_identity"], "NOT_ESTABLISHED")
        self.assertFalse(result["cross_build_identity_proven"])
        self.assertFalse(result["source_compiled"])
        self.assertFalse(result["gameplay_executed"])

    def test_actual_original_binary_sha_mismatch_is_rejected(self):
        index, authority = fixture()
        index["sha256"] = "e" * 64
        with self.assertRaisesRegex(SceneRoleProbeError, "JAR_SHA_MISMATCH"):
            discover_scene_role(index, authority)

    def test_project_class_content_drift_is_rejected(self):
        index, authority = fixture()
        index["entries"]["rs/V.class"]["sha256"] = "d" * 64
        with self.assertRaisesRegex(SceneRoleProbeError, "PROJECT_SURFACE_MISMATCH"):
            discover_scene_role(index, authority)

    def test_missing_scene_visibility_is_not_assumed(self):
        index, authority = fixture()
        scene = index["classes"]["rs/V.class"]
        scene["fields"] = [f for f in scene["fields"]
                           if f["descriptor"] != "[[[[Z"]
        authority["project_class_surface"] = project_class_surface(index)
        with self.assertRaisesRegex(SceneRoleProbeError, "NOT_UNIQUE candidate_count=0"):
            discover_scene_role(index, authority)

    def test_scene_absent_from_client_is_not_promoted(self):
        index, authority = fixture()
        index["classes"]["rs/Client.class"]["fields"] = []
        with self.assertRaisesRegex(SceneRoleProbeError, "NOT_UNIQUE candidate_count=0"):
            discover_scene_role(index, authority)

    def test_tile_missing_self_reference_is_not_promoted(self):
        index, authority = fixture()
        index["classes"]["rs/H.class"]["fields"] = [field("[Lrs/l;")]
        with self.assertRaisesRegex(SceneRoleProbeError, "NOT_UNIQUE candidate_count=0"):
            discover_scene_role(index, authority)

    def test_ambiguous_scene_candidates_are_refused(self):
        index, authority = fixture()
        klass = json.loads(json.dumps(index["classes"]["rs/V.class"]))
        klass["internal_name"] = "rs/W"
        klass["fields"][0] = field("[[[Lrs/G;")
        index["classes"]["rs/W.class"] = klass
        index["entries"]["rs/W.class"] = {"sha256": "d" * 64}
        index["classes"]["rs/G.class"] = {
            "internal_name": "rs/G", "major": 53,
            "fields": [field("Lrs/G;"), field("[Lrs/l;")],
            "methods": [method("<init>", "(III)V")],
        }
        index["entries"]["rs/G.class"] = {"sha256": "e" * 64}
        index["classes"]["rs/Client.class"]["fields"].append(field("Lrs/W;"))
        authority["project_class_surface"] = project_class_surface(index)
        with self.assertRaisesRegex(SceneRoleProbeError, "NOT_UNIQUE candidate_count=2"):
            discover_scene_role(index, authority)

    def test_incorrect_build_number_fails_closed(self):
        index, authority = fixture()
        authority["build"] = 310
        with self.assertRaisesRegex(SceneRoleProbeError, "EXPECTED_V311_AUTHORITY"):
            discover_scene_role(index, authority)

    def test_unparsed_tile_fails_closed(self):
        index, authority = fixture()
        del index["classes"]["rs/H.class"]
        with self.assertRaisesRegex(SceneRoleProbeError, "CLASS_SURFACE_INVALID"):
            discover_scene_role(index, authority)


if __name__ == "__main__":
    unittest.main()

"""R124 original-client ZIP asset intake tests, no original assets in CI."""
from pathlib import Path
import hashlib
import io
import json
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZipInfo

from spk_recovery.private_client_asset_build_delta_r124 import (
    PrivateClientAssetDeltaR124Error,
    inventory_private_original_assets,
    _package_type_collisions,
    _case_insensitive_class_path_collisions,
)


def archive_bytes(items):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as z:
        for name, content in items:
            z.writestr(name, content)
    return buffer.getvalue()


class PrivateClientAssetDeltaR124Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "private-assets.zip"
        self.oldjar = archive_bytes([
            ("rs/Owner.class", b"oldowner"),
            ("rs/Stable.class", b"stable"),
            ("x/Library.class", b"library"),
            ("icon.png", b"resource"),
        ])
        self.newjar = archive_bytes([
            ("rs/Owner.class", b"newowner"),
            ("rs/Stable.class", b"stable"),
            ("rs/Added.class", b"added"),
            ("x/Library.class", b"library"),
            ("icon.png", b"resource"),
        ])
        self.expected = {
            "v308": hashlib.sha256(self.oldjar).hexdigest(),
            "v309": hashlib.sha256(self.newjar).hexdigest(),
        }

    def build(self, additions=()):
        with ZipFile(self.path, "w") as outer:
            outer.writestr(".spawnpk-data/client-v308.jar", self.oldjar)
            outer.writestr(".spawnpk-data/client.jar", self.newjar)
            outer.writestr(".spawnpk/raw/123", b"cached data")
            outer.writestr(".spawnpk/sprites/icon.png", b"sprite")
            outer.writestr(".spawnpk-data/config.properties",
                           b"password=never-publish\naccountid=secret\n")
            for name, data in additions:
                outer.writestr(name, data)
        return inventory_private_original_assets(
            self.path, expected=self.expected)

    def test_exact_client_delta_and_profile_exclusion(self):
        result = self.build()
        game = result["binary_class_delta"]["game_rs"]
        self.assertEqual(game["old"], 2)
        self.assertEqual(game["new"], 3)
        self.assertEqual(game["byte_identical_same_path"], 1)
        self.assertEqual(game["modified_same_path"], 1)
        self.assertEqual(game["new_paths"], 1)
        self.assertEqual(game["removed_paths"], 0)
        self.assertEqual(result["local_profile_files_excluded"], 1)
        self.assertEqual(result["runtime_asset_files"], 2)
        self.assertNotIn("password", json.dumps(result))
        self.assertNotIn("accountid", json.dumps(result))
        self.assertFalse(result["full_deobfuscated_source_tree_accepted"])
        self.assertFalse(result["runtime_equivalence_proven"])

    def test_obfuscated_type_package_collision_frontier(self):
        result = _package_type_collisions({
            "rs/p.class", "rs/p/Child.class",
            "rs/p/f/Other.class", "rs/q.class",
            "gnu/trove/f.class", "gnu/trove/f/b.class",
            "gnu/trove/f/b/cc.class",
        })
        self.assertEqual(
            result["class_names_shadowing_package_names"], 3)
        self.assertEqual(result["descendant_classfiles_affected"], 4)
        self.assertEqual(result["game_rs_shadowing_class_names"], 1)
        self.assertEqual(
            result["game_rs_descendant_classfiles_affected"], 2)
        self.assertTrue(result["java_source_namespace_remapping_required"])
        self.assertFalse(result["automatically_remapped"])

    def test_windows_casefold_source_path_collisions(self):
        evidence = _case_insensitive_class_path_collisions({
            "rs/A.class", "rs/a.class",
            "rs/Foo.class", "rs/foo.class",
            "gnu/F.class", "gnu/f.class",
            "rs/Stable.class",
        })
        self.assertEqual(evidence["casefold_class_path_conflict_groups"], 3)
        self.assertEqual(evidence["affected_classfiles"], 6)
        self.assertEqual(evidence["game_rs_conflict_groups"], 2)
        self.assertEqual(evidence["game_rs_affected_classfiles"], 4)
        self.assertTrue(evidence["windows_source_path_legalization_required"])
        self.assertFalse(evidence["automatically_renamed"])

    def test_manifest_hash_reproducible(self):
        a = self.build()["runtime_asset_sha256_manifest"]
        b = self.build()["runtime_asset_sha256_manifest"]
        self.assertEqual(a, b)

    def test_exact_original_pin_veto(self):
        self.build()
        with self.assertRaisesRegex(
                PrivateClientAssetDeltaR124Error,
                "ORIGINAL_V309_SHA256_MISMATCH"):
            inventory_private_original_assets(
                self.path, expected={
                    "v308": self.expected["v308"], "v309": "0" * 64})

    def test_no_missing_original_v308_allowed(self):
        with ZipFile(self.path, "w") as z:
            z.writestr(".spawnpk-data/client.jar", self.newjar)
        with self.assertRaisesRegex(
                PrivateClientAssetDeltaR124Error,
                "EXACT_CANONICAL_CLIENT_JAR_PAIR_REQUIRED"):
            inventory_private_original_assets(
                self.path, expected=self.expected)

    def test_reject_path_traversal(self):
        with ZipFile(self.path, "w") as z:
            z.writestr(".spawnpk-data/client-v308.jar", self.oldjar)
            z.writestr(".spawnpk-data/client.jar", self.newjar)
            z.writestr(".spawnpk/../../sneaky", b"x")
        with self.assertRaisesRegex(
                PrivateClientAssetDeltaR124Error,
                "UNSAFE_ARCHIVE_MEMBER_PATH"):
            inventory_private_original_assets(
                self.path, expected=self.expected)

    def test_reject_duplicate_member(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(self.path, "w") as z:
                z.writestr(".spawnpk-data/client-v308.jar", self.oldjar)
                z.writestr(".spawnpk-data/client.jar", self.newjar)
                z.writestr(".spawnpk-data/client.jar", self.newjar)
        with self.assertRaisesRegex(
                PrivateClientAssetDeltaR124Error,
                "DUPLICATE_ARCHIVE_MEMBER"):
            inventory_private_original_assets(
                self.path, expected=self.expected)

    def test_reject_zip_symlink(self):
        with ZipFile(self.path, "w") as z:
            z.writestr(".spawnpk-data/client-v308.jar", self.oldjar)
            z.writestr(".spawnpk-data/client.jar", self.newjar)
            link = ZipInfo(".spawnpk/raw/link")
            link.create_system = 3
            link.external_attr = (0o120777 << 16)
            z.writestr(link, b"target")
        with self.assertRaisesRegex(
                PrivateClientAssetDeltaR124Error,
                "ARCHIVE_SYMLINK_NOT_ALLOWED"):
            inventory_private_original_assets(
                self.path, expected=self.expected)

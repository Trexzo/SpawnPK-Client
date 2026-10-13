"""R125 client-only Java/Windows namespace legalization regression tests."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import warnings
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from spk_recovery.private_client_namespace_legalizer_r125 import (
    ClientNamespaceLegalizationError, original_class_inventory,
    plan_client_namespaces, package_prefixes, case_groups,
    derive_private_bytecode_remap_plan,
)


class ClientNamespaceLegalizationR125Tests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.jar = self.root / "v309-original.private.jar"

    def make(self, entries):
        with ZipFile(self.jar, "w") as archive:
            for name, value in entries:
                archive.writestr(name, value)
        return hashlib.sha256(self.jar.read_bytes()).hexdigest()

    def test_original_like_namespace_is_bijective_and_windows_safe(self):
        names = {
            "rs/A", "rs/a", "rs/a$Inner",
            "rs/A/C", "rs/a/Child", "rs/x", "rs/x/Nested",
            "rs/Q/Lower", "rs/q/Upper",
            "gnu/trove/f", "gnu/trove/f/g",
            "rs/Stable", "rs/Stable$Nested",
        }
        result = plan_client_namespaces(names, include_identifiers=True)
        rows = {row["old_internal_name"]: row["new_internal_name"]
                for row in result["remaps"]}
        mapped = {rows.get(name, name) for name in names}
        self.assertEqual(len(mapped), len(names))
        self.assertEqual(case_groups(mapped), [])
        self.assertEqual(case_groups(package_prefixes(mapped)), [])
        self.assertFalse(
            {name.casefold() for name in mapped}
            & {name.casefold() for name in package_prefixes(mapped)})
        self.assertNotEqual(rows["rs/x"], "rs/x")
        self.assertEqual(rows["rs/x$Inner"] if "rs/x$Inner" in rows
                         else "", "")
        self.assertTrue(
            rows["rs/a$Inner"].startswith(rows["rs/a"] + "$")
            if "rs/a" in rows else True)
        self.assertGreater(result["remediation_operations"][
            "windows_package_case_conflicts_fixed"], 0)
        self.assertGreater(result["remediation_operations"][
            "java_type_package_shadow_conflicts_fixed"], 0)
        self.assertTrue(result["mapped_paths_unique_after_casefold"])
        self.assertFalse(result["source_compilation_accepted"])
        self.assertFalse(result["accepted_semantic_names_assigned"])

    def test_nested_binary_family_moves_with_shadowed_outer(self):
        names = {"rs/f", "rs/f/Child", "rs/f$Nested"}
        result = plan_client_namespaces(names, include_identifiers=True)
        rows = {r["old_internal_name"]: r["new_internal_name"]
                for r in result["remaps"]}
        self.assertEqual(rows["rs/f$Nested"], rows["rs/f"] + "$Nested")
        self.assertNotIn("rs/f/Child", rows)

    def test_casefold_leaf_collision_moves_nested_binary_family(self):
        names = {"rs/A", "rs/a", "rs/a$Child"}
        result = plan_client_namespaces(names, include_identifiers=True)
        rows = {r["old_internal_name"]: r["new_internal_name"]
                for r in result["remaps"]}
        self.assertIn("rs/a", rows)
        self.assertEqual(rows["rs/a$Child"], rows["rs/a"] + "$Child")

    def test_unchanged_classes_are_not_renamed(self):
        names = {"rs/Alpha", "rs/beta/Leaf", "com/library/Stable"}
        report = plan_client_namespaces(names, include_identifiers=True)
        self.assertEqual(report["renamed_classfile_count"], 0)
        self.assertEqual(report["remaps"], [])

    def test_mapping_is_reproducible_and_public_excludes_names(self):
        names = {"rs/f", "rs/f/Child", "rs/A", "rs/a"}
        a = plan_client_namespaces(names, include_identifiers=True)
        b = plan_client_namespaces(set(reversed(sorted(names))),
                                   include_identifiers=True)
        self.assertEqual(a, b)
        clean = plan_client_namespaces(names)
        self.assertEqual(clean["private_mapping_sha256"],
                         a["private_mapping_sha256"])
        self.assertNotIn("remaps", clean)
        self.assertNotIn("rs/f", json.dumps(clean))
        self.assertNotIn("rs/A", json.dumps(clean))
        self.assertFalse(clean["source_files_rewritten"])

    def test_exact_original_sha_is_required(self):
        actual = self.make([
            ("rs/One.class", b"synthetic"),
            ("rs/Two.class", b"synthetic"),
        ])
        self.assertEqual(original_class_inventory(self.jar, actual),
                         {"rs/One", "rs/Two"})
        with self.assertRaisesRegex(
                ClientNamespaceLegalizationError,
                "ORIGINAL_CLIENT_JAR_SHA256_MISMATCH"):
            original_class_inventory(self.jar, "0" * 64)

    def test_legacy_bytecode_remapper_adapter_is_hash_pinned(self):
        from spk_recovery.collision_bytecode_remap import (
            _load_plan, _expanded_mappings,
        )
        expected = self.make([
            ("rs/f.class", b"original-synthetic"),
            ("rs/f/Child.class", b"second-synthetic"),
            ("rs/f$Inner.class", b"nested-synthetic"),
            ("rs/Independent.class", b"unaffected"),
        ])
        mapped = derive_private_bytecode_remap_plan(
            self.jar, expected_sha=expected)
        self.assertEqual(mapped["kind"],
                         "class_package_namespace_collision_plan")
        self.assertTrue(mapped["identifiers_included"])
        self.assertEqual(mapped["readable_jar_sha256"], expected)
        self.assertFalse(mapped["r125_source_names_rewritten"])
        plan_path = self.root / "private-remap.json"
        plan_path.write_text(json.dumps(mapped), encoding="utf-8")
        loaded = _load_plan(plan_path)
        expanded, nested = _expanded_mappings(
            {"rs/f", "rs/f/Child", "rs/f$Inner", "rs/Independent"},
            loaded)
        self.assertEqual(nested, 0)
        self.assertEqual(expanded["rs/f$Inner"],
                         expanded["rs/f"] + "$Inner")
        self.assertNotIn("rs/Independent", expanded)

    def test_adapter_rejects_wrong_original_pin(self):
        self.make([("rs/f.class", b"synthetic")])
        with self.assertRaisesRegex(
                ClientNamespaceLegalizationError,
                "ORIGINAL_CLIENT_JAR_SHA256_MISMATCH"):
            derive_private_bytecode_remap_plan(
                self.jar, expected_sha="0" * 64)

    def test_zip_slip_rejected(self):
        actual = self.make([
            ("rs/One.class", b"synthetic"),
            ("rs/../../out.class", b"malicious"),
        ])
        with self.assertRaisesRegex(
                ClientNamespaceLegalizationError,
                "UNSAFE_ARCHIVE_MEMBER_PATH"):
            original_class_inventory(self.jar, actual)

    def test_duplicate_class_members_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            actual = self.make([
                ("rs/One.class", b"first"),
                ("rs/One.class", b"second"),
            ])
        with self.assertRaisesRegex(
                ClientNamespaceLegalizationError,
                "JAR_DUPLICATE_ARCHIVE_MEMBER"):
            original_class_inventory(self.jar, actual)

    def test_zip_symlink_rejected(self):
        with ZipFile(self.jar, "w") as archive:
            archive.writestr("rs/One.class", b"synthetic")
            link = ZipInfo("rs/Sym.class")
            link.create_system = 3
            link.external_attr = 0o120777 << 16
            archive.writestr(link, "target")
        actual = hashlib.sha256(self.jar.read_bytes()).hexdigest()
        with self.assertRaisesRegex(
                ClientNamespaceLegalizationError,
                "ORIGINAL_JAR_SYMLINK_REJECTED"):
            original_class_inventory(self.jar, actual)

    def test_unsafe_jvm_identifier_not_published_as_compilable(self):
        with self.assertRaisesRegex(
                ClientNamespaceLegalizationError,
                "ORIGINAL_JVM_CLASS_NAME_NOT_DIRECTLY_JAVA_LEGAL"):
            plan_client_namespaces({"rs/enum"})

    def test_public_plan_never_claims_source_or_runtime_recovery(self):
        report = plan_client_namespaces({"rs/a", "rs/a/Child"})
        for key in ("source_files_rewritten",
                    "source_compilation_accepted",
                    "classfile_parity_proven",
                    "runtime_equivalence_proven",
                    "accepted_semantic_names_assigned"):
            self.assertIs(report[key], False)

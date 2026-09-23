import copy
import unittest

from spk_recovery.semantic_namespace import (
    SemanticNamespaceError,
    build_semantic_namespace,
)


def _fixture():
    class_lineage = {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [
            {
                "build_id": "v308",
                "build_number": 308,
                "sha256": "a" * 64,
                "source_name": "client.jar",
                "authority": "EXACT_CURRENT_CLIENT",
            }
        ],
        "classes": [
            {
                "logical_id": "CLIENT_CLASS_000001",
                "semantic_name": "ExampleController",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.99,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/a",
                        "entry_path": "rs/a.class",
                        "entry_sha256": "b" * 64,
                        "structural_sha256": "c" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [
                    {"proposal_id": "SEMPROP_CLASS"}
                ],
            },
            {
                "logical_id": "CLIENT_CLASS_000002",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/b",
                        "entry_path": "rs/b.class",
                        "entry_sha256": "d" * 64,
                        "structural_sha256": "e" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            },
        ],
        "unresolved": [],
    }
    member_lineage = {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "a" * 64,
        "members": [
            {
                "member_id": "CLIENT_FIELD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "field",
                "semantic_name": "value",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.97,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "x",
                        "descriptor": "I",
                        "access": 2,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [
                    {"proposal_id": "SEMPROP_FIELD"}
                ],
            },
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": "runTask",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.98,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/a",
                        "name": "a",
                        "descriptor": "()V",
                        "access": 2,
                        "code_length": 5,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [
                    {"proposal_id": "SEMPROP_METHOD"}
                ],
            },
            {
                "member_id": "CLIENT_FIELD_000002",
                "owner_logical_id": "CLIENT_CLASS_000002",
                "kind": "field",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/b",
                        "name": "z",
                        "descriptor": "I",
                        "access": 2,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            },
        ],
        "unresolved": [],
    }
    index = {
        "sha256": "a" * 64,
        "classes": {
            "rs/a.class": {
                "internal_name": "rs/a",
                "fields": [
                    {"name": "x", "descriptor": "I", "access": 2}
                ],
                "methods": [
                    {
                        "name": "a",
                        "descriptor": "()V",
                        "access": 2,
                        "code_length": 5,
                    }
                ],
            },
            "rs/b.class": {
                "internal_name": "rs/b",
                "fields": [
                    {"name": "z", "descriptor": "I", "access": 2}
                ],
                "methods": [],
            },
        },
    }
    return class_lineage, member_lineage, index


class SemanticNamespaceTests(unittest.TestCase):
    def test_only_accepted_semantics_become_remap_plans(self):
        classes, members, index = _fixture()
        manifest, class_plan, member_plan = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
        )

        self.assertEqual(class_plan["class_count"], 1)
        self.assertEqual(
            class_plan["classes"][0]["target_internal_name"],
            "recovered/spawnpk/client/ExampleController",
        )
        self.assertEqual(member_plan["field_count"], 1)
        self.assertEqual(member_plan["method_count"], 1)
        self.assertEqual(manifest["summary"]["classes_total"], 2)
        self.assertEqual(manifest["summary"]["classes_accepted"], 1)
        self.assertEqual(manifest["summary"]["fields_total"], 2)
        self.assertEqual(manifest["summary"]["fields_accepted"], 1)
        self.assertEqual(manifest["summary"]["methods_accepted"], 1)

    def test_candidate_semantic_state_never_becomes_plan(self):
        classes, members, index = _fixture()
        classes["classes"][0]["semantic_status"] = "CANDIDATE"
        classes["classes"][0]["semantic_name"] = "ExampleController"
        classes["classes"][0]["semantic_confidence"] = 0.99

        manifest, class_plan, member_plan = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
        )

        self.assertEqual(class_plan["class_count"], 0)
        self.assertEqual(manifest["summary"]["classes_accepted"], 0)
        self.assertEqual(member_plan["member_count"], 2)

    def test_accepted_class_requires_provenance(self):
        classes, members, index = _fixture()
        classes["classes"][0]["semantic_provenance"] = []
        with self.assertRaises(SemanticNamespaceError):
            build_semantic_namespace(
                classes,
                members,
                index,
                build_id="v308",
            )

    def test_duplicate_class_targets_fail_closed(self):
        classes, members, index = _fixture()
        duplicate = copy.deepcopy(classes["classes"][1])
        duplicate["semantic_name"] = "ExampleController"
        duplicate["semantic_status"] = "ACCEPTED"
        duplicate["semantic_confidence"] = 0.95
        duplicate["semantic_provenance"] = [
            {"proposal_id": "SEMPROP_DUP"}
        ]
        classes["classes"][1] = duplicate

        with self.assertRaises(SemanticNamespaceError):
            build_semantic_namespace(
                classes,
                members,
                index,
                build_id="v308",
            )


    def test_source_safe_fallback_is_opt_in_and_non_semantic(self):
        classes, members, index = _fixture()
        classes["classes"].append(
            {
                "logical_id": "CLIENT_CLASS_000003",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/b/c",
                        "entry_path": "rs/b/c.class",
                        "entry_sha256": "f" * 64,
                        "structural_sha256": "1" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        )
        index["classes"]["rs/b/c.class"] = {
            "internal_name": "rs/b/c",
            "fields": [],
            "methods": [],
        }

        manifest, class_plan, _ = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
        )
        self.assertEqual(class_plan["class_count"], 1)
        self.assertEqual(manifest["summary"]["source_safety_fallbacks"], 0)
        self.assertEqual(manifest["fallback_remaps"], [])

        manifest, class_plan, _ = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
            source_safe_fallback=True,
        )
        self.assertEqual(class_plan["class_count"], 2)
        fallbacks = manifest["fallback_remaps"]
        self.assertEqual(len(fallbacks), 1)
        self.assertEqual(fallbacks[0]["logical_id"], "CLIENT_CLASS_000002")
        self.assertEqual(
            fallbacks[0]["target_internal_name"],
            "rs/Recovered_CLIENT_CLASS_000002",
        )
        row = next(
            row
            for row in class_plan["classes"]
            if row["logical_id"] == "CLIENT_CLASS_000002"
        )
        self.assertEqual(
            row["provenance"][0]["reason"],
            "java_class_package_collision",
        )
        self.assertEqual(
            row["provenance"][0]["strategy"],
            "package_preserving_class_rename",
        )
        self.assertEqual(classes["classes"][1]["semantic_status"], "UNKNOWN")
        self.assertIsNone(classes["classes"][1]["semantic_name"])

    def test_accepted_semantic_remap_takes_precedence_over_fallback(self):
        classes, members, index = _fixture()
        classes["classes"].append(
            {
                "logical_id": "CLIENT_CLASS_000003",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/a/c",
                        "entry_path": "rs/a/c.class",
                        "entry_sha256": "f" * 64,
                        "structural_sha256": "1" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        )
        index["classes"]["rs/a/c.class"] = {
            "internal_name": "rs/a/c",
            "fields": [],
            "methods": [],
        }

        manifest, class_plan, _ = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
            source_safe_fallback=True,
        )
        self.assertEqual(class_plan["class_count"], 1)
        self.assertEqual(manifest["fallback_remaps"], [])
        self.assertEqual(
            class_plan["classes"][0]["target_internal_name"],
            "recovered/spawnpk/client/ExampleController",
        )


    def test_accepted_outer_closes_over_unknown_nested_class(self):
        classes, members, index = _fixture()
        classes["classes"].append(
            {
                "logical_id": "CLIENT_CLASS_000003",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/a$Inner",
                        "entry_path": "rs/a$Inner.class",
                        "entry_sha256": "f" * 64,
                        "structural_sha256": "1" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        )
        index["classes"]["rs/a$Inner.class"] = {
            "internal_name": "rs/a$Inner",
            "inner_outer_name": "rs/a",
            "enclosing_class_name": None,
            "fields": [],
            "methods": [],
        }

        manifest, class_plan, _ = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
        )

        self.assertEqual(class_plan["class_count"], 2)
        nested = next(
            row
            for row in class_plan["classes"]
            if row["logical_id"] == "CLIENT_CLASS_000003"
        )
        self.assertEqual(
            nested["target_internal_name"],
            "recovered/spawnpk/client/ExampleController$Inner",
        )
        self.assertEqual(
            nested["provenance"][0]["reason"],
            "semantic_outer_nested_class_closure",
        )
        self.assertEqual(
            manifest["summary"]["source_safety_nested_class_remaps"],
            1,
        )
        self.assertEqual(
            manifest["nested_class_closure_remaps"][0]["logical_id"],
            "CLIENT_CLASS_000003",
        )
        self.assertEqual(
            classes["classes"][2]["semantic_status"],
            "UNKNOWN",
        )
        self.assertIsNone(classes["classes"][2]["semantic_name"])

    def test_conflicting_accepted_nested_semantic_target_fails_closed(self):
        classes, members, index = _fixture()
        classes["classes"].append(
            {
                "logical_id": "CLIENT_CLASS_000003",
                "semantic_name": "IndependentNested",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.99,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/a$Inner",
                        "entry_path": "rs/a$Inner.class",
                        "entry_sha256": "f" * 64,
                        "structural_sha256": "1" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [
                    {"proposal_id": "SEMPROP_NESTED"}
                ],
            }
        )
        index["classes"]["rs/a$Inner.class"] = {
            "internal_name": "rs/a$Inner",
            "inner_outer_name": "rs/a",
            "enclosing_class_name": None,
            "fields": [],
            "methods": [],
        }

        with self.assertRaises(SemanticNamespaceError):
            build_semantic_namespace(
                classes,
                members,
                index,
                build_id="v308",
            )


    def test_dollar_named_top_level_class_without_nesting_evidence_is_not_closed(self):
        classes, members, index = _fixture()
        classes["classes"].append(
            {
                "logical_id": "CLIENT_CLASS_000003",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/a$Utility",
                        "entry_path": "rs/a$Utility.class",
                        "entry_sha256": "f" * 64,
                        "structural_sha256": "1" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        )
        index["classes"]["rs/a$Utility.class"] = {
            "internal_name": "rs/a$Utility",
            "inner_outer_name": None,
            "enclosing_class_name": None,
            "fields": [],
            "methods": [],
        }

        manifest, class_plan, _ = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
            source_safe_fallback=True,
        )

        self.assertEqual(class_plan["class_count"], 1)
        self.assertEqual(
            manifest["summary"]["source_safety_nested_class_remaps"],
            0,
        )
        self.assertEqual(
            manifest["summary"]["source_safety_same_simple_nested_remaps"],
            0,
        )
        self.assertEqual(manifest["nested_class_closure_remaps"], [])
        self.assertEqual(
            manifest["same_simple_nested_source_safety_remaps"],
            [],
        )


    def test_same_simple_nested_source_safety_is_structural_and_opt_in(self):
        classes, members, index = _fixture()
        classes["classes"].append(
            {
                "logical_id": "CLIENT_CLASS_000003",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/b$b",
                        "entry_path": "rs/b$b.class",
                        "entry_sha256": "f" * 64,
                        "structural_sha256": "1" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        )
        index["classes"]["rs/b$b.class"] = {
            "internal_name": "rs/b$b",
            "inner_outer_name": "rs/b",
            "inner_simple_name": "b",
            "enclosing_class_name": None,
            "fields": [],
            "methods": [],
        }

        manifest, class_plan, _ = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
        )
        self.assertEqual(class_plan["class_count"], 1)
        self.assertEqual(
            manifest["summary"]["source_safety_same_simple_nested_remaps"],
            0,
        )
        self.assertEqual(
            manifest["same_simple_nested_source_safety_remaps"],
            [],
        )

        manifest, class_plan, _ = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
            source_safe_fallback=True,
        )
        self.assertEqual(class_plan["class_count"], 2)
        rows = manifest["same_simple_nested_source_safety_remaps"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["logical_id"], "CLIENT_CLASS_000003")
        self.assertEqual(
            rows[0]["target_internal_name"],
            "rs/b$Recovered_CLIENT_CLASS_000003",
        )
        nested = next(
            row
            for row in class_plan["classes"]
            if row["logical_id"] == "CLIENT_CLASS_000003"
        )
        self.assertEqual(
            nested["provenance"][0]["reason"],
            "java_enclosing_nested_simple_name_collision",
        )
        self.assertEqual(classes["classes"][2]["semantic_status"], "UNKNOWN")
        self.assertIsNone(classes["classes"][2]["semantic_name"])

    def test_same_simple_nested_accepted_semantic_target_keeps_precedence(self):
        classes, members, index = _fixture()
        classes["classes"].append(
            {
                "logical_id": "CLIENT_CLASS_000003",
                "semantic_name": "ReadableNested",
                "semantic_status": "ACCEPTED",
                "semantic_confidence": 0.99,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/b$b",
                        "entry_path": "rs/b$b.class",
                        "entry_sha256": "f" * 64,
                        "structural_sha256": "1" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [
                    {"proposal_id": "SEMPROP_NESTED_SAFE"}
                ],
            }
        )
        index["classes"]["rs/b$b.class"] = {
            "internal_name": "rs/b$b",
            "inner_outer_name": "rs/b",
            "inner_simple_name": "b",
            "enclosing_class_name": None,
            "fields": [],
            "methods": [],
        }

        manifest, class_plan, _ = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
            source_safe_fallback=True,
        )
        self.assertEqual(
            manifest["same_simple_nested_source_safety_remaps"],
            [],
        )
        nested = next(
            row
            for row in class_plan["classes"]
            if row["logical_id"] == "CLIENT_CLASS_000003"
        )
        self.assertEqual(
            nested["target_internal_name"],
            "recovered/spawnpk/client/ReadableNested",
        )


    def test_member_source_safety_is_separate_and_non_semantic(self):
        classes, members, index = _fixture()
        field = members["members"][2]
        field["lineage"][0]["name"] = "if"
        index["classes"]["rs/b.class"]["fields"][0]["name"] = "if"

        manifest, _, member_plan = build_semantic_namespace(
            classes,
            members,
            index,
            build_id="v308",
            source_safe_fallback=True,
        )

        self.assertEqual(member_plan["member_count"], 3)
        self.assertEqual(
            manifest["summary"]["source_safety_member_remaps"],
            1,
        )
        rows = manifest["member_source_safety_remaps"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["member_id"], "CLIENT_FIELD_000002")
        self.assertEqual(
            rows[0]["target_name"],
            "Recovered_CLIENT_FIELD_000002",
        )
        self.assertEqual(field["semantic_status"], "UNKNOWN")
        self.assertIsNone(field["semantic_name"])


if __name__ == "__main__":
    unittest.main()

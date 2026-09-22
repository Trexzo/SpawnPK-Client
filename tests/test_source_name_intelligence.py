import unittest

from spk_recovery.source_name_intelligence import (
    build_source_name_candidate_diagnostics,
    build_source_name_candidates,
)
from spk_recovery.source_name_review import (
    resolve_source_name_candidates,
)


def _inventory(symbols):
    return {
        "schema_version": 1,
        "kind": "source_symbol_inventory",
        "inventory_id": "SRCINV_0123456789ABCDEF0123",
        "source_tree_sha256": "a" * 64,
        "symbols": symbols,
    }


def _param(symbol_id, method_id, current, declared="long"):
    return {
        "source_symbol_id": symbol_id,
        "canonical_method_id": method_id,
        "kind": "parameter",
        "ordinal": 0,
        "current_name": current,
        "declared_type": declared,
    }


def _method(member_id, semantic, status="ACCEPTED"):
    return {
        "member_id": member_id,
        "kind": "method",
        "semantic_name": semantic,
        "semantic_status": status,
    }


def _lineage(methods):
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "members": methods,
    }


class SourceNameIntelligenceTests(unittest.TestCase):
    def test_friend_key_parameter_uses_accepted_semantics(self):
        inv = _inventory([
            _param(
                "SRC_PARAM_00000000000000000001",
                "CLIENT_METHOD_000298",
                "var1",
            )
        ])
        members = _lineage([
            _method(
                "CLIENT_METHOD_000298",
                "addFriend",
            )
        ])

        out = build_source_name_candidates(inv, members)
        self.assertEqual(len(out["candidates"]), 1)
        row = out["candidates"][0]
        self.assertEqual(row["proposed_name"], "nameKey")
        self.assertEqual(row["confidence"], 0.97)

        review = resolve_source_name_candidates(inv, out)
        self.assertEqual(
            review["summary"]["reviewable_proposals"],
            1,
        )
        self.assertEqual(review["summary"]["conflicts"], 0)

    def test_single_argument_setter_derives_property_name(self):
        inv = _inventory([
            _param(
                "SRC_PARAM_00000000000000000002",
                "CLIENT_METHOD_000010",
                "var1",
                "boolean",
            )
        ])
        members = _lineage([
            _method(
                "CLIENT_METHOD_000010",
                "setEnabled",
            )
        ])
        out = build_source_name_candidates(inv, members)
        self.assertEqual(
            out["candidates"][0]["proposed_name"],
            "enabled",
        )
        self.assertEqual(
            out["candidates"][0]["confidence"],
            0.93,
        )

    def test_candidate_semantics_do_not_drive_source_names(self):
        inv = _inventory([
            _param(
                "SRC_PARAM_00000000000000000003",
                "CLIENT_METHOD_000011",
                "var1",
            )
        ])
        members = _lineage([
            _method(
                "CLIENT_METHOD_000011",
                "removeFriend",
                status="CANDIDATE",
            )
        ])
        out = build_source_name_candidates(inv, members)
        self.assertEqual(out["candidates"], [])

    def test_primitive_local_stays_unproposed(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_LOCAL_00000000000000000001",
                "canonical_method_id": "CLIENT_METHOD_000010",
                "kind": "local",
                "ordinal": 0,
                "current_name": "var2",
                "declared_type": "int",
            }
        ])
        members = _lineage([
            _method(
                "CLIENT_METHOD_000010",
                "setCount",
            )
        ])
        out = build_source_name_candidates(inv, members)
        self.assertEqual(out["candidates"], [])
        diagnostics = build_source_name_candidate_diagnostics(
            inv,
            members,
            out,
        )
        self.assertEqual(
            diagnostics["ordinary_locals_considered"],
            1,
        )


    def test_catch_exception_gets_structural_role_name(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_CATCH_00000000000000000001",
                "canonical_method_id": None,
                "kind": "catch",
                "ordinal": 0,
                "current_name": "var3",
                "declared_type": "java.io.IOException",
            }
        ])
        out = build_source_name_candidates(
            inv,
            _lineage([]),
        )
        self.assertEqual(
            out["candidates"][0]["proposed_name"],
            "exception",
        )
        self.assertEqual(
            out["candidates"][0]["confidence"],
            0.94,
        )

    def test_resource_name_uses_declared_type(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_RESOURCE_00000000000000000001",
                "canonical_method_id": None,
                "kind": "resource",
                "ordinal": 0,
                "current_name": "var4",
                "declared_type": "java.io.BufferedReader",
            }
        ])
        out = build_source_name_candidates(
            inv,
            _lineage([]),
        )
        self.assertEqual(
            out["candidates"][0]["proposed_name"],
            "bufferedReader",
        )
        self.assertEqual(
            out["candidates"][0]["confidence"],
            0.88,
        )

    def test_informative_enhanced_for_type_gets_element_role(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_ENHFOR_00000000000000000001",
                "canonical_method_id": None,
                "kind": "enhanced_for",
                "ordinal": 0,
                "current_name": "var5",
                "declared_type": "recovered.spawnpk.client.Player",
            }
        ])
        out = build_source_name_candidates(
            inv,
            _lineage([]),
        )
        self.assertEqual(
            out["candidates"][0]["proposed_name"],
            "player",
        )
        self.assertEqual(
            out["candidates"][0]["confidence"],
            0.86,
        )

    def test_string_enhanced_for_stays_unproposed(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_ENHFOR_00000000000000000002",
                "canonical_method_id": None,
                "kind": "enhanced_for",
                "ordinal": 0,
                "current_name": "var6",
                "declared_type": "String",
            }
        ])
        out = build_source_name_candidates(
            inv,
            _lineage([]),
        )
        self.assertEqual(out["candidates"], [])


    def test_candidate_set_matches_strict_r6b_top_level_shape(self):
        inv = _inventory([
            _param(
                "SRC_PARAM_00000000000000000005",
                "CLIENT_METHOD_000010",
                "var1",
                "boolean",
            )
        ])
        members = _lineage([
            _method(
                "CLIENT_METHOD_000010",
                "setEnabled",
            )
        ])
        out = build_source_name_candidates(inv, members)
        self.assertEqual(
            set(out),
            {
                "schema_version",
                "kind",
                "canonical",
                "inventory_id",
                "source_tree_sha256",
                "candidates",
            },
        )
        self.assertNotIn("producer_summary", out)

    def test_diagnostics_are_separate_from_candidate_schema(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_RESOURCE_00000000000000000002",
                "canonical_method_id": None,
                "kind": "resource",
                "ordinal": 0,
                "current_name": "var7",
                "declared_type": "java.io.InputStream",
            }
        ])
        members = _lineage([])
        out = build_source_name_candidates(inv, members)
        diagnostics = build_source_name_candidate_diagnostics(
            inv,
            members,
            out,
        )
        self.assertEqual(
            diagnostics["kind"],
            "source_name_candidate_diagnostics",
        )
        self.assertEqual(
            diagnostics["candidate_kinds"],
            {"resource": 1},
        )


    def test_unique_typed_local_gets_role_name(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_LOCAL_00000000000000000010",
                "source_method_id": "SRC_METHOD_00000000000000000001",
                "canonical_method_id": "CLIENT_METHOD_000010",
                "kind": "local",
                "ordinal": 0,
                "current_name": "var8",
                "declared_type": "recovered.spawnpk.client.Player",
            }
        ])
        out = build_source_name_candidates(
            inv,
            _lineage([]),
        )
        self.assertEqual(
            out["candidates"][0]["proposed_name"],
            "player",
        )
        self.assertEqual(
            out["candidates"][0]["confidence"],
            0.82,
        )

    def test_duplicate_typed_locals_are_left_unproposed(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_LOCAL_00000000000000000011",
                "source_method_id": "SRC_METHOD_00000000000000000002",
                "canonical_method_id": "CLIENT_METHOD_000010",
                "kind": "local",
                "ordinal": 0,
                "current_name": "var9",
                "declared_type": "recovered.spawnpk.client.Player",
            },
            {
                "source_symbol_id": "SRC_LOCAL_00000000000000000012",
                "source_method_id": "SRC_METHOD_00000000000000000002",
                "canonical_method_id": "CLIENT_METHOD_000010",
                "kind": "local",
                "ordinal": 1,
                "current_name": "var10",
                "declared_type": "recovered.spawnpk.client.Player",
            },
        ])
        out = build_source_name_candidates(
            inv,
            _lineage([]),
        )
        self.assertEqual(out["candidates"], [])

    def test_generic_local_type_is_not_used_as_role(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_LOCAL_00000000000000000013",
                "source_method_id": "SRC_METHOD_00000000000000000003",
                "canonical_method_id": "CLIENT_METHOD_000010",
                "kind": "local",
                "ordinal": 0,
                "current_name": "var11",
                "declared_type": "java.util.List<Player>",
            }
        ])
        out = build_source_name_candidates(
            inv,
            _lineage([]),
        )
        self.assertEqual(out["candidates"], [])


    def test_acronym_type_names_become_java_style_lower_camel(self):
        inv = _inventory([
            {
                "source_symbol_id": "SRC_RESOURCE_00000000000000000003",
                "canonical_method_id": None,
                "kind": "resource",
                "ordinal": 0,
                "current_name": "var12",
                "declared_type": "java.net.URL",
            },
            {
                "source_symbol_id": "SRC_LOCAL_00000000000000000014",
                "source_method_id": "SRC_METHOD_00000000000000000004",
                "canonical_method_id": "CLIENT_METHOD_000010",
                "kind": "local",
                "ordinal": 0,
                "current_name": "var13",
                "declared_type": "example.URLDecoder",
            },
        ])
        out = build_source_name_candidates(
            inv,
            _lineage([]),
        )
        names = {
            row["source_symbol_id"]: row["proposed_name"]
            for row in out["candidates"]
        }
        self.assertEqual(
            names["SRC_RESOURCE_00000000000000000003"],
            "url",
        )
        self.assertEqual(
            names["SRC_LOCAL_00000000000000000014"],
            "urlDecoder",
        )


    def test_reserved_inferred_name_is_skipped_before_r6b(self):
        inv = _inventory([
            _param(
                "SRC_PARAM_00000000000000000006",
                "CLIENT_METHOD_000012",
                "var14",
                "java.lang.Class",
            )
        ])
        members = _lineage([
            _method(
                "CLIENT_METHOD_000012",
                "setClass",
            )
        ])
        out = build_source_name_candidates(inv, members)
        self.assertEqual(out["candidates"], [])

    def test_noop_current_name_is_skipped(self):
        inv = _inventory([
            _param(
                "SRC_PARAM_00000000000000000004",
                "CLIENT_METHOD_000010",
                "enabled",
                "boolean",
            )
        ])
        members = _lineage([
            _method(
                "CLIENT_METHOD_000010",
                "setEnabled",
            )
        ])
        out = build_source_name_candidates(inv, members)
        self.assertEqual(out["candidates"], [])
        self.assertEqual(out["candidates"], [])


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import hashlib
import tempfile
import unittest

from spk_recovery.source_name_flow import (
    SourceNameFlowError,
    build_source_name_flow_evidence,
)
from spk_recovery.source_name_intelligence import (
    build_source_name_candidate_diagnostics,
    build_source_name_candidates,
)


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(root.rglob("*.java")):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _field(member_id, name):
    return {
        "member_id": member_id,
        "owner_logical_id": "CLIENT_CLASS_000001",
        "kind": "field",
        "semantic_name": name,
        "semantic_status": "ACCEPTED",
    }


def _method(member_id, name):
    return {
        "member_id": member_id,
        "owner_logical_id": "CLIENT_CLASS_000001",
        "kind": "method",
        "semantic_name": name,
        "semantic_status": "ACCEPTED",
    }


def _lineage(*members):
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "members": list(members),
    }


def _inventory(root, source, *, names=("var1", "var2")):
    on_disk = (root / "Example.java").read_bytes().decode("utf-8")
    method_start = on_disk.index("void configure")
    return {
        "schema_version": 1,
        "kind": "source_symbol_inventory",
        "inventory_id": "SRCINV_0123456789ABCDEF0123",
        "source_tree_sha256": _tree_digest(root),
        "methods": [
            {
                "source_file": "Example.java",
                "owner_internal_name": "Example",
                "name": "configure",
                "arity": len(names),
                "start": method_start,
                "source_method_id": "SRC_METHOD_TEST",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "canonical_method_id": "CLIENT_METHOD_000001",
            }
        ],
        "symbols": [
            {
                "source_symbol_id": (
                    "SRC_PARAM_0000000000000000000"
                    + str(i + 1)
                ),
                "source_method_id": "SRC_METHOD_TEST",
                "canonical_method_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "parameter",
                "ordinal": i,
                "current_name": name,
                "declared_type": (
                    "boolean" if i == 0 else "int"
                ),
            }
            for i, name in enumerate(names)
        ],
    }


def _inventory_with_duplicate_locals(root, source):
    on_disk = (root / "Example.java").read_bytes().decode("utf-8")
    method_start = on_disk.index("void configure")
    local1_start = on_disk.index("Player var1")
    local2_start = on_disk.index("Player var2")
    return {
        "schema_version": 1,
        "kind": "source_symbol_inventory",
        "inventory_id": "SRCINV_1123456789ABCDEF0123",
        "source_tree_sha256": _tree_digest(root),
        "methods": [
            {
                "source_file": "Example.java",
                "owner_internal_name": "Example",
                "name": "configure",
                "arity": 1,
                "start": method_start,
                "source_method_id": "SRC_METHOD_LOCALS",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "canonical_method_id": "CLIENT_METHOD_000020",
            }
        ],
        "symbols": [
            {
                "source_symbol_id": "SRC_PARAM_10000000000000000001",
                "source_method_id": "SRC_METHOD_LOCALS",
                "canonical_method_id": "CLIENT_METHOD_000020",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "parameter",
                "ordinal": 0,
                "current_name": "flag",
                "declared_type": "boolean",
                "start": on_disk.index("boolean flag"),
            },
            {
                "source_symbol_id": "SRC_LOCAL_10000000000000000001",
                "source_method_id": "SRC_METHOD_LOCALS",
                "canonical_method_id": "CLIENT_METHOD_000020",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "local",
                "ordinal": 0,
                "current_name": "var1",
                "declared_type": "Player",
                "start": local1_start,
            },
            {
                "source_symbol_id": "SRC_LOCAL_10000000000000000002",
                "source_method_id": "SRC_METHOD_LOCALS",
                "canonical_method_id": "CLIENT_METHOD_000020",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "local",
                "ordinal": 1,
                "current_name": "var2",
                "declared_type": "Player",
                "start": local2_start,
            },
        ],
    }


class SourceNameFlowTests(unittest.TestCase):
    def _workspace(self, source):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "Example.java").write_text(
            source,
            encoding="utf-8",
        )
        return td, root

    def test_multi_parameter_direct_field_assignment_produces_bindings(self):
        source = """public class Example {
    boolean enabled;
    int count;
    void configure(boolean var1, int var2) {
        this.enabled = var1;
        this.count = var2;
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory(root, source)
            lineage = _lineage(
                _field("CLIENT_FIELD_000001", "enabled"),
                _field("CLIENT_FIELD_000002", "count"),
            )
            flow = build_source_name_flow_evidence(
                inventory,
                lineage,
                root,
            )

            self.assertFalse(flow["canonical"])
            self.assertEqual(
                flow["summary"]["matched_bindings"],
                2,
            )
            self.assertEqual(
                flow["summary"]["ambiguous_bindings"],
                0,
            )

            candidates = build_source_name_candidates(
                inventory,
                lineage,
                flow,
            )
            names = {
                row["source_symbol_id"]: row["proposed_name"]
                for row in candidates["candidates"]
            }
            self.assertEqual(
                names[
                    "SRC_PARAM_00000000000000000001"
                ],
                "enabled",
            )
            self.assertEqual(
                names[
                    "SRC_PARAM_00000000000000000002"
                ],
                "count",
            )
            self.assertTrue(
                all(
                    row["confidence"] == 0.96
                    for row in candidates["candidates"]
                )
            )

            diagnostics = (
                build_source_name_candidate_diagnostics(
                    inventory,
                    lineage,
                    candidates,
                    flow,
                )
            )
            self.assertEqual(
                diagnostics["flow_bindings_available"],
                2,
            )
            self.assertEqual(
                diagnostics["flow_ambiguities"],
                0,
            )

    def test_duplicate_type_locals_resolve_from_direct_field_initializers(self):
        source = """public class Example {
    static class Player {}
    Player primaryPlayer;
    Player secondaryPlayer;
    void configure(boolean flag) {
        Player var1 = this.primaryPlayer;
        Player var2 = this.secondaryPlayer;
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory_with_duplicate_locals(
                root,
                source,
            )
            lineage = _lineage(
                _field(
                    "CLIENT_FIELD_100001",
                    "primaryPlayer",
                ),
                _field(
                    "CLIENT_FIELD_100002",
                    "secondaryPlayer",
                ),
            )

            baseline = build_source_name_candidates(
                inventory,
                lineage,
            )
            self.assertEqual(
                baseline["candidates"],
                [],
            )

            flow = build_source_name_flow_evidence(
                inventory,
                lineage,
                root,
            )
            self.assertEqual(
                flow["summary"][
                    "direct_this_field_initializers"
                ],
                2,
            )
            self.assertEqual(
                flow["summary"][
                    "direct_this_field_assignments"
                ],
                0,
            )
            self.assertEqual(
                flow["summary"]["matched_bindings"],
                2,
            )

            out = build_source_name_candidates(
                inventory,
                lineage,
                flow,
            )
            names = {
                row["source_symbol_id"]: (
                    row["proposed_name"],
                    row["confidence"],
                )
                for row in out["candidates"]
            }
            self.assertEqual(
                names[
                    "SRC_LOCAL_10000000000000000001"
                ],
                ("primaryPlayer", 0.94),
            )
            self.assertEqual(
                names[
                    "SRC_LOCAL_10000000000000000002"
                ],
                ("secondaryPlayer", 0.94),
            )
            families = {
                evidence["family"]
                for row in out["candidates"]
                for evidence in row["evidence"]
            }
            self.assertIn(
                "direct_this_field_initializer",
                families,
            )

    def test_non_this_member_assignment_is_ignored(self):
        source = """public class Example {
    Example other;
    boolean enabled;
    void configure(boolean var1) {
        other.enabled = var1;
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory(
                root,
                source,
                names=("var1",),
            )
            lineage = _lineage(
                _field("CLIENT_FIELD_000001", "enabled")
            )
            flow = build_source_name_flow_evidence(
                inventory,
                lineage,
                root,
            )
            self.assertEqual(flow["bindings"], [])
            self.assertEqual(
                flow["summary"][
                    "direct_this_field_assignments"
                ],
                0,
            )

    def test_symbol_assigned_to_multiple_accepted_fields_is_ambiguous(self):
        source = """public class Example {
    boolean enabled;
    boolean visible;
    void configure(boolean var1) {
        this.enabled = var1;
        this.visible = var1;
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory(
                root,
                source,
                names=("var1",),
            )
            lineage = _lineage(
                _field("CLIENT_FIELD_000001", "enabled"),
                _field("CLIENT_FIELD_000002", "visible"),
            )
            flow = build_source_name_flow_evidence(
                inventory,
                lineage,
                root,
            )
            self.assertEqual(flow["bindings"], [])
            self.assertEqual(
                flow["ambiguities"][0]["reason"],
                "source_symbol_maps_to_multiple_accepted_fields",
            )

    def test_one_field_receiving_multiple_source_symbols_is_ambiguous(self):
        source = """public class Example {
    int count;
    void configure(boolean var1, int var2) {
        this.count = var1 ? 1 : 0;
        this.count = var2;
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory(root, source)
            lineage = _lineage(
                _field("CLIENT_FIELD_000002", "count")
            )
            flow = build_source_name_flow_evidence(
                inventory,
                lineage,
                root,
            )
            self.assertEqual(
                len(flow["bindings"]),
                1,
            )
            self.assertEqual(
                flow["bindings"][0]["source_symbol_id"],
                "SRC_PARAM_00000000000000000002",
            )

        source2 = """public class Example {
    int count;
    void configure(boolean var1, int var2) {
        this.count = var1;
        this.count = var2;
    }
}
"""
        td2, root2 = self._workspace(source2)
        with td2:
            inventory2 = _inventory(root2, source2)
            flow2 = build_source_name_flow_evidence(
                inventory2,
                lineage,
                root2,
            )
            self.assertEqual(flow2["bindings"], [])
            reasons = {
                row["reason"]
                for row in flow2["ambiguities"]
            }
            self.assertIn(
                "accepted_field_maps_to_multiple_source_symbols",
                reasons,
            )

    def test_existing_setter_candidate_is_corroborated(self):
        source = """public class Example {
    boolean enabled;
    void configure(boolean var1) {
        this.enabled = var1;
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory(
                root,
                source,
                names=("var1",),
            )
            inventory["methods"][0][
                "canonical_method_id"
            ] = "CLIENT_METHOD_000010"
            inventory["symbols"][0][
                "canonical_method_id"
            ] = "CLIENT_METHOD_000010"
            lineage = _lineage(
                _field("CLIENT_FIELD_000001", "enabled"),
                _method("CLIENT_METHOD_000010", "setEnabled"),
            )
            flow = build_source_name_flow_evidence(
                inventory,
                lineage,
                root,
            )
            out = build_source_name_candidates(
                inventory,
                lineage,
                flow,
            )
            self.assertEqual(
                len(out["candidates"]),
                1,
            )
            row = out["candidates"][0]
            self.assertEqual(
                row["proposed_name"],
                "enabled",
            )
            self.assertEqual(row["confidence"], 0.96)
            families = {
                evidence["family"]
                for evidence in row["evidence"]
            }
            self.assertIn(
                "accepted_method_semantics",
                families,
            )
            self.assertIn(
                "direct_this_field_assignment",
                families,
            )
            diagnostics = (
                build_source_name_candidate_diagnostics(
                    inventory,
                    lineage,
                    out,
                    flow,
                )
            )
            self.assertEqual(
                diagnostics[
                    "flow_corroborated_candidates"
                ],
                1,
            )
            self.assertEqual(
                diagnostics[
                    "flow_semantic_disagreements"
                ],
                0,
            )

    def test_conflicting_setter_and_field_semantics_fail_closed(self):
        source = """public class Example {
    boolean enabled;
    void configure(boolean var1) {
        this.enabled = var1;
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory(
                root,
                source,
                names=("var1",),
            )
            inventory["methods"][0][
                "canonical_method_id"
            ] = "CLIENT_METHOD_000010"
            inventory["symbols"][0][
                "canonical_method_id"
            ] = "CLIENT_METHOD_000010"
            lineage = _lineage(
                _field("CLIENT_FIELD_000001", "enabled"),
                _method("CLIENT_METHOD_000010", "setVisible"),
            )
            flow = build_source_name_flow_evidence(
                inventory,
                lineage,
                root,
            )
            out = build_source_name_candidates(
                inventory,
                lineage,
                flow,
            )
            self.assertEqual(out["candidates"], [])
            diagnostics = (
                build_source_name_candidate_diagnostics(
                    inventory,
                    lineage,
                    out,
                    flow,
                )
            )
            self.assertEqual(
                diagnostics[
                    "flow_semantic_disagreements"
                ],
                1,
            )

    def test_anonymous_class_this_assignment_is_ignored(self):
        source = """public class Example {
    boolean enabled;
    void configure(boolean var1) {
        Runnable task = new Runnable() {
            public void run() {
                this.enabled = var1;
            }
        };
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory(
                root,
                source,
                names=("var1",),
            )
            lineage = _lineage(
                _field("CLIENT_FIELD_000001", "enabled")
            )
            flow = build_source_name_flow_evidence(
                inventory,
                lineage,
                root,
            )
            self.assertEqual(flow["bindings"], [])
            self.assertEqual(
                flow["summary"][
                    "direct_this_field_assignments"
                ],
                0,
            )

    def test_stale_source_tree_is_rejected(self):
        source = """public class Example {
    boolean enabled;
    void configure(boolean var1) {
        this.enabled = var1;
    }
}
"""
        td, root = self._workspace(source)
        with td:
            inventory = _inventory(
                root,
                source,
                names=("var1",),
            )
            inventory["source_tree_sha256"] = "f" * 64
            with self.assertRaises(SourceNameFlowError):
                build_source_name_flow_evidence(
                    inventory,
                    _lineage(
                        _field(
                            "CLIENT_FIELD_000001",
                            "enabled",
                        )
                    ),
                    root,
                )


if __name__ == "__main__":
    unittest.main()

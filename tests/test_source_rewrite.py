from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from spk_recovery.source_name_acceptance import (
    SourceNameAcceptanceError,
    build_source_rename_plan,
)
from spk_recovery.source_name_review import resolve_source_name_candidates
from spk_recovery.source_rewrite import rewrite_source_workspace
from spk_recovery.source_symbols import build_source_symbol_inventory


def _tree_digest(root: Path) -> str:
    files = sorted(root.rglob("*.java"))
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _class_lineage():
    return {
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
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "internal_name": "rs/A",
                        "entry_path": "rs/A.class",
                        "entry_sha256": "b" * 64,
                        "structural_sha256": "c" * 64,
                        "relation": "BASELINE",
                        "confidence": 1.0,
                        "provenance": [],
                    }
                ],
                "semantic_provenance": [],
            }
        ],
        "unresolved": [],
    }


def _member_record(member_id: str, name: str, desc: str):
    return {
        "member_id": member_id,
        "owner_logical_id": "CLIENT_CLASS_000001",
        "kind": "method",
        "semantic_name": None,
        "semantic_status": "UNKNOWN",
        "semantic_confidence": 0.0,
        "lineage": [
            {
                "build_id": "v308",
                "owner_internal_name": "rs/A",
                "name": name,
                "descriptor": desc,
                "access": 1,
                "code_length": 1,
                "relation": "BASELINE",
                "confidence": 1.0,
                "provenance": [],
            }
        ],
        "semantic_provenance": [],
    }


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "a" * 64,
        "members": [
            _member_record("CLIENT_METHOD_000001", "work", "(I)I"),
            _member_record("CLIENT_METHOD_000002", "other", "(I)I"),
        ],
        "unresolved": [],
    }


def _candidate_set(inventory, rows):
    return {
        "schema_version": 1,
        "kind": "source_name_candidate_set",
        "canonical": False,
        "inventory_id": inventory["inventory_id"],
        "source_tree_sha256": inventory["source_tree_sha256"],
        "candidates": rows,
    }


def _candidate(symbol_id: str, name: str):
    return {
        "source_symbol_id": symbol_id,
        "proposed_name": name,
        "confidence": 0.92,
        "evidence": [
            {
                "family": "test_dataflow",
                "detail": "synthetic semantic evidence",
            }
        ],
    }


@unittest.skipUnless(
    shutil.which("java") and shutil.which("javac"),
    "Java toolchain required",
)
class SourceRewriteTests(unittest.TestCase):
    def _fixture(self, root: Path):
        src = root / "input" / "rs"
        src.mkdir(parents=True)
        java = src / "A.java"
        java.write_text(
            """
package rs;
public class A {
    public int work(int x) {
        int count = x + 1;
        count += x;
        return count;
    }

    public int other(int x) {
        return x + 10;
    }
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        source_root = root / "input"
        digest = _tree_digest(source_root)
        manifest = {
            "schema_version": 1,
            "kind": "recovered_source_workspace_manifest",
            "workspace_id": "SRCWS_TEST",
            "build_id": "v308",
            "source_authority_sha256": "a" * 64,
            "readable_jar_sha256": "d" * 64,
            "namespace_id": "SEMNS_TEST",
            "class_plan_digest": "e" * 64,
            "member_plan_digest": "f" * 64,
            "engine": "cfr",
            "decompiler_sha256": "1" * 64,
            "source_tree_sha256": digest,
            "java_file_count": 1,
            "source_bytes": java.stat().st_size,
            "source_directory": "src",
        }
        inventory = build_source_symbol_inventory(
            manifest,
            source_root,
            _class_lineage(),
            _member_lineage(),
            build_id="v308",
        )
        return source_root, inventory

    def _symbols(self, inventory):
        work = [
            row
            for row in inventory["symbols"]
            if row["method_name"] == "work"
        ]
        parameter = [
            row for row in work
            if row["kind"] == "parameter"
            and row["current_name"] == "x"
        ][0]
        local = [
            row for row in work
            if row["kind"] == "local"
            and row["current_name"] == "count"
        ][0]
        return parameter, local

    def test_acceptance_refuses_method_scope_collision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, inventory = self._fixture(root)
            parameter, _ = self._symbols(inventory)

            review = resolve_source_name_candidates(
                inventory,
                _candidate_set(
                    inventory,
                    [_candidate(parameter["source_symbol_id"], "count")],
                ),
            )
            acceptance = {
                "schema_version": 1,
                "kind": "source_name_acceptance",
                "inventory_id": inventory["inventory_id"],
                "review_id": review["review_id"],
                "accepted_proposal_ids": [
                    review["proposals"][0]["proposal_id"]
                ],
                "note": "reviewed",
            }
            with self.assertRaises(SourceNameAcceptanceError):
                build_source_rename_plan(
                    inventory,
                    review,
                    acceptance,
                )

    def test_semantic_rewrite_changes_only_bound_variable_elements(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root, inventory = self._fixture(root)
            parameter, local = self._symbols(inventory)

            review = resolve_source_name_candidates(
                inventory,
                _candidate_set(
                    inventory,
                    [
                        _candidate(
                            parameter["source_symbol_id"],
                            "itemId",
                        ),
                        _candidate(
                            local["source_symbol_id"],
                            "total",
                        ),
                    ],
                ),
            )
            acceptance = {
                "schema_version": 1,
                "kind": "source_name_acceptance",
                "inventory_id": inventory["inventory_id"],
                "review_id": review["review_id"],
                "accepted_proposal_ids": [
                    row["proposal_id"]
                    for row in review["proposals"]
                ],
                "note": "synthetic reviewed source names",
            }
            plan = build_source_rename_plan(
                inventory,
                review,
                acceptance,
            )

            first = rewrite_source_workspace(
                plan,
                source_root,
                out_dir=root / "first",
            )
            second = rewrite_source_workspace(
                plan,
                source_root,
                out_dir=root / "second",
            )

            self.assertEqual(
                first["output_source_tree_sha256"],
                second["output_source_tree_sha256"],
            )
            self.assertEqual(first["accepted_rename_count"], 2)
            self.assertGreaterEqual(first["identifier_replacements"], 6)

            rewritten = (
                root / "first" / "src" / "rs" / "A.java"
            ).read_text(encoding="utf-8")
            self.assertIn("work(int itemId)", rewritten)
            self.assertIn("int total = itemId + 1;", rewritten)
            self.assertIn("total += itemId;", rewritten)
            self.assertIn("return total;", rewritten)

            # Same raw variable spelling in another method must not be touched.
            self.assertIn("other(int x)", rewritten)
            self.assertIn("return x + 10;", rewritten)

            original = (
                source_root / "rs" / "A.java"
            ).read_text(encoding="utf-8")
            self.assertIn("work(int x)", original)
            self.assertIn("int count = x + 1;", original)


if __name__ == "__main__":
    unittest.main()

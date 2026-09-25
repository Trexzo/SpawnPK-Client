from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from spk_recovery.source_digest import source_tree_digest
from spk_recovery.source_symbols import build_source_symbol_inventory


def _tree_digest(root: Path) -> str:
    return source_tree_digest(root)[0]


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


def _member_lineage():
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "a" * 64,
        "members": [
            {
                "member_id": "CLIENT_METHOD_000001",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "method",
                "semantic_name": None,
                "semantic_status": "UNKNOWN",
                "semantic_confidence": 0.0,
                "lineage": [
                    {
                        "build_id": "v308",
                        "owner_internal_name": "rs/A",
                        "name": "work",
                        "descriptor": "(ILjava/lang/String;)V",
                        "access": 1,
                        "code_length": 1,
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


@unittest.skipUnless(
    shutil.which("java") and shutil.which("javac"),
    "Java toolchain required",
)
class SourceSymbolInventoryTests(unittest.TestCase):
    def test_ast_inventory_is_deterministic_and_links_method(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "rs"
            src.mkdir(parents=True)
            (src / "A.java").write_text(
                """
package rs;
public class A {
    public void work(int x, String name) {
        int count = x;
        try {
            int y = 1;
        } catch (RuntimeException ex) {
            int caught = 1;
        }
        for (String value : java.util.List.of(name)) {
            int z = value.length();
        }
    }
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            digest = _tree_digest(root)
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
                "source_bytes": source_tree_digest(root)[2],
                "source_directory": "src",
            }

            first = build_source_symbol_inventory(
                manifest,
                root,
                _class_lineage(),
                _member_lineage(),
                build_id="v308",
            )
            second = build_source_symbol_inventory(
                manifest,
                root,
                _class_lineage(),
                _member_lineage(),
                build_id="v308",
            )

            self.assertEqual(first["inventory_id"], second["inventory_id"])
            self.assertEqual(
                [x["source_symbol_id"] for x in first["symbols"]],
                [x["source_symbol_id"] for x in second["symbols"]],
            )

            work = [
                method
                for method in first["methods"]
                if method["name"] == "work"
            ][0]
            self.assertEqual(
                work["canonical_method_id"],
                "CLIENT_METHOD_000001",
            )

            kinds = {row["kind"] for row in first["symbols"]}
            self.assertIn("parameter", kinds)
            self.assertIn("local", kinds)
            self.assertIn("catch", kinds)
            self.assertIn("enhanced_for", kinds)
            self.assertEqual(first["summary"]["parameters"], 2)
            self.assertEqual(first["summary"]["orphan_variables"], 0)


if __name__ == "__main__":
    unittest.main()

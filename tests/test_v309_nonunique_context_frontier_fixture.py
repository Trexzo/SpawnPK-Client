from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = (
    ROOT
    / "research"
    / "v309-field-recovery"
    / "canonical-method-field-context.json"
)


class V309NonuniqueContextFrontierFixtureTests(unittest.TestCase):
    def test_tracked_frontier_has_expected_nonunique_context_residual(self):
        context = json.loads(CONTEXT.read_text(encoding="utf-8"))

        rows = [
            row
            for row in context["rejected"]
            if row.get("reason") == "canonical_method_context_nonunique"
        ]
        self.assertEqual(len(rows), 6)

        owners = {row.get("logical_class_id") for row in rows}
        methods = {row.get("method_id") for row in rows}
        operations = {row.get("operation") for row in rows}
        uniqueness = {
            (row.get("old_unique"), row.get("new_unique"))
            for row in rows
        }

        self.assertEqual(owners, {"CLIENT_CLASS_000113"})
        self.assertEqual(methods, {"CLIENT_METHOD_005704"})
        self.assertEqual(operations, {"putfield"})
        self.assertEqual(uniqueness, {(False, False)})

        ids = {row["relationship_id"] for row in rows}
        self.assertEqual(
            ids,
            {
                "MEMREL_3A07534051FC0496",
                "MEMREL_41F1BA7778A5CE9B",
                "MEMREL_5D7B8E4C8A99F236",
                "MEMREL_64E30CA3D5C206AE",
                "MEMREL_85822239CBE93753",
                "MEMREL_D5AE99F99841F713",
            },
        )


if __name__ == "__main__":
    unittest.main()

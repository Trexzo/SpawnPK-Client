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


class V309MissingContextFrontierFixtureTests(unittest.TestCase):
    def test_tracked_frontier_has_exact_one_missing_context_row(self):
        context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        rows = [
            row for row in context["rejected"]
            if row.get("reason") == "canonical_method_context_missing"
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["relationship_id"], "MEMREL_532D72C8DD8ECFDC")
        self.assertEqual(row["logical_class_id"], "CLIENT_CLASS_000889")
        self.assertEqual(row["method_id"], "CLIENT_METHOD_003028")
        self.assertEqual(row["operation"], "getstatic")
        self.assertEqual(row["expected_count"], 1)
        self.assertEqual(row["old_context_count"], 0)
        self.assertEqual(row["new_context_count"], 0)


if __name__ == "__main__":
    unittest.main()

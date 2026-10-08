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
FRONTIER = (
    ROOT
    / "research"
    / "v309-field-recovery"
    / "frontier.json"
)


class V309SingleContextFrontierFixtureTests(unittest.TestCase):
    def test_tracked_143_frontier_has_expected_single_context_residual(self):
        context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        frontier = json.loads(FRONTIER.read_text(encoding="utf-8"))

        self.assertEqual(
            context["report_id"],
            "METHODCTX_AC21811B4B4AC7112489",
        )
        self.assertEqual(
            frontier["files"]["canonical_method_field_context"]["report_id"],
            context["report_id"],
        )
        self.assertEqual(frontier["frontier"]["unresolved"], 143)
        self.assertEqual(
            frontier["frontier"]["method_context_insufficient_witness"],
            41,
        )

        rows = [
            row
            for row in context["rejected"]
            if row.get("reason")
            == "insufficient_independent_context_witness"
        ]
        self.assertEqual(len(rows), 41)

        shapes: dict[tuple[int, int, int, int], int] = {}
        for row in rows:
            witnesses = row.get("method_witnesses")
            shape = (
                row.get("canonical_methods"),
                row.get("observations"),
                row.get("distinct_contexts"),
                len(witnesses) if isinstance(witnesses, list) else -1,
            )
            shapes[shape] = shapes.get(shape, 0) + 1

        self.assertEqual(
            shapes,
            {
                (1, 1, 1, 1): 39,
                (1, 2, 1, 1): 2,
            },
        )


if __name__ == "__main__":
    unittest.main()

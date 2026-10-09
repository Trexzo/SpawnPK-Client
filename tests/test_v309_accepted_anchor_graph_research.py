from __future__ import annotations

import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from spk_recovery import v309_accepted_anchor_graph_research as graph


class AcceptedAnchorGraphTests(unittest.TestCase):
    def test_typed_jvm_references_without_ordinary_cp_string_guessing(self):
        self.assertEqual(graph._type_names("(La/Target;[Lb/Other;)V"),
                         {"a/Target", "b/Other"})
        self.assertEqual(graph._type_names("a/Target"), set())
        self.assertEqual(graph._type_names("a/Target", owner=True), {"a/Target"})
        self.assertEqual(graph._type_names("private text has a/b literal"), set())

    def test_descriptor_and_actual_code_channels_both_count(self):
        fake = SimpleNamespace(
            super_name="a/Parent", interfaces=["a/Iface"],
            fields=[{"descriptor": "La/Field;"}],
            methods=[{"descriptor": "(La/Argument;)La/Return;"}],
        )
        profile = {"methods": [{
            "instructions": [
                {"owner": "a/Call", "descriptor": "(La/Parameter;)V"},
                {"type": "[La/Cast;"},
                {"constant_pool_tag": 7, "constant": "a/ClassConstant"},
                {"constant_pool_tag": 8, "constant": "a/StringLiteralNotType"},
            ],
            "exception_handlers": [{"catch_type": "a/Caught"}],
        }]}
        with patch.object(graph, "parse_class", return_value=fake):
            refs = graph._typed_references(b"synthetic", profile)
        self.assertEqual(refs, {
            "a/Parent", "a/Iface", "a/Field", "a/Argument",
            "a/Return", "a/Call", "a/Parameter", "a/Cast",
            "a/ClassConstant", "a/Caught",
        })
        self.assertNotIn("a/StringLiteralNotType", refs)

    def test_full_archive_superset_veto_not_hidden_by_matching_set(self):
        incoming = {
            "target": {"L1", "L2"},
            "rival.same": {"L1", "L2"},
            "rival.superset": {"L1", "L2", "L3"},
            "rival.partial": {"L1"},
            "paired.other": {"L1", "L2"},
        }
        all_classes = set(incoming)
        paired = {"paired.other"}
        row = graph._summarize_incoming(
            incoming, "target", all_classes, paired)
        self.assertEqual(row["incoming_accepted_anchor_count"], 2)
        self.assertEqual(row["other_archive_classes_same_anchor_set"], 2)
        self.assertEqual(row["other_unpaired_classes_same_anchor_set"], 1)
        self.assertEqual(row["other_archive_classes_superset_anchor_set"], 3)
        self.assertEqual(row["other_unpaired_classes_superset_anchor_set"], 2)

    def test_no_inbound_accepted_anchors_fails_closed(self):
        with self.assertRaises(graph.V309AnchorGraphError):
            graph._summarize_incoming(
                {"other": {"A"}}, "target", {"target", "other"}, set())
        with self.assertRaises(graph.V309AnchorGraphError):
            graph._summarize_incoming(
                {"target": {"A"}}, "target", {"other"}, set())

    def test_no_private_exception_text_or_output_on_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "new-report.json"
            args = [
                "--v308-jar", "x.jar", "--v309-jar", "y.jar",
                "--frontier", "frontier.json",
                "--class-lineage", "lineage.json",
                "--global-report", "global.json",
                "--out", str(out),
            ]
            with patch.object(graph, "build_v309_anchor_graph",
                              side_effect=ValueError("PRIVATE_OWNER=rs/secret")):
                with contextlib.redirect_stdout(io.StringIO()) as capture:
                    code = graph.main(args)
            self.assertEqual(code, 1)
            self.assertIn("FAIL_CLOSED", capture.getvalue())
            self.assertNotIn("PRIVATE_OWNER", capture.getvalue())
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()

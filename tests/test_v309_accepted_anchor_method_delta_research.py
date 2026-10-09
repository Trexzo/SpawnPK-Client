from __future__ import annotations

import copy
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

from spk_recovery.v309_accepted_anchor_method_delta_research import (
    V309MethodDeltaResearchError,
    _dice,
    _opcode_grams,
    _removed_invokestatic_continuity,
    main,
)


def _method(name: str, *, owner: str | None = None, times: int = 1):
    opcodes = [
        "0x2a", "0x59", "0xb6", "0x2a",
        *(("0xb8" for _ in range(times)) if owner else ()),
        "0x57", "0x2a", "0x57", "0x03", "0xac",
    ]
    instructions = [
        {"opcode": code, "owner": owner if code == "0xb8" else ""}
        for code in opcodes
    ]
    return {
        "name": name, "descriptor": "()I", "access": 1,
        "code_length": len(instructions), "instructions": instructions,
        "exception_handlers": [],
    }


def _profiles():
    old = {"methods": [_method("main", owner="accepted/Old")]}
    new = {"methods": [
        _method("main"),
        _method("unrelated", owner="somewhere/New"),
    ]}
    return old, new


class AcceptedAnchorMethodDeltaTests(unittest.TestCase):
    def compare(self, old=None, new=None):
        base_old, base_new = _profiles()
        return _removed_invokestatic_continuity(
            old if old is not None else base_old,
            new if new is not None else base_new,
            old_target="accepted/Old", new_target="accepted/New",
        )

    def test_exact_named_member_method_delta_is_research_only(self):
        m = self.compare()
        self.assertEqual(m["old_static_call_occurrences"], 1)
        self.assertEqual(m["new_static_call_occurrences"], 0)
        self.assertTrue(m["removed_call_is_inside_changed_region"])
        self.assertEqual(m["exact_new_same_name_descriptor_access_matches"], 1)
        self.assertFalse(m["canonical_member_identity_accepted"])
        self.assertGreater(m["opcode_5gram_dice"], m["next_best_opcode_5gram_dice"])
        self.assertGreater(m["opcode_sequence_alignment_ratio"], 0.8)

    def test_ambiguous_old_calls_do_not_qualify(self):
        old, new = _profiles()
        old["methods"].append(_method("different", owner="accepted/Old"))
        with self.assertRaises(V309MethodDeltaResearchError):
            self.compare(old=old, new=new)

    def test_more_than_one_old_call_does_not_qualify(self):
        old, new = _profiles()
        old["methods"][0] = _method("main", owner="accepted/Old", times=2)
        with self.assertRaises(V309MethodDeltaResearchError):
            self.compare(old=old, new=new)

    def test_old_accepted_call_still_present_in_new_is_rejected(self):
        old, new = _profiles()
        new["methods"][0] = _method("main", owner="accepted/New")
        with self.assertRaises(V309MethodDeltaResearchError):
            self.compare(old=old, new=new)

    def test_changed_method_name_does_not_auto_accept_another_method(self):
        old, new = _profiles()
        new["methods"][0]["name"] = "renamed"
        with self.assertRaises(V309MethodDeltaResearchError):
            self.compare(old=old, new=new)

    def test_duplicate_same_member_declaration_is_rejected(self):
        old, new = _profiles()
        new["methods"].append(copy.deepcopy(new["methods"][0]))
        with self.assertRaises(V309MethodDeltaResearchError):
            self.compare(old=old, new=new)

    def test_candidate_code_differences_are_not_treated_as_semantic_identity(self):
        old, new = _profiles()
        new["methods"][0]["instructions"][0]["opcode"] = "0x2b"
        m = self.compare(old=old, new=new)
        self.assertLess(m["opcode_sequence_alignment_ratio"], 1)
        self.assertFalse(m["canonical_member_identity_accepted"])

    def test_gram_score_is_bounded_and_requires_exact_opcode_order(self):
        a = _opcode_grams({"instructions": [
            {"opcode": x} for x in ["0x01", "0x02", "0x03", "0x04", "0x05", "0x06"]
        ]})
        b = _opcode_grams({"instructions": [
            {"opcode": x} for x in ["0x02", "0x01", "0x03", "0x04", "0x05", "0x06"]
        ]})
        self.assertEqual(_dice(a, a), 1.0)
        self.assertLess(_dice(a, b), 1.0)

    def test_no_clobber_and_no_private_path_in_failure(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            target = path / "existing.json"
            target.write_text("LEAVE_OLD_REPORT", encoding="utf-8")
            with redirect_stdout(io.StringIO()) as out:
                status = main([
                    "--v308-jar", str(path / "missing-private.jar"),
                    "--v309-jar", str(path / "missing-private2.jar"),
                    "--frontier", str(path / "missing-frontier.json"),
                    "--class-lineage", str(path / "missing-lineage.json"),
                    "--global-report", str(path / "missing-report.json"),
                    "--out", str(target),
                ])
            self.assertEqual(status, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "LEAVE_OLD_REPORT")
            self.assertNotIn(root, out.getvalue())

    def test_missing_private_inputs_create_no_report(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            target = path / "new.json"
            with redirect_stdout(io.StringIO()) as out:
                status = main([
                    "--v308-jar", str(path / "missing-private.jar"),
                    "--v309-jar", str(path / "missing-private2.jar"),
                    "--frontier", str(path / "missing-frontier.json"),
                    "--class-lineage", str(path / "missing-lineage.json"),
                    "--global-report", str(path / "missing-report.json"),
                    "--out", str(target),
                ])
            self.assertEqual(status, 1)
            self.assertFalse(target.exists())
            self.assertIn("FAIL_CLOSED", out.getvalue())


if __name__ == "__main__":
    unittest.main()

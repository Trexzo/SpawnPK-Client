"""R119 synthetic three-stage replay ordering, SHA lease and fail-closed tests."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import spk_recovery.private_v309_three_stage_replay_r119 as gate


class PrivateThreeStageReplayR119Tests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.original = self.root / "original.jar"
        self.source = self.root / "source.jar"
        self.original.write_bytes(b"synthetic original only")
        self.source.write_bytes(b"independent javac9 output")
        self.out = self.root / "accepted"
        self.events = []
        self.pin = gate.digest(self.original)
        self.candidate_pin = gate.digest(self.source)

    def replay(self, original_sha=None, candidate_sha=None):
        return gate.replay_source_owner(
            self.original, self.source, "p/Owner.class", "Surrogate",
            self.out, original_sha256=original_sha or self.pin,
            source_sha256=candidate_sha or self.candidate_pin,
        )

    def mocked(self, *, fail=None, mismatch=None):
        def saver(original, candidate, owner_entry, dest, **kwargs):
            self.events.append("R116")
            self.assertEqual(gate.digest(candidate), kwargs["candidate_sha256"])
            self.assertEqual(owner_entry, "p/Owner.class")
            if fail == "R116":
                raise ValueError("private path must never leak")
            dest = Path(dest)
            dest.mkdir()
            jar = dest / "candidate.saver-frame.PRIVATE.jar"
            jar.write_bytes(b"saver repaired metadata only")
            return {
                "saver_frame_normalized_candidate_sha256":
                    "0" * 64 if mismatch == "R116" else gate.digest(jar),
                "original_saver_R66_R81_operands_and_handlers_passed": True,
                "original_saver_StackMapTable_frames_exact": 10,
                "candidate_saver_Code_bytes_preserved": True,
                "saver_original_executable_Code_transferred": False,
            }

        def loader(original, candidate, owner_entry, dest, **kwargs):
            self.events.append("R117")
            self.assertEqual(gate.digest(candidate), kwargs["candidate_sha256"])
            if fail == "R117":
                raise ValueError("private loader rejected")
            dest = Path(dest)
            dest.mkdir()
            jar = dest / "candidate.large-method-frames.PRIVATE.jar"
            jar.write_bytes(b"loader 161 frames repaired only")
            return {
                "final_both_large_method_candidate_sha256":
                    "0" * 64 if mismatch == "R117" else gate.digest(jar),
                "original_loader_161_frame_ordinals_and_verification_states_equal": True,
                "candidate_697_executable_Code_bytes_preserved": True,
                "original_saver_364_R113_all_operands_10_frames_exact": True,
                "original_executable_Code_bytes_transferred": False,
            }

        def owner(original, candidate, owner_entry, surrogate, dest, **kwargs):
            self.events.append("R118")
            self.assertEqual(gate.digest(candidate), kwargs["candidate_sha256"])
            self.assertEqual(surrogate, "Surrogate")
            if fail == "R118":
                raise ValueError("private combined owner rejected")
            dest = Path(dest)
            dest.mkdir()
            jar = dest / "candidate.private.jar"
            jar.write_bytes(b"final symbolic owner only")
            return {
                "final_all_original_gates_candidate_sha256":
                    "0" * 64 if mismatch == "R118" else gate.digest(jar),
                "R95_original_four_enums_passed": True,
                "R94_original_nine_ordinary_owner_methods_passed": True,
                "R58_original_clinit_operand_semantics_passed": True,
                "R88_original_owner_all_declarations_passed": True,
                "original_loader_161_verification_states_equal": True,
                "original_saver_ten_stackmap_frames_exact": True,
                "whole_original_client_runtime_equivalence_certified": False,
            }

        p = [
            patch.object(gate, "CANONICAL_V309_SHA256", self.pin),
            patch.object(gate, "normalize_saver_then_require_original_r113", saver),
            patch.object(gate, "normalize_original_161_frames_then_require_large_R81", loader),
            patch.object(gate, "accept_one_final_v309_source_compiled_owner", owner),
        ]
        for context in p:
            context.start()
            self.addCleanup(context.stop)

    def test_all_three_private_original_gates_on_one_candidate(self):
        self.mocked()
        report = self.replay()
        self.assertEqual(self.events, ["R116", "R117", "R118"])
        self.assertEqual(report["original_sha256"], self.pin)
        self.assertTrue(report["R118_R95_R94_R58_R88_original_final_owner_passed"])
        self.assertFalse(report["whole_client_runtime_or_gameplay_equivalence_certified"])
        self.assertEqual(len(list(self.out.iterdir())), 2)
        self.assertEqual(gate.digest(self.out / "candidate.private.jar"),
                         report["r118_final_owner_sha256"])
        self.assertEqual(gate.digest(self.original), self.pin)
        self.assertEqual(gate.digest(self.source), self.candidate_pin)

    def test_real_canonical_original_pin_is_a_hard_requirement(self):
        self.mocked()
        with patch.object(gate, "CANONICAL_V309_SHA256", "f" * 64):
            with self.assertRaisesRegex(
                    gate.PrivateThreeStageReplayR119Error,
                    "PINNED_COMPLETE_ORIGINAL_V309_JAR_REQUIRED"):
                self.replay()
        self.assertEqual(self.events, [])
        self.assertFalse(self.out.exists())

    def test_wrong_source_sha_is_rejected_before_replay(self):
        self.mocked()
        with self.assertRaisesRegex(
                gate.PrivateThreeStageReplayR119Error,
                "SOURCE_COMPILED_JAVA9_CANDIDATE_SHA256_REQUIRED"):
            self.replay(candidate_sha="0" * 64)
        self.assertEqual(self.events, [])
        self.assertFalse(self.out.exists())

    def test_changed_original_pin_rejected_before_replay(self):
        self.mocked()
        with self.assertRaisesRegex(
                gate.PrivateThreeStageReplayR119Error,
                "PINNED_COMPLETE_ORIGINAL_V309_JAR_REQUIRED"):
            self.replay(original_sha="0" * 64)
        self.assertEqual(self.events, [])
        self.assertFalse(self.out.exists())

    def test_existing_output_never_overwritten(self):
        self.mocked()
        self.out.mkdir()
        (self.out / "preserve.txt").write_text("intact", encoding="utf-8")
        with self.assertRaisesRegex(
                gate.PrivateThreeStageReplayR119Error,
                "FRESH_PRIVATE_OUTPUT_DIRECTORY_REQUIRED"):
            self.replay()
        self.assertEqual((self.out / "preserve.txt").read_text(), "intact")
        self.assertEqual(self.events, [])

    def test_first_rejected_stage_has_no_accepted_output(self):
        self.mocked(fail="R116")
        with self.assertRaises(ValueError):
            self.replay()
        self.assertEqual(self.events, ["R116"])
        self.assertFalse(self.out.exists())

    def test_second_rejected_stage_has_no_accepted_output(self):
        self.mocked(fail="R117")
        with self.assertRaises(ValueError):
            self.replay()
        self.assertEqual(self.events, ["R116", "R117"])
        self.assertFalse(self.out.exists())

    def test_final_rejected_stage_has_no_accepted_output(self):
        self.mocked(fail="R118")
        with self.assertRaises(ValueError):
            self.replay()
        self.assertEqual(self.events, ["R116", "R117", "R118"])
        self.assertFalse(self.out.exists())

    def test_wrong_middle_postimage_sha_vetoes(self):
        self.mocked(mismatch="R117")
        with self.assertRaisesRegex(
                gate.PrivateThreeStageReplayR119Error,
                "R117_LOADER_POSTIMAGE_UNVERIFIED"):
            self.replay()
        self.assertEqual(self.events, ["R116", "R117"])
        self.assertFalse(self.out.exists())

    def test_wrong_final_postimage_sha_vetoes(self):
        self.mocked(mismatch="R118")
        with self.assertRaisesRegex(
                gate.PrivateThreeStageReplayR119Error,
                "R118_FINAL_OWNER_OR_ENUM_PARITY_UNVERIFIED"):
            self.replay()
        self.assertEqual(self.events, ["R116", "R117", "R118"])
        self.assertFalse(self.out.exists())

    def test_unsafe_owner_path_rejected(self):
        self.mocked()
        with self.assertRaisesRegex(
                gate.PrivateThreeStageReplayR119Error,
                "UNSAFE_OWNER_OR_SOURCE_ENUM_IDENTITY"):
            gate.replay_source_owner(
                self.original, self.source, "../Owner.class", "Surrogate",
                self.out, original_sha256=self.pin,
                source_sha256=self.candidate_pin)
        self.assertEqual(self.events, [])
        self.assertFalse(self.out.exists())

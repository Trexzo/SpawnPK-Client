"""R97: fail-closed composition of exact same private candidate, R90+R94+R95."""
import hashlib
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import tempfile

import spk_recovery.private_complete_v309_owner_acceptance as gate


class PrivateFullOwnerAcceptanceTests(TestCase):
    ORIGINAL = b"synthetic-private-original-jar-pin"
    CANDIDATE = b"synthetic-private-java9-compiled-candidate"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "original.jar"
        self.original.write_bytes(self.ORIGINAL)
        self.pin = hashlib.sha256(self.ORIGINAL).hexdigest()
        self.candidate_pin = hashlib.sha256(self.CANDIDATE).hexdigest()
        self.output = self.root / "accepted"
        self.calls = []

    def r90(self, *args, **kwargs):
        self.calls.append("R90")
        dest = Path(args[11])
        dest.mkdir()
        (dest / "candidate.private.jar").write_bytes(self.CANDIDATE)
        return {
            "both_R87_methods_passed": True,
            "R58_initializer_operand_semantics_passed": True,
            "R88_original_owner_field_metadata_passed": True,
            "original_field_declarations": 126,
            "candidate_field_declarations": 126,
            "original_field_declaration_differences": 0,
            "original_initializer_static_writes": 93,
            "original_unrecovered_method_declarations": 0,
            "original_unrecovered_nested_class_entries": 0,
            "candidate_compiled_jar_sha256": self.candidate_pin,
        }

    def r94(self, *args, **kwargs):
        self.calls.append("R94")
        self.assertEqual(Path(args[1]).read_bytes(), self.CANDIDATE)
        self.assertEqual(kwargs["candidate_sha256"], self.candidate_pin)
        return {
            "R66_and_R81_parity_passed_all_nine_ordinary_methods": True,
            "original_ordinary_methods_parity_checked": 9,
            "original_ordinary_jvm_instruction_operands_compared": 1135,
        }

    def r95(self, *args, **kwargs):
        self.calls.append("R95")
        self.assertEqual(Path(args[1]).read_bytes(), self.CANDIDATE)
        self.assertEqual(kwargs["candidate_sha256"], self.candidate_pin)
        return {
            "original_nested_enum_classes_verified": 4,
            "symbolic_InnerClasses_tables_identical_all_four": True,
            "original_candidate_owner_InnerClasses_tables_identical": True,
        }

    def accept(self):
        return gate.accept_complete_private_v309_owner(
            self.original, "p/Owner.class", "load", "save",
            self.root / "src", "p/Owner.class", "load", "save",
            self.root / "load.json", self.root / "save.json",
            self.root / "clinit.json", self.output, original_sha256=self.pin,
        )

    def test_all_three_gates_use_same_private_jar_and_promote_once(self):
        with patch.object(gate, "accept_original_v309_owner_methods_and_initializer", self.r90), \
             patch.object(gate, "replay_all_original_methods", self.r94), \
             patch.object(gate, "replay_private_four_enum_gate", self.r95):
            proof = self.accept()
        self.assertEqual(self.calls, ["R90", "R94", "R95"])
        self.assertTrue(proof["R95_four_nested_enums_and_InnerClasses_passed"])
        self.assertFalse(proof["whole_original_client_runtime_equivalence_certified"])
        self.assertEqual((self.output / "candidate.private.jar").read_bytes(),
                         self.CANDIDATE)
        self.assertEqual(len(list(self.output.iterdir())), 2)
        self.assertEqual(len(list(self.root.glob("v309-owner-all-gates-*"))), 0)

    def test_original_sha_veto_before_compilation(self):
        with patch.object(gate, "accept_original_v309_owner_methods_and_initializer") as mock:
            with self.assertRaisesRegex(gate.CompleteOwnerAcceptanceError,
                                        "ORIGINAL_JAR_PIN_MISMATCH"):
                gate.accept_complete_private_v309_owner(
                    self.original, "p/Owner.class", "load", "save",
                    self.root / "src", "p/Owner.class", "load", "save",
                    "l", "s", "i", self.output, original_sha256="0" * 64)
            mock.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_different_candidate_owner_veto(self):
        with self.assertRaisesRegex(gate.CompleteOwnerAcceptanceError,
                                    "OWNER_IDENTITY_MUST_MATCH"):
            gate.accept_complete_private_v309_owner(
                self.original, "p/Owner.class", "load", "save",
                self.root / "src", "p/NotOwner.class", "load", "save",
                "l", "s", "i", self.output, original_sha256=self.pin)
        self.assertFalse(self.output.exists())

    def test_missing_one_method_never_promotes(self):
        def incomplete(*args, **kwargs):
            p = self.r90(*args, **kwargs)
            p["original_unrecovered_method_declarations"] = 1
            return p
        with patch.object(gate, "accept_original_v309_owner_methods_and_initializer", incomplete), \
             patch.object(gate, "replay_all_original_methods") as m:
            with self.assertRaisesRegex(gate.CompleteOwnerAcceptanceError,
                                        "DECLARATION_OR_INITIALIZER_INCOMPLETE"):
                self.accept()
            m.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_all_methods_parity_failure_never_promotes(self):
        def fail(*args, **kwargs):
            raise gate.AllOwnerMethodsParityError("changed lambda")
        with patch.object(gate, "accept_original_v309_owner_methods_and_initializer", self.r90), \
             patch.object(gate, "replay_all_original_methods", fail), \
             patch.object(gate, "replay_private_four_enum_gate") as nested:
            with self.assertRaisesRegex(gate.CompleteOwnerAcceptanceError,
                                        "R94_NINE_METHOD_GATE_FAILED"):
                self.accept()
            nested.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_fourth_enum_metadata_mismatch_never_promotes(self):
        def fail(*args, **kwargs):
            raise gate.FourNestedEnumAcceptanceError("fourth flattened enum")
        with patch.object(gate, "accept_original_v309_owner_methods_and_initializer", self.r90), \
             patch.object(gate, "replay_all_original_methods", self.r94), \
             patch.object(gate, "replay_private_four_enum_gate", fail):
            with self.assertRaisesRegex(gate.CompleteOwnerAcceptanceError,
                                        "R95_FOUR_ENUM_GATE_FAILED"):
                self.accept()
        self.assertFalse(self.output.exists())

    def test_changed_candidate_file_sha_never_promotes(self):
        def tamper(*args, **kwargs):
            p = self.r90(*args, **kwargs)
            p["candidate_compiled_jar_sha256"] = "1" * 64
            return p
        with patch.object(gate, "accept_original_v309_owner_methods_and_initializer", tamper), \
             patch.object(gate, "replay_all_original_methods") as m:
            with self.assertRaisesRegex(gate.CompleteOwnerAcceptanceError,
                                        "COMPILED_CANDIDATE_PIN_MISMATCH"):
                self.accept()
            m.assert_not_called()
        self.assertFalse(self.output.exists())

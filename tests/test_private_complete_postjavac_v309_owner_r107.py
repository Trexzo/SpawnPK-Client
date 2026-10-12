"""R107: one exact final post-javac candidate, all original owner + enum gates."""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import spk_recovery.private_complete_postjavac_v309_owner_r107 as gate


class PostJavacAllOriginalOwnerGateTests(unittest.TestCase):
    OWNER = "p/Owner.class"
    NESTED = ("p/Owner$Owner.class", "p/Owner$One.class",
              "p/Owner$Two.class", "p/Owner$Three.class")
    SOURCE = ("p/Owner$Surrogate.class", "p/Owner$One.class",
              "p/Owner$Two.class", "p/Owner$Three.class")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.original = self.root / "original.jar"
        self.preimage = self.root / "preimage.jar"
        self.postimage = self.root / "postimage.jar"
        self.output = self.root / "accepted"
        self.events = []
        self.prepare_zip(self.original, (self.OWNER, *self.NESTED))
        self.prepare_zip(self.preimage, (self.OWNER, *self.SOURCE))
        self.prepare_zip(self.postimage, (self.OWNER, *self.NESTED))
        self.original_pin = self.sha(self.original)
        self.source_pin = self.sha(self.preimage)
        self.final_pin = self.sha(self.postimage)
        self.assertNotEqual(self.final_pin, self.source_pin)

    @staticmethod
    def prepare_zip(path, names):
        with ZipFile(path, "w") as z:
            for name in names:
                z.writestr(name, ("private-test|" + name).encode())

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def source_gate(self, *args, **kwargs):
        self.events.append("R90")
        self.assertEqual(kwargs["original_sha256"], self.original_pin)
        out = Path(args[11])
        out.mkdir()
        (out / "candidate.private.jar").write_bytes(self.preimage.read_bytes())
        return {
            "both_R87_methods_passed": True,
            "R58_initializer_operand_semantics_passed": True,
            "R88_original_owner_field_metadata_passed": True,
            "original_field_declarations": 126,
            "candidate_field_declarations": 126,
            "original_field_declaration_differences": 0,
            "original_initializer_static_writes": 93,
            "original_unrecovered_method_declarations": 0,
            "original_unrecovered_nested_class_entries": 1,
            "candidate_compiled_jar_sha256": self.source_pin,
        }

    def enum_gate(self, *args, **kwargs):
        self.events.append("R106+R105+R104+R95")
        self.assertEqual(kwargs["original_sha256"], self.original_pin)
        self.assertEqual(kwargs["candidate_sha256"], self.source_pin)
        self.assertEqual(Path(args[1]).read_bytes(), self.preimage.read_bytes())
        output = Path(args[4])
        output.mkdir()
        (output / "all-four-R95-after-StackMap.private.jar").write_bytes(
            self.postimage.read_bytes())
        return {
            "original_four_nested_enums_R95_accepted": True,
            "original_case_insensitive_lookup_method_frames_identical": True,
            "candidate_method_code_bytes_preserved": True,
            "original_lookups_method_code_bytes_transferred": False,
            "r95_accepted_candidate_sha256": self.final_pin,
        }

    def all_nine(self, *args, **kwargs):
        self.events.append("R94-postimage")
        self.assertEqual(kwargs["candidate_sha256"], self.final_pin)
        self.assertEqual(Path(args[1]).read_bytes(), self.postimage.read_bytes())
        return {
            "R66_and_R81_parity_passed_all_nine_ordinary_methods": True,
            "original_ordinary_methods_parity_checked": 9,
            "original_ordinary_jvm_instruction_operands_compared": 1135,
        }

    def verified_class(self, path, entry, sha):
        self.events.append("load-profile")
        self.assertEqual(entry, self.OWNER)
        self.assertEqual(sha, self.sha(Path(path)))
        return {"internal_name": "p/Owner", "method_marker": path == self.original}

    def clinit(self, original, candidate, aliases):
        self.events.append("R58-postimage")
        self.assertEqual(aliases, [])
        return {
            "identical_normalized_initializer_operand_semantics": True,
            "original_owner_static_writes_in_order": 93,
            "original_initializer_instructions": 213,
        }

    def frontier(self, original, candidate, original_nested, candidate_nested):
        self.events.append("R88-postimage")
        self.assertEqual(original_nested, candidate_nested)
        self.assertEqual(original_nested, set(self.NESTED))
        v = {
            "original_fields": 126, "candidate_fields": 126,
            "original_methods": 10, "candidate_methods": 10,
            "missing_original_fields": 0, "extra_candidate_fields": 0,
            "shared_field_declaration_mismatches": 0,
            "missing_original_methods": 0, "extra_candidate_methods": 0,
            "shared_method_declaration_mismatches": 0,
            "original_nested_classes": 4, "candidate_nested_classes": 4,
            "missing_original_nested_classes": 0,
            "extra_candidate_nested_classes": 0,
        }
        for field in (
            "original_candidate_major_equal",
            "original_candidate_super_equal",
            "original_candidate_class_access_equal",
            "original_candidate_class_signature_equal",
            "original_candidate_interface_list_equal",
        ):
            v[field] = True
        return v

    def accept(self, *, pin=None):
        return gate.accept_private_v309_postjavac_owner(
            self.original, self.OWNER, "load", "save",
            self.root / "src", self.OWNER, "load", "save",
            self.root / "load.json", self.root / "save.json",
            self.root / "clinit.json", "Surrogate", self.output,
            original_sha256=pin or self.original_pin)

    def mocks(self, *, source=None, enum=None, methods=None,
              clinit=None, frontier=None):
        ctx = ExitStack()
        self.addCleanup(ctx.close)
        module_patches = [
            ("accept_original_v309_owner_methods_and_initializer",
             source or self.source_gate),
            ("repair_then_require_r105_r95", enum or self.enum_gate),
            ("replay_all_original_methods", methods or self.all_nine),
            ("_verified_class", self.verified_class),
            ("read_initializer_aliases", lambda path: []),
            ("compare_clinit_operand_semantics", clinit or self.clinit),
            ("private_owner_frontier", frontier or self.frontier),
        ]
        for key, fn in module_patches:
            ctx.enter_context(patch.object(gate, key, fn))
        return ctx

    def test_one_final_jar_replays_every_gate_and_promotes_once(self):
        self.mocks()
        accepted = self.accept()
        self.assertEqual(
            [e for e in self.events if not e.startswith("load")],
            ["R90", "R106+R105+R104+R95", "R94-postimage",
             "R58-postimage", "R88-postimage"])
        self.assertTrue(accepted["R94_final_postimage_nine_owner_methods_passed"])
        self.assertTrue(accepted["R58_final_postimage_initializer_passed"])
        self.assertTrue(accepted["R88_final_postimage_owner_declarations_passed"])
        self.assertTrue(accepted["R106_R105_R104_R95_original_four_nested_enums_passed"])
        self.assertFalse(accepted["whole_original_client_runtime_equivalence_certified"])
        self.assertEqual(self.sha(self.output / "candidate.private.jar"),
                         self.final_pin)
        self.assertEqual(len(list(self.output.iterdir())), 2)
        self.assertEqual(
            list(self.root.glob("v309-owner-postjavac-r107-*")), [])

    def test_wrong_original_jar_pin_vetoes_before_compilation(self):
        self.mocks()
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "ORIGINAL_V309_COMPLETE_JAR_SHA256_MISMATCH"):
            self.accept(pin="0" * 64)
        self.assertEqual(self.events, [])
        self.assertFalse(self.output.exists())

    def test_missing_unrelated_original_enum_vetoes_pre_rebinding(self):
        self.prepare_zip(self.preimage, (
            self.OWNER, "p/Owner$Surrogate.class",
            "p/Owner$One.class", "p/Owner$Two.class"))
        self.source_pin = self.sha(self.preimage)
        self.mocks()
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "EXACT_ONE_SOURCE_INVALID_ORIGINAL_ENUM_COLLISION_REQUIRED"):
            self.accept()
        self.assertNotIn("R106+R105+R104+R95", self.events)
        self.assertFalse(self.output.exists())

    def test_other_missing_method_is_never_accepted(self):
        def bad(*args, **kw):
            data = self.source_gate(*args, **kw)
            data["original_unrecovered_method_declarations"] = 1
            return data
        self.mocks(source=bad)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "R90_SOURCE_FRONTIER_NOT_EXACT_ONE_NAME_COLLISION"):
            self.accept()
        self.assertNotIn("R106+R105+R104+R95", self.events)
        self.assertFalse(self.output.exists())

    def test_more_than_one_missing_nested_name_vetoes_even_if_r90_claims_success(self):
        def bad(*args, **kw):
            data = self.source_gate(*args, **kw)
            data["original_unrecovered_nested_class_entries"] = 2
            return data
        self.mocks(source=bad)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "R90_SOURCE_FRONTIER_NOT_EXACT_ONE_NAME_COLLISION"):
            self.accept()
        self.assertFalse(self.output.exists())

    def test_r106_r95_failure_cannot_promote(self):
        def fail(*args, **kw):
            raise gate.VerifiedEnumStackMapError("synthetic frame mismatch")
        self.mocks(enum=fail)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "R106_R105_R104_R95_FOUR_ENUM_SOURCE_NOT_ACCEPTED"):
            self.accept()
        self.assertNotIn("R94-postimage", self.events)
        self.assertFalse(self.output.exists())

    def test_missing_original_code_nontransfer_provenance_vetoes(self):
        def missing(*args, **kw):
            result = self.enum_gate(*args, **kw)
            result.pop("original_lookups_method_code_bytes_transferred")
            return result
        self.mocks(enum=missing)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "FINAL_FOUR_ENUM_R95_ACCEPTANCE_FLAGS_INCOMPLETE"):
            self.accept()
        self.assertNotIn("R94-postimage", self.events)
        self.assertFalse(self.output.exists())

    def test_original_code_transfer_claim_vetoes(self):
        def forbidden(*args, **kw):
            result = self.enum_gate(*args, **kw)
            result["original_lookups_method_code_bytes_transferred"] = True
            return result
        self.mocks(enum=forbidden)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "FINAL_FOUR_ENUM_R95_ACCEPTANCE_FLAGS_INCOMPLETE"):
            self.accept()
        self.assertNotIn("R94-postimage", self.events)
        self.assertFalse(self.output.exists())

    def test_changed_final_postimage_hash_cannot_reach_r94(self):
        def wrong(*args, **kw):
            v = self.enum_gate(*args, **kw)
            v["r95_accepted_candidate_sha256"] = "1" * 64
            return v
        self.mocks(enum=wrong)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "FINAL_POSTJAVAC_CANDIDATE_SHA256_MISMATCH"):
            self.accept()
        self.assertNotIn("R94-postimage", self.events)
        self.assertFalse(self.output.exists())

    def test_final_r94_nine_method_mismatch_vetoes(self):
        def fail(*args, **kw):
            raise gate.AllOwnerMethodsParityError("wrong owner lambda")
        self.mocks(methods=fail)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "R94_FINAL_NINE_OWNER_METHODS_NOT_EXACT"):
            self.accept()
        self.assertFalse(self.output.exists())

    def test_final_initializer_semantics_mismatch_vetoes(self):
        def fail(*args, **kw):
            raise gate.ClinitOperandWitnessError("original 93-write drift")
        self.mocks(clinit=fail)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "R58_R88_FINAL_OWNER_POSTIMAGE_NOT_VERIFIABLE"):
            self.accept()
        self.assertFalse(self.output.exists())

    def test_final_owner_frontier_mismatch_vetoes(self):
        def bad(*args, **kw):
            v = self.frontier(*args, **kw)
            v["missing_original_nested_classes"] = 1
            return v
        self.mocks(frontier=bad)
        with self.assertRaisesRegex(
            gate.PostJavacCompleteOwnerAcceptanceError,
            "R88_FINAL_OWNER_FIELD_METHOD_ENUM_DECLARATIONS_NOT_EXACT"):
            self.accept()
        self.assertFalse(self.output.exists())

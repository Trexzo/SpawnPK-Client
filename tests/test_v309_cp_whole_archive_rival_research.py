from __future__ import annotations

from collections import Counter
import copy
import unittest

from spk_recovery.v309_cp_whole_archive_rival_research import (
    V309CpRivalWitnessError,
    _coarse,
    _coarse_intersection,
    _cp_fingerprints,
    _scan_direction,
    _unique_cp_matches,
)


class WholeArchiveCpRivalTests(unittest.TestCase):
    @staticmethod
    def code_methods(*lengths: int) -> dict:
        return {
            "methods": [
                {"name": "m" + str(i), "access": 1,
                 "descriptor": "(Ljava/lang/String;)V", "code_length": n}
                for i, n in enumerate(lengths)
            ]
        }

    @staticmethod
    def cp_fingerprints(*values) -> dict:
        return {"fingerprints": Counter(values), "eligible": len(values),
                "unsupported": 0, "non_cp": 0}

    def setUp(self):
        self.keys = (("cp-site-A",), ("cp-site-B",), ("cp-site-C",))
        self.source = self.cp_fingerprints(*self.keys)
        self.oldshape = Counter({(1, "(L;)V", 6): 3})
        self.candidates = {
            "proposed.class": Counter({(1, "(L;)V", 6): 3}),
            "rival.class": Counter({(1, "(L;)V", 6): 3}),
            "nonviable.class": Counter({(1, "(I)V", 6): 3}),
        }
        self.profiles = {
            "proposed.class": self.cp_fingerprints(*self.keys),
            "rival.class": self.cp_fingerprints(("cp-site-X",),
                                                  ("cp-site-Y",), ("cp-site-Z",)),
            "nonviable.class": self.cp_fingerprints(*self.keys),
        }

    def scan(self, profiles=None, candidates=None, **kwargs):
        return _scan_direction(
            self.source, self.oldshape, "proposed.class",
            self.candidates if candidates is None else candidates,
            (self.profiles if profiles is None else profiles).get,
            **kwargs,
        )

    def test_complete_coarse_superset_excludes_nonviable_shape(self):
        outcome = self.scan()
        self.assertEqual(outcome["state"],
                         "NO_QUALIFYING_RIVAL_IN_FULL_COARSE_SUPERSET_RESEARCH_ONLY")
        self.assertEqual(outcome["coarse_viable_classes"], 2)
        self.assertEqual(outcome["qualified_rivals"], 0)
        self.assertTrue(outcome["proposed_target_qualified"])
        self.assertTrue(outcome["exhaustive_supported_scan"])

    def test_genuine_rival_vetoes_proposed_uniqueness(self):
        profiles = dict(self.profiles)
        profiles["rival.class"] = self.cp_fingerprints(*self.keys)
        outcome = self.scan(profiles=profiles)
        self.assertEqual(outcome["state"], "RIVAL_CLASS_CP_WITNESS_VETO")
        self.assertEqual(outcome["qualified_rivals"], 1)

    def test_ambiguous_duplicate_methods_still_count_against_rival_uniqueness(self):
        # The rival's duplicated A does not provide unique positive method
        # evidence, but A/B/C still describe a competing *possible* owner.
        profiles = dict(self.profiles)
        profiles["rival.class"] = self.cp_fingerprints(
            self.keys[0], self.keys[0], self.keys[1], self.keys[2],
        )
        self.assertEqual(
            _unique_cp_matches(self.source["fingerprints"],
                               profiles["rival.class"]["fingerprints"]), 2)
        outcome = self.scan(profiles=profiles)
        self.assertEqual(outcome["state"], "RIVAL_CLASS_CP_WITNESS_VETO")
        self.assertEqual(outcome["qualified_rivals"], 1)

    def test_unscannable_viable_rival_blocks_uniqueness(self):
        profiles = dict(self.profiles)
        profiles["rival.class"] = None
        outcome = self.scan(profiles=profiles)
        self.assertEqual(outcome["state"],
                         "UNSCANNABLE_COARSE_RIVALS_NO_UNIQUENESS_CLAIM")
        self.assertEqual(outcome["unsupported_target_classes"], 1)
        self.assertEqual(outcome["qualified_rivals"], 0)

    def test_broad_pool_never_implicitly_accepts_first_result(self):
        outcome = self.scan(maximum=1)
        self.assertEqual(outcome["state"], "PREFILTER_TOO_BROAD_NO_UNIQUENESS_CLAIM")
        self.assertFalse(outcome["exhaustive_supported_scan"])

    def test_target_not_in_shape_superset_never_promoted(self):
        shape = dict(self.candidates)
        shape["proposed.class"] = Counter({(1, "(I)V", 6): 3})
        outcome = self.scan(candidates=shape)
        self.assertEqual(outcome["state"],
                         "PROPOSED_CLASS_FAILS_NECESSARY_COARSE_GATE")
        self.assertFalse(outcome["proposed_target_qualified"])

    def test_pair_with_two_matches_does_not_qualify(self):
        profiles = dict(self.profiles)
        profiles["proposed.class"] = self.cp_fingerprints(*self.keys[:2])
        outcome = self.scan(profiles=profiles)
        self.assertEqual(outcome["state"], "INSUFFICIENT_PROPOSED_CP_METHOD_WITNESSES")

    def test_duplicate_exact_fingerprint_not_a_unique_method(self):
        left = Counter({("same",): 2, ("other",): 1})
        right = Counter({("same",): 1, ("other",): 1})
        self.assertEqual(_unique_cp_matches(left, right), 1)
        self.assertEqual(_unique_cp_matches(Counter({("same",): 1}),
                                            Counter({("same",): 1})), 1)

    def test_coarse_necessary_shape_is_broad_superset(self):
        shape_a = _coarse(self.code_methods(6, 6, 8))
        shape_b = _coarse(self.code_methods(6, 6, 8))
        self.assertEqual(_coarse_intersection(shape_a, shape_b), 3)
        shape_bad = _coarse(self.code_methods(6, 6, 9))
        self.assertEqual(_coarse_intersection(shape_a, shape_bad), 2)
        # No field-shape or raw-name restrictions are imposed on rival
        # candidates: those would exclude potentially meaningful alternatives.

    def test_renamed_self_owner_is_normalized_but_third_party_not(self):
        def profile(owner: str, third_party: str):
            instructions = [
                {"offset": 0, "opcode": "0xb8", "mnemonic": "invokestatic",
                 "length": 3, "member_constant_pool_tag": 10,
                 "owner": owner, "name": "selfCall",
                 "descriptor": "()V"},
                {"offset": 3, "opcode": "0xb8", "mnemonic": "invokestatic",
                 "length": 3, "member_constant_pool_tag": 10,
                 "owner": third_party, "name": "thirdCall",
                 "descriptor": "()V"},
                {"offset": 6, "opcode": "0xb1", "mnemonic": "return",
                 "length": 1},
            ]
            return {"internal_name": owner,
                    "bootstrap_methods": [],
                    "methods": [{
                        "name": "example", "access": 1, "descriptor": "()V",
                        "code_length": 7, "instructions": instructions,
                        "exception_handlers": [],
                    }]}
        old = _cp_fingerprints(profile("a/Old", "java/lang/String"))
        new = _cp_fingerprints(profile("b/New", "java/lang/String"))
        rival = _cp_fingerprints(profile("b/New", "java/lang/Integer"))
        self.assertEqual(_unique_cp_matches(old["fingerprints"],
                                             new["fingerprints"]), 1)
        self.assertEqual(_unique_cp_matches(old["fingerprints"],
                                             rival["fingerprints"]), 0)
        self.assertEqual(old["eligible"], 1)

    def test_unsupported_method_does_not_become_evidence(self):
        prof = {
            "internal_name": "a/Old", "bootstrap_methods": [],
            "methods": [
                {"name": "m", "access": 1, "descriptor": "()V",
                 "code_length": 4,
                 "instructions": [
                     {"offset": 0, "opcode": "0xc5", "mnemonic": "multianewarray",
                      "length": 3},  # unsupported CP operands
                     {"offset": 3, "opcode": "0xb1", "mnemonic": "return",
                      "length": 1},
                 ], "exception_handlers": []},
            ],
        }
        result = _cp_fingerprints(prof)
        self.assertEqual(result["eligible"], 0)
        self.assertEqual(result["unsupported"], 1)

    def test_malformed_index_shapes_fail_closed(self):
        with self.assertRaises(V309CpRivalWitnessError):
            _coarse({"methods": [{"name": "f", "descriptor": "()V", "access": 1,
                                   "code_length": "6"}]})

    def test_outputs_no_private_method_fingerprints(self):
        import json
        report = self.scan()
        blob = json.dumps(report)
        self.assertNotIn("cp-site-A", blob)
        self.assertNotIn("cp-site-X", blob)
        self.assertNotIn("a/Old", blob)


if __name__ == "__main__":
    unittest.main()

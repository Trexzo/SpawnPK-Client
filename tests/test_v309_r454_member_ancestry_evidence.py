"""R454 synthetic superclass/interface member ancestry evidence tests.

Every classfile and owner TEMP directory is invented. Hosted CI never
receives actual SpawnPK JARs, player-history data, or private Java source.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r453_member_reference_coverage as previous
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r453 import classfile_member_reference as parser
from tools.r454 import member_ancestry_evidence as ancestry
from tools.r454 import audit_inherited_member_ancestry as r454

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r454/audit_inherited_member_ancestry.py"


def make_record(
    name: str,
    superclass: str | None = "java/lang/Object.class",
    interfaces: tuple[str, ...] = (),
    fields: tuple[tuple[str, str, int], ...] = (),
    methods: tuple[tuple[str, str, int], ...] = (),
    refs: tuple[parser.Member, ...] = (),
) -> parser.ClassMembers:
    return parser.ClassMembers(
        name, superclass,
        frozenset((n, d) for n, d, _ in fields),
        frozenset((n, d) for n, d, _ in methods),
        frozenset(refs), frozenset(interfaces),
        tuple(fields), tuple(methods),
        0,
    )


def ref(owner="rs/Child.class", name="run", descriptor="()V",
        kind="method"):
    return parser.Member(owner, name, descriptor, kind)


def fixture(
    parent_methods=(("run", "()V", 0x0001),),
    parent_fields=(),
    child_methods=(),
    interfaces=(),
    parent_super="java/lang/Object.class",
    target=None,
) -> dict[str, parser.ClassMembers]:
    target = ref() if target is None else target
    return {
        "rs/Child.class": make_record(
            "rs/Child.class", "rs/Parent.class", interfaces,
            methods=child_methods, refs=(target,)),
        "rs/Parent.class": make_record(
            "rs/Parent.class", parent_super,
            methods=parent_methods, fields=parent_fields),
    }


def fake_java11_interface_declared_class() -> bytes:
    """Real parsable Java11 CP + immediate super/interface/field flags."""
    cp: list[bytes] = []

    def u2(i):
        return i.to_bytes(2, "big")

    def utf(s):
        encoded = s.encode("ascii")
        cp.append(b"\x01" + u2(len(encoded)) + encoded)
        return len(cp)

    def cls(s):
        i = utf(s)
        cp.append(b"\x07" + u2(i))
        return len(cp)

    own = cls("rs/Synthetic")
    sup = cls("rs/Parent")
    iface = cls("rs/API")
    field_n, field_d = utf("data"), utf("Ljava/lang/String;")
    method_n, method_d = utf("open"), utf("()V")
    raw = (b"\xca\xfe\xba\xbe\x00\x00\x00\x37"
           + u2(len(cp)+1) + b"".join(cp)
           + u2(0x21) + u2(own) + u2(sup)
           + u2(1) + u2(iface))
    raw += u2(1) + u2(0x0002) + u2(field_n) + u2(field_d) + u2(0)
    raw += u2(1) + u2(0x0009) + u2(method_n) + u2(method_d) + u2(0)
    raw += u2(0)
    return raw


class R454AcyclicInheritancePure(unittest.TestCase):
    def test_01_r453_binary_parser_preserves_interface_and_member_access_flags(self):
        rec = parser.parse_class(fake_java11_interface_declared_class())
        self.assertEqual(rec.class_name, "rs/Synthetic.class")
        self.assertEqual(rec.superclass_name, "rs/Parent.class")
        self.assertEqual(rec.interfaces, frozenset({"rs/API.class"}))
        self.assertEqual(rec.declared_field_access,
                         (("data", "Ljava/lang/String;", 0x0002),))
        self.assertEqual(rec.declared_method_access,
                         (("open", "()V", 0x0009),))

    def test_02_direct_declaration_stays_direct(self):
        records = fixture(child_methods=(("run", "()V", 1),))
        chain = ancestry.ancestry(records, "rs/Child.class")
        self.assertEqual(ancestry.lookup(records, ref(), chain).category,
                         "direct_declaration")

    def test_03_immediate_superclass_candidate_not_linkage_proof(self):
        records = fixture()
        chain = ancestry.ancestry(records, "rs/Child.class")
        outcome = ancestry.lookup(records, ref(), chain)
        self.assertEqual(outcome.category, "superclass_signature_candidate")
        self.assertEqual(outcome.candidates, ("rs/Parent.class",))
        summary, private = ancestry.analyze(records, set(), set(), set())
        self.assertEqual(summary["possible_inherited_superclass_member_signature"], 1)
        self.assertFalse(summary["bytecode_linkage_verified"])
        self.assertFalse(private["direct_declaration_is_not_runtime_resolution"])

    def test_04_multigeneration_superclass_method(self):
        records = fixture(parent_methods=(),
                          parent_super="rs/Grand.class")
        records["rs/Grand.class"] = make_record(
            "rs/Grand.class", methods=(("run", "()V", 0x0001),))
        chain = ancestry.ancestry(records, "rs/Child.class")
        self.assertEqual(ancestry.lookup(records, ref(), chain).candidates,
                         ("rs/Grand.class",))

    def test_05_interface_default_or_abstract_method_candidate(self):
        records = fixture(parent_methods=(), interfaces=("rs/IFace.class",))
        records["rs/IFace.class"] = make_record(
            "rs/IFace.class", None,
            methods=(("run", "()V", 0x0001),))
        result = ancestry.lookup(
            records, ref(), ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category, "interface_signature_candidate")
        self.assertEqual(result.candidates, ("rs/IFace.class",))

    def test_06_transitive_superinterface(self):
        records = fixture(parent_methods=(), interfaces=("rs/API.class",))
        records["rs/API.class"] = make_record(
            "rs/API.class", None, ("rs/APIBase.class",))
        records["rs/APIBase.class"] = make_record(
            "rs/APIBase.class", None,
            methods=(("run", "()V", 1),))
        result = ancestry.lookup(
            records, ref(), ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category, "interface_signature_candidate")
        self.assertEqual(result.candidates, ("rs/APIBase.class",))

    def test_07_interface_via_superclass(self):
        records = fixture(parent_methods=())
        records["rs/Parent.class"] = make_record(
            "rs/Parent.class", "java/lang/Object.class",
            ("rs/IFace.class",))
        records["rs/IFace.class"] = make_record(
            "rs/IFace.class", None,
            methods=(("run", "()V", 1),))
        result = ancestry.lookup(
            records, ref(), ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category, "interface_signature_candidate")

    def test_08_private_parent_method_is_not_an_inheritance_candidate(self):
        records = fixture(parent_methods=(("run", "()V", 0x0002),))
        result = ancestry.lookup(
            records, ref(), ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(
            result.category,
            "ancestor_declaration_noninheritable_or_access_unknown")
        self.assertIn("rs/Parent.class#private", result.non_inheritable)

    def test_09_static_interface_method_not_inherited(self):
        records = fixture(parent_methods=(), interfaces=("rs/API.class",))
        records["rs/API.class"] = make_record(
            "rs/API.class", None,
            methods=(("run", "()V", 0x0009),))
        result = ancestry.lookup(
            records, ref(), ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(
            result.category,
            "ancestor_declaration_noninheritable_or_access_unknown")
        self.assertIn(
            "rs/API.class#static-interface-method", result.non_inheritable)

    def test_10_interface_field_structural_candidate(self):
        target = ref(name="COUNT", descriptor="I", kind="field")
        records = fixture(parent_methods=(), interfaces=("rs/API.class",),
                          target=target)
        records["rs/API.class"] = make_record(
            "rs/API.class", None, fields=(("COUNT", "I", 0x0019),))
        result = ancestry.lookup(
            records, target, ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category, "interface_signature_candidate")

    def test_11_private_superclass_field_not_inherited(self):
        target = ref(name="token", descriptor="I", kind="field")
        records = fixture(parent_methods=(),
                          parent_fields=(("token", "I", 0x0002),),
                          target=target)
        result = ancestry.lookup(
            records, target, ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(
            result.category,
            "ancestor_declaration_noninheritable_or_access_unknown")

    def test_12_different_descriptor_is_not_a_match(self):
        records = fixture(parent_methods=(("run", "(I)V", 1),))
        result = ancestry.lookup(
            records, ref(), ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category,
                         "ancestry_external_or_platform_unknown")

    def test_13_constructor_not_inherited_even_when_parent_has_same_signature(self):
        target = ref(name="<init>")
        records = fixture(parent_methods=(("<init>", "()V", 1),),
                          target=target)
        result = ancestry.lookup(
            records, target, ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category, "special_method_not_inheritable")

    def test_14_class_initializer_not_inherited(self):
        target = ref(name="<clinit>")
        records = fixture(parent_methods=(("<clinit>", "()V", 8),),
                          target=target)
        result = ancestry.lookup(
            records, target, ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category, "special_method_not_inheritable")

    def test_15_incomplete_preferred_dependency_ancestry_not_confirmed_missing(self):
        records = fixture(parent_methods=(),
                          parent_super="lib/ExternalBase.class")
        result = ancestry.lookup(
            records, ref(), ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category,
                         "ancestry_external_or_platform_unknown")
        self.assertIn("lib/ExternalBase.class", result.external_edges)

    def test_16_unknown_member_access_metadata_not_promoted(self):
        records = fixture(parent_methods=())
        records["rs/Parent.class"] = parser.ClassMembers(
            "rs/Parent.class", None, frozenset(),
            frozenset({("run", "()V")}), frozenset())
        result = ancestry.lookup(
            records, ref(), ancestry.ancestry(records, "rs/Child.class"))
        self.assertEqual(result.category,
                         "ancestor_declaration_noninheritable_or_access_unknown")

    def test_17_cycle_is_unknown_not_a_verified_ancestor(self):
        records = fixture(parent_methods=(),
                          parent_super="rs/Child.class")
        chain = ancestry.ancestry(records, "rs/Child.class")
        self.assertTrue(chain.cycle)
        self.assertEqual(
            ancestry.lookup(records, ref(), chain).category,
            "cycle_or_budget_uncertain")

    def test_18_interface_diamond_not_false_cycle(self):
        records = fixture(parent_methods=(),
                          interfaces=("rs/A.class", "rs/B.class"))
        records["rs/A.class"] = make_record(
            "rs/A.class", None, ("rs/C.class",))
        records["rs/B.class"] = make_record(
            "rs/B.class", None, ("rs/C.class",))
        records["rs/C.class"] = make_record(
            "rs/C.class", None, methods=(("run", "()V", 1),))
        chain = ancestry.ancestry(records, "rs/Child.class")
        self.assertFalse(chain.cycle)
        self.assertIn(("rs/C.class", "interface"), chain.ancestors)
        self.assertEqual(ancestry.lookup(records, ref(), chain).category,
                         "interface_signature_candidate")

    def test_19_ancestry_depth_budget_excludes_evidence(self):
        records = fixture(parent_methods=(),
                          parent_super="rs/Third.class")
        records["rs/Third.class"] = make_record(
            "rs/Third.class", methods=(("run", "()V", 1),))
        with patch.object(ancestry, "MAX_DEPTH", 1):
            chain = ancestry.ancestry(records, "rs/Child.class")
            self.assertTrue(chain.bounded_unknown)
            self.assertEqual(
                ancestry.lookup(records, ref(), chain).category,
                "cycle_or_budget_uncertain")

    def test_20_ancestry_worklist_budget_excludes_evidence(self):
        records = fixture(parent_methods=())
        with patch.object(ancestry, "MAX_PATH_STATES", 1):
            chain = ancestry.ancestry(records, "rs/Child.class")
            self.assertTrue(chain.bounded_unknown)

    def test_21_unreferenced_owner_absent_refused(self):
        with self.assertRaisesRegex(
                ancestry.Refused, "R454_OWNER_ABSENT_FROM_REBUILT_TREE"):
            ancestry.ancestry(fixture(), "rs/Unknown.class")

    def test_22_class_path_mismatch_refused(self):
        records = fixture()
        records["rs/Fake.class"] = make_record("rs/Other.class")
        with self.assertRaisesRegex(
                ancestry.Refused, "R454_CLASS_PATH_INTERNAL_NAME_MISMATCH"):
            ancestry.ancestry(records, "rs/Child.class")

    def test_23_missing_preferred_classpath_owner_remains_aggregate_only(self):
        target = ref(owner="rs/MissingOwner.class")
        records = fixture(target=target)
        summary, private = ancestry.analyze(
            records, set(), {"rs/MissingOwner.class"},
            {"rs/MissingOwner.class"})
        self.assertEqual(summary["references_with_rebuilt_owner_checked"], 0)
        self.assertEqual(
            summary["nonrebuilt_owner_reference_not_on_preferred_classpath"], 1)
        self.assertEqual(
            summary["nonrebuilt_owner_reference_present_in_alternate_only"], 1)
        self.assertEqual(
            private["unresolved_or_potentially_inherited_member_signatures"], [])

    def test_24_preferred_dependency_and_platform_owner_not_claimed_inspected(self):
        target = ref(owner="lib/Preferred.class")
        p = fixture(target=target)
        p["rs/Parent.class"] = make_record("rs/Parent.class")
        report, _ = ancestry.analyze(
            p, {"lib/Preferred.class"}, set(), set())
        self.assertEqual(
            report["nonrebuilt_owner_reference_preferred_dependency_unchecked"], 1)
        target2 = ref(owner="java/lang/Object.class")
        q = fixture(target=target2)
        report, _ = ancestry.analyze(q, set(), set(), set())
        self.assertEqual(report["nonrebuilt_owner_reference_platform"], 1)

    def test_25_output_is_conservative_even_on_exact_ancestry_match(self):
        records = fixture()
        summary, private = ancestry.analyze(records, set(), set(), set())
        for key in (
            "jvm_classloading_or_access_checks_performed",
            "inherited_methods_proven_accessible",
            "bytecode_linkage_verified",
            "dynamic_dispatch_verified",
            "production_client_executed",
        ):
            self.assertFalse(summary[key])
        self.assertFalse(private["historical_R421_inventory_approved"])

    def test_26_empty_graph_produces_zero_aggregate(self):
        stats, details = ancestry.analyze({}, set(), set(), set())
        self.assertEqual(stats["parsed_rebuilt_classfiles"], 0)
        self.assertEqual(stats["unique_rebuilt_constant_pool_member_references"], 0)
        self.assertEqual(details["unresolved_or_potentially_inherited_member_signatures"], [])


class R454FakeOwnerPrivateGates(unittest.TestCase):
    def setUp(self):
        previous.R453FakeOwnerFullGatedPipeline.setUp(self)

    def outputs(self):
        return sorted(self.temp.glob(r454.PREFIX + "*"))

    def test_27_fake_owner_independent_metadata_and_prior_counts_match(self):
        report, details = r454.inspect(self.original_jar)
        self.assertEqual(report["status"],
                         "R454_REBUILT_ANCESTRY_MEMBER_EVIDENCE_UNAPPROVED")
        self.assertEqual(report["original_v309_class_count"], 5)
        self.assertEqual(report["original_v309_resource_count"], 2)
        self.assertEqual(report["isolated_r421_source_count"], 2)
        self.assertEqual(report["isolated_r421_compiled_classes"], 2)
        self.assertEqual(report["parsed_rebuilt_classfiles"], 2)
        self.assertFalse(report["historical_R421_full_inventory_independently_approved"])
        self.assertFalse(report["release_authorized"])
        self.assertEqual(details["schema"], r454.SCHEMA)

    def test_28_aggregate_stdout_no_names_or_paths(self):
        report = r454.run(self.original_jar)
        self.assertFalse(report["private_worklist_saved"])
        self.assertEqual(self.outputs(), [])
        serialized = json.dumps(report)
        for secret in ("rs/plugins/loottracker/LootHistoryStore",
                       "java/lang/Object", str(self.temp),
                       "textures/missing.png", "images/logo.png",
                       r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(secret, serialized)

    def test_29_explicit_private_temp_contains_names_only(self):
        report = r454.run(self.original_jar, save=True)
        self.assertTrue(report["private_worklist_saved"])
        self.assertEqual(len(self.outputs()), 1)
        private = json.loads(
            (self.outputs()[0] / r454.NAME).read_text("ascii"))
        self.assertEqual(private["schema"], r454.SCHEMA)
        self.assertFalse(private["historical_R421_full_inventory_approved"])
        self.assertFalse(private["release_authorized"])

    def test_30_two_private_runs_never_overwrite(self):
        first = r454.run(self.original_jar, save=True)
        target = self.outputs()[0] / r454.NAME
        content = target.read_bytes()
        second = r454.run(self.original_jar, save=True)
        self.assertEqual(len(self.outputs()), 2)
        self.assertNotEqual(first["owner_private_directory"],
                            second["owner_private_directory"])
        self.assertEqual(content, target.read_bytes())

    def test_31_mismatched_original_SHA_refused(self):
        self.original_jar.write_bytes(b"wrong original version")
        with self.assertRaises(r454.r447.Refused):
            r454.inspect(self.original_jar)

    def test_32_individual_class_modified_after_SHA_snapshot_refused(self):
        snapshot, _ = r454.r446.observe()
        (self.compiled / "rs/Bridge.class").write_bytes(b"changed")
        with self.assertRaisesRegex(
                r454.r453.Refused,
                "R453_R421_CLASS_CHANGED_OR_UNSAFE"):
            r454.r453.observed_members(snapshot)

    def test_33_unrelated_source_modified_between_scans_refused(self):
        actual = r454.inspect
        count = [0]
        def mutate(*args, **kwargs):
            result = actual(*args, **kwargs)
            count[0] += 1
            if count[0] == 1:
                filename = self.source / "rs/Bridge.java"
                filename.write_bytes(filename.read_bytes() + b" other change")
            return result
        with patch.object(r454, "inspect", side_effect=mutate):
            with self.assertRaisesRegex(
                    r454.Refused, "R454_INPUTS_CHANGED_BETWEEN_PRIVATE_SCANS"):
                r454.run(self.original_jar, save=True)
        self.assertEqual(self.outputs(), [])

    def test_34_private_output_size_cap_refused_before_file_write(self):
        with patch.object(r454, "MAX_PRIVATE_BYTES", 32):
            with self.assertRaisesRegex(
                    r454.Refused, "R454_PRIVATE_EVIDENCE_BUDGET_EXCEEDED"):
                r454.run(self.original_jar, save=True)
        self.assertEqual(self.outputs(), [])

    def test_35_missing_original_cli_redacts_owner_path(self):
        missing = self.temp / "private-original-client.jar"
        completed = subprocess.run(
            [sys.executable, "-B", str(CLI), "--original-v309-jar", str(missing)],
            capture_output=True, text=True, check=False, timeout=15)
        self.assertEqual(completed.returncode, 2, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "R454_MEMBER_ANCESTRY_AUDIT_REFUSED")
        self.assertNotIn(str(missing), completed.stdout)
        self.assertFalse(payload["release_authorized"])

    def test_36_no_client_compilation_history_access_or_release_claims(self):
        result = r454.run(self.original_jar)
        for flag in (
            "owner_client_executed",
            "jvm_member_resolution_proven",
            "jvm_access_control_checked",
            "full_source_deobfuscation_proven",
            "original_functionality_mapped_completely",
            "original_resource_packaging_proven",
            "historical_R421_full_inventory_independently_approved",
            "build_authorized",
            "release_authorized",
            "merge_authorized",
        ):
            self.assertFalse(result[flag])


if __name__ == "__main__":
    unittest.main()

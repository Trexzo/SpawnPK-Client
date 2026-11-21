"""R455 public synthetic preferred-JAR member declarations and access tests.

All JARs, reconstructed classes and owner OS TEMP paths are invented; no
real SpawnPK private source/assets or game history reaches GitHub CI.
"""
from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import zipfile

import test_v309_r453_member_reference_coverage as r453_fixture
import test_v309_r454_member_ancestry_evidence as r454_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r453 import classfile_member_reference as parser
from tools.r455 import dependency_member_access as dep
from tools.r455 import audit_dependency_member_access as r455

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r455/audit_dependency_member_access.py"


def archive(entries: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, contents in entries.items():
            z.writestr(name, contents)
    return output.getvalue()


def raw_dep(own: str = "lib/Dep", *, major: int = 52,
            declare_field=True, declare_method=True) -> bytes:
    raw = r453_fixture.fake_member_class(
        own=own, declare_field=declare_field, declare_method=declare_method)
    return raw[:6] + major.to_bytes(2, "big") + raw[8:]


def direct_member(owner="lib/Dep.class", name="open", kind="method",
                  descriptor="()V") -> parser.Member:
    return parser.Member(owner, name, descriptor, kind)


def rebuilt_refs(*targets: parser.Member,
                 superclass="java/lang/Object.class") -> dict:
    return {
        "rs/Caller.class": r454_fixture.make_record(
            "rs/Caller.class", superclass,
            refs=targets, methods=(("local", "()V", 0x0001),)),
    }


class R455SelectiveArchiveTests(unittest.TestCase):
    def test_01_java8_dependency_opt_in_parsed_but_rebuilt_default_stays_java11(self):
        raw = raw_dep()
        with self.assertRaises(parser.Refused):
            parser.parse_class(raw)
        result = parser.parse_class(
            raw, allowed_majors=dep.SUPPORTED_DEPENDENCY_MAJORS)
        self.assertEqual(result.class_name, "lib/Dep.class")
        self.assertIn(("open", "()V"), result.declared_methods)
        self.assertEqual(result.declared_method_access[0][2], 0x0001)

    def test_02_bad_major_or_wrong_allowlist_refused(self):
        for major in (44, 56, 61):
            with self.subTest(major=major):
                with self.assertRaises(parser.Refused):
                    parser.parse_class(
                        raw_dep(major=major),
                        allowed_majors=dep.SUPPORTED_DEPENDENCY_MAJORS)
        with self.assertRaises(parser.Refused):
            parser.parse_class(raw_dep(), allowed_majors=(45, 61))

    def test_03_extract_only_referenced_preferred_dependency_owner(self):
        contents = archive({
            "lib/Dep.class": raw_dep(),
            "lib/Unused.class": b"never parsed unsafe class bytes",
        })
        chosen = dep.selected_dependencies(
            contents, sha256(contents).hexdigest(),
            {"lib/Dep.class", "lib/Unused.class"},
            rebuilt_refs(direct_member()))
        self.assertEqual(set(chosen), {"lib/Dep.class"})
        self.assertIn(("open", "()V"), chosen["lib/Dep.class"].declared_methods)

    def test_04_ancestor_preferred_dependency_selected_without_direct_owner_reference(self):
        contents = archive({"lib/Dep.class": raw_dep()})
        selected = dep.selected_dependencies(
            contents, sha256(contents).hexdigest(),
            {"lib/Dep.class"},
            rebuilt_refs(direct_member("rs/Caller.class"),
                         superclass="lib/Dep.class"))
        self.assertEqual(set(selected), {"lib/Dep.class"})

    def test_05_sha_pins_are_required(self):
        contents = archive({"lib/Dep.class": raw_dep()})
        with self.assertRaisesRegex(dep.Refused,"R455_PREFERRED_JAR_SHA_MISMATCH"):
            dep.selected_dependencies(
                contents, "0"*64, {"lib/Dep.class"},
                rebuilt_refs(direct_member()))

    def test_06_index_mismatch_refused(self):
        contents = archive({"lib/Dep.class": raw_dep()})
        with self.assertRaisesRegex(dep.Refused,"R455_DEPENDENCY_CLASS_INDEX_DRIFT"):
            dep.selected_dependencies(
                contents, sha256(contents).hexdigest(),
                {"lib/Other.class"}, rebuilt_refs(direct_member()))

    def test_07_unsafe_duplicate_archive_refused(self):
        b = io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("lib/Dep.class", raw_dep())
                z.writestr("lib/Dep.class", raw_dep())
        contents=b.getvalue()
        with self.assertRaisesRegex(
                r455.r447.Refused,"R447_DUPLICATE_ZIP_ENTRY"):
            dep.selected_dependencies(
                contents,sha256(contents).hexdigest(),
                {"lib/Dep.class"},rebuilt_refs(direct_member()))

    def test_08_selected_owner_internal_class_must_match_archive_path(self):
        contents=archive({"lib/Dep.class":raw_dep(own="lib/Another")})
        with self.assertRaisesRegex(
                dep.Refused,"R455_SELECTED_DEPENDENCY_PATH_NAME_MISMATCH"):
            dep.selected_dependencies(
                contents,sha256(contents).hexdigest(),
                {"lib/Dep.class"},rebuilt_refs(direct_member()))

    def test_09_corrupt_selected_class_refused_without_java_execution(self):
        contents=archive({"lib/Dep.class":b"not a class"})
        with self.assertRaisesRegex(
                dep.Refused,"R455_SELECTED_DEPENDENCY_CLASS_UNPARSABLE"):
            dep.selected_dependencies(
                contents,sha256(contents).hexdigest(),
                {"lib/Dep.class"},rebuilt_refs(direct_member()))

    def test_10_unselected_corrupt_class_is_never_decompressed(self):
        contents=archive({"lib/Unused.class":b"bad bytecode"})
        self.assertEqual(dep.selected_dependencies(
            contents,sha256(contents).hexdigest(),
            {"lib/Unused.class"},rebuilt_refs()),{})

    def test_11_per_class_budget_refuses_before_decompression(self):
        contents=archive({"lib/Dep.class":raw_dep()})
        with patch.object(dep,"MAX_SELECTED_CLASS_BYTES",10):
            with self.assertRaisesRegex(
                    dep.Refused,"R455_SELECTED_CLASS_SIZE_LIMIT"):
                dep.selected_dependencies(contents,sha256(contents).hexdigest(),
                                          {"lib/Dep.class"},
                                          rebuilt_refs(direct_member()))

    def test_12_total_budget_refused(self):
        contents=archive({"lib/Dep.class":raw_dep()})
        with patch.object(dep,"MAX_TOTAL_SELECTED_BYTES",50):
            with self.assertRaisesRegex(
                    dep.Refused,"R455_SELECTED_DEPENDENCY_TOTAL_BYTE_BUDGET"):
                dep.selected_dependencies(contents,sha256(contents).hexdigest(),
                                          {"lib/Dep.class"},
                                          rebuilt_refs(direct_member()))

    def test_13_dependency_class_count_budget_refused(self):
        contents=archive({"lib/Dep.class":raw_dep()})
        with patch.object(dep,"MAX_SELECTED_CLASSES",0):
            with self.assertRaisesRegex(
                    dep.Refused,"R455_SELECTED_DEPENDENCY_CLASSES_BUDGET"):
                dep.selected_dependencies(contents,sha256(contents).hexdigest(),
                                          {"lib/Dep.class"},
                                          rebuilt_refs(direct_member()))

    def test_14_no_platform_class_decompressed_from_missing_dependency(self):
        contents=archive({"lib/Dep.class":raw_dep()})
        result=dep.selected_dependencies(contents,sha256(contents).hexdigest(),
                                         {"lib/Dep.class"},rebuilt_refs(
                                             direct_member("java/lang/Class.class")))
        self.assertEqual(result,{})


class R455MemberAccessTests(unittest.TestCase):
    def test_15_exact_preferred_dependency_member_signature_found(self):
        record=parser.parse_class(
            raw_dep(),allowed_majors=dep.SUPPORTED_DEPENDENCY_MAJORS)
        summary,private=dep.analyze(
            rebuilt_refs(direct_member()),{"lib/Dep.class":record},
            {"lib/Dep.class"},set())
        self.assertEqual(summary[
            "reference_owners_preferred_dependency_direct_exact_declaration"],1)
        self.assertEqual(summary["preferred_dependency_classfiles_selected_and_parsed"],1)
        self.assertEqual(summary["unresolved_missing_preferred_owner"],0)
        self.assertFalse(summary["dependency_method_and_field_linkage_proven"])
        self.assertEqual(private["member_reference_access_and_dependency_leads"][0][
            "category"],"direct_declaration")

    def test_16_inherited_preferred_dependency_method_candidate(self):
        record=parser.parse_class(
            raw_dep(),allowed_majors=dep.SUPPORTED_DEPENDENCY_MAJORS)
        target=direct_member("rs/Caller.class")
        summary,private=dep.analyze(
            rebuilt_refs(target,superclass="lib/Dep.class"),
            {"lib/Dep.class":record},set(),set())
        self.assertEqual(summary[
            "possible_inherited_signatures_from_preferred_dependency"],1)
        self.assertEqual(summary["possible_superclass_declaration_signatures"],1)
        self.assertTrue(private["access_signals_are_advisory_not_verdicts"])

    def test_17_missing_exact_method_descriptor_is_not_fake_match(self):
        record=parser.parse_class(
            raw_dep(),allowed_majors=dep.SUPPORTED_DEPENDENCY_MAJORS)
        target=direct_member(descriptor="(I)V")
        summary,_=dep.analyze(
            rebuilt_refs(target),{"lib/Dep.class":record},set(),set())
        self.assertEqual(summary[
            "reference_owners_preferred_dependency_direct_exact_declaration"],0)
        self.assertGreaterEqual(summary[
            "unresolved_ancestry_external_or_platform"],1)

    def test_18_private_member_other_caller_has_nestmate_uncertainty(self):
        reference=direct_member()
        record=r454_fixture.make_record(
            "lib/Dep.class",None,
            methods=(("open","()V",0x0002),))
        record=parser.ClassMembers(
            record.class_name,record.superclass_name,record.declared_fields,
            record.declared_methods,record.references,record.interfaces,
            record.declared_field_access,record.declared_method_access,
            0x0001)
        self.assertEqual(dep.member_access(
            "rs/Caller.class","lib/Dep.class",record,reference),
            "private_nestmate_or_access_unknown")

    def test_19_public_member_only_candidate_not_runtime_verdict(self):
        record=parser.parse_class(
            raw_dep(),allowed_majors=dep.SUPPORTED_DEPENDENCY_MAJORS)
        self.assertEqual(dep.member_access(
            "rs/Caller.class","lib/Dep.class",record,direct_member()),
            "public_member_classloader_access_unchecked")

    def test_20_package_private_cross_package_risk_vs_same_package(self):
        def maker():
            record=r454_fixture.make_record(
                "lib/Dep.class",None,
                methods=(("open","()V",0),))
            return parser.ClassMembers(
                record.class_name,record.superclass_name,record.declared_fields,
                record.declared_methods,record.references,record.interfaces,
                record.declared_field_access,record.declared_method_access,1)
        rec=maker()
        self.assertEqual(dep.member_access(
            "rs/Caller.class","lib/Dep.class",rec,direct_member()),
            "package_private_cross_package_access_risk")
        self.assertEqual(dep.member_access(
            "lib/Caller.class","lib/Dep.class",rec,direct_member()),
            "package_private_same_package_candidate")

    def test_21_protected_member_needs_receiver_and_package_rules(self):
        record=r454_fixture.make_record(
            "lib/Dep.class",None,
            methods=(("open","()V",0x0004),))
        rec=parser.ClassMembers(
            record.class_name,record.superclass_name,record.declared_fields,
            record.declared_methods,record.references,record.interfaces,
            record.declared_field_access,record.declared_method_access,1)
        self.assertEqual(dep.member_access(
            "rs/Caller.class","lib/Dep.class",rec,direct_member()),
            "protected_receiver_or_package_access_unknown")

    def test_22_package_private_declaring_class_not_overclaimed(self):
        record=r454_fixture.make_record(
            "lib/Dep.class",None,
            methods=(("open","()V",1),))
        self.assertEqual(dep.member_access(
            "rs/Caller.class","lib/Dep.class",record,direct_member()),
            "declaring_class_visibility_not_proven")

    def test_23_private_nestmate_cannot_be_declared_inaccessible(self):
        record=r454_fixture.make_record(
            "rs/Caller.class",None,
            methods=(("open","()V",2),))
        rec=parser.ClassMembers(
            record.class_name,record.superclass_name,record.declared_fields,
            record.declared_methods,record.references,record.interfaces,
            record.declared_field_access,record.declared_method_access,1)
        self.assertEqual(dep.member_access(
            "rs/Caller.class","rs/Caller.class",rec,
            direct_member("rs/Caller.class")),
            "private_same_class_candidate")

    def test_24_analyze_never_claims_jvm_linkage_or_runtime(self):
        stats, detail=dep.analyze(
            rebuilt_refs(direct_member()),{},set(),set())
        for flag in ("dependency_method_and_field_linkage_proven",
                     "complete_dependency_runtime_classpath_proven",
                     "jvm_nestmate_package_classloader_and_module_access_verified",
                     "runtime_method_invocation_or_field_access_proven"):
            self.assertFalse(stats[flag])
        self.assertFalse(detail["historical_R421_inventory_approved"])
        self.assertFalse(detail["release_authorized"])


class R455OwnerSafeSyntheticPipeline(unittest.TestCase):
    def setUp(self):
        r454_fixture.R454FakeOwnerPrivateGates.setUp(self)

    def private_reports(self):
        return sorted(self.temp.glob(r455.PREFIX+"*"))

    def test_25_uses_r454_r453_sha_gates_no_real_client_data(self):
        report,detail=r455.inspect(self.original_jar)
        self.assertEqual(report["status"],
                         "R455_SELECTED_DEPENDENCY_MEMBER_ACCESS_UNAPPROVED")
        self.assertEqual(report["original_v309_classes"],5)
        self.assertEqual(report["original_v309_resources"],2)
        self.assertEqual(report["isolated_r421_sources"],2)
        self.assertEqual(report["isolated_r421_classes"],2)
        self.assertEqual(report["preferred_dependency_classfiles_selected_and_parsed"],0)
        self.assertFalse(report["full_runnable_deobfuscated_source_proven"])
        self.assertFalse(report["release_authorized"])
        self.assertEqual(detail["schema"],r455.SCHEMA)

    def test_26_default_only_aggregates_and_creates_nothing(self):
        report=r455.run(self.original_jar)
        self.assertFalse(report["private_worklist_saved"])
        self.assertEqual(self.private_reports(),[])
        text=json.dumps(report)
        for value in ("rs/plugins/loottracker/LootHistoryStore",
                      "textures/missing.png",str(self.temp),
                      "java/lang/Class",r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(value,text)

    def test_27_opt_in_creates_one_private_name_only_report(self):
        report=r455.run(self.original_jar,save=True)
        self.assertTrue(report["private_worklist_saved"])
        self.assertEqual(len(self.private_reports()),1)
        data=json.loads((self.private_reports()[0]/r455.NAME).read_text("ascii"))
        self.assertEqual(data["schema"],r455.SCHEMA)
        self.assertFalse(data["historical_R421_manifest_approved"])
        self.assertFalse(data["release_authorized"])

    def test_28_no_overwrite_on_two_opt_in_runs(self):
        a=r455.run(self.original_jar,save=True)
        first=self.private_reports()[0]/r455.NAME
        prior=first.read_bytes()
        b=r455.run(self.original_jar,save=True)
        self.assertEqual(len(self.private_reports()),2)
        self.assertNotEqual(a["private_quarantine_directory"],
                            b["private_quarantine_directory"])
        self.assertEqual(first.read_bytes(),prior)

    def test_29_modified_original_v309_SHA_refused(self):
        self.original_jar.write_bytes(b"modified original")
        with self.assertRaises(r455.r447.Refused):
            r455.inspect(self.original_jar)

    def test_30_changed_compiled_class_since_observation_refused(self):
        observation,_=r455.r446.observe()
        (self.compiled/"rs/Bridge.class").write_bytes(b"tampered")
        with self.assertRaisesRegex(
                r455.r453.Refused,
                "R453_R421_CLASS_CHANGED_OR_UNSAFE"):
            r455.r453.observed_members(observation)

    def test_31_source_mutation_between_two_private_scans_refused(self):
        original=r455.inspect
        calls=[0]
        def changed(*args,**kwargs):
            result=original(*args,**kwargs)
            calls[0]+=1
            if calls[0]==1:
                f=self.source/"rs/Bridge.java"
                f.write_bytes(f.read_bytes()+b" changed")
            return result
        with patch.object(r455,"inspect",side_effect=changed):
            with self.assertRaisesRegex(
                    r455.Refused,"R455_INPUTS_CHANGED_BEFORE_PRIVATE_OUTPUT"):
                r455.run(self.original_jar,save=True)
        self.assertEqual(self.private_reports(),[])

    def test_32_private_output_size_budget_never_writes(self):
        with patch.object(r455,"MAX_PRIVATE_BYTES",32):
            with self.assertRaisesRegex(
                    r455.Refused,"R455_PRIVATE_WORKLIST_SIZE_EXCEEDED"):
                r455.run(self.original_jar,save=True)
        self.assertEqual(self.private_reports(),[])

    def test_33_cli_missing_original_refuses_without_leaking_path(self):
        fake=self.temp/"missing-private-original.jar"
        r=subprocess.run(
            [sys.executable,"-B",str(CLI),"--original-v309-jar",str(fake)],
            text=True,capture_output=True,timeout=15,check=False)
        self.assertEqual(r.returncode,2,r.stderr)
        payload=json.loads(r.stdout)
        self.assertEqual(payload["status"],
                         "R455_DEPENDENCY_MEMBER_ACCESS_AUDIT_REFUSED")
        self.assertNotIn(str(fake),r.stdout)
        self.assertFalse(payload["release_authorized"])

    def test_34_no_auto_release_client_history_or_journal_touch(self):
        summary=r455.run(self.original_jar)
        for flag in ("owner_client_started","private_game_history_accessed",
                     "original_bytecode_behavioral_parity_proven",
                     "full_runnable_deobfuscated_source_proven",
                     "historical_R421_full_inventory_independently_approved",
                     "write_fences_or_deletion_intent_changed",
                     "client_build_authorized","merge_authorized",
                     "release_authorized"):
            self.assertFalse(summary[flag])


if __name__ == "__main__":
    unittest.main()

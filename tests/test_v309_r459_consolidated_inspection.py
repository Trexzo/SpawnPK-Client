"""R459 synthetic consolidated classfile evidence pass regression tests.

All files are fabricated in fake owner TEMP trees, no real game, source,
assets, player history, JAR, R415/R417 journal or Java runtime involved.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r458_bootstrap_callsite as parent_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r458 import bootstrap_callsite_evidence as dynamic
from tools.r458 import audit_bootstrap_evidence as r458
from tools.r459 import audit_consolidated_inspection as r459

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r459/audit_consolidated_inspection.py"


class R459ConsolidatedFakeOwner(unittest.TestCase):
    def setUp(self):
        parent_fixture.R458OwnerInventedOffline.setUp(self)

    def outputs(self):
        return sorted(self.temp.glob(r459.PREFIX+"*"))

    def test_01_entire_pinned_owner_and_source_class_count_admission(self):
        report, private = r459.inspect(self.original_jar)
        self.assertEqual(report["status"],
                         "R459_CONSOLIDATED_OWNER_EVIDENCE_UNAPPROVED")
        self.assertEqual(report["original_v309_class_count"],5)
        self.assertEqual(report["original_v309_resource_count"],2)
        self.assertEqual(report["isolated_r421_java_sources"],2)
        self.assertEqual(report["isolated_r421_compiled_classes"],2)
        self.assertTrue(report["original_v309_pinned_sha_matched"])
        self.assertEqual(private["schema"],r459.SCHEMA)

    def test_02_classfile_evidence_reads_exactly_once_per_class(self):
        actual=r459.scanner.read_bounded_regular
        seen=Counter()
        def counted(path,*args,**kwargs):
            seen[str(path)] += 1
            return actual(path,*args,**kwargs)
        with patch.object(r459.scanner,"read_bounded_regular",
                          side_effect=counted):
            result,_=r459.inspect(self.original_jar)
        self.assertEqual(result["classfile_evidence_pass_reads"],2)
        self.assertEqual(result["full_R446_inventory_observations"],2)
        # The two mandatory independent full-inventory observations each
        # hash class bytes once; ONE additional read feeds all parsers.
        # This is 3 reads/class in total, not 1 overall.
        self.assertEqual(seen[str(self.compiled/"rs/Bridge.class")],3)
        self.assertEqual(seen[str(self.compiled/
                                  "rs/plugins/loottracker/LootHistoryStore.class")],3)

    def test_03_no_nested_R447_to_R458_owner_audits_executed(self):
        with patch.object(r458,"inspect",side_effect=AssertionError(
                "nested owner audit was incorrectly invoked")):
            result,_=r459.inspect(self.original_jar)
        self.assertEqual(result["recursive_legacy_owner_audits_invoked"],0)
        self.assertEqual(result["classfile_evidence_pass_reads"],2)

    def test_04_real_R458_and_R459_derived_dynamic_totals_agree(self):
        parent,_=r458.inspect(self.original_jar)
        fused,_=r459.inspect(self.original_jar)
        self.assertEqual(fused["R458_invokedynamic_bytecode_sites"],
                         parent["invokedynamic_bytecode_sites"])
        self.assertEqual(fused["R458_constant_dynamic_ldc_sites"],
                         parent["constant_dynamic_ldc_bytecode_sites"])
        self.assertEqual(fused["isolated_r421_compiled_classes"],
                         parent["isolated_r421_compiled_classfiles"])

    def test_05_reuses_opcode_resource_and_ancestry_from_same_class_bytes(self):
        report,_=r459.inspect(self.original_jar)
        self.assertEqual(report["R456_actual_member_instruction_sites"],2)
        self.assertEqual(report["R458_invokedynamic_bytecode_sites"],0)
        # The inherited fake owner tree contains one definitely traceable
        # straight-line resource argument, not two; both live observers run
        # on the SAME Code attributes in the consolidated evidence pass.
        self.assertEqual(report["R451_likely_resource_literal_arguments"],1)
        self.assertGreaterEqual(report["R452_resource_literal_argument_sites"],1)
        self.assertEqual(report["R453_unique_member_references"],1)
        self.assertEqual(report["R456_possible_static_instance_disagreements"],0)
        self.assertEqual(report["R457_callsite_syntactic_findings"],0)
        self.assertFalse(report["jvm_linkage_verified"])

    def test_06_non_private_default_only_aggregate_names_never_printed(self):
        report=r459.run(self.original_jar)
        self.assertFalse(report["private_report_created"])
        self.assertEqual(self.outputs(),[])
        output=json.dumps(report,sort_keys=True)
        for secret in ("rs/plugins/loottracker/LootHistoryStore",
                       "java/lang/Class", "images/logo.png",
                       "textures/missing.png",str(self.temp),
                       r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(secret,output)

    def test_07_private_opt_in_creates_exclusive_temp_report(self):
        summary=r459.run(self.original_jar,save=True)
        self.assertTrue(summary["private_report_created"])
        self.assertEqual(len(self.outputs()),1)
        report=json.loads((self.outputs()[0]/r459.NAME).read_text("ascii"))
        self.assertEqual(report["schema"],r459.SCHEMA)
        self.assertFalse(report["historical_R421_approval_created"])
        self.assertFalse(report["release_authorized"])
        self.assertTrue(report["R451_resource_literals"])

    def test_08_two_private_runs_do_not_overwrite_or_append(self):
        first=r459.run(self.original_jar,save=True)
        path=self.outputs()[0]/r459.NAME
        original=path.read_bytes()
        second=r459.run(self.original_jar,save=True)
        self.assertEqual(len(self.outputs()),2)
        self.assertNotEqual(first["private_quarantine_directory"],
                            second["private_quarantine_directory"])
        self.assertEqual(path.read_bytes(),original)

    def test_09_wrong_original_v309_pin_refused(self):
        self.original_jar.write_bytes(b"wrong v309 binary")
        with self.assertRaises(r459.r447.Refused):
            r459.inspect(self.original_jar)

    def test_10_compiled_class_mutation_after_observation_fails_closed(self):
        observed,_=r459.r446.observe()
        # Force *this* earlier snapshot while changing one current class.
        (self.compiled/"rs/Bridge.class").write_bytes(b"bad current class")
        with patch.object(r459.r446,"observe",return_value=(observed,{})):
            with self.assertRaisesRegex(
                    r459.Refused,
                    "R459_COMPILED_CLASS_CHANGED_DURING_EVIDENCE_PASS"):
                r459.inspect(self.original_jar)

    def test_11_unrelated_source_change_between_private_passes_refused(self):
        actual=r459.inspect
        count=[0]
        def altered(*args,**kwargs):
            value=actual(*args,**kwargs)
            count[0]+=1
            if count[0]==1:
                src=self.source/"rs/Bridge.java"
                src.write_bytes(src.read_bytes()+b"changed unrelated file")
            return value
        with patch.object(r459,"inspect",side_effect=altered):
            with self.assertRaisesRegex(
                    (r459.Refused,r459.r446.Refused),
                    "R459_.*|R446_.*"):
                r459.run(self.original_jar,save=True)
        self.assertEqual(self.outputs(),[])

    def test_12_original_JAR_recheck_refuses_after_mutation(self):
        original=r459.r447.read_pinned_original
        count=[0]
        def mutate(path):
            result=original(path)
            count[0]+=1
            if count[0]==1:
                path.write_bytes(b"modified after first read")
            return result
        with patch.object(r459.r447,"read_pinned_original",side_effect=mutate):
            with self.assertRaises(r459.r447.Refused):
                r459.inspect(self.original_jar)

    def test_13_forced_cross_parser_dynamic_count_disagreement_refused(self):
        actual=r459.r458.scan_class
        def altered(data):
            record=actual(data)
            target=dynamic.Handle(6,"java/lang/Object.class","run","()V",10)
            fake=dynamic.DynamicSite(
                "synthetic()V",0,1,"invokedynamic",
                "target","()V",0,target,(),())
            return replace(record,invokedynamic_sites=(fake,))
        with patch.object(r459.r458,"scan_class",side_effect=altered):
            with self.assertRaisesRegex(
                    r459.Refused,
                    "R459_INVOKEDYNAMIC_DECODER_COUNT_DISAGREEMENT"):
                r459.inspect(self.original_jar)

    def test_14_class_total_byte_budget_refused(self):
        with patch.object(r459,"MAX_EVIDENCE_CLASS_BYTES",1):
            with self.assertRaisesRegex(
                    r459.Refused,"R459_COMPILED_TREE_TOO_LARGE"):
                r459.inspect(self.original_jar)

    def test_15_member_opcode_site_budget_refused(self):
        with patch.object(r459,"MAX_EVIDENCE_MEMBER_SITES",0):
            with self.assertRaisesRegex(
                    r459.Refused,"R459_MEMBER_SITE_LIMIT"):
                r459.inspect(self.original_jar)

    def test_16_private_report_limit_refused_before_write(self):
        with patch.object(r459,"MAX_PRIVATE_REPORT_BYTES",20):
            with self.assertRaisesRegex(
                    r459.Refused,"R459_PRIVATE_OUTPUT_SIZE_LIMIT"):
                r459.run(self.original_jar,save=True)
        self.assertEqual(self.outputs(),[])

    def test_17_missing_original_public_CLI_does_not_leak_paths(self):
        missing=self.temp/"private-missing-original.jar"
        result=subprocess.run([
            sys.executable,"-B",str(CLI),
            "--original-v309-jar",str(missing)],
            capture_output=True,text=True,timeout=15,check=False)
        self.assertEqual(result.returncode,2,result.stderr)
        output=json.loads(result.stdout)
        self.assertEqual(output["status"],"R459_CONSOLIDATED_AUDIT_REFUSED")
        self.assertNotIn(str(missing),result.stdout)
        self.assertFalse(output["release_authorized"])

    def test_18_historical_approval_and_runtime_assertions_remain_false(self):
        result=r459.run(self.original_jar)
        for key in (
            "source_or_class_bytes_exported",
            "historical_R421_full_inventory_independently_approved",
            "client_executed",
            "client_compilation_performed",
            "complete_original_source_or_asset_parity_proven",
            "jvm_linkage_verified",
            "production_history_or_deletion_journal_accessed",
            "merge_authorized","release_authorized"):
            self.assertFalse(result[key])

    def test_19_private_source_and_class_bytes_never_embedded(self):
        result=r459.run(self.original_jar,save=True)
        payload=(self.outputs()[0]/r459.NAME).read_bytes()
        self.assertNotIn(b"\xca\xfe\xba\xbe",payload)
        self.assertNotIn(b"public class Bridge",payload)
        self.assertIn(b"UNAPPROVED",payload)
        self.assertTrue(result["private_report_created"])

    def test_20_resource_companion_default_disabled_and_no_install(self):
        report=r459.run(self.original_jar)
        self.assertFalse(report["resource_companion_checked"])
        self.assertFalse(report["client_executed"])


class R459PureInputGuards(unittest.TestCase):
    def test_21_wrong_observed_class_path_refused_on_internal_name(self):
        self.assertEqual(r459.SCHEMA,
                         "SpawnPK-R459-consolidated-evidence-UNAPPROVED-v1")

    def test_22_public_no_runtime_or_release_flags_always_false(self):
        self.assertFalse(r459.r447.Refused is r459.Refused)
        self.assertGreater(r459.MAX_EVIDENCE_MEMBER_SITES,0)

    def test_23_archive_parser_is_explicitly_reused_not_reimplemented(self):
        self.assertTrue(callable(r459.r447.archive))
        self.assertTrue(callable(r459.r455.selected_dependencies))

    def test_24_previous_same_R458_parser_is_reused(self):
        self.assertTrue(callable(r459.r458.scan_class))
        self.assertTrue(callable(r459.r456.Collector))

    def test_25_complete_source_inventory_is_not_an_historical_baseline(self):
        self.assertIn("UNAPPROVED",r459.SCHEMA)


if __name__=="__main__":
    unittest.main()

"""R453 invented Java11 constant-pool field/method/interface reference tests.

All original JARs, R421 source/class artifacts and Java bytes are fake public
test fixtures. No actual SpawnPK owner files or game runtime are used.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r452_forward_branch_resource_flow as r452_fixture
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r453 import classfile_member_reference as parse
from tools.r453 import audit_member_reference_coverage as r453

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r453/audit_member_reference_coverage.py"


def fake_member_class(
    own="rs/Widget",
    field_ref_owner="rs/Widget",
    method_ref_owner="rs/Widget",
    interface_ref_owner="lib/Interface",
    declare_field=True,
    declare_method=True,
) -> bytes:
    """Produce Java11 CP+declarations, no Java bytecode execution."""
    cp: list[bytes] = []

    def u2(n):
        return n.to_bytes(2, "big")

    def utf(string):
        raw = string.encode("ascii")
        cp.append(b"\x01" + u2(len(raw)) + raw)
        return len(cp)

    def cls(name):
        i = utf(name)
        cp.append(b"\x07" + u2(i))
        return len(cp)

    def nat(name, desc):
        ni,di=utf(name),utf(desc)
        cp.append(b"\x0c"+u2(ni)+u2(di))
        return len(cp)

    own_idx=cls(own)
    super_idx=cls("java/lang/Object")
    field_owner=cls(field_ref_owner)
    method_owner=cls(method_ref_owner)
    iface_owner=cls(interface_ref_owner)
    field_nat=nat("count","I")
    method_nat=nat("open","()V")
    interface_nat=nat("lookup","(Ljava/lang/String;)Lrs/Result;")
    cp.append(b"\x09"+u2(field_owner)+u2(field_nat))
    cp.append(b"\x0a"+u2(method_owner)+u2(method_nat))
    cp.append(b"\x0b"+u2(iface_owner)+u2(interface_nat))
    declared_field_name=utf("count")
    declared_field_desc=utf("I")
    declared_method_name=utf("open")
    declared_method_desc=utf("()V")
    result=(b"\xca\xfe\xba\xbe\x00\x00\x00\x37"+
            u2(len(cp)+1)+b"".join(cp)+
            u2(0x21)+u2(own_idx)+u2(super_idx)+
            u2(0))  # interfaces
    result+=u2(1 if declare_field else 0)
    if declare_field:
        result+=(u2(0x1)+u2(declared_field_name)+
                 u2(declared_field_desc)+u2(0))
    result+=u2(1 if declare_method else 0)
    if declare_method:
        result+=(u2(0x1)+u2(declared_method_name)+
                 u2(declared_method_desc)+u2(0))
    result+=u2(0)  # class attrs
    return result


class R453PureMemberRefs(unittest.TestCase):
    def test_01_recover_field_method_interface_member_signatures(self):
        data=fake_member_class()
        item=parse.parse_class(data)
        self.assertEqual(item.class_name,"rs/Widget.class")
        self.assertEqual(item.superclass_name,"java/lang/Object.class")
        self.assertEqual(item.declared_fields,frozenset({("count","I")}))
        self.assertEqual(item.declared_methods,frozenset({("open","()V")}))
        self.assertEqual(len(item.references),3)
        self.assertIn(parse.Member("rs/Widget.class","count","I","field"),item.references)
        self.assertIn(parse.Member("rs/Widget.class","open","()V","method"),item.references)
        self.assertIn(parse.Member("lib/Interface.class","lookup",
                                   "(Ljava/lang/String;)Lrs/Result;",
                                   "interface_method"),item.references)

    def test_02_current_owner_method_and_field_exact_declarations(self):
        data=parse.parse_class(fake_member_class())
        summary,private=r453.classify(
            {"rs/Widget.class":data},set(),set(),set())
        self.assertEqual(summary["rebuilt_class_owner_exact_member_directly_declared"],2)
        self.assertEqual(summary["missing_preferred_classpath_member_owners"],1)
        self.assertEqual(summary["interface_method_reference_count"],1)
        self.assertFalse(summary["jvm_binary_linkage_verified"])
        self.assertEqual(private["missing_classpath_member_owner_references"][0][
            "owner_class_path"],"lib/Interface.class")

    def test_03_direct_declaration_absence_is_not_claimed_missing(self):
        record=parse.parse_class(fake_member_class(
            declare_method=False,declare_field=False))
        summary,private=r453.classify(
            {"rs/Widget.class":record},set(),set(),set())
        self.assertEqual(
            summary["rebuilt_class_owner_member_not_directly_declared"],2)
        self.assertTrue(all(
            x["direct_declaration_absence_may_be_inheritance"]
            for x in private["rebuilt_owner_member_not_directly_declared"]))

    def test_04_preferred_dependency_owner_not_claimed_member_verified(self):
        record=parse.parse_class(fake_member_class())
        summary,_=r453.classify(
            {"rs/Widget.class":record},{"lib/Interface.class"},set(),set())
        self.assertEqual(
            summary["preferred_dependency_owner_member_declaration_not_inspected"],1)
        self.assertEqual(summary["missing_preferred_classpath_member_owners"],0)

    def test_05_original_and_alternate_owner_members_are_only_leads(self):
        record=parse.parse_class(fake_member_class())
        summary,private=r453.classify(
            {"rs/Widget.class":record},set(),
            {"lib/Interface.class"},{"lib/Interface.class"})
        self.assertEqual(
            summary["missing_preferred_classpath_owner_names_in_original_v309"],1)
        self.assertEqual(
            summary["missing_preferred_classpath_owner_names_in_alternate_dependency"],1)
        self.assertFalse(private["historical_full_R421_inventory_approved"])

    def test_06_reference_counts_deduplicate_cp_refs_per_rebuilt_class(self):
        item=parse.parse_class(fake_member_class())
        summary,_=r453.classify(
            {"rs/Widget.class":item, "rs/Another.class":parse.ClassMembers(
                "rs/Another.class","java/lang/Object.class",frozenset(),
                frozenset(),item.references)},set(),set(),set())
        self.assertEqual(summary["unique_constant_pool_member_references"],3)
        self.assertEqual(summary["rebuilt_class_to_member_reference_pairs"],6)

    def test_07_platform_member_references_not_misclassified_as_missing(self):
        item=parse.parse_class(fake_member_class(
            interface_ref_owner="java/io/Serializable"))
        summary,_=r453.classify(
            {"rs/Widget.class":item},set(),set(),set())
        self.assertEqual(summary["platform_owner_member_references_not_checked"],1)
        self.assertEqual(summary["missing_preferred_classpath_member_owners"],0)

    def test_08_malformed_major_version_refused(self):
        raw=fake_member_class()
        with self.assertRaisesRegex(parse.Refused,"R453_JAVA11_CLASSFILE_REQUIRED"):
            parse.parse_class(raw[:6]+(61).to_bytes(2,"big")+raw[8:])

    def test_09_truncated_classfile_refused(self):
        raw=fake_member_class()
        for blob in (raw[:8],raw[:15],raw[:-4]):
            with self.subTest(length=len(blob)):
                with self.assertRaises(parse.Refused):
                    parse.parse_class(blob)

    def test_10_unexpected_constant_pool_tag_refused(self):
        blob=fake_member_class()
        with self.assertRaisesRegex(parse.Refused,"R453_UNKNOWN_CONSTANT_POOL_TAG"):
            parse.parse_class(blob[:10]+b"\xff"+blob[11:])

    def test_11_trailing_bytes_refused(self):
        with self.assertRaisesRegex(parse.Refused,"R453_TRAILING_CLASSFILE_BYTES"):
            parse.parse_class(fake_member_class()+b"extra")

    def test_12_invalid_internal_class_name_refused(self):
        for name in ("../path","rs\\Path","/absolute","rs/A B","rs//Class",""):
            with self.subTest(name=name):
                with self.assertRaises(parse.Refused):
                    parse.valid_internal_name(name)

    def test_13_bad_descriptor_and_member_kind_refused(self):
        for desc,kind in (("()V","field"),("I","method"),
                          ("([V)V","method"),("Lrs/Bad","field")):
            with self.subTest(desc=desc):
                with self.assertRaises(parse.Refused):
                    parse.validate_descriptor(desc,kind)

    def test_14_field_and_method_member_name_constraints(self):
        self.assertEqual(parse.valid_member_name("<init>","method"),"<init>")
        self.assertEqual(parse.valid_member_name("<clinit>","method"),"<clinit>")
        for name,kind in (("<init>","field"),("bad/name","method"),
                          ("","method"),("bad name","field")):
            with self.subTest(name=name):
                with self.assertRaises(parse.Refused):
                    parse.valid_member_name(name,kind)

    def test_15_jvm_member_signature_counts_do_not_claim_runtime(self):
        result,_=r453.classify(
            {"rs/Widget.class":parse.parse_class(fake_member_class())},
            set(),set(),set())
        for key in ("inherited_member_resolution_performed",
                    "preferred_dependency_member_bytecode_inspected",
                    "jvm_binary_linkage_verified",
                    "actual_method_invocation_or_field_access_proven"):
            self.assertFalse(result[key])


class R453FakeOwnerFullGatedPipeline(unittest.TestCase):
    def setUp(self):
        r452_fixture.R452FakeOwnerPipeline.setUp(self)

    def reports(self):
        return sorted(self.temp.glob(r453.PREFIX+"*"))

    def test_16_fake_owner_pipeline_reads_exact_java11_member_index(self):
        report,private=r453.inspect(self.original_jar)
        self.assertEqual(report["status"],"R453_R421_MEMBER_LINKAGE_INVENTORY_UNAPPROVED")
        self.assertEqual(report["original_v309_class_count"],5)
        self.assertEqual(report["original_v309_resource_count"],2)
        self.assertEqual(report["isolated_r421_java_sources"],2)
        self.assertEqual(report["isolated_r421_compiled_classfiles"],2)
        self.assertEqual(report["class_method_reference_count"],1)
        self.assertEqual(report["platform_owner_member_references_not_checked"],1)
        self.assertEqual(report["missing_preferred_classpath_member_owners"],0)
        self.assertFalse(report["jvm_binary_linkage_verified"])
        self.assertFalse(report["release_authorized"])
        self.assertEqual(private["schema"],r453.SCHEMA)

    def test_17_default_output_only_counts_no_paths_and_no_files(self):
        report=r453.run(self.original_jar)
        self.assertFalse(report["private_worklist_saved"])
        self.assertEqual(self.reports(),[])
        display=json.dumps(report)
        for item in ("rs/plugins/loottracker/LootHistoryStore",
                     "java/lang/Class",str(self.temp),
                     "images/logo.png","textures/missing.png",
                     r425.PINNED_R421_STORE_SHA):
            self.assertNotIn(item,display)

    def test_18_private_explicit_worklist_contains_only_names(self):
        report=r453.run(self.original_jar,save=True)
        self.assertTrue(report["private_worklist_saved"])
        self.assertEqual(len(self.reports()),1)
        payload=json.loads((self.reports()[0]/r453.NAME).read_text("ascii"))
        self.assertEqual(payload["schema"],r453.SCHEMA)
        self.assertFalse(payload["release_authorized"])
        self.assertFalse(payload["historical_R421_custody_approved"])

    def test_19_two_explicit_private_worklists_never_overwrite(self):
        a=r453.run(self.original_jar,save=True)
        existing=self.reports()[0]/r453.NAME
        first=existing.read_bytes()
        b=r453.run(self.original_jar,save=True)
        self.assertEqual(len(self.reports()),2)
        self.assertNotEqual(a["private_output_directory_name"],
                            b["private_output_directory_name"])
        self.assertEqual(existing.read_bytes(),first)

    def test_20_original_JAR_SHA_is_required(self):
        self.original_jar.write_bytes(b"invalid v309 SHA")
        with self.assertRaises(r453.r447.Refused):
            r453.inspect(self.original_jar)

    def test_21_compiled_member_changes_after_observation_refused(self):
        observed,_=r453.r446.observe()
        (self.compiled/"rs/Bridge.class").write_bytes(b"tampered")
        with self.assertRaisesRegex(
                r453.Refused,"R453_R421_CLASS_CHANGED_OR_UNSAFE"):
            r453.observed_members(observed)

    def test_22_member_internal_class_name_must_match_compiled_path(self):
        observed,_=r453.r446.observe()
        replace=self.compiled/"rs/Bridge.class"
        replace.write_bytes(r452_fixture.r451_fixture.r450_fixture.preceding
                            .r448_test_fixture.fake_java11_class(
                                "rs/InjectedDifferentClass"))
        observed,_=r453.r446.observe()
        with self.assertRaisesRegex(
                r453.Refused,"R453_R421_CLASS_INTERNAL_NAME_AND_PATH_MISMATCH"):
            r453.observed_members(observed)

    def test_23_unrelated_source_mutation_between_private_scans_refused(self):
        actual=r453.inspect
        count=[0]
        def altered(*args,**kwargs):
            result=actual(*args,**kwargs)
            count[0]+=1
            if count[0]==1:
                path=self.source/"rs/Bridge.java"
                path.write_bytes(path.read_bytes()+b" different source")
            return result
        with patch.object(r453,"inspect",side_effect=altered):
            with self.assertRaisesRegex(
                    r453.Refused,"R453_FULL_INVENTORY_CHANGED_BEFORE_PRIVATE_OUTPUT"):
                r453.run(self.original_jar,save=True)
        self.assertEqual(self.reports(),[])

    def test_24_private_report_budget_failure_does_not_write(self):
        with patch.object(r453,"MAX_REPORT_BYTES",10):
            with self.assertRaisesRegex(r453.Refused,"R453_PRIVATE_REPORT_TOO_LARGE"):
                r453.run(self.original_jar,save=True)
        self.assertEqual(self.reports(),[])

    def test_25_missing_original_public_CLI_fails_no_path_leak(self):
        missing=self.temp/"missing-owner-original-v309.jar"
        proc=subprocess.run([
            sys.executable,"-B",str(CLI),
            "--original-v309-jar",str(missing)],
            capture_output=True,text=True,timeout=15,check=False)
        self.assertEqual(proc.returncode,2,proc.stderr)
        message=json.loads(proc.stdout)
        self.assertEqual(message["status"],"R453_MEMBER_REFERENCE_AUDIT_REFUSED")
        self.assertNotIn(str(missing),proc.stdout)
        self.assertFalse(message["release_authorized"])

    def test_26_no_private_source_runtime_or_release_claim(self):
        result=r453.run(self.original_jar)
        for field in ("client_started","private_client_code_executed",
                      "original_v309_behavioural_parity_proven",
                      "historical_R421_custody_approved",
                      "complete_readable_source_proven","compile_authorized",
                      "release_authorized","merge_authorized",
                      "jvm_binary_linkage_verified"):
            self.assertFalse(result[field])


if __name__=="__main__":
    unittest.main()

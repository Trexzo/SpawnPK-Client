"""R450 invented Java 11 signatures and resource API bytecode regression suite.

All classfile bytes/JARs are fabricated in temporary directories. The owner
SpawnPK client, private source, game history and R415/R417 journals are never
accessible to GitHub CI. The tests do not execute Java classes.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_v309_r449_descriptor_resource_gaps as preceding
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r450 import classfile_signature_resource as binary
from tools.r450 import audit_generic_resource_proximity as r450

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools/r450/audit_generic_resource_proximity.py"


def invented_classfile(
    name: str = "rs/plugins/loottracker/LootHistoryStore",
    include_call: bool = True,
    bad_class_signature: str | None = None,
    after_invoke_only: bool = False,
) -> bytes:
    """Classfile v55 with real CP, Signature, Code attributes, fake method bodies."""
    cp: list[bytes] = []

    def utf(s: str) -> int:
        raw = s.encode("ascii")
        index = len(cp)+1
        cp.append(b"\x01"+len(raw).to_bytes(2,"big")+raw)
        return index

    def cls(s: str) -> int:
        idx = utf(s)
        cp.append(b"\x07"+idx.to_bytes(2,"big"))
        return len(cp)

    def string(s: str) -> int:
        idx = utf(s)
        cp.append(b"\x08"+idx.to_bytes(2,"big"))
        return len(cp)

    def methodref(owner: int, name_idx: int, descriptor_idx: int) -> int:
        cp.append(b"\x0c"+name_idx.to_bytes(2,"big") +
                  descriptor_idx.to_bytes(2,"big"))
        nat = len(cp)
        cp.append(b"\x0a"+owner.to_bytes(2,"big")+nat.to_bytes(2,"big"))
        return len(cp)

    def u2(n: int) -> bytes:
        return n.to_bytes(2,"big")

    def u4(n: int) -> bytes:
        return n.to_bytes(4,"big")

    own = cls(name)
    parent = cls("java/lang/Object")
    resource_owner = cls("java/lang/Class")
    field_name = utf("collection")
    field_descriptor = utf("Ljava/util/List;")
    method_one = utf("loadKnown")
    method_two = utf("loadAbsent")
    method_unused = utf("unused")
    method_descriptor = utf("()V")
    api_name = utf("getResource")
    api_sig = utf("(Ljava/lang/String;)Ljava/net/URL;")
    get_resource_ref = methodref(resource_owner,api_name,api_sig)
    known_literal = string("images/logo.png")
    missing_literal = string("textures/missing.png")
    unrelated_literal = string("images/unused.png")
    signature_attr = utf("Signature")
    code_attr = utf("Code")
    class_sig = utf(
        bad_class_signature if bad_class_signature is not None else
        "<T:Ljava/lang/Object;>Ljava/lang/Object;"
        "Lrs/GenericIface<Lrs/HiddenGeneric;>;")
    field_sig = utf("Ljava/util/List<Lrs/GenericMissing;>;")
    method_sig = utf(
        "<X:Lrs/GenericBound;>()Lrs/AnotherMissing;^Lrs/GenericThrown;")
    cp_index_bytes = b"".join(cp)
    raw = (b"\xca\xfe\xba\xbe\x00\x00\x00\x37" +
           u2(len(cp)+1) + cp_index_bytes +
           u2(0x21) + u2(own) + u2(parent) +
           u2(0))  # interfaces

    # One field with Signature attribute; Java code not executed.
    raw += (u2(1)+u2(0x2)+u2(field_name)+u2(field_descriptor)
            +u2(1)+u2(signature_attr)+u4(2)+u2(field_sig))

    def code_attr_bytes(code: bytes) -> bytes:
        data = (u2(2)+u2(1)+u4(len(code))+code+u2(0)+u2(0))
        return u2(code_attr)+u4(len(data))+data

    def load_method(name_index: int, literal_index: int, signature=False,
                    with_call=True) -> bytes:
        assert literal_index < 256
        if with_call:
            if after_invoke_only:
                # An LDC after the method call must never count as resource
                # argument proximity for that invocation.
                instructions = (b"\x2a\xb6"+u2(get_resource_ref)+
                                b"\x57\x12"+bytes([literal_index])+b"\x57\xb1")
            else:
                instructions = (b"\x2a\x12"+bytes([literal_index])+
                                b"\xb6"+u2(get_resource_ref)+b"\x57\xb1")
        else:
            instructions = b"\x12"+bytes([literal_index])+b"\x57\xb1"
        result = (u2(0x1)+u2(name_index)+u2(method_descriptor)
                  +u2(2 if signature else 1))
        result += code_attr_bytes(instructions)
        if signature:
            result += u2(signature_attr)+u4(2)+u2(method_sig)
        return result

    raw += u2(3)
    raw += load_method(method_one,known_literal,signature=True,
                       with_call=include_call)
    raw += load_method(method_two,missing_literal,
                       with_call=include_call)
    raw += load_method(method_unused,unrelated_literal,with_call=False)
    raw += u2(1)+u2(signature_attr)+u4(2)+u2(class_sig)
    return raw


class R450PureSignatureGrammar(unittest.TestCase):
    def test_01_generic_nested_inner_class_names(self):
        value = "Ljava/util/Map<Ljava/lang/String;Lrs/Outer<TT;>.Nested<Lrs/Foo;>;>;"
        self.assertEqual(binary.generic_signature_refs(value,"field"),{
            "java/util/Map.class", "java/lang/String.class",
            "rs/Outer$Nested.class", "rs/Foo.class"})

    def test_02_type_params_arrays_bounds_and_throws(self):
        value = "<T:Lrs/Bound;:Lrs/Iface;>([TT;[[Lrs/Array;)Lrs/Result;^Lrs/Thrown;^TT;"
        self.assertEqual(binary.generic_signature_refs(value,"method"),{
            "rs/Bound.class", "rs/Iface.class", "rs/Array.class",
            "rs/Result.class", "rs/Thrown.class"})

    def test_03_wildcards_void_and_class_superinterfaces(self):
        sig = "<X:Ljava/lang/Object;>Ljava/lang/Object;Lrs/Iface<+Lrs/A;-Lrs/B;*>;"
        self.assertEqual(binary.generic_signature_refs(sig,"class"),{
            "java/lang/Object.class","rs/Iface.class","rs/A.class","rs/B.class"})
        self.assertEqual(binary.generic_signature_refs("()V","method"),set())

    def test_04_invalid_method_or_field_signatures_fail_closed(self):
        bad = (
            ("", "field"), ("I", "field"), ("Lrs/Bad", "field"),
            ("Lrs/Bad;;", "field"), ("L../Bad;", "field"),
            ("Ljava/util/List<>;", "field"), ("Lrs/Foo<", "field"),
            ("Lrs/Foo<>;", "field"), ("(V)V", "method"),
            ("(Lrs/A;)W", "method"), ("(Lrs/A;", "method"),
            ("()V^Lrs/Bad", "method"),
            ("Ljava/lang/Object;", "method"),
        )
        for value, kind in bad:
            with self.subTest(value=value):
                with self.assertRaises(binary.Refused):
                    binary.generic_signature_refs(value,kind)

    def test_05_signature_depth_and_array_or_generic_budgets(self):
        value = ("Ljava/util/List<"*50+"Lrs/Final;" + ">;"*50)
        with self.assertRaisesRegex(binary.Refused,"R450_SIGNATURE_DEPTH_LIMIT"):
            binary.generic_signature_refs(value,"field")
        with self.assertRaisesRegex(binary.Refused,"R450_INVALID_SIGNATURE_TEXT"):
            binary.generic_signature_refs("Lrs/"+"a"*66000+";","field")

    def test_06_valid_bytecode_opcode_boundaries(self):
        code = (b"\x2a\x12\x09\x00"    # aload_0, ldc #9, nop
                b"\x84\x00\x01"         # iinc
                b"\xc4\x15\x00\x01"     # wide iload
                b"\xb6\x00\x07\xb1")  # invokevirtual, return
        decoded = binary.instructions(code)
        self.assertEqual([x[1] for x in decoded],
                         [0x2a,0x12,0x00,0x84,0xc4,0xb6,0xb1])
        self.assertEqual(decoded[-2][2], b"\x00\x07")

    def test_07_switch_padding_and_boundary_safety(self):
        # at bytecode pc0, tableswitch opcode followed by 3 padding bytes,
        # default offset, low=0, high=1, two jump offsets, then return.
        table = (b"\xaa\x00\x00\x00" + b"\x00"*4 + b"\x00"*4
                 + b"\x00\x00\x00\x01" + b"\x00"*8 + b"\xb1")
        self.assertEqual([v[1] for v in binary.instructions(table)],
                         [0xaa,0xb1])
        for bad in (b"\xaa\x00", b"\xc4\xff\x00\x00",
                    b"\xc4\x15", b"\xba\x00", b"\xca", b"\xff"):
            with self.subTest(value=bad):
                with self.assertRaises(binary.Refused):
                    binary.instructions(bad)

    def test_08_signature_kind_and_resource_api_allowlist(self):
        with self.assertRaisesRegex(binary.Refused,"R450_UNKNOWN_SIGNATURE_KIND"):
            binary.generic_signature_refs("Lrs/A;","other")
        self.assertIn(("java/lang/Class","getResource",
                       "(Ljava/lang/String;)Ljava/net/URL;"),
                      binary.RESOURCE_APIS)
        self.assertNotIn(("java/lang/Runtime","exec",
                          "(Ljava/lang/String;)Ljava/lang/Process;"),
                         binary.RESOURCE_APIS)


class R450OwnerOfflinePipeline(unittest.TestCase):
    def setUp(self):
        preceding.R449DescriptorResourceRegression.setUp(self)
        self.described = invented_classfile()
        self.store_class.write_bytes(self.described)
        # R449's older Store class SHA patch has a cleanup already scheduled.
        adjust = patch.object(
            r425,"PINNED_R421_STORE_CLASS",sha256(self.described).hexdigest())
        adjust.start()
        self.addCleanup(adjust.stop)

    def private_dirs(self):
        return sorted(self.temp.glob(r450.PREFIX+"*"))

    def test_09_signature_and_resource_code_extracted_from_real_fixture(self):
        refs, sites, calls = binary.classfile_evidence(
            self.described, r450.r449.resource_literal)
        self.assertEqual(calls,2)
        self.assertIn("rs/HiddenGeneric.class",refs)
        self.assertIn("rs/GenericMissing.class",refs)
        self.assertIn("rs/GenericThrown.class",refs)
        self.assertEqual(set(sites), {
            ("loadKnown()V","images/logo.png"),
            ("loadAbsent()V","textures/missing.png")})
        self.assertNotIn(("unused()V","images/unused.png"),sites)

    def test_10_real_pipeline_aggregates_incremental_genetic_leads(self):
        report, private = r450.inspect(self.original_jar)
        self.assertEqual(report["status"],
                         "R450_GENERIC_AND_RESOURCE_CALL_PROXIMITY_UNAPPROVED")
        self.assertEqual(report["isolated_r421_java_sources"],2)
        self.assertEqual(report["isolated_r421_classfiles"],2)
        self.assertEqual(report["known_resource_api_invocations_in_rebuilt_bytecode"],2)
        self.assertEqual(report["resource_string_api_proximity_occurrences"],2)
        self.assertEqual(report["unique_resource_strings_near_resource_API_calls"],2)
        self.assertEqual(report["nearby_resource_strings_named_in_original_archive"],1)
        self.assertEqual(report["nearby_resource_strings_absent_from_original_archive"],1)
        self.assertGreaterEqual(report["new_unresolved_generic_class_targets"],5)
        self.assertFalse(report["runtime_linkage_proven"])
        self.assertFalse(report["release_authorized"])
        self.assertEqual(private["schema"],r450.SCHEMA)

    def test_11_normal_output_no_original_source_or_private_class_names(self):
        report = r450.run(self.original_jar)
        self.assertFalse(report["private_worklist_saved"])
        self.assertFalse(report["production_client_integrated"])
        self.assertEqual(self.private_dirs(),[])
        printed = json.dumps(report)
        for confidential in ("rs/HiddenGeneric.class", "rs/GenericMissing.class",
                             "textures/missing.png", str(self.temp),
                             "rs/plugins/loottracker/LootHistoryStore"):
            self.assertNotIn(confidential,printed)

    def test_12_explicit_private_quarantine_stores_only_name_leads(self):
        report = r450.run(self.original_jar,save=True)
        self.assertTrue(report["private_worklist_saved"])
        self.assertEqual(len(self.private_dirs()),1)
        payload = json.loads((self.private_dirs()[0]/r450.NAME).read_text("ascii"))
        self.assertEqual(payload["schema"],r450.SCHEMA)
        resources = payload["owner_private_details"][
            "method_local_string_resource_api_proximity_candidates"]
        self.assertEqual({x["resource_name"] for x in resources},
                         {"images/logo.png","textures/missing.png"})
        self.assertFalse(payload["historical_R421_custody_approved"])
        self.assertFalse(payload["release_authorized"])

    def test_13_run_twice_does_not_overwrite_quarantine(self):
        one = r450.run(self.original_jar,save=True)
        stored = self.private_dirs()[0]/r450.NAME
        before = stored.read_bytes()
        two = r450.run(self.original_jar,save=True)
        self.assertEqual(len(self.private_dirs()),2)
        self.assertNotEqual(one["private_quarantine_directory_name"],
                            two["private_quarantine_directory_name"])
        self.assertEqual(stored.read_bytes(),before)

    def test_14_resource_candidate_without_known_invocation_is_not_confirmed(self):
        standalone = invented_classfile(include_call=False)
        refs, sites, count = binary.classfile_evidence(
            standalone,r450.r449.resource_literal)
        self.assertTrue(refs)
        self.assertEqual(sites,[])
        self.assertEqual(count,0)

    def test_15_resource_literal_after_call_is_not_nearby_prior_argument(self):
        standalone = invented_classfile(after_invoke_only=True)
        _, sites, calls = binary.classfile_evidence(
            standalone,r450.r449.resource_literal)
        self.assertEqual(calls,2)
        self.assertEqual(sites,[])

    def test_16_invalid_class_signature_refuses(self):
        invalid = invented_classfile(bad_class_signature="Ljava/util/List<Lrs/NoEnd;")
        with self.assertRaises(binary.Refused):
            binary.classfile_evidence(invalid,r450.r449.resource_literal)

    def test_17_incorrect_class_major_refuses(self):
        invalid = self.described[:6] + (61).to_bytes(2,"big")+self.described[8:]
        with self.assertRaisesRegex(binary.Refused,"R450_JAVA11_CLASSFILE_REQUIRED"):
            binary.classfile_evidence(invalid,r450.r449.resource_literal)

    def test_18_truncated_and_extra_classfile_bytes_refuse(self):
        for invalid in (self.described[:11],self.described[:-4],
                        self.described+b"trailing"):
            with self.subTest(n=len(invalid)):
                with self.assertRaises(binary.Refused):
                    binary.classfile_evidence(invalid,r450.r449.resource_literal)

    def test_19_changed_compiled_class_between_observation_and_scan(self):
        observed,_ = r450.r446.observe()
        (self.compiled/"rs/Bridge.class").write_bytes(
            preceding.r448_test_fixture.fake_java11_class(
                "rs/Bridge",("rs/Mutation",)))
        with self.assertRaisesRegex(
                r450.Refused,"R450_COMPILED_INPUT_CHANGED_OR_UNSAFE"):
            r450.observed_metadata(observed)

    def test_20_generic_analysis_excludes_known_Class_and_descriptor_types(self):
        classes = {"rs/A.class":{"rs/Already.class"}}
        descriptors = {"rs/A.class":{"rs/Described.class"}}
        generics = {"rs/A.class":{
            "rs/Already.class","rs/Described.class","rs/New.class"}}
        resources = {"rs/A.class":[("m()V","logo.png")]}
        summary,private = r450.analyze(
            classes,descriptors,generics,resources,1,
            {"rs/New.class"},set(),set(),{"logo.png"})
        self.assertEqual(
            summary["new_generic_targets_absent_from_R449_class_and_descriptors"],1)
        self.assertEqual(summary["new_unresolved_generic_class_targets"],1)
        self.assertEqual(summary["nearby_resource_strings_named_in_original_archive"],1)
        self.assertEqual(private["new_unresolved_generic_type_names"][0]["class_name"],
                         "rs/New.class")

    def test_21_reject_graph_mismatch(self):
        with self.assertRaisesRegex(r450.Refused,"R450_GRAPH_KEYSET_MISMATCH"):
            r450.analyze(
                {"rs/A.class":set()},{"rs/B.class":set()},
                {"rs/A.class":set()},{"rs/A.class":[]},0,
                set(),set(),set(),set())

    def test_22_resource_proximity_budget_enforced(self):
        current,_ = r450.r446.observe()
        with patch.object(r450,"MAX_PROXIMITY_SITES",1):
            with self.assertRaisesRegex(
                    r450.Refused,"R450_RESOURCE_PROXIMITY_BUDGET"):
                r450.observed_metadata(current)

    def test_23_change_before_second_scan_never_writes_report(self):
        base = r450.inspect
        n = [0]
        def changed(*args,**kwargs):
            result=base(*args,**kwargs)
            n[0]+=1
            if n[0]==1:
                (self.compiled/"rs/Bridge.class").write_bytes(
                    preceding.r448_test_fixture.fake_java11_class(
                        "rs/Bridge",("rs/OutOfBand",)))
            return result
        with patch.object(r450,"inspect",side_effect=changed):
            with self.assertRaises(r450.Refused):
                r450.run(self.original_jar,save=True)
        self.assertEqual(self.private_dirs(),[])

    def test_24_private_output_size_guard(self):
        with patch.object(r450,"MAX_PRIVATE_REPORT_BYTES",25):
            with self.assertRaisesRegex(
                    r450.Refused,"R450_PRIVATE_REPORT_TOO_LARGE"):
                r450.run(self.original_jar,save=True)
        self.assertEqual(self.private_dirs(),[])

    def test_25_missing_original_public_cli_no_path_leak(self):
        missing = self.temp/"absent-v309.jar"
        cmd = subprocess.run([
            sys.executable,"-B",str(CLI),
            "--original-v309-jar",str(missing),
        ],capture_output=True,text=True,check=False,timeout=15)
        self.assertEqual(cmd.returncode,2)
        result=json.loads(cmd.stdout)
        self.assertEqual(result["status"],"R450_GENERIC_RESOURCE_AUDIT_REFUSED")
        self.assertNotIn(str(missing),cmd.stdout)
        self.assertFalse(result["release_authorized"])

    def test_26_no_live_runtime_or_automatic_private_output(self):
        text = (ROOT/"tools/r450/audit_generic_resource_proximity.py").read_text(
            encoding="utf-8")
        self.assertNotIn("subprocess.run(",text)
        self.assertNotIn("shutil.rmtree(",text)
        self.assertIn("O_EXCL",text)
        self.assertIn("--save-private-unapproved-worklist",text)
        report=r450.run(self.original_jar)
        for field in ("private_client_executed","production_client_integrated",
                      "compile_authorized","release_authorized",
                      "merge_authorized","historical_R421_custody_approved"):
            self.assertFalse(report[field])


if __name__ == "__main__":
    unittest.main()

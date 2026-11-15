"""R415 strict private audit tests using ONLY fabricated Java/class bytes.

Purpose: exercise SHA-pinned inventory/delta checks without publishing any
recovered Java, compiled private class or player history. The fabricated
source deliberately does NOT satisfy the production semantic validator;
only the inventory tests mock that last stage. The real private source
must separately pass the complete unmocked audit on the owner TEMP copy.
"""
from __future__ import annotations
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "r415_private_gate",ROOT/"tools/r415/audit_private_intent_delta.py")
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def digest(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

class R415PrivateInventoryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r415-fabricated-inventory-")
        self.addCleanup(temp.cleanup)
        d=Path(temp.name)
        self.kit=d/"invented-source.zip"
        self.ref=d/"invented-class.jar"
        self.old_source=d/"old-source"
        self.new_source=d/"new-source"
        self.old_class=d/"old-class"
        self.new_class=d/"new-class"
        self.source_original={}
        self.source_prior={}
        self.source_now={}
        for name in gate.GOLD_SOURCE_DIFF|{gate.PRICE}:
            original=(b"fabricated_original_"+name.encode())
            old=original if name==gate.PRICE else (b"fabricated_prior_"+name.encode())
            new=(b"fabricated_now_"+name.encode()) if name in gate.SOURCE_DIFF else old
            self.source_original[name]=original
            self.source_prior[name]=old
            self.source_now[name]=new
        self.class_gold={name:b"fabricated_gold_"+name.encode()
                         for name in gate.GOLD_CLASS_DIFF}
        self.class_prior={name:b"fabricated_old_"+name.encode()
                          for name in gate.GOLD_CLASS_DIFF}
        self.class_prior.update({
            name:b"fabricated_preexisting_nested_"+name.encode()
            for name in gate.NESTED_PREEXISTING})
        self.class_now=self.class_prior.copy()
        for name in gate.CLASS_DIFF:
            self.class_now[name]=b"fabricated_new_"+name.encode()
        self.sync()

    @staticmethod
    def tree_write(root:Path,data:dict):
        root.mkdir(parents=True,exist_ok=True)
        for file in root.rglob("*"):
            if file.is_file():file.unlink()
        for name,body in data.items():
            f=root/name
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_bytes(body)

    def sync(self):
        with ZipFile(self.kit,"w") as z:
            for n,v in sorted(self.source_original.items()):
                z.writestr("source/"+n,v)
        with ZipFile(self.ref,"w") as z:
            for n,v in sorted(self.class_gold.items()):
                z.writestr(n,v)
        self.tree_write(self.old_source,self.source_prior)
        self.tree_write(self.new_source,self.source_now)
        self.tree_write(self.old_class,self.class_prior)
        self.tree_write(self.new_class,self.class_now)

    def args(self,**changes):
        kwargs={
            "kit":self.kit,"kit_sha":digest(self.kit),
            "reference":self.ref,"reference_sha":digest(self.ref),
            "previous_sources":self.old_source,
            "previous_classes":self.old_class,
            "candidate_sources":self.new_source,
            "candidate_classes":self.new_class,
            "expected_sources":7,"previous_classes_count":12,
            "candidate_classes_count":12,"golden_classes_count":8,
        }
        kwargs.update(changes)
        return kwargs

    def check_scope(self,**changes):
        # Mock ONLY source-level semantic analysis here: these sources
        # are intentionally fake bytes. Exact scope/pin checks remain real.
        with mock.patch.object(gate,"verify_structure",return_value={
            "invented_corpus_only":True}):
            return gate.audit(**self.args(**changes))

    def refused(self,reason=None,**changes):
        if reason:
            with self.assertRaisesRegex(gate.Refused,reason):
                self.check_scope(**changes)
        else:
            with self.assertRaises(gate.Refused):
                self.check_scope(**changes)

    def test_fabricated_scope_accepts_only_two_existing_pairs(self):
        report=self.check_scope()
        self.assertEqual(report["status"],
                         "R415_PRIVATE_NONCLOBBER_INTENT_STATIC_GATE_PASS")
        self.assertEqual(report["source_count"],7)
        self.assertEqual(report["compiled_class_count"],12)
        self.assertEqual(report["changed_existing_source_vs_r414"],2)
        self.assertEqual(report["changed_existing_class_vs_r414"],2)
        self.assertEqual(report["new_nested_class_vs_r414"],0)
        self.assertTrue(report["invented_corpus_only"])
        self.assertFalse(report["private_release_authorized"])
        self.assertFalse(report["merge_approved"])

    def test_scope_report_never_contains_fabricated_bytes(self):
        encoded=json.dumps(self.check_scope())
        self.assertNotIn("fabricated_",encoded)
        self.assertNotIn(str(self.old_source),encoded)

    def test_forged_kit_hash_refused(self):
        self.refused("ARCHIVE_SHA_DRIFT",kit_sha="0"*64)

    def test_forged_original_compiled_archive_hash_refused(self):
        self.refused("ARCHIVE_SHA_DRIFT",reference_sha="0"*64)

    def test_missing_candidate_plugin_source_refused(self):
        self.source_now.pop(gate.PLUGIN);self.sync()
        self.refused("R415_PINNED_SOURCE_CLASS_COUNT_DRIFT")

    def test_extra_candidate_source_refused(self):
        self.source_now["rs/plugins/loottracker/Fake.java"]=b"fabricated"
        self.sync()
        self.refused("R415_PINNED_SOURCE_CLASS_COUNT_DRIFT")

    def test_old_and_new_class_inventory_mismatch_refused(self):
        self.class_now["rs/plugins/loottracker/NewClass.class"]=b"invented"
        self.sync()
        self.refused("R415_PINNED_SOURCE_CLASS_COUNT_DRIFT")

    def test_unrelated_panel_class_mutation_refused(self):
        path=gate.P+"LootTrackerPanel.class"
        self.class_now[path]=b"panel-unrelated-changed"
        self.sync()
        self.refused("R415_EXACT_TWO_EXISTING_SOURCE_CLASS_DIFF_REQUIRED")

    def test_unrelated_price_java_mutation_refused(self):
        self.source_now[gate.PRICE]=b"modified-cache"
        self.sync()
        self.refused("R415_EXACT_TWO_EXISTING_SOURCE_CLASS_DIFF_REQUIRED")

    def test_unrelated_atomic_mover_java_mutation_refused(self):
        self.source_now[gate.MOVE]=b"modified-mover"
        self.sync()
        self.refused("R415_EXACT_TWO_EXISTING_SOURCE_CLASS_DIFF_REQUIRED")

    def test_store_source_not_modified_refused(self):
        self.source_now[gate.STORE]=self.source_prior[gate.STORE]
        self.sync()
        self.refused("R415_EXACT_TWO_EXISTING_SOURCE_CLASS_DIFF_REQUIRED")

    def test_plugin_source_not_modified_refused(self):
        self.source_now[gate.PLUGIN]=self.source_prior[gate.PLUGIN]
        self.sync()
        self.refused("R415_EXACT_TWO_EXISTING_SOURCE_CLASS_DIFF_REQUIRED")

    def test_store_class_not_modified_refused(self):
        k=gate.P+"LootHistoryStore.class"
        self.class_now[k]=self.class_prior[k]
        self.sync()
        self.refused("R415_EXACT_TWO_EXISTING_SOURCE_CLASS_DIFF_REQUIRED")

    def test_plugin_class_not_modified_refused(self):
        k=gate.P+"LootTrackerPlugin.class"
        self.class_now[k]=self.class_prior[k]
        self.sync()
        self.refused("R415_EXACT_TWO_EXISTING_SOURCE_CLASS_DIFF_REQUIRED")

    def test_new_nested_class_refused(self):
        name=gate.P+"Extra.class"
        self.class_now[name]=b"new"
        self.sync()
        self.refused("R415_PINNED_SOURCE_CLASS_COUNT_DRIFT")

    def test_dropped_preexisting_nested_class_refused(self):
        self.class_now.pop(next(iter(gate.NESTED_PREEXISTING)))
        self.sync()
        self.refused("R415_PINNED_SOURCE_CLASS_COUNT_DRIFT")

    def test_original_source_diff_scope_refused(self):
        self.source_original[gate.PRICE]=b"different-original-price"
        self.sync()
        self.refused("R415_GOLDEN_SOURCE_CLASS_DELTA_MISMATCH")

    def test_missing_golden_compiled_class_refused(self):
        self.class_gold.pop(next(iter(gate.GOLD_CLASS_DIFF)))
        self.sync()
        self.refused("R415_PINNED_SOURCE_CLASS_COUNT_DRIFT")

    def test_semantic_gate_must_reject_invalid_java_source(self):
        # This specifically is NOT an original game source.
        with self.assertRaises(gate.Refused):
            gate.verify_structure(b"class Invented {}",
                b"class Invented {}",
                b"class InventedPlugin {}",
                b"class InventedPlugin {}",
                b"fake atomic helper",b"fake atomic helper",
                b"fake price",b"fake price")

    def test_semantic_gate_rejects_changed_atomic_mover(self):
        with self.assertRaisesRegex(gate.Refused,"R415_ATOMIC_MOVER_OR_PRICING_CHANGED"):
            gate.verify_structure(b"old",b"new",
                b"old plugin",b"new plugin",
                b"mover v1",b"mover v2",
                b"price v1",b"price v1")

    def test_semantic_gate_rejects_changed_price_cache(self):
        with self.assertRaisesRegex(gate.Refused,"R415_ATOMIC_MOVER_OR_PRICING_CHANGED"):
            gate.verify_structure(b"old",b"new",
                b"old plugin",b"new plugin",
                b"mover",b"mover",b"cache v1",b"cache v2")

    def test_token_order_refuses_missing_or_reversed(self):
        gate.ordered("first middle last","first","middle","last")
        with self.assertRaises(gate.Refused):
            gate.ordered("last first middle","first","middle","last")

    def test_utf8_decode_rejects_non_utf8_java(self):
        with self.assertRaisesRegex(gate.Refused,"R415_NON_UTF8_SOURCE"):
            gate.code(b"\xff\xfe")

    def test_existing_receipt_not_overwritten(self):
        output=Path(self.kit.parent)/"existing-report.json"
        output.write_text("KEEP",encoding="utf8")
        argv=["--kit",str(self.kit),"--kit-sha256",digest(self.kit),
            "--reference",str(self.ref),"--reference-sha256",digest(self.ref),
            "--previous-sources",str(self.old_source),
            "--previous-classes",str(self.old_class),
            "--candidate-sources",str(self.new_source),
            "--candidate-classes",str(self.new_class),
            "--out",str(output)]
        with redirect_stdout(io.StringIO()):
            code=gate.main(argv)
        self.assertEqual(code,2)
        self.assertEqual(output.read_text(encoding="utf8"),"KEEP")

    def test_private_corpus_defaults_remain_pinned(self):
        source=Path(gate.__file__).read_text(encoding="utf8")
        for invariant in ("expected_sources:int=1277",
                          "previous_classes_count:int=1392",
                          "candidate_classes_count:int=1392",
                          "golden_classes_count:int=1388",
                          "verified_actual_client_restart_or_handoff",
                          "private_release_authorized"):
            self.assertIn(invariant,source)

if __name__=="__main__":
    unittest.main()

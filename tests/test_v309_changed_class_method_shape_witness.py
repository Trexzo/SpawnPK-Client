from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from spk_recovery.descriptor_class_dependencies import build_descriptor_class_dependency_report
from spk_recovery.v309_changed_class_method_shape_witness import (
    V309MethodShapeWitnessError,
    build_v309_changed_class_method_shape_witness,
)


ROOT = Path(__file__).resolve().parents[1] / "research" / "v309-field-recovery"
FOCUS = "CLIENT_CLASS_000486"


def _method(length: int) -> dict:
    return {
        "name": "m" + str(length),
        "access": 1,
        "descriptor": "()I",
        "code_length": length,
    }


def _class(path: str, fields: list, methods: list, structural: str) -> dict:
    return {
        "internal_name": path[:-6],
        "fields": fields,
        "methods": methods,
        "field_count": len(fields),
        "method_count": len(methods),
        "structural_sha256": structural,
    }


class V309MethodShapeWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT / "global-field-usage.json").read_text(encoding="utf-8"))
        cls.lineage = json.loads((ROOT / "class-lineage.json").read_text(encoding="utf-8"))
        deps = build_descriptor_class_dependency_report(cls.report)["class_dependencies"]
        old_classes, new_classes, old_entries, new_entries = {}, {}, {}, {}
        cls.old_paths, cls.new_paths = {}, {}
        cls.focus_fields = [
            {"access": 1, "name": "fieldA", "descriptor": "I"},
            {"access": 1, "name": "fieldB", "descriptor": "Ljava/lang/Object;"},
        ]
        cls.focus_old_methods = [_method(70), _method(71), _method(72)]
        cls.focus_new_methods = [_method(70), _method(71), _method(72), _method(99)]
        for group in deps:
            cid = group["old_canonical_class_id"]
            owner = next(c for c in cls.lineage["classes"] if c["logical_id"] == cid)
            old = next(l for l in owner["lineage"] if l["build_id"] == "v308")
            op = old["entry_path"]
            np = group["new_raw_descriptors"][0][1:-1] + ".class"
            cls.old_paths[cid], cls.new_paths[cid] = op, np
            fields = cls.focus_fields if cid == FOCUS else []
            om = cls.focus_old_methods if cid == FOCUS else []
            nm = cls.focus_new_methods if cid == FOCUS else []
            old_classes[op] = _class(op, fields, om, old["structural_sha256"])
            new_classes[np] = _class(np, fields, nm, "d" * 64)
            old_entries[op] = {"sha256": old["entry_sha256"]}
            new_entries[np] = {
                "sha256": hashlib.sha256(("synthetic-v309-" + cid).encode()).hexdigest()
            }
        for version, classes, entries, count in (
            ("v308", old_classes, old_entries, 10472),
            ("v309", new_classes, new_entries, 10502),
        ):
            for i in range(count - len(classes)):
                path = f"synthetic-{version}/placeholder-{i:05}.class"
                classes[path] = _class(path, [], [], "a" * 64)
                entries[path] = {"sha256": "b" * 64}
        cls.old_index = {
            "sha256": cls.report["old_sha256"], "classes": old_classes,
            "entries": old_entries,
            "summary": {"class_count": 10472, "class_parse_error_count": 0},
        }
        cls.new_index = {
            "sha256": cls.report["new_sha256"], "classes": new_classes,
            "entries": new_entries,
            "summary": {"class_count": 10502, "class_parse_error_count": 0},
        }

    def run_witness(self, old=None, new=None):
        return build_v309_changed_class_method_shape_witness(
            self.report, self.lineage,
            self.old_index if old is None else old,
            self.new_index if new is None else new,
        )

    def test_focused_bidirectional_witness_is_research_not_acceptance(self):
        result = self.run_witness()
        self.assertEqual(result, self.run_witness())
        self.assertFalse(result["canonical"])
        self.assertEqual(result["summary"]["accepted_unresolved_fields"], 143)
        self.assertEqual(result["summary"]["canonical_identities_accepted"], 0)
        self.assertEqual(result["summary"]["candidate_classes"], 1)
        self.assertEqual(result["summary"]["rejected_classes"], 7)
        item = result["candidates"][0]
        self.assertEqual(item["old_canonical_class_id"], FOCUS)
        self.assertEqual(item["matched_code_method_shapes"], 3)
        self.assertEqual(item["union_code_method_shapes"], 4)
        self.assertEqual(item["jaccard"], 0.75)
        self.assertEqual(item["field_shape_count"], 2)
        self.assertEqual(item["eligible_new_class_count"], 1)
        self.assertEqual(item["eligible_old_class_count"], 1)
        self.assertEqual(item["classification"], "RESEARCH_CANDIDATE_NOT_ACCEPTED")
        self.assertNotIn("accepted_class_identities", result)

    def test_competing_new_class_fails_mutual_uniqueness(self):
        index = copy.deepcopy(self.new_index)
        rival = "synthetic-v309/placeholder-00000.class"
        index["classes"][rival] = _class(
            rival, self.focus_fields, self.focus_new_methods, "e" * 64,
        )
        result = self.run_witness(new=index)
        row = next(x for x in result["rejected"] if x["old_canonical_class_id"] == FOCUS)
        self.assertEqual(row["reason"], "bidirectional_whole_archive_uniqueness_failed")
        self.assertEqual(row["eligible_new_class_count"], 2)

    def test_competing_old_class_fails_mutual_uniqueness(self):
        index = copy.deepcopy(self.old_index)
        rival = "synthetic-v308/placeholder-00000.class"
        index["classes"][rival] = _class(
            rival, self.focus_fields, self.focus_old_methods, "e" * 64,
        )
        result = self.run_witness(old=index)
        row = next(x for x in result["rejected"] if x["old_canonical_class_id"] == FOCUS)
        self.assertEqual(row["reason"], "bidirectional_whole_archive_uniqueness_failed")
        self.assertEqual(row["eligible_old_class_count"], 2)

    def test_weak_method_overlap_fails_closed(self):
        index = copy.deepcopy(self.new_index)
        item = index["classes"][self.new_paths[FOCUS]]
        item["methods"] = [_method(70), _method(71), _method(999), _method(1000)]
        item["method_count"] = 4
        result = self.run_witness(new=index)
        row = next(x for x in result["rejected"] if x["old_canonical_class_id"] == FOCUS)
        self.assertEqual(row["reason"], "insufficient_exact_field_and_method_shape_overlap")

    def test_missing_class_index_entry_fails_before_matching(self):
        index = copy.deepcopy(self.new_index)
        index["entries"].pop(self.new_paths[FOCUS])
        with self.assertRaisesRegex(V309MethodShapeWitnessError, "invalid class path"):
            self.run_witness(new=index)

    def test_wrong_exact_build_hash_refused(self):
        index = dict(self.new_index)
        index["sha256"] = "0" * 64
        with self.assertRaisesRegex(V309MethodShapeWitnessError, "SHA/lineage"):
            self.run_witness(new=index)

    def test_unparsed_class_refused(self):
        index = dict(self.old_index)
        index["summary"] = dict(index["summary"], class_parse_error_count=1)
        with self.assertRaisesRegex(V309MethodShapeWitnessError, "incomplete or unparsed"):
            self.run_witness(old=index)

    def test_no_private_bytecode_material_in_report(self):
        result = self.run_witness()
        as_json = json.dumps(result)
        self.assertNotIn("fieldA", as_json)
        self.assertNotIn("fieldB", as_json)
        self.assertNotIn("raw_bytecode", as_json)
        self.assertEqual(len(result["candidates"]) + len(result["rejected"]), 8)


if __name__ == "__main__":
    unittest.main()

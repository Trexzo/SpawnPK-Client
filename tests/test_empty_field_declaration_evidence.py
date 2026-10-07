from __future__ import annotations

from collections import Counter
import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from spk_recovery.empty_field_declaration_evidence import (
    EmptyFieldDeclarationEvidenceError,
    _jar_field_table,
    _stable_digest,
    build_empty_field_declaration_evidence,
)


@unittest.skipUnless(shutil.which("javac"), "Java compiler required")
class ExactJarFieldTableTests(unittest.TestCase):
    def test_exact_jar_reader_preserves_jvm_field_table_order(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src" / "rs"
            classes = root / "classes"
            src.mkdir(parents=True)
            classes.mkdir()

            java = src / "A.java"
            java.write_text(
                "package rs; public class A { "
                "public int z; "
                "private String x; "
                "protected long a; "
                "}",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                [
                    "javac",
                    "-g:none",
                    "-d",
                    str(classes),
                    str(java),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                compiled.returncode,
                0,
                compiled.stdout + compiled.stderr,
            )

            jar = root / "client.jar"
            with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as archive:
                archive.write(
                    classes / "rs" / "A.class",
                    "rs/A.class",
                )

            fields = _jar_field_table(jar, owner="rs/A")
            self.assertEqual(
                [row["name"] for row in fields],
                ["z", "x", "a"],
            )


class EmptyFieldDeclarationEvidenceTests(unittest.TestCase):
    def _classes(self):
        return {
            "builds": [
                {"build_id": "v308", "sha256": "1" * 64},
                {"build_id": "v309", "sha256": "2" * 64},
            ],
            "classes": [
                {
                    "logical_id": "CLIENT_CLASS_A",
                    "lineage": [
                        {"build_id": "v308", "internal_name": "rs/A"},
                        {"build_id": "v309", "internal_name": "rs/B"},
                    ],
                }
            ],
        }

    def _members(self):
        return {
            "members": [
                {
                    "member_id": "CLIENT_FIELD_LEFT",
                    "owner_logical_id": "CLIENT_CLASS_A",
                    "kind": "field",
                    "lineage": [
                        {
                            "build_id": "v308",
                            "owner_internal_name": "rs/A",
                            "name": "z",
                            "descriptor": "I",
                            "access": 1,
                        },
                        {
                            "build_id": "v309",
                            "owner_internal_name": "rs/B",
                            "name": "q",
                            "descriptor": "I",
                            "access": 1,
                        },
                    ],
                },
                {
                    "member_id": "CLIENT_FIELD_RIGHT",
                    "owner_logical_id": "CLIENT_CLASS_A",
                    "kind": "field",
                    "lineage": [
                        {
                            "build_id": "v308",
                            "owner_internal_name": "rs/A",
                            "name": "a",
                            "descriptor": "J",
                            "access": 1,
                        },
                        {
                            "build_id": "v309",
                            "owner_internal_name": "rs/B",
                            "name": "r",
                            "descriptor": "J",
                            "access": 1,
                        },
                    ],
                },
            ],
            "unresolved": [
                {
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "source": "member_identity_candidates",
                    "old_build_id": "v308",
                    "new_build_id": "v309",
                    "candidate": {
                        "relationship_id": "MEMREL_EMPTY_1",
                        "strategy": "stable_symbol",
                        "old_owner": "rs/A.class",
                        "new_owner": "rs/B.class",
                        "old": {
                            "name": "x",
                            "descriptor": "Ljava/lang/String;",
                            "access": 2,
                        },
                        "new": {
                            "name": "x",
                            "descriptor": "Ljava/lang/String;",
                            "access": 2,
                        },
                    },
                }
            ],
        }

    def _old_index(self):
        return {
            "sha256": "1" * 64,
            "classes": {
                "rs/A.class": {
                    "fields": [
                        {
                            "name": "z",
                            "descriptor": "I",
                            "access": 1,
                            "attributes": [],
                        },
                        {
                            "name": "x",
                            "descriptor": "Ljava/lang/String;",
                            "access": 2,
                            "attributes": ["Synthetic"],
                        },
                        {
                            "name": "a",
                            "descriptor": "J",
                            "access": 1,
                            "attributes": [],
                        },
                    ]
                }
            },
        }

    def _new_index(self):
        return {
            "sha256": "2" * 64,
            "classes": {
                "rs/B.class": {
                    "fields": [
                        {
                            "name": "q",
                            "descriptor": "I",
                            "access": 1,
                            "attributes": [],
                        },
                        {
                            "name": "x",
                            "descriptor": "Ljava/lang/String;",
                            "access": 2,
                            "attributes": ["Synthetic"],
                        },
                        {
                            "name": "r",
                            "descriptor": "J",
                            "access": 1,
                            "attributes": [],
                        },
                    ]
                }
            },
        }

    def _report(self, members):
        outcomes = [
            {
                "relationship_id": "MEMREL_EMPTY_1",
                "logical_class_id": "CLIENT_CLASS_A",
                "old_owner": "rs/A",
                "new_owner": "rs/B",
                "old": {
                    "name": "x",
                    "descriptor": "Ljava/lang/String;",
                    "access": 2,
                },
                "new": {
                    "name": "x",
                    "descriptor": "Ljava/lang/String;",
                    "access": 2,
                },
                "outcome": "empty_both",
                "canonical_method_topology": [],
                "global_source_class_topology": [],
            }
        ]
        member_digest = _stable_digest(members)
        material = {
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": member_digest,
            "candidates": [],
            "review_outcomes": outcomes,
        }
        return {
            "schema_version": 1,
            "kind": "global_field_usage_identity_candidates",
            "canonical": False,
            "report_id": (
                "GLOBALFIELDUSE_"
                + _stable_digest(material)[:20].upper()
            ),
            "old_build_id": "v308",
            "new_build_id": "v309",
            "old_sha256": "1" * 64,
            "new_sha256": "2" * 64,
            "member_lineage_digest": member_digest,
            "summary": {
                "input_stable_symbol_reviews": 1,
                "review_outcomes": 1,
                "empty_both": 1,
            },
            "candidates": [],
            "review_outcomes": outcomes,
            "descriptor_identity_rejections": [],
        }

    def _refresh_report_id(self, report):
        material = {
            "old_build_id": report["old_build_id"],
            "new_build_id": report["new_build_id"],
            "old_sha256": report["old_sha256"],
            "new_sha256": report["new_sha256"],
            "member_lineage_digest": report["member_lineage_digest"],
            "candidates": report["candidates"],
            "review_outcomes": report["review_outcomes"],
        }
        report["report_id"] = (
            "GLOBALFIELDUSE_"
            + _stable_digest(material)[:20].upper()
        )
        return report

    def _build(
        self,
        *,
        members=None,
        old_index=None,
        new_index=None,
        report=None,
        old_method_usage=None,
        new_method_usage=None,
        old_global_usage=None,
        new_global_usage=None,
    ):
        members = members or self._members()
        old_index = old_index or self._old_index()
        new_index = new_index or self._new_index()
        report = report or self._report(members)
        def jar_fields(_jar_path, *, owner):
            source = old_index if owner == "rs/A" else new_index
            return copy.deepcopy(
                source["classes"][owner + ".class"]["fields"]
            )

        with (
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "validate_lineage"
            ),
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "validate_member_lineage"
            ),
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "sha256_file",
                side_effect=["1" * 64, "2" * 64],
            ),
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "_jar_field_table",
                side_effect=jar_fields,
            ),
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "_paired_method_maps",
                return_value=({}, {}, 0),
            ),
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "_scan_usage",
                side_effect=[
                    (old_method_usage or {}, {}),
                    (new_method_usage or {}, {}),
                ],
            ),
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "_scan_source_class_usage",
                side_effect=[
                    (old_global_usage or {}, {}),
                    (new_global_usage or {}, {}),
                ],
            ),
        ):
            return build_empty_field_declaration_evidence(
                self._classes(),
                members,
                old_index,
                new_index,
                Path("old.jar"),
                Path("new.jar"),
                report,
            )

    def test_exact_two_sided_anchor_interval_emits_candidate(self):
        report = self._build()
        self.assertFalse(report["canonical"])
        self.assertEqual(
            report["summary"]["input_empty_both_reviews"],
            1,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 1)
        self.assertEqual(
            report["summary"]["remaining_without_declaration_proof"],
            0,
        )
        candidate = report["candidates"][0]
        self.assertEqual(
            candidate["strategy"],
            "canonical_anchor_declaration_interval_exact",
        )
        self.assertEqual(
            candidate["left_anchor_member_id"],
            "CLIENT_FIELD_LEFT",
        )
        self.assertEqual(
            candidate["right_anchor_member_id"],
            "CLIENT_FIELD_RIGHT",
        )
        self.assertEqual(candidate["interval_length"], 1)
        self.assertEqual(candidate["interval_offset"], 0)
        self.assertEqual(candidate["global_observations"], 0)

    def test_changed_whole_jar_topology_vetoes_declaration(self):
        old_global = {
            ("rs/A", "x", "Ljava/lang/String;"): Counter(
                {("CLIENT_CLASS_C", "getfield"): 1}
            )
        }
        new_global = {
            ("rs/B", "x", "Ljava/lang/String;"): Counter(
                {("CLIENT_CLASS_C", "getfield"): 2}
            )
        }
        report = self._build(
            old_global_usage=old_global,
            new_global_usage=new_global,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["global_class_topology_guard_rejected"],
            1,
        )
        self.assertEqual(
            report["rejected"][0]["reason"],
            "global_class_topology_guard_rejected",
        )

    def test_raw_whole_jar_source_vetoes_declaration(self):
        topology = Counter({("RAW:rs/unmapped", "getfield"): 1})
        report = self._build(
            old_global_usage={
                ("rs/A", "x", "Ljava/lang/String;"): topology
            },
            new_global_usage={
                ("rs/B", "x", "Ljava/lang/String;"): topology
            },
        )
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["raw_source_guard_rejected"],
            1,
        )
        self.assertEqual(
            report["rejected"][0]["reason"],
            "raw_source_guard_rejected",
        )

    def test_empty_both_is_rechecked_from_exact_jar_usage(self):
        old_method = {
            ("rs/A", "x", "Ljava/lang/String;"): Counter(
                {("CLIENT_METHOD_1", "getfield"): 1}
            )
        }
        with self.assertRaisesRegex(
            EmptyFieldDeclarationEvidenceError,
            "empty_both classification disagrees",
        ):
            self._build(old_method_usage=old_method)

    def test_anchor_identity_mismatch_is_rejected(self):
        new_index = self._new_index()
        new_index["classes"]["rs/B.class"]["fields"] = [
            {
                "name": "r",
                "descriptor": "J",
                "access": 1,
                "attributes": [],
            },
            {
                "name": "x",
                "descriptor": "Ljava/lang/String;",
                "access": 2,
                "attributes": ["Synthetic"],
            },
            {
                "name": "q",
                "descriptor": "I",
                "access": 1,
                "attributes": [],
            },
        ]
        report = self._build(new_index=new_index)
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["canonical_anchor_identity_mismatch"],
            1,
        )
        self.assertEqual(
            report["rejected"][0]["reason"],
            "canonical_anchor_identity_mismatch",
        )

    def test_missing_two_sided_anchor_is_rejected(self):
        members = self._members()
        members["members"] = [
            row
            for row in members["members"]
            if row["member_id"] == "CLIENT_FIELD_LEFT"
        ]
        report_doc = self._report(members)
        report = self._build(
            members=members,
            report=report_doc,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["missing_two_sided_canonical_anchor"],
            1,
        )

    def test_interval_shape_mismatch_is_rejected(self):
        old_index = self._old_index()
        new_index = self._new_index()
        old_index["classes"]["rs/A.class"]["fields"].insert(
            2,
            {
                "name": "u",
                "descriptor": "I",
                "access": 4,
                "attributes": [],
            },
        )
        new_index["classes"]["rs/B.class"]["fields"].insert(
            2,
            {
                "name": "u",
                "descriptor": "J",
                "access": 4,
                "attributes": [],
            },
        )
        report = self._build(
            old_index=old_index,
            new_index=new_index,
        )
        self.assertEqual(report["summary"]["candidate_fields"], 0)
        self.assertEqual(
            report["summary"]["declaration_interval_shape_mismatch"],
            1,
        )

    def test_exact_jar_sha_drift_is_refused(self):
        members = self._members()
        report = self._report(members)
        with (
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "validate_lineage"
            ),
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "validate_member_lineage"
            ),
            patch(
                "spk_recovery.empty_field_declaration_evidence."
                "sha256_file",
                side_effect=["9" * 64, "2" * 64],
            ),
        ):
            with self.assertRaisesRegex(
                EmptyFieldDeclarationEvidenceError,
                "old JAR SHA does not match exact old index",
            ):
                build_empty_field_declaration_evidence(
                    self._classes(),
                    members,
                    self._old_index(),
                    self._new_index(),
                    Path("old.jar"),
                    Path("new.jar"),
                    report,
                )

    def test_member_lineage_digest_drift_is_refused(self):
        members = self._members()
        report = self._report(members)
        report["member_lineage_digest"] = "9" * 64
        with self.assertRaisesRegex(
            EmptyFieldDeclarationEvidenceError,
            "member lineage digest",
        ):
            self._build(
                members=members,
                report=report,
            )

    def test_only_empty_both_outcomes_are_considered(self):
        members = self._members()
        second = copy.deepcopy(members["unresolved"][0])
        second["candidate"]["relationship_id"] = "MEMREL_VETO_2"
        second["candidate"]["old"]["name"] = "v"
        second["candidate"]["new"]["name"] = "v"
        members["unresolved"].append(second)

        old_index = self._old_index()
        new_index = self._new_index()
        old_index["classes"]["rs/A.class"]["fields"].insert(
            2,
            {
                "name": "v",
                "descriptor": "I",
                "access": 8,
                "attributes": [],
            },
        )
        new_index["classes"]["rs/B.class"]["fields"].insert(
            2,
            {
                "name": "v",
                "descriptor": "I",
                "access": 8,
                "attributes": [],
            },
        )

        report_doc = self._report(members)
        report_doc["summary"].update(
            {
                "input_stable_symbol_reviews": 2,
                "review_outcomes": 2,
                "empty_both": 1,
            }
        )
        report_doc["review_outcomes"].append(
            {
                "relationship_id": "MEMREL_VETO_2",
                "logical_class_id": "CLIENT_CLASS_A",
                "old_owner": "rs/A",
                "new_owner": "rs/B",
                "old": {
                    "name": "v",
                    "descriptor": "I",
                    "access": 8,
                },
                "new": {
                    "name": "v",
                    "descriptor": "I",
                    "access": 8,
                },
                "outcome": "global_class_topology_guard_rejected",
            }
        )

        self._refresh_report_id(report_doc)
        report = self._build(
            members=members,
            old_index=old_index,
            new_index=new_index,
            report=report_doc,
        )
        self.assertEqual(
            report["summary"]["input_empty_both_reviews"],
            1,
        )
        self.assertEqual(
            {row["relationship_id"] for row in report["candidates"]},
            {"MEMREL_EMPTY_1"},
        )

    def test_tampered_outcome_ledger_report_id_is_refused(self):
        members = self._members()
        report = self._report(members)
        report["review_outcomes"][0]["relationship_id"] = "MEMREL_TAMPERED"
        with self.assertRaisesRegex(
            EmptyFieldDeclarationEvidenceError,
            "report_id digest",
        ):
            self._build(
                members=members,
                report=report,
            )

    def test_outcome_ledger_must_cover_exact_unresolved_frontier(self):
        members = self._members()
        report = self._report(members)
        report["review_outcomes"][0]["relationship_id"] = "MEMREL_OTHER"
        self._refresh_report_id(report)
        with self.assertRaisesRegex(
            EmptyFieldDeclarationEvidenceError,
            "exact unresolved stable-symbol frontier",
        ):
            self._build(
                members=members,
                report=report,
            )


if __name__ == "__main__":
    unittest.main()

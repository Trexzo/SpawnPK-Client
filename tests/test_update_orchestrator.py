from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.indexer import index_jar
from spk_recovery.lineage import seed_lineage
from spk_recovery.member_lineage import seed_member_lineage
from spk_recovery.update_orchestrator import migrate_update


@unittest.skipUnless(shutil.which("javac"), "javac required")
class UpdateOrchestratorTests(unittest.TestCase):
    def _fixture(self, root: Path):
        src = root / "src" / "rs"
        src.mkdir(parents=True)
        (src / "A.java").write_text(
            "package rs; public class A { "
            "public int x = 1; "
            "public void a() { x++; } "
            "}",
            encoding="utf-8",
        )

        classes = root / "classes"
        classes.mkdir()
        subprocess.run(
            ["javac", "-d", str(classes), str(src / "A.java")],
            check=True,
        )
        class_bytes = (classes / "rs" / "A.class").read_bytes()

        old_jar = root / "old.jar"
        new_jar = root / "new.jar"
        for path, marker in ((old_jar, b"old"), (new_jar, b"new")):
            with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
                z.writestr("rs/A.class", class_bytes)
                z.writestr("build.txt", marker)

        old_index = index_jar(old_jar)
        new_index = index_jar(new_jar)
        self.assertNotEqual(old_index["sha256"], new_index["sha256"])
        self.assertEqual(
            old_index["entries"]["rs/A.class"]["sha256"],
            new_index["entries"]["rs/A.class"]["sha256"],
        )

        class_lineage = seed_lineage(
            old_index,
            build_id="v308",
            build_number=308,
            authority="EXACT_CURRENT_CLIENT",
        )
        member_lineage = seed_member_lineage(
            class_lineage,
            old_index,
            build_id="v308",
        )

        old_cls = old_index["classes"]["rs/A.class"]
        new_cls = new_index["classes"]["rs/A.class"]

        field_old = old_cls["fields"][0]
        field_new = new_cls["fields"][0]
        method_old = next(
            m for m in old_cls["methods"]
            if m["name"] not in {"<init>", "<clinit>"}
        )
        method_new = next(
            m for m in new_cls["methods"]
            if m["name"] not in {"<init>", "<clinit>"}
        )

        candidates = {
            "schema_version": 1,
            "kind": "member_identity_candidates",
            "canonical": False,
            "old_sha256": old_index["sha256"],
            "new_sha256": new_index["sha256"],
            "summary": {},
            "classes": [
                {
                    "old_owner": "rs/A.class",
                    "new_owner": "rs/A.class",
                    "class_strategy": "exact_sha256",
                    "class_score": 1.0,
                    "fields": {
                        "relationships": [
                            {
                                "relationship_id": "MEMREL_FIELD",
                                "kind": "field",
                                "old_owner": "rs/A.class",
                                "new_owner": "rs/A.class",
                                "old": {
                                    "name": field_old["name"],
                                    "descriptor": field_old["descriptor"],
                                    "access": field_old["access"],
                                },
                                "new": {
                                    "name": field_new["name"],
                                    "descriptor": field_new["descriptor"],
                                    "access": field_new["access"],
                                },
                                "strategy": "stable_symbol",
                                "score": 0.999,
                                "confidence": "CROSS_BUILD",
                                "evidence": {},
                            }
                        ],
                        "unmatched_old": [],
                        "unmatched_new": [],
                    },
                    "methods": {
                        "relationships": [
                            {
                                "relationship_id": "MEMREL_METHOD",
                                "kind": "method",
                                "old_owner": "rs/A.class",
                                "new_owner": "rs/A.class",
                                "old": {
                                    "name": method_old["name"],
                                    "descriptor": method_old["descriptor"],
                                    "access": method_old["access"],
                                    "code_length": method_old["code_length"],
                                },
                                "new": {
                                    "name": method_new["name"],
                                    "descriptor": method_new["descriptor"],
                                    "access": method_new["access"],
                                    "code_length": method_new["code_length"],
                                },
                                "strategy": "stable_symbol",
                                "score": 0.999,
                                "confidence": "CROSS_BUILD",
                                "evidence": {},
                            }
                        ],
                        "unmatched_old": [],
                        "unmatched_new": [],
                    },
                }
            ],
            "skipped_classes": [],
        }
        return (
            old_index,
            new_jar,
            class_lineage,
            member_lineage,
            candidates,
        )

    def test_trivial_update_reaches_authority_in_one_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                old_index,
                new_jar,
                class_lineage,
                member_lineage,
                candidates,
            ) = self._fixture(root)

            result = migrate_update(
                old_index,
                new_jar,
                class_lineage,
                member_lineage,
                old_build_id="v308",
                new_build_id="v309",
                new_build_number=309,
                out_dir=root / "workspace",
                member_candidates=candidates,
            )

            self.assertTrue(result["ready_for_authority"])
            self.assertEqual(result["focused_analysis_items"], 0)
            self.assertEqual(
                result["class_transfer_summary"]["trusted_applied"],
                1,
            )
            self.assertEqual(
                result["member_transfer_summary"][
                    "applied_member_relationships"
                ],
                2,
            )

            self.assertEqual(
                result["class_delta_summary"]["byte_identical"],
                1,
            )
            self.assertEqual(
                result["member_delta_summary"][
                    "member_shape_unchanged"
                ],
                2,
            )
            delta_report = Path(
                result["paths"]["delta_report"]
            ).read_text(encoding="utf-8")
            self.assertIn('"kind": "update_delta_report"', delta_report)

    def test_missing_member_intelligence_blocks_without_guessing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                old_index,
                new_jar,
                class_lineage,
                member_lineage,
                _,
            ) = self._fixture(root)

            result = migrate_update(
                old_index,
                new_jar,
                class_lineage,
                member_lineage,
                old_build_id="v308",
                new_build_id="v309",
                new_build_number=309,
                out_dir=root / "workspace",
            )

            self.assertFalse(result["ready_for_authority"])
            self.assertGreater(result["focused_analysis_items"], 0)
            queue = Path(
                result["paths"]["focused_analysis_queue"]
            ).read_text(encoding="utf-8")
            self.assertIn(
                "member_identity_candidates_required",
                queue,
            )

    def test_workspace_id_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (
                old_index,
                new_jar,
                class_lineage,
                member_lineage,
                candidates,
            ) = self._fixture(root)

            a = migrate_update(
                old_index,
                new_jar,
                class_lineage,
                member_lineage,
                old_build_id="v308",
                new_build_id="v309",
                new_build_number=309,
                out_dir=root / "a",
                member_candidates=candidates,
            )
            b = migrate_update(
                old_index,
                new_jar,
                class_lineage,
                member_lineage,
                old_build_id="v308",
                new_build_id="v309",
                new_build_number=309,
                out_dir=root / "b",
                member_candidates=candidates,
            )
            self.assertEqual(a["workspace_id"], b["workspace_id"])


if __name__ == "__main__":
    unittest.main()

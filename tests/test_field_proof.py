from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.field_proof import (
    FieldProofError,
    prove_and_apply_fields,
)
from spk_recovery.indexer import index_jar


@unittest.skipUnless(
    shutil.which("javac"),
    "Java compiler required",
)
class FieldProofTests(unittest.TestCase):
    def _jar(
        self,
        root: Path,
        *,
        class_name: str,
        source: str,
        jar_name: str,
    ) -> Path:
        src = root / (jar_name + "-src") / "rs"
        src.mkdir(parents=True)
        java = src / f"{class_name}.java"
        java.write_text(source, encoding="utf-8")

        classes = root / (jar_name + "-classes")
        classes.mkdir()
        subprocess.run(
            ["javac", "-g:none", "-d", str(classes), str(java)],
            check=True,
        )

        jar = root / jar_name
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            for path in sorted(classes.rglob("*.class")):
                z.write(path, path.relative_to(classes).as_posix())
        return jar

    def _fixture(self, root: Path):
        old_jar = self._jar(
            root,
            class_name="a",
            jar_name="old.jar",
            source=(
                "package rs; public class a { "
                "int bG; int bH; int bI; int bZ; "
                "int m(){ return bG + bG; } "
                "int n(){ return bH + bH; } "
                "int p(){ return bI + bI; } "
                "int q(){ return bZ; } "
                "}"
            ),
        )
        new_jar = self._jar(
            root,
            class_name="b",
            jar_name="new.jar",
            source=(
                "package rs; public class b { "
                "int bI; int bJ; int bK; int bL; "
                "int m(){ return bI + bI; } "
                "int n(){ return bJ + bJ; } "
                "int p(){ return bK + bK; } "
                "int q(){ return bL; } "
                "}"
            ),
        )
        old_index = index_jar(old_jar)
        new_index = index_jar(new_jar)

        old_cls = old_index["classes"]["rs/a.class"]
        new_cls = new_index["classes"]["rs/b.class"]
        class_lineage = {
            "schema_version": 1,
            "namespace": "spawnpk-client",
            "id_format": "CLIENT_CLASS_%06d",
            "baseline_build_id": "v1",
            "builds": [
                {
                    "build_id": "v1",
                    "build_number": 1,
                    "sha256": old_index["sha256"],
                    "source_name": "old.jar",
                    "authority": "EXACT_HISTORICAL_CLIENT",
                },
                {
                    "build_id": "v2",
                    "build_number": 2,
                    "sha256": new_index["sha256"],
                    "source_name": "new.jar",
                    "authority": "CROSS_BUILD",
                },
            ],
            "classes": [
                {
                    "logical_id": "CLIENT_CLASS_000001",
                    "semantic_name": None,
                    "semantic_status": "UNKNOWN",
                    "semantic_confidence": 0.0,
                    "lineage": [
                        {
                            "build_id": "v1",
                            "internal_name": "rs/a",
                            "entry_path": "rs/a.class",
                            "entry_sha256": old_index["entries"]["rs/a.class"]["sha256"],
                            "structural_sha256": old_cls["structural_sha256"],
                            "relation": "BASELINE",
                            "confidence": 1.0,
                            "provenance": [],
                        },
                        {
                            "build_id": "v2",
                            "internal_name": "rs/b",
                            "entry_path": "rs/b.class",
                            "entry_sha256": new_index["entries"]["rs/b.class"]["sha256"],
                            "structural_sha256": new_cls["structural_sha256"],
                            "relation": "STRUCTURAL",
                            "confidence": 0.995,
                            "provenance": [],
                        },
                    ],
                    "semantic_provenance": [],
                }
            ],
            "unresolved": [],
        }

        fields = []
        for ordinal, name in enumerate(("bG", "bH", "bI", "bZ"), start=1):
            old_decl = next(
                row
                for row in old_cls["fields"]
                if row["name"] == name
            )
            fields.append(
                {
                    "member_id": f"CLIENT_FIELD_{ordinal:06d}",
                    "owner_logical_id": "CLIENT_CLASS_000001",
                    "kind": "field",
                    "semantic_name": None,
                    "semantic_status": "UNKNOWN",
                    "semantic_confidence": 0.0,
                    "lineage": [
                        {
                            "build_id": "v1",
                            "owner_internal_name": "rs/a",
                            "name": name,
                            "descriptor": "I",
                            "access": old_decl["access"],
                            "relation": "BASELINE",
                            "confidence": 1.0,
                            "provenance": [],
                        }
                    ],
                    "semantic_provenance": [],
                }
            )

        methods = []
        for ordinal, name in enumerate(("m", "n", "p", "q"), start=1):
            old_decl = next(
                row for row in old_cls["methods"]
                if row["name"] == name
            )
            new_decl = next(
                row for row in new_cls["methods"]
                if row["name"] == name
            )
            methods.append(
                {
                    "member_id": f"CLIENT_METHOD_{ordinal:06d}",
                    "owner_logical_id": "CLIENT_CLASS_000001",
                    "kind": "method",
                    "semantic_name": None,
                    "semantic_status": "UNKNOWN",
                    "semantic_confidence": 0.0,
                    "lineage": [
                        {
                            "build_id": "v1",
                            "owner_internal_name": "rs/a",
                            "name": name,
                            "descriptor": "()I",
                            "access": old_decl["access"],
                            "code_length": old_decl["code_length"],
                            "relation": "BASELINE",
                            "confidence": 1.0,
                            "provenance": [],
                        },
                        {
                            "build_id": "v2",
                            "owner_internal_name": "rs/b",
                            "name": name,
                            "descriptor": "()I",
                            "access": new_decl["access"],
                            "code_length": new_decl["code_length"],
                            "relation": "STRUCTURAL",
                            "confidence": 0.99,
                            "provenance": [],
                        },
                    ],
                    "semantic_provenance": [],
                }
            )

        member_lineage = {
            "schema_version": 1,
            "kind": "member_lineage",
            "class_namespace": "spawnpk-client",
            "baseline_build_id": "v1",
            "source_sha256": old_index["sha256"],
            "members": fields + methods,
            "unresolved": [
                {
                    "old_build_id": "v1",
                    "new_build_id": "v2",
                    "kind": "member_identity_review",
                    "member_kind": "field",
                    "candidate": {
                        "old_owner": "rs/a.class",
                        "new_owner": "rs/b.class",
                        "old": {"name": "bI", "descriptor": "I"},
                        "new": {"name": "bK", "descriptor": "I"},
                        "strategy": "exact_matched_method_access_positions",
                    },
                    "source": "member_identity_candidates",
                }
            ],
        }
        return (
            old_jar,
            new_jar,
            old_index,
            new_index,
            class_lineage,
            member_lineage,
        )

    def test_shifted_same_shape_fields_are_proved_from_bytecode(self):
        with tempfile.TemporaryDirectory() as td:
            (
                old_jar,
                new_jar,
                old_index,
                new_index,
                classes,
                members,
            ) = self._fixture(Path(td))

            out, proof, summary = prove_and_apply_fields(
                classes,
                members,
                old_index,
                new_index,
                old_jar,
                new_jar,
                old_build_id="v1",
                new_build_id="v2",
            )

            mapping = {}
            for record in out["members"]:
                if record["kind"] != "field":
                    continue
                old_entry = next(
                    row for row in record["lineage"]
                    if row["build_id"] == "v1"
                )
                new_entries = [
                    row for row in record["lineage"]
                    if row["build_id"] == "v2"
                ]
                if new_entries:
                    mapping[old_entry["name"]] = new_entries[0]["name"]

            self.assertEqual(mapping["bG"], "bI")
            self.assertEqual(mapping["bH"], "bJ")
            self.assertEqual(mapping["bI"], "bK")
            self.assertNotIn("bZ", mapping)
            self.assertEqual(proof["proof_count"], 3)
            self.assertEqual(summary["applied_fields"], 3)
            self.assertEqual(summary["unresolved_removed"], 1)
            self.assertEqual(len(out["unresolved"]), 0)

    def test_tampered_new_jar_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            (
                old_jar,
                new_jar,
                old_index,
                new_index,
                classes,
                members,
            ) = self._fixture(Path(td))
            with new_jar.open("ab") as f:
                f.write(b"tamper")

            with self.assertRaises(FieldProofError):
                prove_and_apply_fields(
                    classes,
                    members,
                    old_index,
                    new_index,
                    old_jar,
                    new_jar,
                    old_build_id="v1",
                    new_build_id="v2",
                )


if __name__ == "__main__":
    unittest.main()

"""Synthetic, original-bytecode-backed R11 external anchor tests."""
from __future__ import annotations

import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.external_field_witness_research import (
    ExternalWitnessError,
    _accepted_descriptor_identity,
    build_external_field_witness_research,
)
from spk_recovery.indexer import index_jar


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ExternalFieldWitnessResearchTests(unittest.TestCase):
    def _jar(self, root: Path, tag: str, target: str, fields: tuple[str, str], *, object_fields: bool = False) -> Path:
        src = root / (tag + "_src") / "rs"
        src.mkdir(parents=True)
        if object_fields:
            field_type = tag + "type"
            source = (
                "package rs; public class " + target + " { public " + field_type + " " +
                fields[0] + "," + fields[1] +
                "; public void set(" + field_type + " x," + field_type + " y){" +
                fields[0] + "=x;" + fields[1] + "=y;} } " +
                "class " + field_type + " {} " +
                "class p { static Object get(" + target + " v) {return v." + fields[0] + ";} } " +
                "class q { static Object get(" + target + " v) {return v." + fields[1] + ";} } "
            )
        else:
            source = (
                "package rs; public class " + target + " { public int " +
                fields[0] + "," + fields[1] +
                "; public void set(int x,int y){" + fields[0] +
                "=x;" + fields[1] + "=y;} } " +
                "class p { static int get(" + target + " v) {return v." +
                fields[0] + "+v." + fields[1] + ";} } " +
                "class q { static int get(" + target + " v) {return v." +
                fields[0] + "-v." + fields[1] + ";} } "
            )
        (src / (target + ".java")).write_text(source, encoding="utf-8")
        classes = root / (tag + "_classes")
        classes.mkdir()
        subprocess.run(
            ["javac", "-g:none", "-d", str(classes), str(src / (target + ".java"))],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        jar = root / (tag + ".jar")
        with zipfile.ZipFile(jar, "w") as z:
            for p in sorted(classes.rglob("*.class")):
                z.write(p, p.relative_to(classes).as_posix())
        return jar

    def _fixture(self, root: Path, *, object_fields: bool = False):
        old = self._jar(root, "old", "a", ("c", "d"), object_fields=object_fields)
        new = self._jar(root, "new", "b", ("e", "f"), object_fields=object_fields)
        oi, ni = index_jar(old), index_jar(new)
        classes = []
        for i, (ol, nl) in enumerate((("a", "b"), ("p", "p"), ("q", "q")), 1):
            entries = []
            for build, idx, name in (("v1", oi, ol), ("v2", ni, nl)):
                path = "rs/" + name + ".class"
                entries.append({
                    "build_id": build, "internal_name": "rs/" + name,
                    "entry_path": path, "entry_sha256": idx["entries"][path]["sha256"],
                    "structural_sha256": idx["classes"][path]["structural_sha256"],
                    "relation": "BASELINE" if build == "v1" else "STRUCTURAL",
                    "confidence": 1.0, "provenance": [],
                })
            classes.append({
                "logical_id": f"CLIENT_CLASS_{i:06d}", "semantic_name": None,
                "semantic_status": "UNKNOWN", "semantic_confidence": 0.0,
                "semantic_provenance": [], "lineage": entries,
            })
        lineage = {
            "schema_version": 1, "namespace": "spawnpk-client",
            "id_format": "CLIENT_CLASS_%06d", "baseline_build_id": "v1",
            "builds": [
                {"build_id": b, "build_number": n, "sha256": idx["sha256"],
                 "source_name": b + ".jar",
                 "authority": "EXACT_HISTORICAL_CLIENT" if b == "v1" else "CROSS_BUILD"}
                for b, n, idx in (("v1", 1, oi), ("v2", 2, ni))
            ], "classes": classes, "unresolved": [],
        }
        members = []
        unresolved = []
        for i, (old_name, new_name) in enumerate((("c", "e"), ("d", "f")), 1):
            original = next(
                f for f in oi["classes"]["rs/a.class"]["fields"]
                if f["name"] == old_name
            )
            members.append({
                "member_id": f"CLIENT_FIELD_{i:06d}",
                "owner_logical_id": "CLIENT_CLASS_000001",
                "kind": "field", "semantic_name": None,
                "semantic_status": "UNKNOWN", "semantic_confidence": 0.0,
                "semantic_provenance": [],
                "lineage": [{
                    "build_id": "v1", "owner_internal_name": "rs/a",
                    "name": old_name, "descriptor": "I", "access": original["access"],
                    "relation": "BASELINE", "confidence": 1.0, "provenance": [],
                }],
            })
            unresolved.append({
                "old_build_id": "v1", "new_build_id": "v2",
                "kind": "member_identity_review", "member_kind": "field",
                "source": "member_identity_candidates",
                "candidate": {
                    "old_owner": "rs/a.class", "new_owner": "rs/b.class",
                    "old": {"name": old_name, "descriptor": original["descriptor"]},
                    "new": {"name": new_name, "descriptor": next(
                        f["descriptor"] for f in ni["classes"]["rs/b.class"]["fields"]
                        if f["name"] == new_name
                    )},
                },
            })
        for i, (ol, nl, method) in enumerate(
            (("a", "b", "set"), ("p", "p", "get"), ("q", "q", "get")), 1
        ):
            a = next(m for m in oi["classes"]["rs/" + ol + ".class"]["methods"]
                     if m["name"] == method)
            b = next(m for m in ni["classes"]["rs/" + nl + ".class"]["methods"]
                     if m["name"] == method)
            members.append({
                "member_id": f"CLIENT_METHOD_{i:06d}",
                "owner_logical_id": f"CLIENT_CLASS_{i:06d}",
                "kind": "method", "semantic_name": None,
                "semantic_status": "UNKNOWN", "semantic_confidence": 0.0,
                "semantic_provenance": [],
                "lineage": [
                    {"build_id": "v1", "owner_internal_name": "rs/" + ol,
                     "name": method, "descriptor": a["descriptor"], "access": a["access"],
                     "code_length": a["code_length"], "relation": "BASELINE",
                     "confidence": 1.0, "provenance": []},
                    {"build_id": "v2", "owner_internal_name": "rs/" + nl,
                     "name": method, "descriptor": b["descriptor"], "access": b["access"],
                     "code_length": b["code_length"], "relation": "STRUCTURAL",
                     "confidence": 1.0, "provenance": []},
                ],
            })
        ml = {
            "schema_version": 1, "kind": "member_lineage",
            "class_namespace": "spawnpk-client", "baseline_build_id": "v1",
            "source_sha256": oi["sha256"], "members": members, "unresolved": unresolved,
        }
        return old, new, oi, ni, lineage, ml

    def _probe(self, fixture, **kw):
        old, new, oi, ni, classes, members = fixture
        return build_external_field_witness_research(
            classes, members, oi, ni, old, new,
            old_build_id="v1", new_build_id="v2",
            logical_class_id="CLIENT_CLASS_000001", **kw,
        )

    def test_three_canonical_methods_and_zero_acceptance(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self._fixture(Path(td))
            report = self._probe(fixture)
            self.assertEqual([c["distinct_canonical_method_witnesses"]
                              for c in report["candidates"]], [3, 3])
            self.assertTrue(all(c["status"] == "REVIEWABLE_EXTERNAL_ANCHORS"
                                for c in report["candidates"]))
            self.assertFalse(report["canonical"])
            self.assertEqual(report["accepted_identities"], 0)

    def test_swapped_field_proposals_are_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = list(self._fixture(Path(td)))
            fixture[-1] = copy.deepcopy(fixture[-1])
            for u in fixture[-1]["unresolved"]:
                name = u["candidate"]["new"]["name"]
                u["candidate"]["new"]["name"] = "f" if name == "e" else "e"
            report = self._probe(fixture)
            self.assertTrue(all(c["status"] == "BLOCKED"
                                for c in report["candidates"]))

    def test_threshold_below_two_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ExternalWitnessError):
                self._probe(self._fixture(Path(td)), min_independent_methods=1)

    def test_descriptor_only_accepted_owner_aliases(self):
        aliases = {"rs/a": "CLIENT_CLASS_000001"}
        self.assertEqual(
            _accepted_descriptor_identity("[[Lrs/a;", aliases),
            "[[L@CLIENT_CLASS_000001;",
        )
        self.assertEqual(_accepted_descriptor_identity("I", aliases), "I")
        self.assertIsNone(_accepted_descriptor_identity("Lrs/unknown;", aliases))
        self.assertIsNone(_accepted_descriptor_identity("[Lrs/unknown;", aliases))
        with self.assertRaises(ExternalWitnessError):
            _accepted_descriptor_identity("Lrs/malformed", aliases)

    def test_unmapped_object_descriptors_block_both_fields(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = self._fixture(Path(td), object_fields=True)
            report = self._probe(fixture)
            self.assertEqual(len(report["candidates"]), 2)
            self.assertTrue(all(c["status"] == "BLOCKED"
                                for c in report["candidates"]))
            self.assertEqual(report["accepted_identities"], 0)

    def test_tampered_jar_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = list(self._fixture(Path(td)))
            with fixture[1].open("ab") as f:
                f.write(b"tamper")
            with self.assertRaises(ExternalWitnessError):
                self._probe(fixture)


if __name__ == "__main__":
    unittest.main()

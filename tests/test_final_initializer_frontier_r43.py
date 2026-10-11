"""R43: real javac-compiled synthetic <clinit> final-assignment evidence."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.source_class_method_matrix import build_class_method_matrix
from spk_recovery.final_initializer_frontier import (
    FinalInitializerFrontierError,
    build_final_initializer_frontier,
    examine_final_initializers,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class FinalInitializerJavacTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, members: str) -> Path:
        src = root / name / "src" / "p"
        output = root / name / "classes"
        src.mkdir(parents=True)
        output.mkdir(parents=True)
        file = src / "A.java"
        file.write_text(
            "package p; public class A {" + members
            + " public static void keep(){} }", encoding="utf-8",
        )
        result = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(output), str(file)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as archive:
            archive.write(output / "p" / "A.class", "p/A.class")
        return jar

    def _fixture(self, root: Path, candidate: str = "public static int[] array;"):
        original = self._jar(
            root, "original",
            'public static final String text;'
            'public static final int[] array;'
            'public static final Integer boxed;'
            'public static final int literal=42;'
            'static {text=System.getProperty("p.example");'
            'array=new int[3];boxed=Integer.valueOf(7);}',
        )
        rebuilt = self._jar(root, "candidate", candidate)
        return original, rebuilt

    def _replay(self, old: Path, new: Path):
        return build_final_initializer_frontier(
            old, new, original_sha256=_sha(old),
            candidate_sha256=_sha(new), class_entry="p/A.class",
        )

    def test_tracks_three_stores_without_inventing_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._fixture(Path(tmp))
            report = self._replay(old, new)
            self.assertEqual(report["original_final_fields_without_constantvalue"], 3)
            self.assertEqual(report["type_counts"], {
                "boxed_integer": 1, "int_array": 1, "string": 1,
            })
            self.assertEqual(report["candidate_status_counts"], {
                "missing": 2, "present_metadata_difference": 1,
                "present_same_metadata": 0,
            })
            self.assertFalse(report["runtime_initializer_equivalence_certified"])
            self.assertFalse(report["complete_source_reconstructed"])
            self.assertFalse(report["source_expressions_emitted"])
            pcs = [r["original_clinit_write_pc"] for r in report["assignment_sites"]]
            self.assertEqual(pcs, sorted(pcs))
            self.assertEqual(len(pcs), len(set(pcs)))
            self.assertTrue(all(r["assignment_store_site_verified"]
                                for r in report["assignment_sites"]))
            self.assertTrue(all(not r["expression_or_runtime_value_recovered"]
                                for r in report["assignment_sites"]))
            self.assertNotIn("p/A", str(report))
            self.assertNotIn('"text"', str(report))
            self.assertNotIn('"boxed"', str(report))
            self.assertEqual(report, self._replay(old, new))

    def test_wrong_jar_hash_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._fixture(Path(tmp))
            with self.assertRaises(FinalInitializerFrontierError):
                build_final_initializer_frontier(
                    old, new, original_sha256=_sha(old),
                    candidate_sha256="0" * 64,
                    class_entry="p/A.class",
                )

    def test_mutated_clinit_write_profile_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._fixture(Path(tmp))
            matrix = build_class_method_matrix(
                old, new,
                original_sha256=_sha(old), candidate_sha256=_sha(new),
                class_entry="p/A.class",
            )
            original = profile_jar_class(old, "p/A.class")
            candidate = profile_jar_class(new, "p/A.class")
            clinit = next(m for m in original["methods"] if m["name"] == "<clinit>")
            write = next(x for x in clinit["field_accesses"]
                         if x["operation"] == "putstatic"
                         and x["owner"] == original["internal_name"])
            bad = copy.deepcopy(original)
            target = next(m for m in bad["methods"] if m["name"] == "<clinit>")
            target["field_accesses"].append(copy.deepcopy(write))
            with self.assertRaisesRegex(
                FinalInitializerFrontierError,
                "FINAL_NONCONSTANT_REQUIRES_EXACTLY_ONE_CLINIT_WRITE",
            ):
                examine_final_initializers(
                    bad, candidate, matrix, original_sha256=_sha(old),
                )

    def test_missing_store_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = self._fixture(Path(tmp))
            matrix = build_class_method_matrix(
                old, new, original_sha256=_sha(old),
                candidate_sha256=_sha(new), class_entry="p/A.class",
            )
            original = profile_jar_class(old, "p/A.class")
            candidate = profile_jar_class(new, "p/A.class")
            target = next(m for m in original["methods"] if m["name"] == "<clinit>")
            target["field_accesses"] = []
            with self.assertRaisesRegex(
                FinalInitializerFrontierError,
                "FINAL_NONCONSTANT_REQUIRES_EXACTLY_ONE_CLINIT_WRITE",
            ):
                examine_final_initializers(
                    original, candidate, matrix, original_sha256=_sha(old),
                )

    def test_nonfinal_static_writes_are_not_promoted_to_final_assignments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = self._jar(
                root, "original",
                "public static final int[] unique;"
                "public static int mutable;"
                "static { unique=new int[2]; mutable=99; }",
            )
            new = self._jar(root, "candidate", "public static int mutable;")
            report = self._replay(old, new)
            self.assertEqual(report["original_final_fields_without_constantvalue"], 1)
            self.assertEqual(report["type_counts"], {"int_array": 1})


if __name__ == "__main__":
    unittest.main()

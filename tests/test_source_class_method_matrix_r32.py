"""R32: synthetic and javac-backed class-wide method parity, without client code."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
import warnings
from zipfile import ZipFile

from spk_recovery.source_class_method_matrix import (
    ClassMethodMatrixError,
    build_class_method_matrix,
    compare_class_method_profiles,
)


def _digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def _method(name: str, opcode: str) -> dict:
    return {
        "name": name,
        "descriptor": "()I",
        "access": 1,
        "code_length": 2,
        "max_stack": 1,
        "max_locals": 1,
        "instructions": [
            {"offset": 0, "length": 1, "opcode": opcode, "mnemonic": "synthetic",
             "int_constant": 1 if opcode == "0x04" else 2},
            {"offset": 1, "length": 1, "opcode": "0xac", "mnemonic": "synthetic"},
        ],
        "exception_handlers": [],
        "stackmap_table_present": False,
        "stackmap_frames": [],
    }


def _profile(methods: list[dict], owner: str = "p/A") -> dict:
    return {
        "internal_name": owner,
        "methods": methods,
        "bootstrap_methods": [],
    }


class ClassMatrixSyntheticTests(unittest.TestCase):
    def test_aggregate_match_drift_missing_and_extra(self):
        original = _profile([_method("same", "0x04"), _method("changed", "0x04"),
                             _method("absent", "0x04")])
        candidate = _profile([_method("same", "0x04"), _method("changed", "0x05"),
                              _method("new", "0x04")])
        result = compare_class_method_profiles(original, candidate, original_sha="a" * 64)
        self.assertEqual(result["counts"], {
            "instruction_parity": 1, "body_difference": 1,
            "missing_method": 1, "extra_method": 1,
            "no_original_code": 0, "candidate_has_no_code": 0,
        })
        self.assertFalse(result["all_method_bodies_instruction_parity"])
        self.assertFalse(result["source_equivalence_certified"])
        self.assertFalse(result["whole_class_equivalence_certified"])
        self.assertNotIn("p/A", str(result))
        self.assertNotIn("changed", str(result))
        self.assertEqual(result, compare_class_method_profiles(
            original, candidate, original_sha="a" * 64
        ))

    def test_exact_candidates_never_certify_source_equivalence(self):
        p = _profile([_method("same", "0x04")])
        report = compare_class_method_profiles(p, p, original_sha="f" * 64)
        self.assertTrue(report["all_method_bodies_instruction_parity"])
        self.assertEqual(report["counts"]["instruction_parity"], 1)
        self.assertFalse(report["source_equivalence_certified"])
        self.assertFalse(report["canonical_identity_accepted"])

    def test_missing_code_and_abstract_original_are_explicit(self):
        original = _profile([_method("body", "0x04"), _method("abstract", "0x04")])
        candidate = _profile([_method("body", "0x04"), _method("abstract", "0x04")])
        candidate["methods"][0]["code_length"] = None
        original["methods"][1]["code_length"] = None
        report = compare_class_method_profiles(original, candidate,
                                               original_sha="a" * 64)
        self.assertEqual(report["counts"]["candidate_has_no_code"], 1)
        self.assertEqual(report["counts"]["no_original_code"], 1)
        self.assertFalse(report["all_method_bodies_instruction_parity"])

    def test_ambiguous_method_inventory_and_aliases_fail_closed(self):
        original = _profile([_method("same", "0x04")])
        duplicated = _profile([_method("same", "0x04"), _method("same", "0x04")])
        with self.assertRaisesRegex(ClassMethodMatrixError, "DUPLICATE_OR_INVALID_METHOD"):
            compare_class_method_profiles(original, duplicated, original_sha="a" * 64)
        alias = _profile([_method("same", "0x04")], owner="p/Other")
        with self.assertRaisesRegex(ClassMethodMatrixError, "NO_ACCEPTED_OWNER_ALIAS"):
            compare_class_method_profiles(original, alias, original_sha="a" * 64)

    def test_invalid_method_body_refuses_whole_batch(self):
        original = _profile([_method("same", "0x04")])
        candidate = _profile([_method("same", "0x04")])
        del candidate["methods"][0]["max_stack"]
        with self.assertRaisesRegex(ClassMethodMatrixError, "NON_EVALUABLE_METHOD_BODY"):
            compare_class_method_profiles(original, candidate, original_sha="a" * 64)


@unittest.skipUnless(shutil.which("javac"), "Java compiler required")
class ClassMatrixJavacTests(unittest.TestCase):
    def _jar(self, root: Path, stem: str, methods: str) -> Path:
        src = root / stem / "source" / "p"
        output = root / stem / "classes"
        src.mkdir(parents=True)
        output.mkdir(parents=True)
        p = src / "A.java"
        p.write_text("package p; public class A {" + methods + "}",
                     encoding="utf-8")
        cmd = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-d", str(output), str(p)],
            capture_output=True, text=True,
        )
        self.assertEqual(cmd.returncode, 0, cmd.stdout + cmd.stderr)
        jar = root / (stem + ".jar")
        with ZipFile(jar, "w") as z:
            z.write(output / "p" / "A.class", "p/A.class")
        return jar

    def _run(self, a: Path, b: Path, *, original_sha=None, candidate_sha=None):
        return build_class_method_matrix(
            a, b,
            original_sha256=original_sha or _digest(a),
            candidate_sha256=candidate_sha or _digest(b),
            class_entry="p/A.class",
        )

    def test_javac_methods_match_drift_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._jar(root, "original",
                "public int keep(int x){return x+1;}"
                "public int change(int x){return x+2;}"
                'public String originalOnly(){return "old";}'
            )
            candidate = self._jar(root, "candidate",
                "public int keep(int x){return x+1;}"
                "public int change(int x){return x+3;}"
                "public int added(){return 9;}"
            )
            report = self._run(original, candidate)
            self.assertEqual(report["original_declared_method_count"], 4)
            self.assertEqual(report["candidate_declared_method_count"], 4)
            self.assertEqual(report["counts"]["instruction_parity"], 2)
            self.assertEqual(report["counts"]["body_difference"], 1)
            self.assertEqual(report["counts"]["missing_method"], 1)
            self.assertEqual(report["counts"]["extra_method"], 1)
            self.assertEqual(report, self._run(original, candidate))

    def test_changed_hash_fails_and_output_is_not_touched(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = self._jar(root, "old", "public int x(){return 1;}")
            new = self._jar(root, "new", "public int x(){return 1;}")
            with self.assertRaisesRegex(ClassMethodMatrixError, "JAR_SHA256_MISMATCH"):
                self._run(old, new, candidate_sha="0" * 64)
            self.assertTrue(old.exists())
            self.assertTrue(new.exists())

    def test_duplicate_class_entry_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = self._jar(root, "old", "public int x(){return 1;}")
            new = self._jar(root, "new", "public int x(){return 1;}")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(new, "a") as archive:
                    archive.writestr("p/A.class", b"bad")
            with self.assertRaisesRegex(ClassMethodMatrixError, "MISSING_OR_DUPLICATE_CLASS"):
                self._run(old, new)


if __name__ == "__main__":
    unittest.main()

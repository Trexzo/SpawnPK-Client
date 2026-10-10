"""R35: fields must not be hidden behind matching reconstructed methods."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.source_class_method_matrix import (
    ClassMethodMatrixError,
    build_class_method_matrix,
    compare_class_method_profiles,
)


def _field(name: str, *, access=1, descriptor="I",
           signature=None, constant_value=None):
    return {
        "name": name, "descriptor": descriptor,
        "access": access, "signature": signature,
        "constant_value": constant_value,
    }


def _profile(fields, signature=None):
    return {
        "internal_name": "p/A",
        "class_access": 0x21,
        "classfile_major": 53,
        "classfile_minor": 0,
        "super_name": "java/lang/Object",
        "interfaces": [],
        "signature": signature,
        "fields": fields,
        "methods": [],
        "bootstrap_methods": [],
    }


class ClassFieldInventorySyntheticTests(unittest.TestCase):
    def test_matching_missing_extra_and_changed_metadata_are_separate(self):
        original = _profile([
            _field("same"), _field("changed", access=1),
            _field("absent"),
        ])
        candidate = _profile([
            _field("same"), _field("changed", access=9),
            _field("added"),
        ])
        report = compare_class_method_profiles(original, candidate,
                                               original_sha="a" * 64)
        self.assertEqual(report["original_declared_field_count"], 3)
        self.assertEqual(report["candidate_declared_field_count"], 3)
        self.assertEqual(report["field_counts"], {
            "shared_exact": 1, "shared_metadata_difference": 1,
            "missing_field": 1, "extra_field": 1,
        })
        self.assertFalse(report["field_inventory_exact"])
        self.assertFalse(report["source_equivalence_certified"])
        self.assertNotIn("changed", str(report))
        self.assertNotIn("absent", str(report))
        self.assertEqual(report, compare_class_method_profiles(
            original, candidate, original_sha="a" * 64
        ))

    def test_identical_fields_still_never_certify_whole_class(self):
        fields = [_field("constant", access=25, constant_value=15)]
        p = _profile(fields)
        report = compare_class_method_profiles(p, p, original_sha="0" * 64)
        self.assertTrue(report["field_inventory_exact"])
        self.assertEqual(report["field_counts"]["shared_exact"], 1)
        self.assertFalse(report["whole_class_equivalence_certified"])
        self.assertFalse(report["all_method_bodies_instruction_parity"])

    def test_constant_signature_and_signed_zero_difference(self):
        samples = [
            (_field("f", constant_value=1), _field("f", constant_value=2)),
            (_field("f", signature="Ljava/util/List<Ljava/lang/String;>;"),
             _field("f", signature=None)),
            (_field("f", descriptor="F", constant_value=-0.0),
             _field("f", descriptor="F", constant_value=0.0)),
        ]
        for before, after in samples:
            with self.subTest(before=before, after=after):
                result = compare_class_method_profiles(
                    _profile([before]), _profile([after]), original_sha="a" * 64
                )
                self.assertEqual(result["field_counts"]["shared_metadata_difference"], 1)
                self.assertFalse(result["field_inventory_exact"])

    def test_nan_constant_fails_closed(self):
        p = _profile([_field("f", descriptor="F", constant_value=float("nan"))])
        with self.assertRaisesRegex(ClassMethodMatrixError, "UNSAFE_NAN_CONSTANT_VALUE"):
            compare_class_method_profiles(p, p, original_sha="a" * 64)

    def test_class_generic_signature_is_distinguished(self):
        a = _profile([_field("f")], signature="<T:Ljava/lang/Object;>Ljava/lang/Object;")
        b = _profile([_field("f")], signature=None)
        report = compare_class_method_profiles(a, b, original_sha="a" * 64)
        self.assertFalse(report["class_signature_exact"])
        self.assertTrue(report["field_inventory_exact"])
        self.assertFalse(report["whole_class_equivalence_certified"])

    def test_missing_or_duplicate_field_inventory_rejected(self):
        a = _profile([_field("f")])
        for wrong in (
            {"internal_name": "p/A", "signature": None, "methods": []},
            _profile([_field("f"), _field("f")]),
            _profile([_field("f", access=True)]),
            _profile([{"name": "f", "descriptor": "I", "access": 1, "signature": None}]),
        ):
            with self.subTest(wrong=wrong):
                with self.assertRaises(ClassMethodMatrixError):
                    compare_class_method_profiles(a, wrong, original_sha="a" * 64)

    def test_missing_class_signature_metadata_rejected(self):
        a = _profile([_field("f")])
        b = _profile([_field("f")])
        b.pop("signature")
        with self.assertRaisesRegex(ClassMethodMatrixError, "CLASS_SIGNATURE_EVIDENCE_MISSING"):
            compare_class_method_profiles(a, b, original_sha="a" * 64)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ClassFieldInventoryJavacTests(unittest.TestCase):
    def _jar(self, root: Path, stem: str, fields: str) -> Path:
        src = root / stem / "source" / "p"
        classes = root / stem / "classes"
        src.mkdir(parents=True)
        classes.mkdir()
        java = src / "A.java"
        java.write_text(
            "package p; public class A { " + fields +
            " public int value(){return 1;} }",
            encoding="utf-8",
        )
        result = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(java)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        jar = root / f"{stem}.jar"
        with ZipFile(jar, "w") as archive:
            archive.write(classes / "p" / "A.class", "p/A.class")
        return jar

    def test_real_compiled_class_missing_original_fields_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = self._jar(root, "original", "public int state; public int extra;")
            candidate = self._jar(root, "candidate", "public int state;")
            report = build_class_method_matrix(
                original, candidate,
                original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                class_entry="p/A.class",
            )
            self.assertEqual(report["counts"]["instruction_parity"], 2)
            self.assertTrue(report["all_method_bodies_instruction_parity"])
            self.assertEqual(report["field_counts"]["shared_exact"], 1)
            self.assertEqual(report["field_counts"]["missing_field"], 1)
            self.assertFalse(report["field_inventory_exact"])
            self.assertFalse(report["whole_class_equivalence_certified"])


if __name__ == "__main__":
    unittest.main()

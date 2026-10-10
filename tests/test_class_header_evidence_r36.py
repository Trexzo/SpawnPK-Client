"""R36 class-header evidence tests; synthetic Java only, no private client bytes."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.class_header_evidence import (
    ClassHeaderError, compare_class_headers,
)
from spk_recovery.source_class_method_matrix import (
    ClassMethodMatrixError, compare_class_method_profiles,
)


def _header(**patch):
    profile = {
        "internal_name": "p/A",
        "class_access": 0x21,
        "classfile_major": 53,
        "classfile_minor": 0,
        "super_name": "java/lang/Object",
        "interfaces": ["p/I"],
    }
    profile.update(patch)
    return profile


class HeaderUnitTests(unittest.TestCase):
    def test_identical_header_is_research_only(self):
        result = compare_class_headers(_header(), _header())
        self.assertTrue(result["class_header_exact"])
        self.assertTrue(all(result["checks"].values()))
        self.assertFalse(result["canonical_identity_accepted"])
        self.assertFalse(result["source_equivalence_certified"])
        self.assertNotIn("p/A", str(result))
        self.assertNotIn("java/lang/Object", str(result))

    def test_independent_header_dimensions(self):
        for key, value, check in (
            ("class_access", 0x31, "access_flags"),
            ("super_name", "p/Alt", "direct_superclass"),
            ("interfaces", ["p/I", "p/J"], "ordered_interfaces"),
            ("classfile_major", 52, "classfile_major"),
            ("classfile_minor", 65535, "classfile_minor"),
        ):
            with self.subTest(key=key):
                candidate = _header(**{key: value})
                evidence = compare_class_headers(_header(), candidate)
                self.assertFalse(evidence["class_header_exact"])
                self.assertFalse(evidence["checks"][check])
                self.assertEqual(sum(not v for v in evidence["checks"].values()), 1)

    def test_interface_order_changes_are_detected(self):
        one = _header(interfaces=["p/I", "p/J"])
        two = _header(interfaces=["p/J", "p/I"])
        self.assertFalse(
            compare_class_headers(one, two)["checks"]["ordered_interfaces"]
        )

    def test_missing_or_malformed_header_fails_closed(self):
        for field, bad in (
            ("class_access", True), ("class_access", None),
            ("classfile_major", "53"), ("classfile_minor", -1),
            ("super_name", ""), ("interfaces", None),
            ("interfaces", ["p/I", "p/I"]), ("interfaces", [None]),
        ):
            with self.subTest(field=field, bad=bad):
                with self.assertRaises(ClassHeaderError):
                    compare_class_headers(_header(), _header(**{field: bad}))
        for key in ("class_access", "classfile_major",
                    "classfile_minor", "super_name", "interfaces"):
            incomplete = _header()
            incomplete.pop(key)
            with self.subTest(missing=key):
                with self.assertRaises(ClassHeaderError):
                    compare_class_headers(_header(), incomplete)

    def test_matrix_reports_class_header_even_without_declared_methods(self):
        original = {
            **_header(), "signature": None, "fields": [],
            "methods": [], "bootstrap_methods": [],
        }
        candidate = {
            **_header(super_name="p/Alt"), "signature": None, "fields": [],
            "methods": [], "bootstrap_methods": [],
        }
        report = compare_class_method_profiles(
            original, candidate, original_sha="f" * 64,
        )
        self.assertFalse(report["class_header"]["class_header_exact"])
        self.assertFalse(report["class_header"]["checks"]["direct_superclass"])
        self.assertTrue(report["field_inventory_exact"])
        self.assertFalse(report["whole_class_equivalence_certified"])
        self.assertFalse(report["all_method_bodies_instruction_parity"])
        self.assertNotIn("p/Alt", str(report))

        broken = dict(candidate)
        del broken["interfaces"]
        with self.assertRaisesRegex(
            ClassMethodMatrixError, "CLASS_HEADER_EVIDENCE_INVALID",
        ):
            compare_class_method_profiles(
                original, broken, original_sha="f" * 64,
            )

    def test_owner_alias_not_inferred(self):
        with self.assertRaisesRegex(ClassHeaderError, "NO_ACCEPTED_CLASS_OWNER_ALIAS"):
            compare_class_headers(_header(), _header(internal_name="p/B"))

    def test_java_lang_object_has_no_superclass(self):
        root = _header(internal_name="java/lang/Object", super_name=None,
                       interfaces=[])
        evidence = compare_class_headers(root, root)
        self.assertTrue(evidence["class_header_exact"])
        self.assertFalse(evidence["original_superclass_present"])


@unittest.skipUnless(shutil.which("javac"), "javac required")
class HeaderJavacTests(unittest.TestCase):
    def _profile(self, root: Path, name: str, *, base="Base",
                 interfaces="I", modifier="", release="9"):
        src = root / name / "source" / "p"
        output = root / name / "classes"
        src.mkdir(parents=True)
        output.mkdir(parents=True)
        source = src / "A.java"
        source.write_text(
            "package p; class Base {} class Alt {} interface I {} interface J {}"
            f" public {modifier}class A extends {base} implements {interfaces} "
            " { public int value(){return 1;} }",
            encoding="utf-8",
        )
        run = subprocess.run(
            ["javac", "--release", release, "-g:none", "-proc:none",
             "-d", str(output), str(source)],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return profile_class_field_accesses((output / "p" / "A.class").read_bytes())

    def test_compiled_superclass_interface_and_flags_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            baseline = self._profile(root, "base")
            changed_super = self._profile(root, "alt-super", base="Alt")
            changed_interfaces = self._profile(root, "plus-iface", interfaces="I,J")
            final_class = self._profile(root, "final", modifier="final ")
            self.assertTrue(compare_class_headers(baseline, baseline)["class_header_exact"])
            self.assertFalse(
                compare_class_headers(baseline, changed_super)["checks"]["direct_superclass"]
            )
            self.assertFalse(
                compare_class_headers(baseline, changed_interfaces)["checks"]["ordered_interfaces"]
            )
            self.assertFalse(
                compare_class_headers(baseline, final_class)["checks"]["access_flags"]
            )

    def test_compiled_version_is_retained(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            java8 = self._profile(root, "java8", release="8")
            java9 = self._profile(root, "java9", release="9")
            self.assertEqual(java8["classfile_major"], 52)
            self.assertEqual(java9["classfile_major"], 53)
            evidence = compare_class_headers(java8, java9)
            self.assertFalse(evidence["checks"]["classfile_major"])
            self.assertFalse(evidence["class_header_exact"])


if __name__ == "__main__":
    unittest.main()

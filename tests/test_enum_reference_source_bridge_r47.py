"""R47: original enum-type dependencies and owner-field descriptor-only parity.

All fixtures compile synthetic Java with javac; no private SpawnPK source,
class names, enum constants or raw original method bodies are committed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.enum_reference_source_bridge import (
    EnumReferenceScaffoldError,
    build_enum_reference_scaffold,
    plan_nested_enum_field_references,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class EnumReferenceBridgeJavacTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, java_body: str) -> Path:
        src = root / name / "src" / "p"
        classes = root / name / "classes"
        src.mkdir(parents=True)
        classes.mkdir(parents=True)
        file = src / "Owner.java"
        file.write_text(
            "package p; public class Owner { " + java_body + " }",
            encoding="utf-8",
        )
        compile_result = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(file)],
            capture_output=True, text=True,
        )
        self.assertEqual(
            compile_result.returncode, 0,
            compile_result.stdout + compile_result.stderr,
        )
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as archive:
            for compiled in sorted(classes.rglob("*.class")):
                archive.write(
                    compiled, compiled.relative_to(classes).as_posix(),
                )
        return jar

    def _pair(self, root: Path) -> tuple[Path, Path]:
        old = self._jar(
            root, "original",
            "public static boolean existing;"
            "public static Shade first, second;"
            "public static Theme third;"
            "public static final Special important=Special.ONE;"
            "public static int unrelated;"
            "public enum Shade { RED, BLUE }"
            "public enum Theme { DAY, NIGHT }"
            "public enum Special { ONE, TWO }",
        )
        new = self._jar(
            root, "candidate",
            "public static boolean existing;",
        )
        return old, new

    def _replay(self, original: Path, candidate: Path, output: Path,
                *, original_pin=None, candidate_pin=None) -> dict:
        return build_enum_reference_scaffold(
            original, candidate, output,
            original_sha256=original_pin or _sha(original),
            candidate_sha256=candidate_pin or _sha(candidate),
            class_entry="p/Owner.class",
        )

    def test_stage_only_mutable_original_enum_references(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            out = root / "private-output"
            manifest = self._replay(original, candidate, out)
            self.assertEqual(manifest["selected_field_declaration_count"], 3)
            self.assertEqual(manifest["distinct_type_shell_count"], 2)
            self.assertEqual(
                manifest["original_final_nested_enum_fields_excluded"], 1,
            )
            self.assertEqual(
                manifest["unresolved_missing_fields_outside_this_scope"], 2,
            )
            self.assertFalse(manifest["owner_source_equivalence_certified"])
            self.assertFalse(
                manifest["original_enum_source_equivalence_certified"]
            )
            self.assertFalse(
                manifest["canonical_field_or_class_identity_accepted"]
            )
            self.assertEqual(manifest["enum_constant_values_reconstructed"], 0)
            self.assertEqual(manifest["enum_method_bodies_reconstructed"], 0)
            fields = (out / "owner-enum-reference-fields.fragment.txt").read_text()
            shells = (out / "unverified-enum-type-shells.fragment.txt").read_text()
            self.assertIn("public static Shade first;", fields)
            self.assertIn("public static Shade second;", fields)
            self.assertIn("public static Theme third;", fields)
            self.assertNotIn("important;", fields)
            self.assertNotIn("unrelated;", fields)
            self.assertIn("public enum Shade { ; }", shells)
            self.assertIn("public enum Theme { ; }", shells)
            self.assertNotIn("public enum Special", shells)
            self.assertIn("NOT recovered original enum source", shells)
            self.assertNotIn("RED", shells)
            self.assertNotIn("NIGHT", shells)
            self.assertNotIn("first", json.dumps(manifest))
            self.assertNotIn("Owner", json.dumps(manifest))
            self.assertEqual(
                _sha(out / "owner-enum-reference-fields.fragment.txt"),
                manifest["private_field_fragment_sha256"],
            )
            self.assertEqual(
                json.loads(
                    (out / "aggregate-private-source-bridge.json").read_text()
                ),
                manifest,
            )

    def test_source_only_bridge_compiles_exact_owner_field_descriptors(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            output = root / "bridge"
            self._replay(original, candidate, output)
            rebuilt = self._jar(
                root, "recompiled-bridge",
                "public static boolean existing;"
                + (output / "owner-enum-reference-fields.fragment.txt").read_text()
                + (output / "unverified-enum-type-shells.fragment.txt").read_text(),
            )
            original_profile = profile_jar_class(original, "p/Owner.class")
            rebuilt_profile = profile_jar_class(rebuilt, "p/Owner.class")
            o = {(f["name"], f["descriptor"]): f for f in original_profile["fields"]}
            r = {(f["name"], f["descriptor"]): f for f in rebuilt_profile["fields"]}
            self.assertEqual(len(r), 4)
            self.assertEqual(
                sorted(
                    (f["descriptor"], f["access"], f["signature"])
                    for f in r.values()
                ),
                sorted(
                    (o[k]["descriptor"], o[k]["access"], o[k]["signature"])
                    for k in r
                ),
            )
            for name in ("p/Owner$Shade", "p/Owner$Theme"):
                self.assertEqual(
                    profile_jar_class(rebuilt, name + ".class")["internal_name"],
                    name,
                )
            self.assertFalse(
                any(f["name"] == "important" for f in rebuilt_profile["fields"])
            )

    def test_deterministic_and_no_existing_output_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            first = self._replay(original, candidate, root / "one")
            second = self._replay(original, candidate, root / "two")
            self.assertEqual(first, second)
            marker = root / "one" / "KEEP.txt"
            marker.write_text("DO NOT DELETE", encoding="utf-8")
            with self.assertRaisesRegex(
                EnumReferenceScaffoldError, "OUTPUT_ALREADY_EXISTS",
            ):
                self._replay(original, candidate, root / "one")
            self.assertEqual(marker.read_text(), "DO NOT DELETE")

    def test_wrong_original_sha_refused_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            out = root / "not-created"
            with self.assertRaisesRegex(
                EnumReferenceScaffoldError, "WHOLE_JAR_SHA256_MISMATCH",
            ):
                self._replay(
                    original, candidate, out,
                    original_pin="0" * 64,
                )
            self.assertFalse(out.exists())

    def test_wrong_candidate_sha_refused_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            out = root / "not-created"
            with self.assertRaisesRegex(
                EnumReferenceScaffoldError, "WHOLE_JAR_SHA256_MISMATCH",
            ):
                self._replay(
                    original, candidate, out,
                    candidate_pin="0" * 64,
                )
            self.assertFalse(out.exists())

    def test_missing_original_enum_dependency_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            damaged = root / "missing-enum.jar"
            with ZipFile(original) as original_archive, ZipFile(
                damaged, "w"
            ) as archive:
                for item in original_archive.infolist():
                    if item.filename != "p/Owner$Shade.class":
                        archive.writestr(
                            item.filename,
                            original_archive.read(item.filename),
                        )
            with self.assertRaisesRegex(
                EnumReferenceScaffoldError,
                "DEPENDENCY_ENUM_CLASS_MISSING_OR_DUPLICATE",
            ):
                self._replay(damaged, candidate, root / "nothing")

    def test_wrong_dependency_type_is_not_assumed_enum(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            real = profile_jar_class(original, "p/Owner.class")
            baseline = profile_jar_class(candidate, "p/Owner.class")
            shade = profile_jar_class(original, "p/Owner$Shade.class")
            theme = profile_jar_class(original, "p/Owner$Theme.class")
            shade["super_name"] = "java/lang/Object"
            with self.assertRaisesRegex(
                EnumReferenceScaffoldError,
                "ORIGINAL_DEPENDENCY_IS_NOT_EXACT_ENUM_CLASS",
            ):
                plan_nested_enum_field_references(
                    real, baseline,
                    {"p/Owner$Shade": shade, "p/Owner$Theme": theme},
                    expected_missing_fields=5,
                )

    def test_final_field_without_initializer_never_staged_as_mutable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            report = self._replay(original, candidate, root / "private")
            self.assertEqual(
                report["original_final_nested_enum_fields_excluded"], 1
            )
            self.assertEqual(report["selected_field_declaration_count"], 3)
            self.assertFalse(report["initializer_values_reconstructed"])


if __name__ == "__main__":
    unittest.main()

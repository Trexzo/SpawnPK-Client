from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_remap_proof import (
    prove_dependency_remaps,
)


class DependencyRemapProofTests(unittest.TestCase):
    def _compile_jar(
        self,
        root: Path,
        name: str,
        sources: dict[str, str],
    ) -> Path:
        src = root / (name + "-src")
        classes = root / (name + "-classes")
        src.mkdir()
        classes.mkdir()
        paths: list[str] = []
        for rel, text in sources.items():
            path = src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            paths.append(str(path))
        proc = subprocess.run(
            ["javac", "-d", str(classes), *paths],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise AssertionError("javac fixture failed: " + proc.stderr)
        jar = root / (name + ".jar")
        with zipfile.ZipFile(jar, "w") as archive:
            for class_file in sorted(classes.rglob("*.class")):
                archive.write(
                    class_file,
                    class_file.relative_to(classes).as_posix(),
                )
        return jar

    def _surface(
        self,
        root: Path,
        rows: list[dict[str, object]],
    ) -> Path:
        path = root / "depref.json"
        payload = {
            "schema_version": 1,
            "kind": "project_non_project_reference_surface",
            "reference_surface_id": "DEPREF_TEST",
            "class_references": [],
            "member_references": rows,
        }
        path.write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def _row(
        self,
        kind: str,
        owner: str,
        name: str,
        descriptor: str,
        count: int = 1,
    ) -> dict[str, object]:
        return {
            "kind": kind,
            "owner": owner,
            "name": name,
            "descriptor": descriptor,
            "reference_count": count,
            "source_class_count": 1,
            "source_classes": ["project/Main"],
        }

    def test_same_name_exact_api_surface_allows_code_length_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public int ping(int value) { return value; } "
                        "}"
                    )
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public int ping(int value) { "
                        "int copy = value; return copy; "
                        "} "
                        "}"
                    )
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "dep/Api",
                        "ping",
                        "(I)I",
                        3,
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(row["status"], "accepted_identity")
            self.assertEqual(row["new_owner"], "dep/Api")
            self.assertEqual(row["new_name"], "ping")
            class_row = report["referenced_class_mappings"][0]
            self.assertEqual(
                class_row["strategy"],
                "identity_api_surface",
            )
            self.assertEqual(
                report["summary"]["identity_api_surface_count"],
                1,
            )

    def test_same_name_api_surface_drift_does_not_accept_changed_api(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public int ping(int value) { return value; } "
                        "}"
                    )
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public long ping(long value) { return value; } "
                        "}"
                    )
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "dep/Api",
                        "ping",
                        "(I)I",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(
                row["status"],
                "bundled_unresolved_class",
            )

    def test_package_authority_api_shape_maps_exact_and_unique_descriptor_members(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "old/pkg/s1.java": (
                        "package old.pkg; public class s1 { "
                        "public int one() { return 1; } }"
                    ),
                    "old/pkg/s2.java": (
                        "package old.pkg; public class s2 { "
                        "public long two() { return 2L; } }"
                    ),
                    "old/pkg/s3.java": (
                        "package old.pkg; public class s3 { "
                        "public double three() { return 3.0; } }"
                    ),
                    "old/pkg/x.java": (
                        "package old.pkg; public class x { "
                        "public String a(String value) { return value; } }"
                    ),
                    "old/pkg/y.java": (
                        "package old.pkg; public class y { "
                        "public int ping(int value) { return value; } }"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "target/pkg/SupportOne.java": (
                        "package target.pkg; public class SupportOne { "
                        "public int one() { return 1; } }"
                    ),
                    "target/pkg/SupportTwo.java": (
                        "package target.pkg; public class SupportTwo { "
                        "public long two() { return 2L; } }"
                    ),
                    "target/pkg/SupportThree.java": (
                        "package target.pkg; public class SupportThree { "
                        "public double three() { return 3.0; } }"
                    ),
                    "target/pkg/Api.java": (
                        "package target.pkg; public class Api { "
                        "public String real(String value) { "
                        "String copy = value; return copy; } }"
                    ),
                    "target/pkg/ExactApi.java": (
                        "package target.pkg; public class ExactApi { "
                        "public int ping(int value) { "
                        "int copy = value; return copy; } }"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "old/pkg/x",
                        "a",
                        "(Ljava/lang/String;)Ljava/lang/String;",
                        4,
                    ),
                    self._row(
                        "method",
                        "old/pkg/y",
                        "ping",
                        "(I)I",
                        2,
                    ),
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            mapped = {
                row["old_owner"]: row
                for row in report["member_results"]
            }
            self.assertEqual(
                mapped["old/pkg/x"]["status"],
                "accepted_remap",
            )
            self.assertEqual(
                mapped["old/pkg/x"]["new_owner"],
                "target/pkg/Api",
            )
            self.assertEqual(
                mapped["old/pkg/x"]["new_name"],
                "real",
            )
            self.assertIn(
                "package_api_shape_translated_unique_descriptor_member",
                mapped["old/pkg/x"]["proof"][
                    "member_transfer_strategies"
                ],
            )
            self.assertEqual(
                mapped["old/pkg/y"]["status"],
                "accepted_remap",
            )
            self.assertEqual(
                mapped["old/pkg/y"]["new_owner"],
                "target/pkg/ExactApi",
            )
            self.assertEqual(
                mapped["old/pkg/y"]["new_name"],
                "ping",
            )
            self.assertIn(
                "package_api_shape_translated_exact_member",
                mapped["old/pkg/y"]["proof"][
                    "member_transfer_strategies"
                ],
            )
            class_rows = {
                row["old_name"]: row
                for row in report["referenced_class_mappings"]
            }
            self.assertEqual(
                class_rows["old/pkg/x"]["strategy"],
                "package_api_shape",
            )
            self.assertEqual(
                class_rows["old/pkg/x"]["package_authority"][
                    "support_count"
                ],
                3,
            )
            self.assertEqual(
                report["summary"]["package_api_shape_count"],
                2,
            )

    def test_package_api_shape_ambiguity_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "old/pkg/s1.java": (
                        "package old.pkg; public class s1 { "
                        "public int one() { return 1; } }"
                    ),
                    "old/pkg/s2.java": (
                        "package old.pkg; public class s2 { "
                        "public long two() { return 2L; } }"
                    ),
                    "old/pkg/s3.java": (
                        "package old.pkg; public class s3 { "
                        "public double three() { return 3.0; } }"
                    ),
                    "old/pkg/x.java": (
                        "package old.pkg; public class x { "
                        "public String a(String value) { return value; } }"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "target/pkg/SupportOne.java": (
                        "package target.pkg; public class SupportOne { "
                        "public int one() { return 1; } }"
                    ),
                    "target/pkg/SupportTwo.java": (
                        "package target.pkg; public class SupportTwo { "
                        "public long two() { return 2L; } }"
                    ),
                    "target/pkg/SupportThree.java": (
                        "package target.pkg; public class SupportThree { "
                        "public double three() { return 3.0; } }"
                    ),
                    "target/pkg/ApiOne.java": (
                        "package target.pkg; public class ApiOne { "
                        "public String realOne(String value) { "
                        "String copy = value; return copy; } }"
                    ),
                    "target/pkg/ApiTwo.java": (
                        "package target.pkg; public class ApiTwo { "
                        "public String realTwo(String value) { "
                        "String copy = value; return copy; } }"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "old/pkg/x",
                        "a",
                        "(Ljava/lang/String;)Ljava/lang/String;",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(
                row["status"],
                "bundled_unresolved_class",
            )
            self.assertEqual(
                report["summary"]["package_api_shape_count"],
                0,
            )

    def test_package_api_topology_maps_when_full_method_shape_drifted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "old/pkg/s1.java": (
                        "package old.pkg; public class s1 { "
                        "public int one() { return 1; } }"
                    ),
                    "old/pkg/s2.java": (
                        "package old.pkg; public class s2 { "
                        "public long two() { return 2L; } }"
                    ),
                    "old/pkg/s3.java": (
                        "package old.pkg; public class s3 { "
                        "public double three() { return 3.0; } }"
                    ),
                    "old/pkg/x.java": (
                        "package old.pkg; public class x { "
                        "public int marker; "
                        "public int a(int value) { return value; } "
                        "public Object helper(int value) { return null; } "
                        "}"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "target/pkg/SupportOne.java": (
                        "package target.pkg; public class SupportOne { "
                        "public int one() { return 1; } }"
                    ),
                    "target/pkg/SupportTwo.java": (
                        "package target.pkg; public class SupportTwo { "
                        "public long two() { return 2L; } }"
                    ),
                    "target/pkg/SupportThree.java": (
                        "package target.pkg; public class SupportThree { "
                        "public double three() { return 3.0; } }"
                    ),
                    "target/pkg/Api.java": (
                        "package target.pkg; public class Api { "
                        "public int marker; "
                        "public int real(int value) { return value; } "
                        "public Object helper(long value) { return null; } "
                        "}"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "old/pkg/x",
                        "a",
                        "(I)I",
                        4,
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(row["status"], "accepted_remap")
            self.assertEqual(row["new_owner"], "target/pkg/Api")
            self.assertEqual(row["new_name"], "real")
            self.assertIn(
                "package_api_topology_translated_unique_descriptor_member",
                row["proof"]["member_transfer_strategies"],
            )
            class_row = report["referenced_class_mappings"][0]
            self.assertEqual(
                class_row["strategy"],
                "package_api_topology",
            )
            self.assertEqual(
                report["summary"]["package_api_topology_count"],
                1,
            )

    def test_package_api_topology_known_super_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "old/pkg/s1.java": (
                        "package old.pkg; public class s1 { "
                        "public int one() { return 1; } }"
                    ),
                    "old/pkg/s2.java": (
                        "package old.pkg; public class s2 { "
                        "public long two() { return 2L; } }"
                    ),
                    "old/pkg/s3.java": (
                        "package old.pkg; public class s3 { "
                        "public double three() { return 3.0; } }"
                    ),
                    "old/pkg/x.java": (
                        "package old.pkg; "
                        "public class x extends java.util.ArrayList<Object> { "
                        "public Object helper(int value) { return null; } "
                        "}"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "target/pkg/SupportOne.java": (
                        "package target.pkg; public class SupportOne { "
                        "public int one() { return 1; } }"
                    ),
                    "target/pkg/SupportTwo.java": (
                        "package target.pkg; public class SupportTwo { "
                        "public long two() { return 2L; } }"
                    ),
                    "target/pkg/SupportThree.java": (
                        "package target.pkg; public class SupportThree { "
                        "public double three() { return 3.0; } }"
                    ),
                    "target/pkg/Api.java": (
                        "package target.pkg; public class Api { "
                        "public Object helper(long value) { return null; } "
                        "}"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "old/pkg/x",
                        "helper",
                        "(I)Ljava/lang/Object;",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(
                row["status"],
                "bundled_unresolved_class",
            )
            self.assertEqual(
                report["summary"]["package_api_topology_count"],
                0,
            )

    def test_package_mapping_translates_self_return_descriptor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "old/pkg/s1.java": (
                        "package old.pkg; public class s1 { "
                        "public int one() { return 1; } }"
                    ),
                    "old/pkg/s2.java": (
                        "package old.pkg; public class s2 { "
                        "public long two() { return 2L; } }"
                    ),
                    "old/pkg/s3.java": (
                        "package old.pkg; public class s3 { "
                        "public double three() { return 3.0; } }"
                    ),
                    "old/pkg/x.java": (
                        "package old.pkg; public class x { "
                        "public x a() { return this; } "
                        "public Object helper(int value) { return null; } "
                        "}"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "target/pkg/SupportOne.java": (
                        "package target.pkg; public class SupportOne { "
                        "public int one() { return 1; } }"
                    ),
                    "target/pkg/SupportTwo.java": (
                        "package target.pkg; public class SupportTwo { "
                        "public long two() { return 2L; } }"
                    ),
                    "target/pkg/SupportThree.java": (
                        "package target.pkg; public class SupportThree { "
                        "public double three() { return 3.0; } }"
                    ),
                    "target/pkg/Api.java": (
                        "package target.pkg; public class Api { "
                        "public Api create() { return this; } "
                        "public Object helper(long value) { return null; } "
                        "}"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "old/pkg/x",
                        "a",
                        "()Lold/pkg/x;",
                        3,
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(row["status"], "accepted_remap")
            self.assertEqual(row["new_owner"], "target/pkg/Api")
            self.assertEqual(row["new_name"], "create")
            self.assertEqual(
                row["new_descriptor"],
                "()Ltarget/pkg/Api;",
            )
            self.assertIn(
                "package_api_topology_translated_unique_descriptor_member",
                row["proof"]["member_transfer_strategies"],
            )

    def test_package_mapping_accepts_exact_translated_constructor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "old/pkg/s1.java": (
                        "package old.pkg; public class s1 { "
                        "public int one() { return 1; } }"
                    ),
                    "old/pkg/s2.java": (
                        "package old.pkg; public class s2 { "
                        "public long two() { return 2L; } }"
                    ),
                    "old/pkg/s3.java": (
                        "package old.pkg; public class s3 { "
                        "public double three() { return 3.0; } }"
                    ),
                    "old/pkg/p.java": (
                        "package old.pkg; public class p { public int value; }"
                    ),
                    "old/pkg/x.java": (
                        "package old.pkg; public class x { "
                        "public x(old.pkg.p value) {} }"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "target/pkg/SupportOne.java": (
                        "package target.pkg; public class SupportOne { "
                        "public int one() { return 1; } }"
                    ),
                    "target/pkg/SupportTwo.java": (
                        "package target.pkg; public class SupportTwo { "
                        "public long two() { return 2L; } }"
                    ),
                    "target/pkg/SupportThree.java": (
                        "package target.pkg; public class SupportThree { "
                        "public double three() { return 3.0; } }"
                    ),
                    "target/pkg/Param.java": (
                        "package target.pkg; public class Param { public int value; }"
                    ),
                    "target/pkg/Api.java": (
                        "package target.pkg; public class Api { "
                        "public Api(target.pkg.Param value) { "
                        "Object copy = value; } }"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "old/pkg/x",
                        "<init>",
                        "(Lold/pkg/p;)V",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(row["status"], "accepted_remap")
            self.assertEqual(row["new_name"], "<init>")
            self.assertEqual(
                row["new_descriptor"],
                "(Ltarget/pkg/Param;)V",
            )
            self.assertTrue(
                any(
                    strategy.endswith("_translated_constructor")
                    for strategy in row["proof"][
                        "member_transfer_strategies"
                    ]
                )
            )

    def test_package_mapping_unmapped_descriptor_type_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "old/pkg/s1.java": (
                        "package old.pkg; public class s1 { "
                        "public int one() { return 1; } }"
                    ),
                    "old/pkg/s2.java": (
                        "package old.pkg; public class s2 { "
                        "public long two() { return 2L; } }"
                    ),
                    "old/pkg/s3.java": (
                        "package old.pkg; public class s3 { "
                        "public double three() { return 3.0; } }"
                    ),
                    "old/pkg/u.java": "package old.pkg; public class u {}",
                    "old/pkg/x.java": (
                        "package old.pkg; public class x { "
                        "public old.pkg.u a() { return null; } }"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "target/pkg/SupportOne.java": (
                        "package target.pkg; public class SupportOne { "
                        "public int one() { return 1; } }"
                    ),
                    "target/pkg/SupportTwo.java": (
                        "package target.pkg; public class SupportTwo { "
                        "public long two() { return 2L; } }"
                    ),
                    "target/pkg/SupportThree.java": (
                        "package target.pkg; public class SupportThree { "
                        "public double three() { return 3.0; } }"
                    ),
                    "target/pkg/Api.java": (
                        "package target.pkg; public class Api { "
                        "public Object real() { "
                        "Object copy = null; return copy; } }"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "old/pkg/x",
                        "a",
                        "()Lold/pkg/u;",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(
                row["status"],
                "bundled_member_unresolved",
            )

    def test_unique_structural_class_and_member_position_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "dep/a.java": (
                        "package dep; public class a { "
                        "public static int x = 1; "
                        "public String a(int v) { return String.valueOf(v); } "
                        "}"
                    )
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public static int VALUE = 1; "
                        "public String ping(int v) { return String.valueOf(v); } "
                        "}"
                    )
                },
            )
            surface = self._surface(
                root,
                [
                    self._row("field", "dep/a", "x", "I", 2),
                    self._row(
                        "method",
                        "dep/a",
                        "a",
                        "(I)Ljava/lang/String;",
                        3,
                    ),
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            self.assertEqual(
                report["summary"]["member_status_counts"],
                {"accepted_remap": 2},
            )
            mapped = {
                (row["kind"], row["old_name"]): row
                for row in report["member_results"]
            }
            self.assertEqual(mapped[("field", "x")]["new_owner"], "dep/Api")
            self.assertEqual(mapped[("field", "x")]["new_name"], "VALUE")
            self.assertEqual(mapped[("method", "a")]["new_name"], "ping")
            self.assertEqual(
                report["summary"]["weighted_member_status_counts"],
                {"accepted_remap": 5},
            )

    def test_inherited_member_transfer_uses_mapped_declaring_class(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "dep/b.java": (
                        "package dep; public class b { "
                        "public String a(int v) { return String.valueOf(v); } "
                        "}"
                    ),
                    "dep/a.java": "package dep; public class a extends b {}",
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/BaseApi.java": (
                        "package dep; public class BaseApi { "
                        "public String ping(int v) { return String.valueOf(v); } "
                        "}"
                    ),
                    "dep/Api.java": (
                        "package dep; public class Api extends BaseApi {}"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "dep/a",
                        "a",
                        "(I)Ljava/lang/String;",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(row["status"], "accepted_remap")
            self.assertEqual(row["new_owner"], "dep/Api")
            self.assertEqual(row["new_name"], "ping")
            self.assertEqual(
                row["proof"]["mapped_declaration_count"],
                1,
            )

    def test_multiple_interface_paths_accept_only_when_they_converge(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "dep/b.java": (
                        "package dep; public interface b { "
                        "void a(); int leftMarker(); "
                        "}"
                    ),
                    "dep/c.java": (
                        "package dep; public interface c { "
                        "void a(); long rightMarker(); "
                        "}"
                    ),
                    "dep/a.java": (
                        "package dep; public interface a extends b, c {}"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/BaseOne.java": (
                        "package dep; public interface BaseOne { "
                        "void ping(); int leftMarker(); "
                        "}"
                    ),
                    "dep/BaseTwo.java": (
                        "package dep; public interface BaseTwo { "
                        "void ping(); long rightMarker(); "
                        "}"
                    ),
                    "dep/Api.java": (
                        "package dep; public interface Api "
                        "extends BaseOne, BaseTwo {}"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "interface_method",
                        "dep/a",
                        "a",
                        "()V",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(row["status"], "accepted_remap")
            self.assertEqual(row["new_owner"], "dep/Api")
            self.assertEqual(row["new_name"], "ping")
            self.assertEqual(
                row["proof"]["mapped_declaration_count"],
                2,
            )

    def test_multiple_interface_paths_fail_when_targets_diverge(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "dep/b.java": (
                        "package dep; public interface b { "
                        "void a(); int leftMarker(); "
                        "}"
                    ),
                    "dep/c.java": (
                        "package dep; public interface c { "
                        "void a(); long rightMarker(); "
                        "}"
                    ),
                    "dep/a.java": (
                        "package dep; public interface a extends b, c {}"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/BaseOne.java": (
                        "package dep; public interface BaseOne { "
                        "void ping(); int leftMarker(); "
                        "}"
                    ),
                    "dep/BaseTwo.java": (
                        "package dep; public interface BaseTwo { "
                        "void pong(); long rightMarker(); "
                        "}"
                    ),
                    "dep/Api.java": (
                        "package dep; public interface Api "
                        "extends BaseOne, BaseTwo {}"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "interface_method",
                        "dep/a",
                        "a",
                        "()V",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(
                row["status"],
                "bundled_member_ambiguous",
            )
            self.assertEqual(row["new_name"], None)

    def test_constructor_uses_mapped_descriptor_not_position_guess(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "dep/b.java": (
                        "package dep; public class b { public long marker; }"
                    ),
                    "dep/a.java": (
                        "package dep; public class a { "
                        "public int marker; "
                        "public a(dep.b value) {} "
                        "}"
                    ),
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/Param.java": (
                        "package dep; public class Param { public long marker; }"
                    ),
                    "dep/Api.java": (
                        "package dep; public class Api { "
                        "public int marker; "
                        "public Api(dep.Param value) {} "
                        "}"
                    ),
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "dep/a",
                        "<init>",
                        "(Ldep/b;)V",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(row["status"], "accepted_remap")
            self.assertEqual(row["new_owner"], "dep/Api")
            self.assertEqual(row["new_name"], "<init>")
            self.assertEqual(
                row["new_descriptor"],
                "(Ldep/Param;)V",
            )
            self.assertIn(
                "constructor_mapped_descriptor",
                row["proof"]["member_transfer_strategies"],
            )

    def test_non_bundled_runtime_superclass_member_is_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {
                    "dep/a.java": (
                        "package dep; import java.io.*; "
                        "public class a extends InputStream { "
                        "public int read() { return -1; } "
                        "}"
                    )
                },
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/Api.java": (
                        "package dep; import java.io.*; "
                        "public class Api extends InputStream { "
                        "public int read() { return -1; } "
                        "}"
                    )
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "dep/a",
                        "readAllBytes",
                        "()[B",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(
                row["status"],
                "external_hierarchy_member",
            )
            self.assertIn(
                "java/io/InputStream",
                row["proof"]["external_hierarchy_boundaries"],
            )

    def test_non_bundled_platform_owner_is_separate_not_missing_dependency(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {"dep/a.java": "package dep; public class a {}"},
            )
            official = self._compile_jar(
                root,
                "official",
                {"dep/Api.java": "package dep; public class Api {}"},
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "java/lang/String",
                        "length",
                        "()I",
                        4,
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(row["status"], "platform_runtime")
            self.assertEqual(
                report["summary"]["weighted_member_status_counts"],
                {"platform_runtime": 4},
            )

    def test_non_unique_structural_class_match_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bundled = self._compile_jar(
                root,
                "bundled",
                {"dep/a.java": "package dep; public class a {}"},
            )
            official = self._compile_jar(
                root,
                "official",
                {
                    "dep/ApiOne.java": "package dep; public class ApiOne {}",
                    "dep/ApiTwo.java": "package dep; public class ApiTwo {}",
                },
            )
            surface = self._surface(
                root,
                [
                    self._row(
                        "method",
                        "dep/a",
                        "toString",
                        "()Ljava/lang/String;",
                    )
                ],
            )

            report = prove_dependency_remaps(
                surface,
                bundled,
                [official],
                java_release=9,
                project_prefixes=("project/",),
            )

            row = report["member_results"][0]
            self.assertEqual(
                row["status"],
                "bundled_unresolved_class",
            )
            self.assertEqual(row["new_owner"], None)


if __name__ == "__main__":
    unittest.main()

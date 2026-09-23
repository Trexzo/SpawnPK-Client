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
                        "void a(); int marker(); "
                        "}"
                    ),
                    "dep/c.java": (
                        "package dep; public interface c { "
                        "void a(); long marker(); "
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
                        "void ping(); int marker(); "
                        "}"
                    ),
                    "dep/BaseTwo.java": (
                        "package dep; public interface BaseTwo { "
                        "void ping(); long marker(); "
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
                        "void a(); int marker(); "
                        "}"
                    ),
                    "dep/c.java": (
                        "package dep; public interface c { "
                        "void a(); long marker(); "
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
                        "void ping(); int marker(); "
                        "}"
                    ),
                    "dep/BaseTwo.java": (
                        "package dep; public interface BaseTwo { "
                        "void pong(); long marker(); "
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

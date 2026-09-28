from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.dependency_reference_surface import (
    scan_project_reference_surface,
)
from spk_recovery.dependency_reverse_transport_apply import (
    DependencyReverseTransportApplyError,
    apply_dependency_reverse_transport,
)


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("java"),
    "JDK required",
)
class DependencyReverseTransportApplyTests(unittest.TestCase):
    def _compile(
        self,
        root: Path,
        sources: dict[str, str],
        *,
        classpath: Path | None = None,
    ) -> Path:
        src = root / "src"
        out = root / "classes"
        src.mkdir(parents=True)
        out.mkdir()
        paths = []
        for rel, text in sources.items():
            path = src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            paths.append(path)

        cmd = [
            "javac",
            "--release",
            "9",
            "-d",
            str(out),
        ]
        if classpath is not None:
            cmd.extend(["-classpath", str(classpath)])
        cmd.extend(str(path) for path in paths)
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr,
        )
        return out

    def _jar(self, classes: Path, out: Path) -> Path:
        with zipfile.ZipFile(
            out,
            "w",
            zipfile.ZIP_STORED,
        ) as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(
                    path,
                    path.relative_to(classes).as_posix(),
                )
        return out

    def _fixture(self, root: Path):
        official_classes = self._compile(
            root / "official",
            {
                "official/T.java": (
                    "package official; public class T {}\n"
                ),
                "official/I.java": (
                    "package official; "
                    "public interface I { void call(T t); }\n"
                ),
                "official/Api.java": (
                    "package official; "
                    "public class Api { "
                    "public T value; "
                    "public void run(T t) { value = t; } "
                    "}\n"
                ),
            },
        )
        official_jar = self._jar(
            official_classes,
            root / "official.jar",
        )

        bundled_classes = self._compile(
            root / "bundled",
            {
                "bundled/T.java": (
                    "package bundled; public class T {}\n"
                ),
                "bundled/I.java": (
                    "package bundled; "
                    "public interface I { void z(T t); }\n"
                ),
                "bundled/Api.java": (
                    "package bundled; "
                    "public class Api { "
                    "public T b; "
                    "public void x(T t) { b = t; } "
                    "}\n"
                ),
            },
        )
        bundled_jar = self._jar(
            bundled_classes,
            root / "bundled.jar",
        )

        official_project = self._compile(
            root / "official-project",
            {
                "app/Use.java": (
                    "package app; "
                    "public class Use { "
                    "public static official.T use("
                    "official.Api a, official.I i, official.T t) { "
                    "a.value = t; a.run(t); i.call(t); "
                    "return a.value; "
                    "} "
                    "public static official.Api make() { "
                    "return new official.Api(); "
                    "} "
                    "}\n"
                ),
            },
            classpath=official_jar,
        )
        official_project_jar = self._jar(
            official_project,
            root / "official-project.jar",
        )

        bundled_project = self._compile(
            root / "bundled-project",
            {
                "app/Use.java": (
                    "package app; "
                    "public class Use { "
                    "public static bundled.T use("
                    "bundled.Api a, bundled.I i, bundled.T t) { "
                    "a.b = t; a.x(t); i.z(t); "
                    "return a.b; "
                    "} "
                    "public static bundled.Api make() { "
                    "return new bundled.Api(); "
                    "} "
                    "}\n"
                ),
            },
            classpath=bundled_jar,
        )
        bundled_project_jar = self._jar(
            bundled_project,
            root / "bundled-project.jar",
        )

        plan = {
            "schema_version": 1,
            "kind": "dependency_reverse_compile_transport_plan",
            "reverse_plan_id": "DEPREVERSE_" + "A" * 20,
            "bundled_jar_sha256": "1" * 64,
            "summary": {
                "ready_for_bytecode_restore": True,
                "blocker_count": 0,
            },
            "blockers": [],
            "class_reverse": [
                {
                    "class_reverse_id": "C1",
                    "official_owner": "official/Api",
                    "bundled_owner": "bundled/Api",
                },
                {
                    "class_reverse_id": "C2",
                    "official_owner": "official/I",
                    "bundled_owner": "bundled/I",
                },
                {
                    "class_reverse_id": "C3",
                    "official_owner": "official/T",
                    "bundled_owner": "bundled/T",
                },
            ],
            "member_reverse": [
                {
                    "member_reverse_id": "M1",
                    "reference_kind": "field",
                    "transport_kind": "field",
                    "official_owner": "official/Api",
                    "official_name": "value",
                    "official_descriptor": "Lofficial/T;",
                    "bundled_owner": "bundled/Api",
                    "bundled_name": "b",
                    "bundled_descriptor": "Lbundled/T;",
                },
                {
                    "member_reverse_id": "M2",
                    "reference_kind": "method",
                    "transport_kind": "method",
                    "official_owner": "official/Api",
                    "official_name": "run",
                    "official_descriptor": "(Lofficial/T;)V",
                    "bundled_owner": "bundled/Api",
                    "bundled_name": "x",
                    "bundled_descriptor": "(Lbundled/T;)V",
                },
                {
                    "member_reverse_id": "M3",
                    "reference_kind": "interface_method",
                    "transport_kind": "method",
                    "official_owner": "official/I",
                    "official_name": "call",
                    "official_descriptor": "(Lofficial/T;)V",
                    "bundled_owner": "bundled/I",
                    "bundled_name": "z",
                    "bundled_descriptor": "(Lbundled/T;)V",
                },
            ],
            "identifiers_included": True,
        }
        plan_path = root / "reverse-plan.json"
        plan_path.write_text(
            json.dumps(plan, indent=2) + "\n",
            encoding="utf-8",
        )
        return (
            plan_path,
            official_project_jar,
            bundled_project_jar,
        )

    def test_reverse_transport_matches_bundled_reference_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, official_project, bundled_project = (
                self._fixture(root)
            )
            restored = root / "restored.jar"

            report = apply_dependency_reverse_transport(
                plan,
                official_project,
                restored,
                project_prefixes=("app/",),
            )

            self.assertTrue(
                report["summary"]["reference_surface_match"]
            )
            self.assertEqual(
                report["summary"][
                    "project_class_identity_changed_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"]["field_mapping_count"],
                1,
            )
            self.assertEqual(
                report["summary"]["method_mapping_count"],
                2,
            )

            restored_surface = scan_project_reference_surface(
                restored,
                project_prefixes=("app/",),
            )
            bundled_surface = scan_project_reference_surface(
                bundled_project,
                project_prefixes=("app/",),
            )

            for key in (
                "project_class_count",
                "class_references",
                "member_references",
            ):
                self.assertEqual(
                    restored_surface[key],
                    bundled_surface[key],
                )

            encoded = json.dumps(restored_surface)
            self.assertNotIn("official/", encoded)
            self.assertIn("bundled/Api", encoded)
            self.assertIn("bundled/I", encoded)

    def test_blocked_plan_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, official_project, _bundled_project = (
                self._fixture(root)
            )
            data = json.loads(plan.read_text(encoding="utf-8"))
            data["summary"]["ready_for_bytecode_restore"] = False
            data["summary"]["blocker_count"] = 1
            data["blockers"] = [{"code": "test"}]
            plan.write_text(
                json.dumps(data) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                DependencyReverseTransportApplyError
            ):
                apply_dependency_reverse_transport(
                    plan,
                    official_project,
                    root / "out.jar",
                    project_prefixes=("app/",),
                )

    def test_descriptor_transport_must_be_explained_by_class_map(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan, official_project, _bundled_project = (
                self._fixture(root)
            )
            data = json.loads(plan.read_text(encoding="utf-8"))
            data["member_reverse"][0][
                "bundled_descriptor"
            ] = "Ljava/lang/String;"
            plan.write_text(
                json.dumps(data) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                DependencyReverseTransportApplyError
            ):
                apply_dependency_reverse_transport(
                    plan,
                    official_project,
                    root / "out.jar",
                    project_prefixes=("app/",),
                )


if __name__ == "__main__":
    unittest.main()

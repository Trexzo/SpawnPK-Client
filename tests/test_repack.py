from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.indexer import index_jar
from spk_recovery.repack import RepackError, remap_jar


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(
    shutil.which("java") and shutil.which("javac"),
    "Java toolchain required",
)
class RepackTest(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, dict, dict]:
        src = root / "src" / "example"
        src.mkdir(parents=True)
        (src / "Svc.java").write_text(
            "package example; public interface Svc { String value(); }",
            encoding="utf-8",
        )
        (src / "B.java").write_text(
            "package example; "
            "public class B implements Svc { "
            "public String value() { return \"ok\"; } }",
            encoding="utf-8",
        )
        (src / "A.java").write_text(
            "package example; "
            "public class A { "
            "public B make() { return new B(); } "
            "public static final String REF = \"example.B\"; "
            "public static void main(String[] x) { System.out.print(new B().value()); } "
            "}",
            encoding="utf-8",
        )

        classes = root / "classes"
        classes.mkdir()
        subprocess.run(
            [
                "javac",
                "-d",
                str(classes),
                str(src / "Svc.java"),
                str(src / "B.java"),
                str(src / "A.java"),
            ],
            check=True,
        )

        jar = root / "fixture.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            z.writestr(
                "META-INF/MANIFEST.MF",
                "Manifest-Version: 1.0\r\nMain-Class: example.A\r\n\r\n",
            )
            z.writestr("META-INF/services/example.Svc", "example.B\n")
            for path in sorted(classes.rglob("*.class")):
                z.write(path, path.relative_to(classes).as_posix())

        index = index_jar(jar)
        rows = []
        for source, target in [
            ("example/A", "recovered/Main"),
            ("example/B", "recovered/Helper"),
        ]:
            path = source + ".class"
            rows.append(
                {
                    "logical_id": "TEST_" + source.rsplit("/", 1)[-1],
                    "source_internal_name": source,
                    "source_entry_path": path,
                    "source_entry_sha256": index["entries"][path]["sha256"],
                    "target_internal_name": target,
                    "target_entry_path": target + ".class",
                    "confidence": 1.0,
                    "provenance": [{"authority": "test", "source": "unit"}],
                }
            )
        plan = {
            "schema_version": 1,
            "kind": "remap_plan",
            "build_id": "test",
            "source_sha256": index["sha256"],
            "class_count": len(rows),
            "classes": rows,
        }
        return jar, index, plan

    def test_refuses_unacknowledged_class_name_string(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, index, plan = self._fixture(root)
            with self.assertRaises(RepackError):
                remap_jar(jar, index, plan, root / "out.jar")

    def test_real_class_remap_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, index, plan = self._fixture(root)
            out1 = root / "one.jar"
            out2 = root / "two.jar"

            first = remap_jar(
                jar,
                index,
                plan,
                out1,
                rewrite_class_name_strings=True,
            )
            second = remap_jar(
                jar,
                index,
                plan,
                out2,
                rewrite_class_name_strings=True,
            )

            self.assertEqual(_sha(out1), _sha(out2))
            self.assertEqual(first["output_sha256"], second["output_sha256"])
            self.assertEqual(first["class_parse_errors"], 0)

            out_index = index_jar(out1)
            self.assertIn("recovered/Main.class", out_index["classes"])
            self.assertIn("recovered/Helper.class", out_index["classes"])
            self.assertNotIn("example/A.class", out_index["entries"])
            self.assertNotIn("example/B.class", out_index["entries"])

            with zipfile.ZipFile(out1) as z:
                manifest = z.read("META-INF/MANIFEST.MF").decode("utf-8")
                service = z.read("META-INF/services/example.Svc").decode("utf-8")
                helper_bytes = z.read("recovered/Main.class")

            self.assertIn("Main-Class: recovered.Main", manifest)
            self.assertEqual(service, "recovered.Helper\n")
            self.assertIn(b"recovered.Helper", helper_bytes)
            self.assertNotIn(b"example.B", helper_bytes)

    def _member_plan(self, index: dict) -> dict:
        members = [
            {
                "member_id": "TEST_FIELD_REF",
                "owner_logical_id": "TEST_A",
                "kind": "field",
                "owner_internal_name": "example/A",
                "source_name": "REF",
                "descriptor": "Ljava/lang/String;",
                "target_name": "helperClassName",
                "confidence": 1.0,
                "provenance": [{"source": "unit"}],
            },
            {
                "member_id": "TEST_METHOD_SVC",
                "owner_logical_id": "TEST_SVC",
                "kind": "method",
                "owner_internal_name": "example/Svc",
                "source_name": "value",
                "descriptor": "()Ljava/lang/String;",
                "target_name": "valueText",
                "confidence": 1.0,
                "provenance": [{"source": "unit"}],
            },
            {
                "member_id": "TEST_METHOD_B",
                "owner_logical_id": "TEST_B",
                "kind": "method",
                "owner_internal_name": "example/B",
                "source_name": "value",
                "descriptor": "()Ljava/lang/String;",
                "target_name": "valueText",
                "confidence": 1.0,
                "provenance": [{"source": "unit"}],
            },
            {
                "member_id": "TEST_METHOD_MAKE",
                "owner_logical_id": "TEST_A",
                "kind": "method",
                "owner_internal_name": "example/A",
                "source_name": "make",
                "descriptor": "()Lexample/B;",
                "target_name": "createHelper",
                "confidence": 1.0,
                "provenance": [{"source": "unit"}],
            },
        ]
        return {
            "schema_version": 1,
            "kind": "member_remap_plan",
            "build_id": "test",
            "source_sha256": index["sha256"],
            "field_count": 1,
            "method_count": 3,
            "member_count": len(members),
            "members": members,
        }

    def test_member_remap_requires_explicit_reflection_risk_ack(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, index, class_plan = self._fixture(root)
            member_plan = self._member_plan(index)
            with self.assertRaises(RepackError):
                remap_jar(
                    jar,
                    index,
                    class_plan,
                    root / "out.jar",
                    member_plan=member_plan,
                    rewrite_class_name_strings=True,
                )

    def test_combined_class_and_member_remap(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar, index, class_plan = self._fixture(root)
            member_plan = self._member_plan(index)
            out1 = root / "members-one.jar"
            out2 = root / "members-two.jar"

            first = remap_jar(
                jar,
                index,
                class_plan,
                out1,
                member_plan=member_plan,
                rewrite_class_name_strings=True,
                allow_member_reflection_risk=True,
            )
            second = remap_jar(
                jar,
                index,
                class_plan,
                out2,
                member_plan=member_plan,
                rewrite_class_name_strings=True,
                allow_member_reflection_risk=True,
            )

            self.assertEqual(_sha(out1), _sha(out2))
            self.assertEqual(first["mapped_fields"], 1)
            self.assertEqual(first["mapped_methods"], 3)
            self.assertEqual(first["class_parse_errors"], 0)

            out_index = index_jar(out1)
            main_cls = out_index["classes"]["recovered/Main.class"]
            helper_cls = out_index["classes"]["recovered/Helper.class"]
            svc_cls = out_index["classes"]["example/Svc.class"]

            self.assertTrue(any(
                f["name"] == "helperClassName"
                for f in main_cls["fields"]
            ))
            self.assertTrue(any(
                m["name"] == "createHelper"
                and m["descriptor"] == "()Lrecovered/Helper;"
                for m in main_cls["methods"]
            ))
            self.assertTrue(any(
                m["name"] == "valueText"
                for m in helper_cls["methods"]
            ))
            self.assertTrue(any(
                m["name"] == "valueText"
                for m in svc_cls["methods"]
            ))

            with zipfile.ZipFile(out1) as z:
                main_bytes = z.read("recovered/Main.class")
                helper_bytes = z.read("recovered/Helper.class")
                svc_bytes = z.read("example/Svc.class")

            self.assertIn(b"createHelper", main_bytes)
            self.assertIn(b"valueText", main_bytes)
            self.assertIn(b"valueText", helper_bytes)
            self.assertIn(b"valueText", svc_bytes)


if __name__ == "__main__":
    unittest.main()

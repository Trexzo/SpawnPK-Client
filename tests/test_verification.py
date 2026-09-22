from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.indexer import index_jar
from spk_recovery.repack import remap_jar
from spk_recovery.verification import verify_transformed_jar


@unittest.skipUnless(
    shutil.which("java") and shutil.which("javac"),
    "Java toolchain required",
)
class VerificationTests(unittest.TestCase):
    def _fixture(self, root: Path):
        src = root / "src" / "example"
        src.mkdir(parents=True)
        (src / "A.java").write_text(
            "package example; public class A { "
            "public int x = 1; "
            "public void a() { System.out.print(x); } "
            "public static void main(String[] v) { new A().a(); } "
            "}",
            encoding="utf-8",
        )
        classes = root / "classes"
        classes.mkdir()
        subprocess.run(
            ["javac", "-d", str(classes), str(src / "A.java")],
            check=True,
        )
        jar = root / "source.jar"
        with zipfile.ZipFile(jar, "w", zipfile.ZIP_STORED) as z:
            z.writestr(
                "META-INF/MANIFEST.MF",
                "Manifest-Version: 1.0\r\n"
                "Main-Class: example.A\r\n\r\n",
            )
            z.write(
                classes / "example" / "A.class",
                "example/A.class",
            )

        index = index_jar(jar)
        class_plan = {
            "schema_version": 1,
            "kind": "remap_plan",
            "build_id": "test",
            "source_sha256": index["sha256"],
            "class_count": 1,
            "classes": [{
                "logical_id": "CLIENT_CLASS_000001",
                "source_internal_name": "example/A",
                "source_entry_path": "example/A.class",
                "source_entry_sha256": index["entries"]["example/A.class"]["sha256"],
                "target_internal_name": "recovered/ReadableA",
                "target_entry_path": "recovered/ReadableA.class",
                "confidence": 1.0,
                "provenance": [{"source": "unit"}],
            }],
        }
        member_plan = {
            "schema_version": 1,
            "kind": "member_remap_plan",
            "build_id": "test",
            "source_sha256": index["sha256"],
            "field_count": 1,
            "method_count": 1,
            "member_count": 2,
            "members": [
                {
                    "member_id": "CLIENT_FIELD_000001",
                    "owner_logical_id": "CLIENT_CLASS_000001",
                    "kind": "field",
                    "owner_internal_name": "example/A",
                    "source_name": "x",
                    "descriptor": "I",
                    "target_name": "value",
                    "confidence": 1.0,
                    "provenance": [{"source": "unit"}],
                },
                {
                    "member_id": "CLIENT_METHOD_000001",
                    "owner_logical_id": "CLIENT_CLASS_000001",
                    "kind": "method",
                    "owner_internal_name": "example/A",
                    "source_name": "a",
                    "descriptor": "()V",
                    "target_name": "runTask",
                    "confidence": 1.0,
                    "provenance": [{"source": "unit"}],
                },
            ],
        }
        return jar, index, class_plan, member_plan

    def test_verifies_real_transformed_archive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, index, class_plan, member_plan = self._fixture(root)
            output = root / "out.jar"
            remap_jar(
                source,
                index,
                class_plan,
                output,
                member_plan=member_plan,
                allow_member_reflection_risk=True,
            )
            report = verify_transformed_jar(
                index,
                output,
                class_plan=class_plan,
                member_plan=member_plan,
            )
            self.assertTrue(report["pass"], report["issues"])
            self.assertEqual(report["summary"]["mapped_class_checks"], 1)
            self.assertEqual(report["summary"]["mapped_member_checks"], 2)
            self.assertTrue(
                report["summary"]["manifest_main_class_present"]
            )

    def test_untransformed_archive_fails_expected_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, index, class_plan, member_plan = self._fixture(root)
            report = verify_transformed_jar(
                index,
                source,
                class_plan=class_plan,
                member_plan=member_plan,
            )
            self.assertFalse(report["pass"])
            self.assertTrue(report["issues"])


if __name__ == "__main__":
    unittest.main()

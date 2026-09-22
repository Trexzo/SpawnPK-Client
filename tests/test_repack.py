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


if __name__ == "__main__":
    unittest.main()

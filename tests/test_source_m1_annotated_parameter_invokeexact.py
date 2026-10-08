from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from spk_recovery.source_normalization import (
    _normalize_methodhandle_invokeexact_result_casts,
    _source_parameter_names,
    _source_parameter_shapes,
    _source_parameters_match_descriptor,
)


EXPRESSION = (
    "MethodHandles.constant(Consumer.class, "
    "(Consumer<Object>)(ignored -> System.out.println(ignored))).invokeExact()"
)
CASTED = "invokeExact = (Consumer<Object>)(" + EXPRESSION + ");"
BROKEN = "invokeExact = " + EXPRESSION + ";"


def source(*, parameter="Object", repeated=False):
    return (
        "package p;\n"
        "import java.lang.invoke.MethodHandles;\n"
        "import java.util.function.Consumer;\n"
        "@interface Nonnull {}\n"
        "public class Worker {\n"
        "  public void register(@Nonnull final " + parameter + " x)"
        " throws Throwable {\n"
        "    Consumer<Object> invokeExact = null;\n"
        "    " + CASTED + "\n"
        + ("    " + CASTED + "\n" if repeated else "")
        + "  }\n"
        "}\n"
    )


@unittest.skipUnless(shutil.which("javac"), "JDK 11-compatible javac required")
class AnnotatedParameterInvokeExactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "src"
        (self.source / "p").mkdir(parents=True)
        self.target = self.source / "p" / "Worker.java"
        self.original = source()
        self.target.write_text(self.original, encoding="utf-8")
        self.jar = self.make_authority()
        self.target.write_text(
            self.original.replace(CASTED, BROKEN), encoding="utf-8"
        )

    def javac(self, out):
        out.mkdir(parents=True, exist_ok=True)
        return subprocess.run(
            [
                "javac", "--release", "11", "-proc:none",
                "-d", str(out), str(self.target),
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def make_authority(self):
        output = self.root / "authority"
        result = self.javac(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        jar = self.root / "readable.jar"
        with zipfile.ZipFile(jar, "w") as bundle:
            for file in output.rglob("*.class"):
                bundle.write(file, file.relative_to(output).as_posix())
        return jar

    def normalize(self):
        with zipfile.ZipFile(self.jar) as authority:
            return _normalize_methodhandle_invokeexact_result_casts(
                source_root=self.source,
                path=self.target,
                readable_zip=authority,
            )

    def test_annotated_production_shape_reconstructs_cast_then_compiles(self):
        broken = self.javac(self.root / "broken")
        self.assertNotEqual(broken.returncode, 0)
        self.assertIn("Object cannot be converted to Consumer<Object>", broken.stderr)

        actions = self.normalize()
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["method_name"], "register")
        self.assertEqual(actions[0]["method_descriptor"], "(Ljava/lang/Object;)V")
        self.assertEqual(actions[0]["replacement_count"], 1)
        self.assertEqual(actions[0]["target_types"], ["Consumer<Object>"])
        self.assertEqual(self.target.read_text(encoding="utf-8"), self.original)
        repaired = self.javac(self.root / "repaired")
        self.assertEqual(repaired.returncode, 0, repaired.stderr)
        self.assertEqual(self.normalize(), [])

    def test_method_parameter_parser_preserves_exact_descriptor_types(self):
        self.assertEqual(
            _source_parameter_shapes("@Nonnull final Object x"),
            [(0, "simple_ref", "Object")],
        )
        self.assertEqual(
            _source_parameter_names("@Nonnull final Object x"),
            ["x"],
        )
        self.assertTrue(
            _source_parameters_match_descriptor(
                "@Nonnull final Object x",
                "(Ljava/lang/Object;)V",
            )
        )
        self.assertFalse(
            _source_parameters_match_descriptor(
                "@Nonnull final Object x",
                "(Ljava/lang/String;)V",
            )
        )
        self.assertIsNone(
            _source_parameter_shapes("@Nonnull(value=true) Object x"),
        )

    def test_source_method_parameter_drift_leaves_cast_untouched(self):
        self.target.write_text(
            self.target.read_text(encoding="utf-8").replace(
                "@Nonnull final Object x",
                "@Nonnull final String x",
            ),
            encoding="utf-8",
        )
        self.assertEqual(self.normalize(), [])
        self.assertIn(BROKEN, self.target.read_text(encoding="utf-8"))

    def test_extra_source_invokeexact_call_without_bytecode_fails_closed(self):
        broken = self.target.read_text(encoding="utf-8")
        self.target.write_text(
            broken.replace(BROKEN, BROKEN + "\n    " + BROKEN),
            encoding="utf-8",
        )
        self.assertEqual(self.normalize(), [])

    def test_annotation_arguments_do_not_silently_change_method_identity(self):
        self.target.write_text(
            self.target.read_text(encoding="utf-8").replace(
                "@Nonnull final Object x",
                "@Nonnull(value=true) final Object x",
            ),
            encoding="utf-8",
        )
        self.assertEqual(self.normalize(), [])


if __name__ == "__main__":
    unittest.main()

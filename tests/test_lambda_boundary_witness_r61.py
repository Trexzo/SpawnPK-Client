"""R61: Java9 exact four-op LambdaMetafactory consumer evidence."""
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
from spk_recovery.lambda_boundary_witness import (
    LambdaBoundaryWitnessError, plan_original_lambda_boundary,
    replay_private_lambda_boundary,
)


@unittest.skipUnless(shutil.which("javac"), "javac needed")
class LambdaBoundaryTests(unittest.TestCase):
    def _jar(self, root: Path, label: str, *, body: str | None = None) -> Path:
        src = root / label / "src" / "p"
        classes = root / label / "classes"
        src.mkdir(parents=True)
        classes.mkdir()
        (src / "Demo.java").write_text(
            "package p; public final class Demo {"
            "public static void register(){"
            + (body if body is not None
               else 'Consumer.accept("original", () -> {});')
            + " } }",
            encoding="utf-8"
        )
        (src / "Consumer.java").write_text(
            "package p; public final class Consumer {"
            "public static void accept(String name, Runnable fn){}"
            "}",
            encoding="utf-8",
        )
        run = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src / "Demo.java"),
             str(src / "Consumer.java")],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as out:
            for cls in ("Demo", "Consumer"):
                out.write(classes / "p" / (cls + ".class"),
                          "p/" + cls + ".class")
        return jar

    @staticmethod
    def _sha(jar: Path) -> str:
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    @staticmethod
    def _profiles(jar: Path) -> tuple[dict, dict]:
        owner = profile_jar_class(jar, "p/Demo.class")
        consumer = profile_jar_class(jar, "p/Consumer.class")
        return owner, {"p/Consumer": consumer}

    def test_exact_lambda_chain_and_no_source_fabrication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "positive")
            report = replay_private_lambda_boundary(
                jar, "p/Demo.class", root / "out", sha256=self._sha(jar)
            )
            self.assertEqual(report["exact_four_instruction_methods"], 1)
            self.assertEqual(report["bootstrap_method"],
                             "metafactory")
            self.assertTrue(report["consumer_method_declared_static"])
            self.assertTrue(report["literal_ldc_string_exactly_proven"])
            self.assertFalse(report["lambda_implementation_body_reconstructed"])
            self.assertFalse(report["java_lambda_expression_source_recovered"])
            self.assertFalse(report["runtime_equivalence_certified"])
            self.assertEqual(len(report["original_four_op_private_witness_sha256"]), 64)
            self.assertTrue((root / "out" / "lambda-boundary.aggregate.json").is_file())
            self.assertNotIn('"original"', json.dumps(report))
            self.assertNotIn("p/Consumer", str(report))

    def test_invalid_consumer_descriptor_is_explicit_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "source")
            owner, dependent = self._profiles(jar)
            method = next(x for x in owner["methods"]
                          if x.get("name") == "register")
            invoke = next(x for x in method["instructions"]
                          if x["opcode"] == "0xb8")
            invoke["descriptor"] = "(Ljava/lang/String;)V"
            with self.assertRaisesRegex(
                LambdaBoundaryWitnessError,
                "FUNCTIONAL_INTERFACE_NOT_SAME_CONSUMER_DESCRIPTOR",
            ):
                plan_original_lambda_boundary(owner, dependent)

    def test_false_lambda_bootstrap_must_not_be_inferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "source")
            owner, dependent = self._profiles(jar)
            entry = next(x for x in owner["bootstrap_methods"]
                         if x["bootstrap_method"]["owner"]
                         == "java/lang/invoke/LambdaMetafactory")
            entry["bootstrap_method"]["name"] = "unsupportedFactory"
            with self.assertRaisesRegex(
                LambdaBoundaryWitnessError,
                "EXACTLY_ONE_ORIGINAL_FOUR_OP_LAMBDA_BOUNDARY_REQUIRED",
            ):
                plan_original_lambda_boundary(owner, dependent)

    def test_wrong_ldc_type_or_method_shape_is_not_a_lambda_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "source")
            owner, dependent = self._profiles(jar)
            method = next(x for x in owner["methods"]
                          if x.get("name") == "register")
            method["instructions"][0]["constant_pool_tag"] = 7
            with self.assertRaisesRegex(
                LambdaBoundaryWitnessError,
                "EXACTLY_ONE_ORIGINAL_FOUR_OP_LAMBDA_BOUNDARY_REQUIRED",
            ):
                plan_original_lambda_boundary(owner, dependent)

    def test_wrong_whole_jar_sha_and_output_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "source")
            out = root / "private"
            with self.assertRaisesRegex(
                LambdaBoundaryWitnessError, "ORIGINAL_JAR_SHA256_MISMATCH",
            ):
                replay_private_lambda_boundary(
                    jar, "p/Demo.class", out, sha256="0" * 64
                )
            self.assertFalse(out.exists())
            out.mkdir()
            marker = out / "KEEP"
            marker.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                LambdaBoundaryWitnessError, "OUTPUT_ALREADY_EXISTS",
            ):
                replay_private_lambda_boundary(
                    jar, "p/Demo.class", out, sha256=self._sha(jar)
                )
            self.assertEqual(marker.read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

"""R55 synthetic Java9 tests for direct external String helper concat source."""
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
from spk_recovery.external_helper_concat_source import (
    ExternalHelperConcatError,
    plan_external_helper_concat,
    private_external_helper_concat_source,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ExternalHelperConcatTests(unittest.TestCase):
    def _jar(self, root: Path, label: str, body: str) -> Path:
        src = root / label / "source" / "p" / "Demo.java"
        helper = src.with_name("Provider.java")
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text("package p; public final class Demo {"
                       + body + "}", encoding="utf-8")
        helper.write_text(
            "package p; public final class Provider {"
            ' public static String base(){return "demo";} }',
            encoding="utf-8",
        )
        run = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src), str(helper)],
            capture_output=True, text=True
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as zipfile:
            for name in ("Demo", "Provider"):
                zipfile.write(classes / "p" / (name + ".class"),
                              "p/" + name + ".class")
        return jar

    @staticmethod
    def _sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def _pair(self, jar):
        return profile_jar_class(jar, "p/Demo.class"), {
            "p/Provider": profile_jar_class(jar, "p/Provider.class")
        }

    def _build(self, jar, root, *, sha=None):
        return private_external_helper_concat_source(
            jar, "p/Demo.class", root,
            original_sha256=sha or self._sha(jar),
        )

    def test_one_no_arg_static_helper_concat_final_matches_exact_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(
                root, "original",
                'public static final String config = "pre" + '
                'Provider.base() + "suffix";',
            )
            out = root / "private"
            result = self._build(jar, out)
            self.assertEqual(result["original_nonconstant_final_string_fields"], 1)
            self.assertEqual(result["exact_external_helper_concat_expression_forms"], 1)
            self.assertEqual(result["other_string_fields_not_handled_by_this_source_form"], 0)
            self.assertFalse(result["external_helper_runtime_semantics_verified"])
            self.assertFalse(result["runtime_equivalence_certified"])
            source = (out / "external-helper-concat.private.txt").read_text()
            self.assertIn('config = "pre" + p.Provider.base() + "suffix";', source)
            self.assertNotIn('"config"', json.dumps(result))
            self.assertNotIn('"suffix"', json.dumps(result))
            self.assertEqual(self._sha(out / "external-helper-concat.private.txt"),
                             result["private_fragment_sha256"])

    def test_nonstatic_producer_method_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                'public static final String config = "pre" + '
                'Provider.base() + "suffix";',
            )
            owner, external = self._pair(jar)
            method = next(
                x for x in external["p/Provider"]["methods"]
                if x["name"] == "base"
            )
            method["access"] &= ~0x0008
            plan = plan_external_helper_concat(owner, external)
            self.assertEqual(plan["exact_external_helper_concat_expression_forms"], 0)

    def test_wrong_concat_bootstrap_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                'public static final String config = "pre" + '
                'Provider.base() + "suffix";',
            )
            owner, ext = self._pair(jar)
            owner["bootstrap_methods"][0]["bootstrap_method"]["owner"] = "wrong/Factory"
            result = plan_external_helper_concat(owner, ext)
            self.assertEqual(result["exact_external_helper_concat_expression_forms"], 0)

    def test_incoming_edge_to_external_helper_store_is_a_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                'public static final String config = "pre" + '
                'Provider.base() + "suffix";',
            )
            owner, ext = self._pair(jar)
            init = next(x for x in owner["methods"] if x["name"] == "<clinit>")
            store = next(x for x in init["instructions"]
                         if x.get("opcode") == "0xb3")
            init["instructions"][0]["branch_target_offset"] = store["offset"]
            result = plan_external_helper_concat(owner, ext)
            self.assertEqual(result["exact_external_helper_concat_expression_forms"], 0)

    def test_duplicate_final_store_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(
                Path(tmp), "original",
                'public static final String config = "pre" + '
                'Provider.base() + "suffix";',
            )
            owner, ext = self._pair(jar)
            init = next(x for x in owner["methods"] if x["name"] == "<clinit>")
            store = next(x for x in init["instructions"]
                         if x.get("opcode") == "0xb3")
            init["instructions"].append(
                {**store, "offset": init["code_length"] + 4}
            )
            with self.assertRaisesRegex(
                ExternalHelperConcatError,
                "ORIGINAL_FINAL_STRING_STORE_MISSING_OR_DUPLICATE",
            ):
                plan_external_helper_concat(owner, ext)

    def test_hash_mismatch_and_output_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(
                root, "original",
                'public static final String config = "pre" + '
                'Provider.base() + "suffix";',
            )
            out = root / "private"
            with self.assertRaisesRegex(
                ExternalHelperConcatError, "ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                self._build(jar, out, sha="0" * 64)
            self.assertFalse(out.exists())
            out.mkdir()
            (out / "KEEP").write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                ExternalHelperConcatError, "OUTPUT_ALREADY_EXISTS"
            ):
                self._build(jar, out)
            self.assertEqual((out / "KEEP").read_text(), "KEEP")


if __name__ == "__main__":
    unittest.main()

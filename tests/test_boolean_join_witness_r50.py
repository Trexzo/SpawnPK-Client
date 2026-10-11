"""R50 synthetic javac coverage for conditional boolean-store witnesses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.boolean_join_witness import (
    BooleanJoinWitnessError,
    build_private_boolean_join_witness,
    plan_conditional_boolean_witnesses,
)
from spk_recovery.bytecode_profile import profile_jar_class


@unittest.skipUnless(shutil.which("javac"), "javac required")
class BooleanJoinWitnessTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, members: str) -> Path:
        src = root / name / "p" / "Demo.java"
        classes = root / name / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class Demo {"
            + members + " public static int get(){return number;} }",
            encoding="utf-8",
        )
        cp = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        jar = root / (name + ".jar")
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "Demo.class", "p/Demo.class")
        return jar

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _pair(self, root: Path):
        original = self._jar(
            root, "original",
            'public static int number=7; '
            'public static boolean flag='
            '(System.getProperty("synthetic.setting")==null ? true:false);',
        )
        candidate = self._jar(
            root, "candidate",
            "public static int number; public static boolean flag;",
        )
        return original, candidate

    def _build(self, original, candidate, output, **options):
        return build_private_boolean_join_witness(
            original, candidate, "p/Demo.class", output,
            original_sha256=options.get("original_sha") or self._sha(original),
            candidate_sha256=options.get("candidate_sha") or self._sha(candidate),
        )

    def test_exact_javac_diamond_proves_two_values_not_predicate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            out = root / "private"
            report = self._build(original, candidate, out)
            self.assertEqual(report["conditional_boolean_stores_examined"], 1)
            self.assertEqual(report["short_diamond_witnesses"], 1)
            self.assertEqual(report["unresolved_conditional_boolean_stores"], 0)
            self.assertTrue(report["conditional_boolean_value_pairs_verified_locally"])
            self.assertFalse(report["original_predicate_source_recovered"])
            self.assertFalse(report["standalone_java_assignment_reconstructed"])
            self.assertFalse(report["runtime_equivalence_certified"])
            self.assertFalse(report["canonical_identifiers_accepted"])
            private = json.loads(
                (out / "original-boolean-join-private.json").read_text()
            )
            self.assertEqual(len(private), 1)
            self.assertEqual(private[0]["field_name"], "flag")
            self.assertEqual(
                {private[0]["fallthrough_value"],
                 private[0]["branch_taken_value"]}, {True, False},
            )
            self.assertFalse(private[0]["condition_source_recovered"])
            aggregate = (out / "boolean-join-aggregate.json").read_text()
            self.assertNotIn('"flag"', aggregate)
            self.assertNotIn("synthetic.setting", aggregate)
            self.assertNotIn('"flag"', json.dumps(report))

    def test_second_branch_into_diamond_is_explicit_veto(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            old = profile_jar_class(original, "p/Demo.class")
            new = profile_jar_class(candidate, "p/Demo.class")
            baseline = plan_conditional_boolean_witnesses(old, new)
            self.assertEqual(baseline["short_diamond_witnesses"], 1)
            init = next(x for x in old["methods"] if x["name"] == "<clinit>")
            rows = init["instructions"]
            store = next(
                i for i, row in enumerate(rows)
                if row.get("opcode") == "0xb3"
                and row.get("name") == "flag"
            )
            first_literal = rows[store - 3]["offset"]
            # Inject an extra incoming edge from an unrelated instruction.
            rows[0]["branch_target_offset"] = first_literal
            rejected = plan_conditional_boolean_witnesses(old, new)
            self.assertEqual(rejected["short_diamond_witnesses"], 0)
            self.assertEqual(rejected["unresolved_conditional_boolean_stores"], 1)

    def test_exception_handler_over_diamond_is_a_veto(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            old = profile_jar_class(original, "p/Demo.class")
            new = profile_jar_class(candidate, "p/Demo.class")
            init = next(x for x in old["methods"] if x["name"] == "<clinit>")
            store = next(
                i for i, row in enumerate(init["instructions"])
                if row.get("opcode") == "0xb3"
                and row.get("name") == "flag"
            )
            start = init["instructions"][store - 4]["offset"]
            end = init["instructions"][store]["offset"] + 3
            init["exception_handlers"].append({
                "start_pc": start, "end_pc": end,
                "handler_pc": start, "catch_type": None,
            })
            result = plan_conditional_boolean_witnesses(old, new)
            self.assertEqual(result["short_diamond_witnesses"], 0)
            self.assertEqual(result["unresolved_conditional_boolean_stores"], 1)

    def test_reject_duplicate_original_field_store(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            old = profile_jar_class(original, "p/Demo.class")
            new = profile_jar_class(candidate, "p/Demo.class")
            init = next(x for x in old["methods"] if x["name"] == "<clinit>")
            row = next(x for x in init["instructions"]
                       if x.get("opcode") == "0xb3"
                       and x.get("name") == "flag")
            init["instructions"].append({
                **row, "offset": init["code_length"] + 10,
            })
            with self.assertRaisesRegex(
                BooleanJoinWitnessError, "DUPLICATE_ORIGINAL_BOOLEAN_STORE",
            ):
                plan_conditional_boolean_witnesses(old, new)

    def test_wrong_sha_has_no_output_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original, candidate = self._pair(root)
            out = root / "private"
            with self.assertRaisesRegex(
                BooleanJoinWitnessError, "INPUT_JAR_SHA256_MISMATCH",
            ):
                self._build(original, candidate, out, original_sha="0" * 64)
            self.assertFalse(out.exists())
            out.mkdir()
            (out / "KEEP").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(
                BooleanJoinWitnessError, "WITNESS_OUTPUT_ALREADY_EXISTS",
            ):
                self._build(original, candidate, out)
            self.assertEqual((out / "KEEP").read_text(), "preserve")

    def test_direct_literal_is_not_misclassified_as_branch_join(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self._jar(
                root, "original", "public static int number=1;"
                " public static boolean flag=true;",
            )
            candidate = self._jar(
                root, "candidate", "public static int number;"
                " public static boolean flag;",
            )
            report = self._build(original, candidate, root / "private")
            self.assertEqual(report["conditional_boolean_stores_examined"], 0)
            self.assertEqual(report["short_diamond_witnesses"], 0)
            self.assertFalse(report["conditional_boolean_value_pairs_verified_locally"])


if __name__ == "__main__":
    unittest.main()

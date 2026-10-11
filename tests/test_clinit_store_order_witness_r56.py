"""R56 synthetic Java 9 tests for ordered original/candidate clinit replay."""
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
from spk_recovery.clinit_store_order_witness import (
    ClinitOrderWitnessError, prove_private_clinit_order,
    verify_ordered_owner_stores,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ClinitOrderWitnessTests(unittest.TestCase):
    def _jar(self, root: Path, label: str, cls: str, code: str):
        src = root / label / "source" / "p" / (cls + ".java")
        classes = root / label / "classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class " + cls + " { " + code + " }",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(src)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / (cls + ".class"),
                    "p/" + cls + ".class")
        return jar

    @staticmethod
    def _sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def _case(self, root: Path, bcode: str):
        a = self._jar(root, "original", "A",
                      "public static int x=3; public static int y=x+4;")
        b = self._jar(root, "candidate", "B", bcode)
        aliases = [
            {"original": {"name": "x", "descriptor": "I"},
             "candidate": {"name": "first", "descriptor": "I"}},
            {"original": {"name": "y", "descriptor": "I"},
             "candidate": {"name": "second", "descriptor": "I"}},
        ]
        return a, b, aliases

    def _profiles(self, a, b):
        return (profile_jar_class(a, "p/A.class"),
                profile_jar_class(b, "p/B.class"))

    def test_all_original_candidate_store_orders_and_opcodes_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, aliases = self._case(
                root,
                "public static int first=3; "
                "public static int second=first+4;",
            )
            original, candidate = self._profiles(a, b)
            report = verify_ordered_owner_stores(original, candidate, aliases)
            self.assertEqual(report["owner_static_field_writes"], 2)
            self.assertEqual(report["unique_static_field_targets_written"], 2)
            self.assertTrue(report["exact_mapped_static_store_order"])
            self.assertTrue(report["exact_jvm_opcode_sequence_shape"])
            self.assertTrue(report["exact_branch_target_instruction_ordinals"])
            self.assertFalse(report["runtime_equivalence_certified"])
            self.assertFalse(report["constant_pool_operand_semantics_equivalent"])

            alias_path = root / "aliases.private.json"
            alias_path.write_text(
                json.dumps({"schema_version": 1, "aliases": aliases}),
                encoding="utf-8",
            )
            out = root / "private"
            result = prove_private_clinit_order(
                a, "p/A.class", b, "p/B.class", alias_path, out,
                original_sha256=self._sha(a),
                candidate_sha256=self._sha(b),
            )
            self.assertEqual(result["owner_static_field_writes"], 2)
            self.assertTrue((out / "clinit-order.aggregate.json").exists())
            self.assertNotIn('"first"', json.dumps(result))
            self.assertNotIn('"x"', json.dumps(result))

    def test_original_order_mismatch_is_a_hard_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, aliases = self._case(
                root, "public static int second=first+4;"
                      "public static int first=3;",
            )
            with self.assertRaisesRegex(
                ClinitOrderWitnessError, "STORE_ORDER_MISMATCH"
            ):
                verify_ordered_owner_stores(
                    *self._profiles(a, b), aliases,
                )

    def test_missing_alias_or_duplicate_candidate_identity_is_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, aliases = self._case(
                root, "public static int first=3;"
                      "public static int second=first+4;",
            )
            original, candidate = self._profiles(a, b)
            with self.assertRaisesRegex(
                ClinitOrderWitnessError, "ALIAS_DOES_NOT_COVER"
            ):
                verify_ordered_owner_stores(
                    original, candidate, aliases[:1]
                )
            aliases[1]["candidate"] = dict(aliases[0]["candidate"])
            with self.assertRaisesRegex(
                ClinitOrderWitnessError, "DUPLICATED_PRIVATE_FIELD_ALIAS"
            ):
                verify_ordered_owner_stores(
                    original, candidate, aliases
                )

    def test_identical_store_order_but_different_opcodes_is_a_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, aliases = self._case(
                root, "public static int first=3;"
                      "public static int second=first+4;",
            )
            original, candidate = self._profiles(a, b)
            method = next(m for m in candidate["methods"] if m["name"] == "<clinit>")
            method["instructions"][0]["opcode"] = "0x04"
            with self.assertRaisesRegex(
                ClinitOrderWitnessError, "OPCODE_SEQUENCE_MISMATCH"
            ):
                verify_ordered_owner_stores(original, candidate, aliases)

    def test_alias_name_or_descriptor_must_exist_as_declared_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, aliases = self._case(
                root, "public static int first=3;"
                      "public static int second=first+4;",
            )
            aliases[1]["candidate"]["descriptor"] = "Ljava/lang/String;"
            with self.assertRaisesRegex(
                ClinitOrderWitnessError, "ALIAS_FIELD_DECLARATION_MISMATCH"
            ):
                verify_ordered_owner_stores(
                    *self._profiles(a, b), aliases
                )

    def test_sha_pin_and_existing_destination_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, aliases = self._case(
                root, "public static int first=3;"
                      "public static int second=first+4;",
            )
            alias_path = root / "private.json"
            alias_path.write_text(
                json.dumps({"schema_version": 1, "aliases": aliases}),
                encoding="utf-8",
            )
            out = root / "out"
            with self.assertRaisesRegex(
                ClinitOrderWitnessError, "COMPLETE_JAR_SHA256_MISMATCH"
            ):
                prove_private_clinit_order(
                    a, "p/A.class", b, "p/B.class", alias_path, out,
                    original_sha256="0" * 64, candidate_sha256=self._sha(b),
                )
            self.assertFalse(out.exists())
            out.mkdir()
            (out / "KEEP").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(
                ClinitOrderWitnessError, "OUTPUT_ALREADY_EXISTS"
            ):
                prove_private_clinit_order(
                    a, "p/A.class", b, "p/B.class", alias_path, out,
                    original_sha256=self._sha(a), candidate_sha256=self._sha(b),
                )
            self.assertEqual((out / "KEEP").read_text(), "keep")


if __name__ == "__main__":
    unittest.main()

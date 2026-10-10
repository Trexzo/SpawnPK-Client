"""Synthetic-only R25 tests; no proprietary source or client JAR in CI."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import warnings
from zipfile import ZipFile

from spk_recovery.source_method_parity import (
    MethodParityError,
    build_report,
    compare_profiles,
)


def _row(opcode: str, offset: int, length: int = 1, **kwargs) -> dict:
    return {"opcode": opcode, "mnemonic": "synthetic", "offset": offset,
            "length": length, **kwargs}


def _profile(rows=None, *, handlers=None, bsm=None, owner="p/A") -> dict:
    rows = rows or [_row("0x04", 0, int_constant=1), _row("0xac", 1)]
    return {
        "internal_name": owner,
        "bootstrap_methods": [] if bsm is None else bsm,
        "methods": [{
            "name": "value", "descriptor": "()I", "access": 1,
            "code_length": sum(x["length"] for x in rows),
            "instructions": rows,
            "exception_handlers": [] if handlers is None else handlers,
        }],
    }


def _bootstrap(index: int, cp: int, target="lambda$value$0") -> list:
    return [{
        "index": index,
        "bootstrap_method_ref": cp,
        "bootstrap_method": {
            "reference_kind": 6, "reference_index": cp,
            "target_kind": "method",
            "owner": "java/lang/invoke/LambdaMetafactory",
            "name": "metafactory", "descriptor": "(X)Y",
        },
        "arguments": [{
            "kind": "method_handle", "constant_pool_index": cp + 1,
            "method_handle": {
                "reference_kind": 6, "reference_index": cp + 2,
                "target_kind": "method",
                "owner": "p/A", "name": target, "descriptor": "()V",
            },
        }],
    }]


class SourceMethodParitySyntheticTests(unittest.TestCase):
    def test_simple_methods_match_but_never_certify_equivalence(self):
        a = _profile()
        b = copy.deepcopy(a)
        result = compare_profiles(a, b, "value", "()I")
        self.assertEqual(result["classification"], "CANDIDATE_INSTRUCTION_PARITY")
        self.assertFalse(result["canonical_identity_accepted"])
        self.assertFalse(result["full_method_equivalence_certified"])
        self.assertTrue(result["code_subattributes_and_stackmaps_unverified"])
        self.assertEqual(result, compare_profiles(a, b, "value", "()I"))
        self.assertNotIn("internal_name", result)

    def test_changed_return_constant_is_rejected(self):
        a, b = _profile(), _profile()
        b["methods"][0]["instructions"][0]["int_constant"] = 2
        result = compare_profiles(a, b, "value", "()I")
        self.assertEqual(result["classification"], "BYTECODE_DIFFERENCE")
        self.assertFalse(result["checks"]["decoded_instructions_and_resolved_cp"])

    def test_changed_handler_is_detected(self):
        a = _profile(handlers=[{
            "start_pc": 0, "end_pc": 1, "handler_pc": 1,
            "catch_type": "java/lang/RuntimeException",
        }])
        b = copy.deepcopy(a)
        b["methods"][0]["exception_handlers"][0]["catch_type"] = "java/lang/Exception"
        result = compare_profiles(a, b, "value", "()I")
        self.assertFalse(result["checks"]["exception_handlers"])

    def test_ldc_cp_reindex_matches_but_value_change_does_not(self):
        a = _profile([
            _row("0x12", 0, 2, constant_pool_index=7,
                 constant_pool_tag=8, constant="hello"),
            _row("0xb0", 2),
        ])
        b = copy.deepcopy(a)
        b["methods"][0]["instructions"][0]["constant_pool_index"] = 33
        self.assertEqual(
            compare_profiles(a, b, "value", "()I")["classification"],
            "CANDIDATE_INSTRUCTION_PARITY",
        )
        b["methods"][0]["instructions"][0]["constant"] = "goodbye"
        self.assertEqual(compare_profiles(a, b, "value", "()I")["classification"],
                         "BYTECODE_DIFFERENCE")

    def test_float_bit_pattern_is_not_discarded(self):
        a = _profile([
            _row("0x12", 0, 2, constant_pool_index=4,
                 constant_pool_tag=4, constant_raw_bits="80000000"),
            _row("0xae", 2),
        ])
        b = copy.deepcopy(a)
        b["methods"][0]["instructions"][0]["constant_raw_bits"] = "00000000"
        self.assertEqual(compare_profiles(a, b, "value", "()I")["classification"],
                         "BYTECODE_DIFFERENCE")

    def test_reject_dynamic_constant_without_resolution(self):
        a = _profile([
            _row("0x12", 0, 2, constant_pool_index=4, constant_pool_tag=17),
            _row("0xb0", 2),
        ])
        with self.assertRaisesRegex(MethodParityError, "UNSUPPORTED_LDC_CONSTANT"):
            compare_profiles(a, a, "value", "()I")

    def test_bootstrap_indices_normalize_but_targets_do_not(self):
        rows = [
            _row("0xba", 0, 5, name="run", descriptor="()Ljava/lang/Runnable;",
                 bootstrap_method_attr_index=0, invokedynamic_reserved=0),
            _row("0xb0", 5),
        ]
        a = _profile(rows, bsm=_bootstrap(0, 10))
        b = copy.deepcopy(a)
        b["bootstrap_methods"] = _bootstrap(0, 40)
        self.assertEqual(
            compare_profiles(a, b, "value", "()I")["classification"],
            "CANDIDATE_INSTRUCTION_PARITY",
        )
        b["bootstrap_methods"] = _bootstrap(0, 40, "differentCallback")
        self.assertEqual(compare_profiles(a, b, "value", "()I")["classification"],
                         "BYTECODE_DIFFERENCE")

    def test_unresolved_bootstrap_argument_rejected(self):
        a = _profile([
            _row("0xba", 0, 5, name="run", descriptor="()V",
                 bootstrap_method_attr_index=0, invokedynamic_reserved=0),
            _row("0xb1", 5),
        ], bsm=_bootstrap(0, 10))
        a["bootstrap_methods"][0]["arguments"] = [
            {"kind": "constant_pool_entry", "tag": 17},
        ]
        with self.assertRaisesRegex(MethodParityError, "UNSUPPORTED_BOOTSTRAP_ARGUMENT"):
            compare_profiles(a, a, "value", "()I")

    def test_invalid_branch_target_rejected(self):
        a = _profile([
            _row("0x99", 0, 3, branch_target_offset=2),
            _row("0xb1", 3),
        ])
        with self.assertRaisesRegex(MethodParityError, "INVALID_BRANCH_TARGET"):
            compare_profiles(a, a, "value", "()I")

    def test_missing_operand_and_short_decode_rejected(self):
        a = _profile([_row("0x10", 0, 2), _row("0xac", 2)])
        with self.assertRaisesRegex(MethodParityError, "UNDECODED_INSTRUCTION_OPERAND"):
            compare_profiles(a, a, "value", "()I")
        a = _profile()
        a["methods"][0]["code_length"] += 1
        with self.assertRaisesRegex(MethodParityError, "INCOMPLETE_METHOD_DECODE"):
            compare_profiles(a, a, "value", "()I")

    def test_no_implicit_owner_alias_or_ambiguous_method(self):
        a, b = _profile(), _profile(owner="p/B")
        with self.assertRaisesRegex(MethodParityError, "OWNER_NAME_DIFFERS"):
            compare_profiles(a, b, "value", "()I")
        a = _profile()
        a["methods"].append(copy.deepcopy(a["methods"][0]))
        with self.assertRaisesRegex(MethodParityError, "METHOD_NOT_UNIQUE"):
            compare_profiles(a, a, "value", "()I")

    def test_unsupported_ret_instruction_rejected(self):
        a = _profile([_row("0xa9", 0, 2, local_index=0), _row("0xb1", 2)])
        with self.assertRaisesRegex(MethodParityError, "UNSUPPORTED_OPCODE"):
            compare_profiles(a, a, "value", "()I")

    def test_bootstrap_reserved_nonzero_rejected(self):
        a = _profile([
            _row("0xba", 0, 5, name="run", descriptor="()V",
                 bootstrap_method_attr_index=0, invokedynamic_reserved=1),
            _row("0xb1", 5),
        ], bsm=_bootstrap(0, 10))
        with self.assertRaisesRegex(MethodParityError, "INVALID_INVOKEDYNAMIC_RESERVED"):
            compare_profiles(a, a, "value", "()I")


@unittest.skipUnless(shutil.which("javac"), "javac unavailable")
class SourceMethodParityCompiledTests(unittest.TestCase):
    def _jar(self, root: Path, tag: str, extra: str, constant: int) -> Path:
        src = root / tag / "src" / "p"
        output = root / tag / "classes"
        src.mkdir(parents=True)
        output.mkdir(parents=True)
        source = src / "A.java"
        source.write_text(
            "package p; public class A { "
            + extra + f" public int value(int x) {{return x + {constant};}}"
            + " }", encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "-g:none", "-d", str(output), str(source)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / f"{tag}.jar"
        with ZipFile(jar, "w") as z:
            z.write(output / "p" / "A.class", "p/A.class")
        return jar

    def test_real_javac_parity_drift_and_jar_pin(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = self._jar(root, "old", "", 1)
            candidate = self._jar(
                root, "rebuilt",
                'private static String other(){return "hi";}', 1,
            )
            bad = self._jar(root, "changed", "", 2)
            def compare(right: Path, sha=None):
                return build_report(
                    old, right, entry_path="p/A.class",
                    method_name="value", descriptor="(I)I",
                    original_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
                    candidate_sha256=sha or hashlib.sha256(right.read_bytes()).hexdigest(),
                )
            self.assertEqual(
                compare(candidate)["classification"], "CANDIDATE_INSTRUCTION_PARITY"
            )
            self.assertEqual(compare(bad)["classification"], "BYTECODE_DIFFERENCE")
            with self.assertRaisesRegex(MethodParityError, "JAR_SHA256_MISMATCH"):
                compare(candidate, "0" * 64)

    def test_duplicate_original_entry_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(root, "one", "", 1)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(jar, "a") as z:
                    z.writestr("p/A.class", b"not a class")
            sha = hashlib.sha256(jar.read_bytes()).hexdigest()
            with self.assertRaisesRegex(MethodParityError, "MISSING_OR_DUPLICATE_CLASS_ENTRY"):
                build_report(
                    jar, jar, entry_path="p/A.class",
                    method_name="value", descriptor="(I)I",
                    original_sha256=sha, candidate_sha256=sha,
                )


if __name__ == "__main__":
    unittest.main()

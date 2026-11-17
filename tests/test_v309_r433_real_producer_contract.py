"""R433 cross-check REAL public receipt producers against R432 consumer contract.

AST-inspects checked-in R422/R425 Java-harness runners; does not execute
anything against owner-private source, history, JARs or game runtime.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from tools.r432.chain_private_process_acceptance import REQUIRED_R422_CHECKS
from tools.r424.prepare_private_legacy_cleanup_patch import (
    REPLACEMENT_METHOD, PINNED_R421_STORE_SHA,
)
from tools.r425.compile_and_accept_private_overlay import (
    PINNED_R421_STORE_CLASS,
)

ROOT = Path(__file__).resolve().parents[1]
R422 = ROOT/"tools/r422/run_private_store_acceptance.py"
R425 = ROOT/"tools/r425/compile_and_accept_private_overlay.py"
R424 = ROOT/"tools/r424/prepare_private_legacy_cleanup_patch.py"
R432 = ROOT/"tools/r432/chain_private_process_acceptance.py"


def code(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def func(mod: ast.AST, name: str) -> ast.FunctionDef:
    matches = [n for n in mod.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == name]
    if len(matches) != 1:
        raise AssertionError(f"Expected exactly one {name}")
    return matches[0]


def dict_keys(node: ast.Dict) -> set[str]:
    result = set()
    for key in node.keys:
        if not isinstance(key, ast.Constant) or not isinstance(key.value,str):
            raise AssertionError("Receipt uses dynamic or non-string key")
        if key.value in result:
            raise AssertionError("Duplicate receipt key "+key.value)
        result.add(key.value)
    return result


class R433ProducerConsumerContracts(unittest.TestCase):
    def test_01_actual_r422_passed_labels_exactly_match_r432_gate(self):
        runner = func(code(R422), "main")
        labels=[]
        for n in ast.walk(runner):
            if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Name):
                continue
            if n.func.id != "passed":
                continue
            self.assertGreaterEqual(len(n.args),1)
            self.assertIsInstance(n.args[0], ast.Constant)
            self.assertIsInstance(n.args[0].value, str)
            labels.append(n.args[0].value)
        self.assertEqual(len(labels),17)
        self.assertEqual(len(labels),len(set(labels)))
        self.assertEqual(set(labels),REQUIRED_R422_CHECKS)

    def test_02_r425_produced_top_level_receipt_matches_r432_reader(self):
        runner=func(code(R425),"run")
        found=[n.value for n in ast.walk(runner)
               if isinstance(n,ast.Assign)
               and any(isinstance(t,ast.Name) and t.id=="receipt"
                       for t in n.targets)
               and isinstance(n.value,ast.Dict)]
        self.assertEqual(len(found),1)
        keys=dict_keys(found[0])
        needed={
            "status","source_scope","class_scope","actual_private_store",
            "private_source_patch","legacy_deletion_enabled",
            "real_history_read_or_changed","private_game_launched",
            "release_authorized","merge_authorized",
        }
        self.assertTrue(needed <= keys, sorted(needed-keys))
        for k,v in zip(found[0].keys,found[0].values):
            if k.value in {"legacy_deletion_enabled",
                           "real_history_read_or_changed",
                           "private_game_launched","release_authorized",
                           "merge_authorized"}:
                self.assertIsInstance(v,ast.Constant)
                self.assertIs(v.value,False)

    def test_03_r425_actual_store_return_receipt_has_expected_identity(self):
        acceptance=func(code(R425),"execute_actual_class_acceptance")
        returned=[n.value for n in ast.walk(acceptance)
                  if isinstance(n,ast.Return) and isinstance(n.value,ast.Dict)]
        self.assertEqual(len(returned),1)
        keys=dict_keys(returned[0])
        self.assertTrue({"status","real_class_assertions"} <= keys)
        values={k.value:v for k,v in zip(returned[0].keys,returned[0].values)}
        self.assertEqual(values["status"].value,
                         "R425_ACTUAL_PRIVATE_STORE_DRY_RUN_TEMP_PASS")
        self.assertTrue(
            "R425_ACTUAL_PRIVATE_STORE_DRY_RUN_TEMP_PASS" in
            R432.read_text(encoding="utf-8"))

    def test_04_r422_producer_fields_match_consumer_requirements(self):
        tree=code(R422)
        literal_receipts=[
            n for n in ast.walk(func(tree,"main"))
            if isinstance(n,ast.Dict) and
            any(isinstance(k,ast.Constant) and k.value=="class_sha256_verified"
                for k in n.keys)
        ]
        self.assertEqual(len(literal_receipts),1)
        keys=dict_keys(literal_receipts[0])
        self.assertTrue({
            "status","checks","cases","real_store_assertions",
            "class_sha256_verified","original_game_started",
            "production_history_opened","private_release_authorized"
        } <= keys)
        for key,value in zip(literal_receipts[0].keys,
                             literal_receipts[0].values):
            if key.value in {"original_game_started",
                             "production_history_opened",
                             "private_release_authorized"}:
                self.assertIsInstance(value,ast.Constant)
                self.assertIs(value.value, False)

    def test_05_pins_and_public_compiler_adapter_do_not_add_unknown_enum(self):
        self.assertEqual(PINNED_R421_STORE_SHA,
            "0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29")
        self.assertEqual(PINNED_R421_STORE_CLASS,
            "65272371272fdcf9142095880a042aa007a9a088f93c969a57878188fae37a09")
        self.assertIn(
            '() -> !r411RefuseUnresolvedStage("legacy cleanup")',
            REPLACEMENT_METHOD)
        self.assertNotIn("R411StageState", REPLACEMENT_METHOD)
        self.assertNotIn("r411StageState()", REPLACEMENT_METHOD)
        self.assertIn("false); // R424:", REPLACEMENT_METHOD)

    def test_06_r422_producer_status_is_exact_consumer_status(self):
        source=R422.read_text(encoding="utf-8")
        reader=R432.read_text(encoding="utf-8")
        self.assertIn(
            '"status": "R422_OWNER_PRIVATE_ACTUAL_STORE_PROCESS_ACCEPTANCE_PASS"',
            source)
        self.assertIn(
            '"R422_OWNER_PRIVATE_ACTUAL_STORE_PROCESS_ACCEPTANCE_PASS"',
            reader)
        self.assertIn('"class_sha256_verified": args.expected_store_class_sha256',
                      source)
        self.assertIn("len(REQUIRED_R422_CHECKS)", reader)


if __name__ == "__main__":
    unittest.main()

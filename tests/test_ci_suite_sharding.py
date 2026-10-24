"""Public, deterministic checks for four-way full-suite CI sharding."""
from collections import Counter
from pathlib import Path
import importlib.util
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_unit_suite_shard.py"
SPEC = importlib.util.spec_from_file_location("recovery_test_sharder", SCRIPT)
shard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(shard)


def fixture_case(module: str):
    class Fixture(unittest.TestCase):
        def runTest(self):
            pass
    Fixture.__module__ = module
    return Fixture()


def complete_fixture():
    candidates = {}
    for index in range(128):
        name = "test_synthetic_ci_bucket_" + str(index)
        bucket = shard.assign(name)
        if bucket not in candidates:
            candidates[bucket] = name
        if len(candidates) == 3:
            break
    assert set(candidates) == {1, 2, 3}
    return [fixture_case(shard.HEAVY_MODULE)] + [
        fixture_case(candidates[bucket]) for bucket in (1, 2, 3)
    ]


class RecoveryShardSafety(unittest.TestCase):
    def test_fvn_hash_stable_public_reference(self):
        self.assertEqual(shard.stable_bucket("hello"), 0x4F9F2CAB)

    def test_heavy_module_solely_in_shard_zero(self):
        self.assertEqual(shard.assign(shard.HEAVY_MODULE), 0)
        self.assertTrue(all(shard.assign("test_other_" + str(i)) in (1, 2, 3)
                            for i in range(100)))

    def test_all_four_shards_have_unique_coverage(self):
        cases = complete_fixture()
        with mock.patch.object(shard, "BASELINE_TEST_COUNT", 4):
            groups = shard.plan_cases(cases)
        self.assertEqual([len(group) for group in groups], [1, 1, 1, 1])
        self.assertEqual(
            Counter(case.id() for group in groups for case in group),
            Counter(case.id() for case in cases),
        )

    def test_same_module_cases_remain_together_in_original_order(self):
        cases = complete_fixture()
        repeat = fixture_case(cases[1].__class__.__module__)
        # Give the second case a different method identifier to avoid duplicate id.
        repeat.__class__.id = lambda self: self.__class__.__module__ + ".Fixture.other_test"
        cases.append(repeat)
        with mock.patch.object(shard, "BASELINE_TEST_COUNT", 4):
            groups = shard.plan_cases(cases)
        chosen = shard.assign(cases[1].__class__.__module__)
        self.assertEqual(groups[chosen], [cases[1], repeat])

    def test_duplicate_test_identifier_fails_closed(self):
        cases = complete_fixture()
        cases.append(cases[0])
        with mock.patch.object(shard, "BASELINE_TEST_COUNT", 4):
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_TEST_ID"):
                shard.plan_cases(cases)

    def test_discovery_count_regression_fails_closed(self):
        cases = complete_fixture()
        with mock.patch.object(shard, "BASELINE_TEST_COUNT", 5):
            with self.assertRaisesRegex(RuntimeError, "DISCOVERY_REGRESSION"):
                shard.plan_cases(cases)

    def test_missing_whole_shard_fails_closed(self):
        cases = [fixture_case(shard.HEAVY_MODULE)]
        with mock.patch.object(shard, "BASELINE_TEST_COUNT", 1):
            with self.assertRaisesRegex(RuntimeError, "EMPTY_GROUP"):
                shard.plan_cases(cases)

    def test_missing_heavy_module_fails_closed(self):
        cases = [case for case in complete_fixture()
                 if case.__class__.__module__ != shard.HEAVY_MODULE]
        with mock.patch.object(shard, "BASELINE_TEST_COUNT", 3):
            with self.assertRaisesRegex(RuntimeError, "EMPTY_GROUP"):
                shard.plan_cases(cases)

    def test_nested_unittest_suite_is_flattened_without_changes(self):
        cases = complete_fixture()
        suite = unittest.TestSuite([
            unittest.TestSuite(cases[:2]),
            unittest.TestSuite(cases[2:]),
        ])
        self.assertEqual(list(shard.flatten(suite)), cases)


if __name__ == "__main__":
    unittest.main(verbosity=2)

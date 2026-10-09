from __future__ import annotations

import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.v309_accepted_owner_cp_research import (
    V309AcceptedOwnerResearchError,
    _whole_archive_necessary_pool,
    rewrite_accepted_class_types,
)
from spk_recovery.v309_cp_method_referent_research import compare_cp_method_profiles


def _profile(owner: str, referenced: str, member: str = "work") -> dict:
    methods = []
    for i in range(3):
        methods.append({
            "name": "test" + str(i),
            "access": 1, "descriptor": "(L" + referenced + ";)V",
            "code_length": 4, "exception_handlers": [],
            "instructions": [
                {"opcode": "0xb8", "mnemonic": "invokestatic",
                 "offset": 0, "length": 3,
                 "member_constant_pool_tag": 10,
                 "owner": referenced, "name": member + str(i),
                 "descriptor": "()V"},
                {"opcode": "0xb1", "mnemonic": "return",
                 "offset": 3, "length": 1},
            ],
        })
    return {"internal_name": owner, "bootstrap_methods": [], "methods": methods}


def _compare(old, new):
    return compare_cp_method_profiles(
        old, new, old_owner="p/Old", new_owner="p/New",
    )["unique_cp_semantic_method_matches"]


class AcceptedOwnerAliasResearchTests(unittest.TestCase):
    def setUp(self):
        self.old = _profile("p/Old", "known/Old")
        self.new = _profile("p/New", "known/New")
        self.old_alias = {"known/Old": "@ACCEPTED_CLIENT_CLASS_000001"}
        self.new_alias = {"known/New": "@ACCEPTED_CLIENT_CLASS_000001"}

    def rewritten(self):
        return (
            rewrite_accepted_class_types(self.old, self.old_alias),
            rewrite_accepted_class_types(self.new, self.new_alias),
        )

    def test_only_exact_preaccepted_owner_ids_can_add_cp_witnesses(self):
        self.assertEqual(_compare(self.old, self.new), 0)
        old, new = self.rewritten()
        self.assertEqual(_compare(old, new), 3)
        self.assertEqual(self.old["methods"][0]["descriptor"], "(Lknown/Old;)V")
        self.assertEqual(old["internal_name"], "p/Old")
        self.assertEqual(new["internal_name"], "p/New")

    def test_different_accepted_canonical_ids_do_not_equate(self):
        old = rewrite_accepted_class_types(self.old, self.old_alias)
        new = rewrite_accepted_class_types(
            self.new, {"known/New": "@ACCEPTED_CLIENT_CLASS_000002"})
        self.assertEqual(_compare(old, new), 0)

    def test_unaccepted_external_owner_does_not_gain_alias(self):
        old = rewrite_accepted_class_types(self.old, {"someone/Else": "@ID"})
        new = rewrite_accepted_class_types(self.new, {"someone/Else2": "@ID"})
        self.assertEqual(_compare(old, new), 0)

    def test_member_name_change_is_never_erased_by_owner_alias(self):
        old, new = self.rewritten()
        new["methods"][1]["instructions"][0]["name"] = "changedMember"
        self.assertEqual(_compare(old, new), 2)

    def test_string_literal_and_numeric_payload_are_never_aliased(self):
        old = _profile("p/Old", "known/Old")
        new = _profile("p/New", "known/New")
        for profile, literal in ((old, "known/Old"), (new, "known/New")):
            method = profile["methods"][0]
            method["instructions"] = [
                {"opcode": "0x12", "mnemonic": "ldc", "offset": 0, "length": 2,
                 "constant_pool_tag": 8, "constant": literal},
                {"opcode": "0xb1", "mnemonic": "return", "offset": 2, "length": 1},
            ]
            method["code_length"] = 3
        a = rewrite_accepted_class_types(old, self.old_alias)
        b = rewrite_accepted_class_types(new, self.new_alias)
        self.assertEqual(a["methods"][0]["instructions"][0]["constant"], "known/Old")
        self.assertEqual(b["methods"][0]["instructions"][0]["constant"], "known/New")
        self.assertEqual(_compare(a, b), 2)  # only other two CP-bearing methods match

    def test_class_ldc_is_typed_and_may_reuse_accepted_class_identity(self):
        old = copy.deepcopy(self.old)
        new = copy.deepcopy(self.new)
        for profile, owner in ((old, "known/Old"), (new, "known/New")):
            method = profile["methods"][0]
            method["instructions"] = [
                {"opcode": "0x12", "mnemonic": "ldc", "offset": 0, "length": 2,
                 "constant_pool_tag": 7, "constant": owner},
                {"opcode": "0xb1", "mnemonic": "return", "offset": 2, "length": 1},
            ]
            method["code_length"] = 3
        a = rewrite_accepted_class_types(old, self.old_alias)
        b = rewrite_accepted_class_types(new, self.new_alias)
        self.assertEqual(_compare(a, b), 3)

    def test_missing_duplicate_and_invalid_alias_authority_refused(self):
        for aliases in (
            {}, {"a": "@DUP", "b": "@DUP"}, {"": "@ID"},
            {"a": ""}, {"a": 5},
        ):
            with self.subTest(aliases=aliases):
                with self.assertRaises(V309AcceptedOwnerResearchError):
                    rewrite_accepted_class_types(self.old, aliases)


@unittest.skipUnless(shutil.which("javac"), "Java compiler required")
class RealJavaNecessaryPoolTests(unittest.TestCase):
    def test_incomplete_original_archive_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            java = path / "SyntheticClass.java"
            java.write_text(
                "public final class SyntheticClass {\n"
                " public void m1() { System.out.println(1); }\n"
                " public void m2() { System.out.println(2); }\n"
                " public void m3() { System.out.println(3); }\n"
                "}\n", encoding="utf-8",
            )
            compile_result = subprocess.run(
                ["javac", "--release", "11", "-proc:none", "-d", str(path), str(java)],
                text=True, capture_output=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            archive = path / "only-fixture.jar"
            with zipfile.ZipFile(archive, "w") as z:
                z.write(path / "SyntheticClass.class", "SyntheticClass.class")
            with zipfile.ZipFile(archive) as z:
                with self.assertRaises(V309AcceptedOwnerResearchError):
                    _whole_archive_necessary_pool(z, "v308", "SyntheticClass.class")


if __name__ == "__main__":
    unittest.main()

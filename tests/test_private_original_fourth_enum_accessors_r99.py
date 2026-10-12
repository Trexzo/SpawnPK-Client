"""R99 synthetic Java 9 compiler evidence for two fourth-enum accessors."""
import copy
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_original_fourth_enum_accessors import (
    OriginalEnumAccessorError,
    derive_private_fourth_enum_accessor_aliases,
    replay_private_fourth_enum_accessors,
)


@unittest.skipUnless(shutil.which("javac"), "Java 9-compatible javac required")
class OriginalFourthEnumAccessorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "src" / "p"
        self.source.mkdir(parents=True)
        self.classes = self.root / "classes"
        self.classes.mkdir()
        code = (
            "package p; public final class Owner {"
            "public enum Surrogate {"
            ' A("One","https://example.invalid"),'
            ' B("Two","https://example.invalid");'
            "private String x; private String y;"
            "Surrogate(String a,String b){x=a;y=b;}"
            "public String first(){return x;}"
            "public String second(){return y;}"
            "}"
            "public static String readX(Surrogate s){return s.x;}"
            "public static String readY(Surrogate s){return s.y;}"
            "}"
        )
        path = self.source / "Owner.java"
        path.write_text(code, encoding="utf-8")
        build = subprocess.run(
            ["javac", "--release", "9", "-proc:none", "-g:none",
             "-d", str(self.classes), str(path)],
            capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.jar = self.root / "candidate.jar"
        with ZipFile(self.jar, "w") as z:
            for f in self.classes.rglob("*.class"):
                z.write(f, f.relative_to(self.classes).as_posix())
        self.profile = profile_jar_class(
            self.jar, "p/Owner$Surrogate.class")

    def fake_original(self):
        original = copy.deepcopy(self.profile)
        accessors = [
            m for m in original["methods"]
            if m.get("access") == 0x1008
            and m.get("descriptor") ==
                "(Lp/Owner$Surrogate;)Ljava/lang/String;"
        ]
        self.assertEqual(len(accessors), 2)
        accessors[0]["name"] = "a"
        accessors[1]["name"] = "b"
        return original

    def test_compiler_emits_two_exact_three_instruction_accessors(self):
        proof = derive_private_fourth_enum_accessor_aliases(
            self.fake_original(), self.profile)
        self.assertEqual(proof["original_synthetic_accessor_count"], 2)
        self.assertEqual(proof["original_synthetic_accessor_jvm_instructions_compared"], 6)
        self.assertEqual(len(proof["private_accessor_aliases"]), 2)
        self.assertTrue(proof["original_synthetic_accessor_pattern_verified"])
        self.assertFalse(proof["R95_method_parity_passed_by_this_tool"])
        self.assertFalse(proof["original_client_runtime_equivalence_proven"])

    def test_invalid_private_field_read_is_rejected(self):
        bad = self.fake_original()
        accessor = next(m for m in bad["methods"] if m["name"] == "a")
        accessor["instructions"][1]["name"] = "unrelated"
        with self.assertRaisesRegex(OriginalEnumAccessorError, "NOT_UNIQUE"):
            derive_private_fourth_enum_accessor_aliases(bad, self.profile)

    def test_tampered_bytecode_is_rejected(self):
        bad = self.fake_original()
        accessor = next(m for m in bad["methods"] if m["name"] == "a")
        accessor["instructions"][2]["opcode"] = "0xb1"
        with self.assertRaisesRegex(OriginalEnumAccessorError, "THREE_OPCODE_PATTERN"):
            derive_private_fourth_enum_accessor_aliases(bad, self.profile)

    def test_missing_generated_accessor_is_rejected(self):
        bad = copy.deepcopy(self.profile)
        method = next(m for m in bad["methods"]
                      if m.get("name", "").startswith("access$")
                      and m.get("descriptor", "").endswith("Ljava/lang/String;"))
        method["access"] = 0x0008
        with self.assertRaisesRegex(OriginalEnumAccessorError, "TWO_SYNTHETIC_ENUM"):
            derive_private_fourth_enum_accessor_aliases(
                self.fake_original(), bad)

    def test_data_field_identity_must_match(self):
        bad = copy.deepcopy(self.profile)
        name = next(f for f in bad["fields"]
                    if f.get("name") == "x" and
                    f.get("descriptor") == "Ljava/lang/String;")
        name["name"] = "changed"
        for m in bad["methods"]:
            for row in m.get("instructions", []):
                if row.get("name") == "x" and row.get("owner") == bad["internal_name"]:
                    row["name"] = "changed"
        with self.assertRaisesRegex(OriginalEnumAccessorError,
                                    "FIELD_IDENTITIES"):
            derive_private_fourth_enum_accessor_aliases(
                self.fake_original(), bad)

    def test_incorrect_original_jar_sha_fails_before_output(self):
        out = self.root / "proof"
        with self.assertRaisesRegex(OriginalEnumAccessorError,
                                    "EXACT_COMPLETE_JAR_SHA256_MISMATCH"):
            replay_private_fourth_enum_accessors(
                self.jar, self.jar, "p/Owner$Owner.class",
                "p/Owner$Surrogate.class", out,
                original_sha256="0" * 64,
                candidate_sha256=hashlib.sha256(self.jar.read_bytes()).hexdigest())
        self.assertFalse(out.exists())

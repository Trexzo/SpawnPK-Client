"""R49: synthetic Java9 enums and bounded original-name alias parity."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.nested_enum_source_parity import (
    NestedEnumSourceParityError,
    compare_nested_enum_source, replay_nested_enum_source,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("javac"), "javac required")
class NestedEnumSourceJavacTests(unittest.TestCase):
    def _jar(self, root: Path, name: str, *,
             color="RED(7), BLUE(10)",
             mode="FIXED, RESIZABLE, FULLSCREEN") -> Path:
        source = root / name / "source" / "p" / "Host.java"
        classes = root / name / "classes"
        source.parent.mkdir(parents=True)
        classes.mkdir(parents=True)
        source.write_text(
            "package p; public final class Host {"
            "  public enum Color { " + color + "; public int code;"
            "    private Color(int n) { this.code=n; }"
            "  }"
            "  public enum Mode { " + mode + ";"
            "    public static Mode parse(String value) {"
            "      for(Mode item: values())"
            "        if(item.name().equalsIgnoreCase(value)) return item;"
            "      return FIXED;"
            "    }"
            "  }"
            "  public enum Season { SUMMER, WINTER, SPRING; }"
            "}", encoding="utf-8",
        )
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(classes), str(source)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        path = root / (name + ".jar")
        with ZipFile(path, "w") as output:
            for child in sorted((classes / "p").glob("*.class")):
                output.write(child, "p/" + child.name)
        return path

    def _replay(self, old: Path, new: Path, *, candidate_pin=None):
        return replay_nested_enum_source(
            old, new,
            original_sha256=_sha(old),
            candidate_sha256=candidate_pin or _sha(new),
            entries=[
                "p/Host$Color.class",
                "p/Host$Mode.class",
                "p/Host$Season.class",
            ],
        )

    def test_java9_candidate_replay_three_enums(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = self._jar(root, "old")
            new = self._jar(root, "new")
            result = self._replay(old, new)
            self.assertEqual(result["enum_classes_checked"], 3)
            self.assertEqual(result["enum_constant_declarations"], 8)
            self.assertEqual(result["exact_normalized_method_bodies"],
                             result["method_declarations_compared"])
            self.assertTrue(result["all_exact_after_explicit_aliases"])
            self.assertFalse(result["canonical_identity_accepted"])
            self.assertFalse(result["whole_client_source_reconstructed"])
            self.assertEqual(result, self._replay(old, new))
            self.assertNotIn("FIXED", str(result))
            self.assertNotIn("RED", str(result))

    def test_explicit_obfuscation_of_enum_fields_and_helper_still_matches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(root, "baseline")
            candidate = profile_jar_class(jar, "p/Host$Color.class")
            original = copy.deepcopy(candidate)
            owner = original["internal_name"]
            aliases = {}
            count = 0
            for field in original["fields"]:
                if field["access"] & 0x4000:
                    replacement = chr(ord("a") + count)
                    aliases[field["name"]] = replacement
                    field["name"] = replacement
                    count += 1
                elif field["descriptor"] == "[L" + owner + ";":
                    aliases[field["name"]] = "z"
                    field["name"] = "z"
            helper = next(m for m in original["methods"]
                          if m["descriptor"] == "()[L" + owner + ";"
                          and m["name"] != "values")
            aliases_helper = helper["name"]
            helper["name"] = "r"
            for method in original["methods"]:
                for insn in method.get("instructions", []):
                    if insn.get("owner") != owner:
                        continue
                    if insn.get("opcode") in ("0xb2", "0xb3", "0xb4", "0xb5"):
                        insn["name"] = aliases.get(insn["name"], insn["name"])
                    if insn.get("opcode") in ("0xb6", "0xb7", "0xb8", "0xb9"):
                        if insn.get("name") == aliases_helper and insn.get("descriptor") == "()[L" + owner + ";":
                            insn["name"] = "r"
            proof = compare_nested_enum_source(
                original, candidate, original_jar_sha256="a" * 64,
            )
            self.assertEqual(proof["allowed_enum_constant_field_alias_count"], 2)
            self.assertEqual(proof["method_declarations_compared"],
                             proof["method_instruction_parity_after_aliases"])
            self.assertFalse(proof["canonical_enum_identity_accepted"])
            self.assertNotIn("RED", str(proof))
            self.assertNotIn('"z"', str(proof))

    def test_changed_constructor_literal_veto(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = self._jar(root, "old")
            changed = self._jar(root, "changed", color="RED(7), BLUE(11)")
            with self.assertRaisesRegex(
                NestedEnumSourceParityError, "ENUM_METHOD_INSTRUCTION_PARITY_MISMATCH"
            ):
                self._replay(old, changed)

    def test_changed_enum_order_veto(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = self._jar(root, "old")
            changed = self._jar(root, "changed", mode="RESIZABLE, FIXED, FULLSCREEN")
            with self.assertRaises(NestedEnumSourceParityError):
                self._replay(old, changed)

    def test_bad_input_sha_pin(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = self._jar(root, "old")
            candidate = self._jar(root, "candidate")
            with self.assertRaisesRegex(
                NestedEnumSourceParityError, "ENUM_JAR_SHA_MISMATCH"
            ):
                self._replay(old, candidate, candidate_pin="0" * 64)

    def test_java_nested_enum_cannot_have_same_simple_name_as_outer(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            file = root / "Host.java"
            file.write_text(
                "public class Host { public enum Host { YES, NO } }",
                encoding="utf-8",
            )
            result = subprocess.run(
                ["javac", "--release", "9", "-proc:none", str(file)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already defined", result.stderr)


if __name__ == "__main__":
    unittest.main()

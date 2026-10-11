"""R57: synthetic Java9 complete ordered initializer success and mutation vetoes."""
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
from spk_recovery.ordered_complete_clinit_source import (
    OrderedClinitSourceError, plan_ordered_initializer,
    recover_private_ordered_initializer,
)


@unittest.skipUnless(shutil.which("javac"), "javac is required")
class CompleteClinitSourceTests(unittest.TestCase):
    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _jar(self, root: Path, label: str) -> Path:
        folder = root / label / "source" / "p"
        classes = root / label / "classes"
        folder.mkdir(parents=True)
        classes.mkdir()
        (folder / "Provider.java").write_text(
            "package p; public final class Provider {"
            ' public static String base(){return "x";} }',
            encoding="utf-8",
        )
        (folder / "Demo.java").write_text(
            "package p; public final class Demo {"
            " public enum Mode { FIRST, SECOND;"
            " public static String label(Mode m){return m.name();}"
            " public static String alt(Mode m){return m.toString();} }"
            " public static Mode selected = Mode.FIRST;"
            ' public static String conditional = "pre" + '
            '(selected == Mode.FIRST ? "red" : "blue") + "post";'
            " public static Mode blank = null;"
            " public static Mode copy = selected;"
            " public static int count = 3;"
            " public static boolean switchFlag = false;"
            " public static boolean identity = selected == Mode.FIRST;"
            " public static boolean negated = !switchFlag;"
            " public static String viaEnum = Mode.label(selected);"
            " public static String viaEnumOther = Mode.alt(selected);"
            " public static int[] slots = new int[10];"
            " public static Integer boxed = Integer.valueOf(35000);"
            ' public static String viaExternal = "prefix" + '
            'Provider.base() + "suffix";'
            ' public static String literal = "hello";'
            "}",
            encoding="utf-8",
        )
        cmd = ["javac", "--release", "9", "-g:none", "-proc:none",
               "-d", str(classes)]
        cmd += [str(folder / "Demo.java"), str(folder / "Provider.java")]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        jar = root / (label + ".jar")
        with ZipFile(jar, "w") as z:
            for name in ("Demo", "Demo$Mode", "Provider"):
                z.write(classes / "p" / (name + ".class"),
                        "p/" + name + ".class")
        return jar

    @staticmethod
    def _profiles(path: Path):
        return (
            profile_jar_class(path, "p/Demo.class"),
            {name: profile_jar_class(path, name + ".class")
             for name in ("p/Demo$Mode", "p/Provider")},
        )

    def test_real_java9_all_source_forms_preserve_one_ordered_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            out = root / "private"
            result = recover_private_ordered_initializer(
                jar, "p/Demo.class", out, sha256=self._sha(jar)
            )
            source = (out / "complete-clinit.private.java.txt").read_text()
            self.assertIn("selected = p.Demo$Mode.FIRST;", source)
            self.assertIn("count = 3;", source)
            self.assertIn("slots = new int[10];", source)
            self.assertIn("boxed = Integer.valueOf(35000);", source)
            self.assertIn("identity = (selected == p.Demo$Mode.FIRST);", source)
            self.assertIn("negated = (!switchFlag);", source)
            self.assertIn("viaEnum = p.Demo$Mode.label(selected);", source)
            self.assertIn("viaEnumOther = p.Demo$Mode.alt(selected);", source)
            self.assertIn('viaExternal = "prefix" + p.Provider.base() + "suffix";', source)
            self.assertIn('literal = "hello";', source)
            self.assertEqual(result["source_form_counts"]["conditional_concat_string"], 1)
            self.assertEqual(result["source_form_counts"]["boolean_negation"], 1)
            self.assertEqual(result["source_form_counts"]["boolean_reference_equality"], 1)
            self.assertEqual(result["source_form_counts"]["enum_helper_string"], 2)
            self.assertEqual(result["source_form_counts"]["boxed_integer"], 1)
            self.assertEqual(result["source_form_counts"]["array"], 1)
            self.assertEqual(result["source_form_counts"]["external_concat_string"], 1)
            self.assertFalse(result["matches_known_v309_126field_213instruction_93write_shape"])
            self.assertFalse(result["java_source_compilation_parity_certified"])
            self.assertFalse(result["runtime_equivalence_certified"])
            self.assertNotIn('"FIRST"', json.dumps(result))
            self.assertNotIn('"red"', json.dumps(result))
            self.assertEqual(
                self._sha(out / "complete-clinit.private.java.txt"),
                result["private_source_fragment_sha256"],
            )

    def test_private_jar_pin_and_occupied_path_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            out = root / "private"
            with self.assertRaisesRegex(
                OrderedClinitSourceError, "WHOLE_ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_ordered_initializer(
                    jar, "p/Demo.class", out, sha256="0" * 64
                )
            self.assertFalse(out.exists())
            out.mkdir()
            keep = out / "KEEP"
            keep.write_text("KEEP", encoding="utf-8")
            with self.assertRaisesRegex(
                OrderedClinitSourceError, "OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_ordered_initializer(
                    jar, "p/Demo.class", out, sha256=self._sha(jar)
                )
            self.assertEqual(keep.read_text(), "KEEP")

    def test_original_unaccounted_opcode_is_a_hard_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = self._jar(root, "original")
            p, deps = self._profiles(jar)
            init = next(x for x in p["methods"] if x["name"] == "<clinit>")
            # Inject an unmatched real-looking JVM instruction at end of
            # the sequence. The fully accounted source plan must reject.
            tail = init["instructions"][-1]
            self.assertEqual(tail["opcode"], "0xb1")
            tail["opcode"] = "0x00"
            with self.assertRaisesRegex(
                OrderedClinitSourceError,
                "DOES_NOT_TERMINATE_WITH_RETURN",
            ):
                plan_ordered_initializer(p, deps)

    def test_original_extra_branch_target_is_a_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            p, deps = self._profiles(jar)
            init = next(x for x in p["methods"] if x["name"] == "<clinit>")
            a = init["instructions"][0]
            a["branch_target_offset"] = init["instructions"][1]["offset"]
            with self.assertRaisesRegex(
                OrderedClinitSourceError, "UNACCOUNTED_OR_UNSUPPORTED_CLINIT_CONTROL_FLOW"
            ):
                plan_ordered_initializer(p, deps)

    def test_competing_write_operator_or_reordered_group_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self._jar(Path(tmp), "original")
            p, deps = self._profiles(jar)
            init = next(x for x in p["methods"] if x["name"] == "<clinit>")
            target = next(x for x in init["instructions"]
                          if x.get("opcode") == "0xb3"
                          and x.get("name") == "count")
            target["opcode"] = "0xb2"
            with self.assertRaises(OrderedClinitSourceError):
                plan_ordered_initializer(p, deps)


if __name__ == "__main__":
    unittest.main()

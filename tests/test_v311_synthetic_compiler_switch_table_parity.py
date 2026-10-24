"""JDK-only synthetic javac switch-table identity and refusal regressions.

Every enum and switch-owner class here is independently authored toy Java.
No original v311 game Java, binaries, class names, or owner-specific constants.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from spk_recovery.switch_table_identity import restore_generated_switch_table

MODE = "package toy.switches; public enum Mode {OFF,ON,AUTO;}\n"
TEMPLATE = """package toy.switches;
class {owner} {{
 static int translate(Mode value){{
  switch(value){{
   {first}
   {second}
   case AUTO: return 3;
   default:return 0;
  }}
 }}
}}
"""
PROBE = """import java.lang.reflect.*;
public class ToyR98Probe {
 public static void main(String[] args)throws Exception{
  Class<?> c=Class.forName("toy.switches.OriginalMap");
  Field f=c.getDeclaredField("m");f.setAccessible(true);
  int[] table=(int[])f.get(null);
  for(toy.switches.Mode mode:toy.switches.Mode.values())
   System.out.println("MAP:"+mode.name()+":"+mode.ordinal()+":"+table[mode.ordinal()]);
  System.out.println("IS_SYNTHETIC:"+c.isSynthetic());
  System.out.println("NO_CONSTRUCTOR:"+(c.getDeclaredConstructors().length==0));
 }
}
"""


def call(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=55)
    if p.returncode:
        raise AssertionError(p.stderr[-1500:])
    return p.stdout


def switch_output(root, owner, swap=False):
    source = root / "sources/toy/switches"
    source.mkdir(parents=True, exist_ok=True)
    mode = source / "Mode.java"
    mode.write_text(MODE, encoding="utf-8")
    first = "case ON:return 1;"
    second = "case OFF:return 2;"
    if swap:
        first = "case OFF:return 1;"
        second = "case ON:return 2;"
    top = source / (owner + ".java")
    top.write_text(TEMPLATE.format(owner=owner, first=first, second=second),
                   encoding="utf-8")
    output = root / "classes"
    output.mkdir()
    call(["javac", "--release", "9", "-proc:none", "-g:none", "-d",
          str(output), str(mode), str(top)])
    raw = (output / "toy/switches" / (owner + "$1.class")).read_bytes()
    name = "toy/switches/" + owner + "$1"
    restored = restore_generated_switch_table(
        raw, source_class=name, target_class="toy/switches/OriginalMap",
        source_field="$SwitchMap$toy$switches$Mode", target_field="m",
    )
    return restored, output


def disasm(root):
    output = call(["javap", "-c", "-p", "-s", "-classpath", str(root),
                   "toy.switches.OriginalMap"])
    return re.sub(r"#\d+\b", "#CP", output)


@unittest.skipUnless(
    all(shutil.which(exe) for exe in ("java", "javac", "javap")),
    "Java9 compiler and JDK runtime required",
)
class ToyGeneratedSwitchMap(unittest.TestCase):
    def test_two_independent_owners_restore_same_jvm_code_and_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            a = base / "a"
            b = base / "b"
            first, c1 = switch_output(a, "FirstOwner")
            second, c2 = switch_output(b, "SecondOwner")
            for dest, raw in ((a, first), (b, second)):
                file = dest / "restored/toy/switches/OriginalMap.class"
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(raw)
            self.assertEqual(disasm(a / "restored"), disasm(b / "restored"))
            probe = base / "ToyR98Probe.java"
            probe.write_text(PROBE, encoding="utf-8")
            call(["javac", "--release", "9", "-cp", str(c1), "-d",
                  str(base), str(probe)])
            outputs = []
            for dest, cls in ((a, c1), (b, c2)):
                outputs.append(call([
                    "java", "-cp", str(base) + os.pathsep +
                    str(dest / "restored") + os.pathsep + str(cls),
                    "ToyR98Probe",
                ]))
            self.assertEqual(outputs[0], outputs[1])
            self.assertIn("MAP:OFF:0:2", outputs[0])
            self.assertIn("MAP:ON:1:1", outputs[0])
            self.assertIn("MAP:AUTO:2:3", outputs[0])
            self.assertEqual(len(outputs[0].splitlines()), 5)

    def test_changed_enum_case_order_must_not_match_original_instructions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, _ = switch_output(root / "a", "FirstOwner")
            b, _ = switch_output(root / "b", "SecondOwner", swap=True)
            self.assertNotEqual(a, b)
            for folder, raw in ((root / "a", a), (root / "b", b)):
                file = folder / "restored/toy/switches/OriginalMap.class"
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(raw)
            self.assertNotEqual(disasm(root / "a/restored"),
                                disasm(root / "b/restored"))

    def test_unknown_switch_member_and_corrupt_classfile_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, output = switch_output(root, "FirstOwner")
            raw = (output / "toy/switches/FirstOwner$1.class").read_bytes()
            with self.assertRaisesRegex(
                ValueError, "SWITCH_TABLE_EXPECTED_SYMBOL"
            ):
                restore_generated_switch_table(
                    raw, source_class="toy/switches/FirstOwner$1",
                    target_class="toy/switches/OriginalMap",
                    source_field="NOT_A_REAL_FIELD", target_field="m",
                )
            with self.assertRaisesRegex(
                ValueError, "SWITCH_TABLE_NOT_JAVA9"
            ):
                restore_generated_switch_table(
                    b"invalid", source_class="toy/switches/FirstOwner$1",
                    target_class="toy/switches/OriginalMap",
                    source_field="whatever", target_field="m",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Synthetic-only 27-stage Java9 enum member restoration and behavior.

Toy values are unrelated to the owner's original game; no game/vendor
binaries, extracted Java, original stage names or classfiles are included.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from spk_recovery.enum_member_identity import restore_enum_member_identity

NAMES = [f"GATE_{i:02d}" for i in range(27)]
OBF = list("abcdefghijklmnopqrstuvwxyzA")


def source(overridden=False):
    rows = [
        name + ("(true)" if i >= 18 else "")
        for i, name in enumerate(NAMES)
    ]
    fallback = "true" if overridden else "false"
    return (
        "package toy.stage; public enum Pass {\n"
        + ",\n".join(rows)
        + ";\nboolean enabled = true;\n"
        + "private Pass(boolean yes) { this.enabled=yes; }\n"
        + "private Pass() { this.enabled=" + fallback + "; }\n"
        + "}\n"
    )


PROBE = """import java.lang.reflect.*;
public class ToyStageProbe {
  public static void main(String[] arg)throws Exception {
    Class<?> type=Class.forName("toy.stage.Pass");
    Object[] all=(Object[])type.getMethod("values").invoke(null);
    Field flag=type.getDeclaredField("enabled");flag.setAccessible(true);
    String letters="abcdefghijklmnopqrstuvwxyzA";
    for(int i=0;i<all.length;i++){
      Enum<?> e=(Enum<?>)all[i];
      String field=(Boolean.getBoolean("synthetic.alias")?
        letters.substring(i,i+1):e.name());
      System.out.println("STAGE:"+e.name()+":"+e.ordinal()+":"+
       flag.getBoolean(e)+":"+(type.getField(field).get(null)==e)+":"+
       (type.getMethod("valueOf",String.class).invoke(null,e.name())==e));
    }
    System.out.println("CLONE:"+(type.getMethod("values").invoke(null)!=all));
  }
}
"""


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise AssertionError(result.stderr[-1600:])
    return result.stdout


@unittest.skipUnless(
    all(shutil.which(x) for x in ("javac", "javap", "java")),
    "Java9 JDK required",
)
class ToyStageEnum27Tests(unittest.TestCase):
    def build(self, root, override=False):
        path = root / "src/toy/stage/Pass.java"
        path.parent.mkdir(parents=True)
        path.write_text(source(override), encoding="utf-8")
        out = root / "original"
        out.mkdir()
        run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-d", str(out), str(path),
        ])
        raw = (out / "toy/stage/Pass.class").read_bytes()
        return out, raw

    def restore(self, root, raw):
        fields = dict(zip(NAMES, OBF))
        fields["$VALUES"] = "B"
        altered = restore_enum_member_identity(
            raw, "toy/stage/Pass", fields, "a",
        )
        path = root / "restored/toy/stage/Pass.class"
        path.parent.mkdir(parents=True)
        path.write_bytes(altered)
        return path.parents[2]

    def test_27_aliases_preserve_names_values_flags_and_clone(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original, binary = self.build(root)
            restored = self.restore(root, binary)
            self.assertNotEqual(
                binary, (restored / "toy/stage/Pass.class").read_bytes()
            )
            probe = root / "ToyStageProbe.java"
            probe.write_text(PROBE, encoding="utf-8")
            run([
                "javac", "--release", "9", "-d", str(root), str(probe),
            ])
            outputs = []
            for cp, alias in ((original, "false"), (restored, "true")):
                outputs.append(run([
                    "java", "-Dsynthetic.alias=" + alias,
                    "-cp", str(root) + os.pathsep + str(cp),
                    "ToyStageProbe",
                ]))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(len(outputs[0].splitlines()), 28)
            self.assertIn("STAGE:GATE_00:0:false:true:true", outputs[0])
            self.assertIn("STAGE:GATE_26:26:true:true:true", outputs[0])
            self.assertTrue(outputs[0].endswith("CLONE:true\n"))

    def test_modified_constructor_cannot_preserve_compiled_class_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, previous = self.build(root / "one")
            _, altered = self.build(root / "two", True)
            self.assertNotEqual(previous, altered)
            one = self.restore(root / "one", previous)
            two = self.restore(root / "two", altered)
            self.assertNotEqual(
                (one / "toy/stage/Pass.class").read_bytes(),
                (two / "toy/stage/Pass.class").read_bytes(),
            )

    def test_missing_or_unreviewed_enum_fields_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, binary = self.build(root)
            with self.assertRaisesRegex(
                ValueError, "MISSING_ORIGINAL_ENUM_MEMBER",
            ):
                restore_enum_member_identity(
                    binary, "toy/stage/Pass",
                    {"GATE_00": "a", "GATE_99": "b", "$VALUES": "B"}, "a",
                )
            with self.assertRaises(ValueError):
                restore_enum_member_identity(
                    b"invalid", "toy/stage/Pass",
                    {"GATE_00": "a", "$VALUES": "B"}, "a",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

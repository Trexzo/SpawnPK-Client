"""Synthetic-only Java9 enum restoration; no original SpawnPK source or binary."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from spk_recovery.enum_member_identity import restore_enum_member_identity

SOURCE = "package toy.enums; public enum ColorMode {RED,GREEN,BLUE;}\n"
PROBE = """import java.lang.reflect.*;
public final class ToyEnumProbe {
 public static void main(String[] ignored)throws Exception{
  Class<?> type=Class.forName("toy.enums.ColorMode");
  Object[] all=(Object[])type.getMethod("values").invoke(null);
  for(int i=0;i<all.length;i++){
   Enum<?> e=(Enum<?>)all[i];
   String field=String.valueOf((char)('a'+i));
   System.out.println("CONST:"+e.name()+":"+e.ordinal()+":"+e.toString()+":"+
     (type.getField(field).get(null)==e)+":"+
     (type.getMethod("valueOf",String.class).invoke(null,e.name())==e));
  }
 }
}
"""


def execute(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=50)
    if p.returncode:
        raise RuntimeError(p.stderr[-1500:])
    return p.stdout


@unittest.skipUnless(
    all(shutil.which(x) for x in ("java", "javac", "javap")),
    "Java9-capable JDK required",
)
class ToyEnumRestoration(unittest.TestCase):
    def fixture(self, root):
        source = root / "src/toy/enums/ColorMode.java"
        source.parent.mkdir(parents=True)
        source.write_text(SOURCE, encoding="utf-8")
        compiled = root / "before"
        compiled.mkdir()
        execute([
            "javac", "--release", "9", "-g:none", "-proc:none",
            "-d", str(compiled), str(source),
        ])
        return (compiled / "toy/enums/ColorMode.class").read_bytes()

    def test_field_helper_alias_preserves_actual_enum_names_and_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = self.fixture(root)
            altered = restore_enum_member_identity(
                binary, "toy/enums/ColorMode",
                {"RED": "a", "GREEN": "b", "BLUE": "c", "$VALUES": "d"}, "a",
            )
            target = root / "after/toy/enums/ColorMode.class"
            target.parent.mkdir(parents=True)
            target.write_bytes(altered)
            disassembly = execute([
                "javap", "-p", "-c", "-classpath", str(root / "after"),
                "toy.enums.ColorMode",
            ])
            self.assertIn("public static final toy.enums.ColorMode a;", disassembly)
            self.assertIn("private static toy.enums.ColorMode[] a();", disassembly)
            self.assertIn("String RED", disassembly)
            probe = root / "ToyEnumProbe.java"
            probe.write_text(PROBE, encoding="utf-8")
            execute([
                "javac", "--release", "9", "-d", str(root), str(probe),
            ])
            result = execute([
                "java", "-cp", str(root) + os.pathsep + str(root / "after"),
                "ToyEnumProbe",
            ])
            self.assertEqual(len(result.splitlines()), 3)
            self.assertTrue(
                all(line.endswith(":true:true") for line in result.splitlines())
            )
            self.assertIn("CONST:RED:0:RED", result)
            self.assertIn("CONST:BLUE:2:BLUE", result)

    def test_missing_original_member_and_nonclass_bytes_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = self.fixture(Path(temp))
            with self.assertRaisesRegex(
                ValueError, "MISSING_ORIGINAL_ENUM_MEMBER"
            ):
                restore_enum_member_identity(
                    binary, "toy/enums/ColorMode",
                    {"RED": "a", "NOT_A_FIELD": "b", "$VALUES": "d"}, "a",
                )
            with self.assertRaises(ValueError):
                restore_enum_member_identity(
                    b"notaclass", "toy/enums/ColorMode",
                    {"RED": "a", "$VALUES": "d"}, "a",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

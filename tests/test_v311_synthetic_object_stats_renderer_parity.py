"""Independent synthetic JDK9 record, counter and Swing-renderer parity tests.

These are unrelated toy source files, not owner-recovered original-v311 Java.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError,
    verify_standalone_sources,
)

SOURCES = {
    "rs/synthetic83/ToyInteraction.java": """
package rs.synthetic83;
public final class ToyInteraction {
 private int id, row;
 public ToyInteraction(){}
 public void setId(int value){id=value;}
 public void setRow(int value){row=value;}
 public int getId(){return id;}
 public int getRow(){return row;}
 public int score(){return id*7+row;}
}
""",
    "rs/synthetic83/ToyCounter.java": """
package rs.synthetic83;
public final class ToyCounter {
 private int successes, total;
 public ToyCounter(int total){this.total=total;}
 public void add(boolean success){total++;if(success)successes++;}
 public float fraction(){return total==0?0f:(float)successes/(float)total;}
 public int successes(){return successes;}
 public String toString(){return "Ratio="+successes+"/"+total;}
}
""",
    "rs/synthetic83/ToyColorRenderer.java": """
package rs.synthetic83;
import java.awt.Color;
import java.awt.Component;
import javax.swing.*;
public final class ToyColorRenderer extends DefaultListCellRenderer {
 private final JComboBox<String> box;
 private final Color[] shades;
 public ToyColorRenderer(JComboBox<String> box, Color[] shades){
  this.box=box;this.shades=shades;setOpaque(true);
 }
 @Override public Component getListCellRendererComponent(
  JList<?> list,Object text,int index,boolean selected,boolean focus){
  JLabel result=(JLabel)super.getListCellRendererComponent(
   list,text,index,selected,focus);
  result.setForeground(shades[index==-1?box.getSelectedIndex():index]);
  return result;
 }
}
""",
}

PROBE = """
import rs.synthetic83.*;
import java.awt.Color;
import javax.swing.*;
public final class Synthetic83Transcript {
 public static void main(String[] ignored) {
  for(int i:new int[]{Integer.MIN_VALUE,-7,0,23,Integer.MAX_VALUE}){
   ToyInteraction event=new ToyInteraction();
   event.setId(i);event.setRow(i*3);
   System.out.println("EVENT:"+event.getId()+":"+event.getRow()+":"+event.score());
  }
  for(boolean yes:new boolean[]{false,true}){
   ToyCounter c=new ToyCounter(1);c.add(yes);
   System.out.println("COUNTER:"+c+":"+Float.floatToRawIntBits(c.fraction()));
  }
  JComboBox<String> combo=new JComboBox<>(new String[]{"A","B"});
  Color[] palette={Color.BLUE,Color.GREEN};
  ToyColorRenderer painter=new ToyColorRenderer(combo,palette);
  JList<String> list=new JList<>(new String[]{"A","B"});
  for(int i=0;i<2;i++){
   combo.setSelectedIndex(i);
   JLabel label=(JLabel)painter.getListCellRendererComponent(list,"label",-1,false,false);
   System.out.println("SELECT:"+i+":"+label.getForeground().getRGB());
  }
 }
}
"""


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def execute(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=45)
    if p.returncode:
        raise AssertionError(p.stderr[-1800:])
    return p.stdout


@unittest.skipUnless(
    all(shutil.which(exe) for exe in ("javac", "javap", "java")),
    "Java 9-capable JDK required",
)
class Synthetic83SourceTests(unittest.TestCase):
    def fixture(self, root: Path):
        source = root / "source"
        for name, body in SOURCES.items():
            dest = source / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")
        classes = root / "original"
        classes.mkdir()
        execute([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-sp"),
            "-d", str(classes),
            *[str(source / name) for name in sorted(SOURCES)],
        ])
        archive = root / "toy-original.jar"
        with zipfile.ZipFile(archive, "w") as jar:
            for clazz in sorted(classes.rglob("*.class")):
                jar.writestr(clazz.relative_to(classes).as_posix(), clazz.read_bytes())
        with zipfile.ZipFile(archive) as jar:
            pins = {name: sha(jar.read(name)) for name in jar.namelist()}
        self.assertEqual(len(pins), 3)
        return source, archive, pins

    def test_complete_closed_source_parity_and_nine_behaviors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, archive, pins = self.fixture(root)
            report = verify_standalone_sources(
                archive, source, root / "rebuilt",
                original_sha256=sha(archive.read_bytes()),
                class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 3)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            probe = root / "Synthetic83Transcript.java"
            probe.write_text(PROBE, encoding="utf-8")
            execute(["javac", "--release", "9", "-cp", str(archive),
                     "-d", str(root), str(probe)])
            transcripts = []
            for compiled in (archive, root / "rebuilt" / "classes"):
                transcripts.append(execute([
                    "java", "-Djava.awt.headless=true",
                    "-cp", str(root) + os.pathsep + str(compiled),
                    "Synthetic83Transcript",
                ]))
            self.assertEqual(transcripts[0], transcripts[1])
            self.assertEqual(len(transcripts[0].splitlines()), 9)

    def test_changed_integer_accessor_fails_exact_original_instructions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, archive, pins = self.fixture(root)
            target = source / "rs/synthetic83/ToyInteraction.java"
            original = target.read_text()
            modified = original.replace("getId(){return id;}", "getId(){return row;}")
            self.assertNotEqual(original, modified)
            target.write_text(modified)
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    archive, source, root / "rejected",
                    original_sha256=sha(archive.read_bytes()), class_sha256=pins,
                )

    def test_changed_counter_math_fails_original_instructions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, archive, pins = self.fixture(root)
            target = source / "rs/synthetic83/ToyCounter.java"
            text = target.read_text()
            target.write_text(text.replace(
                "(float)successes/(float)total",
                "(float)total/(float)successes",
            ))
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    archive, source, root / "rejected",
                    original_sha256=sha(archive.read_bytes()), class_sha256=pins,
                )

    def test_missing_original_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, archive, pins = self.fixture(root)
            (source / "rs/synthetic83/ToyColorRenderer.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    archive, source, root / "rejected",
                    original_sha256=sha(archive.read_bytes()), class_sha256=pins,
                )

    def test_wrong_original_jar_authority_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, archive, pins = self.fixture(root)
            with self.assertRaisesRegex(
                StandaloneSourceParityError, "WRONG_ORIGINAL_JAR",
            ):
                verify_standalone_sources(
                    archive, source, root / "rejected",
                    original_sha256="0" * 64, class_sha256=pins,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

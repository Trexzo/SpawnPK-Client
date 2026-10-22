"""Unrelated synthetic Java9 scrollbar source-island parity and raster check.

Neither original v311 game binaries nor reconstructed game source is used.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)

SOURCES = {
    "rs/synthetic/ScrollPalette.java": """
package rs.synthetic;
import java.awt.Color;
public final class ScrollPalette {
 public static final Color THUMB = new Color(70,110,170);
 public static final Color TRACK = new Color(20,30,40);
}
""",
    "rs/synthetic/MockBar.java": """
package rs.synthetic;
import java.awt.*; import javax.swing.*;
import javax.swing.plaf.*; import javax.swing.plaf.basic.*;
public class MockBar extends BasicScrollBarUI {
 private Color thumb=ScrollPalette.THUMB;
 private Color track=ScrollPalette.TRACK;
 public static ComponentUI createUI(JComponent c) {
  JScrollBar bar=(JScrollBar)c;
  bar.setUnitIncrement(16);
  bar.setPreferredSize(new Dimension(7,7));
  return new MockBar();
 }
 public void setThumb(Color color){thumb=color;}
 protected void paintThumb(Graphics g,JComponent c,Rectangle r){
  g.setColor(thumb); g.fillRect(r.x,r.y,r.width,r.height);
 }
 protected void paintTrack(Graphics g,JComponent c,Rectangle r){
  g.setColor(track); g.fillRect(r.x,r.y,r.width,r.height);
 }
 public void draw(Graphics g,JScrollBar bar,int kind){
  if(kind==0)paintTrack(g,bar,new Rectangle(3,4,15,8));
  else paintThumb(g,bar,new Rectangle(3,4,15,8));
 }
}
""",
}

PROBE = """
import java.awt.*;import java.awt.image.*;import java.security.*;
import javax.swing.*;import rs.synthetic.MockBar;
public final class SyntheticScrollProbe {
 public static void main(String[] ignored)throws Exception {
  System.setProperty("java.awt.headless","true");
  JScrollBar bar=new JScrollBar();
  Object created=MockBar.createUI(bar);
  if(!(created instanceof MockBar))throw new AssertionError("wrong ui");
  System.out.println("setup:"+bar.getUnitIncrement()+":"+bar.getPreferredSize());
  MockBar ui=new MockBar();
  for(int mode=0;mode<4;mode++){
   if(mode>1)ui.setThumb(new Color(100,20*mode,30));
   BufferedImage im=new BufferedImage(34,20,BufferedImage.TYPE_INT_ARGB);
   Graphics g=im.getGraphics();
   g.setColor(Color.BLACK);g.fillRect(0,0,34,20);
   ui.draw(g,bar,mode%2);g.dispose();
   MessageDigest h=MessageDigest.getInstance("SHA-256");
   for(int y=0;y<20;y++)for(int x=0;x<34;x++){
    int p=im.getRGB(x,y);
    h.update((byte)(p>>>24));h.update((byte)(p>>>16));
    h.update((byte)(p>>>8));h.update((byte)p);
   }
   StringBuilder out=new StringBuilder();
   for(byte b:h.digest())out.append(String.format("%02x",b&255));
   System.out.println("raster:"+mode+":"+out);
  }
 }
}
"""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(
    all(shutil.which(x) for x in ("javac", "java", "javap")),
    "JDK and headless Java2D are required",
)
class SyntheticScrollbarParity(unittest.TestCase):
    def fixture(self, root: Path):
        source = root / "sources"
        for name, body in SOURCES.items():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        originals = root / "original-compiled"
        originals.mkdir()
        run = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-encoding", "UTF-8", "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-sp"), "-d", str(originals),
            *[str(source / name) for name in sorted(SOURCES)],
        ], capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr)
        jar = root / "synthetic-original.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for file in sorted(originals.rglob("*.class")):
                archive.writestr(file.relative_to(originals).as_posix(), file.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            pins = {name: digest(archive.read(name)) for name in archive.namelist()}
        self.assertEqual(len(pins), 2)
        return source, jar, pins

    def test_two_source_classes_and_four_exact_rasters(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, jar, pins = self.fixture(root)
            report = verify_standalone_sources(
                jar, source, root / "rebuilt",
                original_sha256=digest(jar.read_bytes()), class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 2)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertGreaterEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"], 1,
            )
            probe = root / "SyntheticScrollProbe.java"
            probe.write_text(PROBE, encoding="utf-8")
            compile_probe = subprocess.run([
                "javac", "--release", "9", "-cp", str(jar),
                "-d", str(root), str(probe),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(compile_probe.returncode, 0, compile_probe.stderr)
            output = []
            for cp in (jar, root / "rebuilt" / "classes"):
                result = subprocess.run([
                    "java", "-Djava.awt.headless=true", "-cp",
                    str(root) + __import__("os").pathsep + str(cp),
                    "SyntheticScrollProbe",
                ], capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stderr)
                output.append(result.stdout)
            self.assertEqual(output[0], output[1])
            self.assertEqual(output[0].count("raster:"), 4)
            self.assertIn("setup:16:java.awt.Dimension[width=7,height=7]", output[0])

    def test_altered_scrollbar_unit_increment_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, jar, pins = self.fixture(root)
            path = source / "rs/synthetic/MockBar.java"
            path.write_text(path.read_text(encoding="utf-8").replace(
                "bar.setUnitIncrement(16)", "bar.setUnitIncrement(17)"
            ), encoding="utf-8")
            with self.assertRaisesRegex(StandaloneSourceParityError,
                                        "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"):
                verify_standalone_sources(
                    jar, source, root / "rejected",
                    original_sha256=digest(jar.read_bytes()), class_sha256=pins,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

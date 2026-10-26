"""Synthetic Java9 UI font/banner/meter closure and pixel parity.

Public fixtures intentionally do not reproduce original SpawnPK client Java.
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
from spk_recovery.source_dependency_closure import (
    SourceClosureError, require_selected_source_closure,
)

SOURCES = {
    "rs/synthetic/TypefaceVault.java": r"""
package rs.synthetic;
import java.awt.Font;
public class TypefaceVault {
 public static Font headerFont() {return new Font("Dialog", Font.BOLD, 13);}
}
""",
    "rs/synthetic/BannerPanel.java": r"""
package rs.synthetic;
import java.awt.*;import javax.swing.*;
public class BannerPanel extends JPanel {
 private final JLabel heading = new JLabel();
 public BannerPanel() {
  setLayout(new BorderLayout());
  heading.setFont(TypefaceVault.headerFont());
  heading.setForeground(Color.WHITE);
  add(heading, BorderLayout.NORTH);
 }
 public void heading(String text) {heading.setText(text);}
}
""",
    "rs/synthetic/MeterWidget.java": r"""
package rs.synthetic;
import java.awt.*;
public class MeterWidget extends BannerPanel {
 private int value;
 public void progress(int next) {value=next;repaint();}
 @Override public void paint(Graphics g) {
  g.setColor(new Color(32,40,47));
  g.fillRect(0,0,getWidth(),getHeight());
  g.setColor(new Color(66,145,135));
  g.fillRect(0,34,getWidth()*value/100,8);
  super.paintComponents(g);
 }
}
""",
}

PROBE = r"""
import java.awt.*;import java.awt.image.*;import java.io.*;
import java.net.*;import java.security.*;import java.lang.reflect.*;
public final class SyntheticMeterPixels {
 static String render(URL url, String label, int value)throws Exception {
  try(URLClassLoader cl=new URLClassLoader(new URL[]{url},ClassLoader.getPlatformClassLoader())){
   Class<?> c=cl.loadClass("rs.synthetic.MeterWidget");
   Component widget=(Component)c.getConstructor().newInstance();
   c.getMethod("heading",String.class).invoke(widget,label);
   c.getMethod("progress",int.class).invoke(widget,value);
   widget.setSize(220,46);
   ((Container)widget).doLayout();
   BufferedImage im=new BufferedImage(220,46,BufferedImage.TYPE_INT_ARGB);
   Graphics graphics=im.getGraphics(); widget.paint(graphics);graphics.dispose();
   MessageDigest sha=MessageDigest.getInstance("SHA-256");
   for(int y=0;y<im.getHeight();y++)for(int x=0;x<im.getWidth();x++){
    int p=im.getRGB(x,y);
    sha.update((byte)(p>>>24));sha.update((byte)(p>>>16));
    sha.update((byte)(p>>>8));sha.update((byte)p);
   }
   StringBuilder out=new StringBuilder();
   for(byte b:sha.digest())out.append(String.format("%02x",b&255));
   return out.toString();
  }
 }
 public static void main(String[] args)throws Exception{
  System.setProperty("java.awt.headless","true");
  URL first=new File(args[0]).toURI().toURL();
  URL second=new File(args[1]).toURI().toURL();
  int cases=0;
  for(String label:new String[]{"Small","Progress",""})
   for(int value:new int[]{0,73}) {
    if(!render(first,label,value).equals(render(second,label,value)))
     throw new AssertionError("SYNTHETIC_METER_PIXELS_DIFFER");
    cases++;
   }
  if(cases!=6)throw new AssertionError("UNEXPECTED_COUNT");
  System.out.println("SYNTHETIC_THREE_CLASS_PIXEL_PARITY_6_PASS");
 }
}
"""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(all(shutil.which(x) for x in ("javac", "javap", "java")),
                     "Requires JDK Java9 source compiler and Swing")
class SyntheticThreeComponentTests(unittest.TestCase):
    def fixture(self, root: Path):
        source = root / "sources"
        for name, data in SOURCES.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding="utf-8")
        compiled = root / "compiled"
        compiled.mkdir()
        run = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-source"),
            "-d", str(compiled),
            *[str(source / name) for name in sorted(SOURCES)],
        ], capture_output=True, text=True, timeout=45)
        self.assertEqual(run.returncode, 0, run.stderr)
        jar = root / "synthetic.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for path in sorted(compiled.rglob("*.class")):
                archive.writestr(path.relative_to(compiled).as_posix(),
                                 path.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            pins = {path: digest(archive.read(path)) for path in archive.namelist()}
        self.assertEqual(len(pins), 3)
        return source, jar, pins

    def test_three_connected_classes_exact_instructions_and_rasters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, jar, pins = self.fixture(root)
            report = verify_standalone_sources(
                jar, source, root / "rebuilt",
                original_sha256=digest(jar.read_bytes()), class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 3)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertGreaterEqual(report["explicit_original_project_dependency_closure"]
                                    ["source_project_dependency_edges"], 2)
            probe = root / "SyntheticMeterPixels.java"
            probe.write_text(PROBE, encoding="utf-8")
            compile_probe = subprocess.run([
                "javac", "--release", "9", "-d", str(root), str(probe),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(compile_probe.returncode, 0, compile_probe.stderr)
            run = subprocess.run([
                "java", "-Djava.awt.headless=true", "-cp", str(root),
                "SyntheticMeterPixels", str(jar), str(root / "rebuilt" / "classes"),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("SYNTHETIC_THREE_CLASS_PIXEL_PARITY_6_PASS", run.stdout)

    def test_missing_typeface_in_selection_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, jar, _ = self.fixture(root)
            with zipfile.ZipFile(jar) as archive:
                with self.assertRaisesRegex(SourceClosureError,
                                            "PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION"):
                    require_selected_source_closure(archive, {
                        "rs/synthetic/BannerPanel.class",
                        "rs/synthetic/MeterWidget.class",
                    })

    def test_changed_synthetic_progress_height_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, jar, pins = self.fixture(root)
            meter = source / "rs/synthetic/MeterWidget.java"
            meter.write_text(meter.read_text(encoding="utf-8").replace(
                "getWidth()*value/100,8", "getWidth()*value/100,7",
            ), encoding="utf-8")
            with self.assertRaisesRegex(StandaloneSourceParityError,
                                        "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"):
                verify_standalone_sources(
                    jar, source, root / "rejected",
                    original_sha256=digest(jar.read_bytes()), class_sha256=pins,
                )
            self.assertFalse((root / "rejected" / "SOURCE-REBUILD-VERIFY.json").exists())

    def test_changed_synthetic_font_size_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, jar, pins = self.fixture(root)
            utility = source / "rs/synthetic/TypefaceVault.java"
            utility.write_text(utility.read_text(encoding="utf-8").replace(
                "Font.BOLD, 13", "Font.BOLD, 14",
            ), encoding="utf-8")
            with self.assertRaisesRegex(StandaloneSourceParityError,
                                        "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"):
                verify_standalone_sources(
                    jar, source, root / "rejected",
                    original_sha256=digest(jar.read_bytes()), class_sha256=pins,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

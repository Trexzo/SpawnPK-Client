"""JDK-only synthetic connected Swing label/UI source and raster parity.

Public fixtures are NOT original v311 proprietary classes or reconstructed code.
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
    "rs/synthetic/GlowCaption.java": """
package rs.synthetic;
import java.awt.*; import javax.swing.*;
public final class GlowCaption extends JLabel {
    private Color secondaryColor = new Color(90,30,120);
    public GlowCaption(String text) { super(text); setUI(new GlowCaptionUI()); }
    public Color secondaryColor() { return secondaryColor; }
    public void secondaryColor(Color c) { secondaryColor=c; repaint(); }
}
""",
    "rs/synthetic/GlowCaptionUI.java": """
package rs.synthetic;
import java.awt.*; import javax.swing.*; import javax.swing.plaf.basic.*;
public final class GlowCaptionUI extends BasicLabelUI {
    protected void paintEnabledText(JLabel label, Graphics g, String text, int x, int y) {
        if (label instanceof GlowCaption) {
            g.setColor(((GlowCaption) label).secondaryColor());
            g.drawString(text, x + 2, y + 4);
        }
        g.setColor(label.getForeground());
        g.drawString(text,x,y);
    }
}
""",
}

PROBE = r"""
import java.awt.*;import java.awt.image.*;import java.io.*;import java.net.*;
import java.security.*;import javax.swing.*;
public final class SyntheticCaptionPixels {
 static String raster(URL location,String text,Color c)throws Exception{
  try(URLClassLoader loader=new URLClassLoader(new URL[]{location},
                                             ClassLoader.getPlatformClassLoader())){
   Class<?> caption=loader.loadClass("rs.synthetic.GlowCaption");
   JLabel label=(JLabel)caption.getConstructor(String.class).newInstance(text);
   label.setForeground(Color.WHITE);
   label.setFont(new Font("Dialog",Font.PLAIN,14));
   caption.getMethod("secondaryColor",Color.class).invoke(label,c);
   label.setSize(145,37);
   BufferedImage img=new BufferedImage(145,37,BufferedImage.TYPE_INT_ARGB);
   Graphics g=img.getGraphics();label.paint(g);g.dispose();
   MessageDigest h=MessageDigest.getInstance("SHA-256");
   for(int y=0;y<img.getHeight();y++)for(int x=0;x<img.getWidth();x++){
    int pixel=img.getRGB(x,y);
    h.update((byte)(pixel>>>24));h.update((byte)(pixel>>>16));
    h.update((byte)(pixel>>>8));h.update((byte)pixel);
   }
   StringBuilder out=new StringBuilder();
   for(byte b:h.digest())out.append(String.format("%02x",b&255));
   return out.toString();
  }
 }
 public static void main(String[] args)throws Exception{
  System.setProperty("java.awt.headless","true");
  UIManager.setLookAndFeel(UIManager.getCrossPlatformLookAndFeelClassName());
  URL original=new File(args[0]).toURI().toURL();
  URL rebuilt=new File(args[1]).toURI().toURL();
  for(String message:new String[]{"abc","Visual","Caption"})
   for(Color c:new Color[]{Color.RED,Color.DARK_GRAY})
    if(!raster(original,message,c).equals(raster(rebuilt,message,c)))
     throw new AssertionError("SYNTHETIC_CAPTION_PIXEL_MISMATCH");
  System.out.println("SYNTHETIC_CAPTION_PIXEL_PARITY_6_PASS");
 }
}
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(
    all(shutil.which(x) for x in ("javac", "javap", "java")),
    "JDK and Java2D required",
)
class SyntheticCaptionDependencyTests(unittest.TestCase):
    def fixture(self, root: Path):
        source = root / "sources"
        for name, data in SOURCES.items():
            p = source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(data, encoding="utf-8")
        original_classes = root / "synthetic-original-classes"
        original_classes.mkdir()
        run = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-sourcepath"),
            "-d", str(original_classes),
            *[str(source / name) for name in sorted(SOURCES)],
        ], capture_output=True, text=True, timeout=45)
        self.assertEqual(run.returncode, 0, run.stderr)
        jar = root / "synthetic-original.jar"
        with zipfile.ZipFile(jar, "w") as z:
            for p in sorted(original_classes.rglob("*.class")):
                z.writestr(p.relative_to(original_classes).as_posix(), p.read_bytes())
        with zipfile.ZipFile(jar) as z:
            pins = {name: sha(z.read(name)) for name in z.namelist()}
        self.assertEqual(len(pins), 2)
        return source, jar, pins

    def test_two_connected_java9_classes_exact_bytecode_and_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src, jar, pins = self.fixture(root)
            report = verify_standalone_sources(
                jar, src, root / "accepted",
                original_sha256=sha(jar.read_bytes()), class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 2)
            self.assertEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"
                ], 2,
            )
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            probe = root / "SyntheticCaptionPixels.java"
            probe.write_text(PROBE, encoding="utf-8")
            built = subprocess.run([
                "javac", "--release", "9", "-d", str(root), str(probe),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(built.returncode, 0, built.stderr)
            compared = subprocess.run([
                "java", "-Djava.awt.headless=true", "-cp", str(root),
                "SyntheticCaptionPixels", str(jar),
                str(root / "accepted" / "classes"),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(compared.returncode, 0, compared.stderr)
            self.assertIn("SYNTHETIC_CAPTION_PIXEL_PARITY_6_PASS", compared.stdout)

    def test_modified_synthetic_shadow_offset_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src, jar, pins = self.fixture(root)
            painter = src / "rs/synthetic/GlowCaptionUI.java"
            painter.write_text(
                painter.read_text(encoding="utf-8").replace(
                    "x + 2, y + 4", "x + 4, y + 4",
                ), encoding="utf-8",
            )
            output = root / "rejected"
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, src, output,
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins,
                )
            self.assertFalse((output / "SOURCE-REBUILD-VERIFY.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

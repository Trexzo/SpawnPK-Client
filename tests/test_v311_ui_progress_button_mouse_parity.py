"""Synthetic UI parity: three JDK-only controls, raster and mouse behavior.

Deliberately NOT original SpawnPK code, original JAR or private Java.
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
    "rs/synthetic/ProgressStrip.java": """
package rs.synthetic;
import java.awt.*; import javax.swing.*;
public final class ProgressStrip extends JPanel {
    private int total = 100, completed;
    public void set(int n) { completed = n; }
    public void paintComponent(Graphics g) {
        super.paintComponent(g);
        g.setColor(new Color(40,110,200));
        g.fillRect(0,0,getWidth()*completed/total,getHeight());
    }
}
""",
    "rs/synthetic/ColorSwatch.java": """
package rs.synthetic;
import java.awt.*; import javax.swing.*;
public final class ColorSwatch extends JComponent {
    private final Color tint = new Color(40,90,160,230);
    public void paintComponent(Graphics g) {
        super.paintComponent(g);
        g.setColor(tint);
        g.fillRoundRect(3,2,getWidth()-6,getHeight()-4,8,8);
    }
}
""",
    "rs/synthetic/ClickRelay.java": """
package rs.synthetic;
import java.awt.*; import java.awt.event.*; import javax.swing.*;
public final class ClickRelay extends MouseAdapter {
    private final Component destination;
    public ClickRelay(Component target) { destination = target; }
    public void mousePressed(MouseEvent event) {
        if (SwingUtilities.isLeftMouseButton(event)) {
            MouseEvent copy = SwingUtilities.convertMouseEvent(
                (Component)event.getSource(),event,destination);
            destination.dispatchEvent(copy);
        }
    }
}
""",
}

PROBE = r"""
import java.awt.*; import java.awt.event.*; import java.awt.image.*;
import java.net.*; import java.io.*; import java.security.*; import javax.swing.*;
public final class SyntheticUiEvidence {
    static String pixels(BufferedImage image) throws Exception {
        MessageDigest sha = MessageDigest.getInstance("SHA-256");
        for(int y=0;y<image.getHeight();y++)for(int x=0;x<image.getWidth();x++){
            int p=image.getRGB(x,y);
            sha.update((byte)(p>>>24));sha.update((byte)(p>>>16));
            sha.update((byte)(p>>>8));sha.update((byte)p);
        }
        StringBuilder text=new StringBuilder();
        for(byte b:sha.digest())text.append(String.format("%02x",b&255));
        return text.toString();
    }
    static String run(URL sourceUrl) throws Exception {
        try(URLClassLoader loader=new URLClassLoader(new URL[]{sourceUrl},
                ClassLoader.getPlatformClassLoader())) {
            StringBuilder result=new StringBuilder();
            Class<?> kind=loader.loadClass("rs.synthetic.ProgressStrip");
            for(int amount:new int[]{0,24,73,100}){
                JPanel progress=(JPanel)kind.getConstructor().newInstance();
                kind.getMethod("set",int.class).invoke(progress,amount);
                progress.setSize(74,16);
                BufferedImage img=new BufferedImage(74,16,BufferedImage.TYPE_INT_ARGB);
                Graphics g=img.getGraphics();progress.paint(g);g.dispose();
                result.append(pixels(img)).append(';');
            }
            kind=loader.loadClass("rs.synthetic.ColorSwatch");
            JComponent swatch=(JComponent)kind.getConstructor().newInstance();
            swatch.setSize(74,16);
            BufferedImage img=new BufferedImage(74,16,BufferedImage.TYPE_INT_ARGB);
            Graphics g=img.getGraphics();swatch.paint(g);g.dispose();
            result.append(pixels(img)).append(';');
            JPanel root=new JPanel(null),from=new JPanel(),to=new JPanel();
            root.setSize(140,90);from.setBounds(7,9,40,40);
            to.setBounds(30,27,40,40);root.add(from);root.add(to);
            StringBuilder events=new StringBuilder();
            to.addMouseListener(new MouseAdapter(){
                public void mousePressed(MouseEvent e){
                    events.append(e.getX()).append(',').append(e.getY())
                          .append(',').append(e.getButton()).append(';');
                }
            });
            Class<?> relay=loader.loadClass("rs.synthetic.ClickRelay");
            Object adapter=relay.getConstructor(Component.class).newInstance(to);
            for(int button:new int[]{MouseEvent.BUTTON1,MouseEvent.BUTTON3}){
                MouseEvent e=new MouseEvent(from,MouseEvent.MOUSE_PRESSED,1234L,
                        0,8,10,1,false,button);
                relay.getMethod("mousePressed",MouseEvent.class).invoke(adapter,e);
            }
            if(!events.toString().equals("-15,-8,1;"))
                throw new AssertionError("Incorrect synthetic event relay "+events);
            return result.append(events).toString();
        }
    }
    public static void main(String[] args)throws Exception{
        System.setProperty("java.awt.headless","true");
        UIManager.setLookAndFeel(UIManager.getCrossPlatformLookAndFeelClassName());
        String before=run(new File(args[0]).toURI().toURL());
        String after=run(new File(args[1]).toURI().toURL());
        if(!before.equals(after))
            throw new AssertionError("SYNTHETIC_UI_PIXELS_OR_EVENTS_DIFFER");
        System.out.println("SYNTHETIC_UI_RASTER_AND_MOUSE_PARITY_PASS");
    }
}
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(
    all(shutil.which(tool) for tool in ("javac", "javap", "java")),
    "JDK with headless Java2D required",
)
class SyntheticUiControlsParityTests(unittest.TestCase):
    def fixture(self, root: Path):
        src = root / "sources"
        for relative, code in SOURCES.items():
            file = src / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(code, encoding="utf-8")
        classes = root / "original-synthetic-classes"
        classes.mkdir()
        proc = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-cp"),
            "-sourcepath", str(root / "empty-sp"),
            "-d", str(classes),
            *[str(src / name) for name in sorted(SOURCES)],
        ], capture_output=True, text=True, timeout=50)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        jar = root / "synthetic-original.jar"
        with zipfile.ZipFile(jar, "w") as z:
            for file in sorted(classes.rglob("*.class")):
                z.writestr(file.relative_to(classes).as_posix(), file.read_bytes())
        with zipfile.ZipFile(jar) as z:
            pins = {name: sha(z.read(name)) for name in z.namelist()}
        self.assertEqual(len(pins), 3)
        return src, jar, pins

    def test_java9_ui_bytecode_pixels_and_mouse_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, jar, pins = self.fixture(root)
            report = verify_standalone_sources(
                jar, source, root / "accepted",
                original_sha256=sha(jar.read_bytes()), class_sha256=pins,
            )
            self.assertEqual(report["total_classes"], 3)
            self.assertTrue(report["all_passed"])
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            program = root / "SyntheticUiEvidence.java"
            program.write_text(PROBE, encoding="utf-8")
            compiled = subprocess.run([
                "javac", "--release", "9", "-d", str(root), str(program),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([
                "java", "-Djava.awt.headless=true", "-cp", str(root),
                "SyntheticUiEvidence", str(jar), str(root / "accepted" / "classes"),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("SYNTHETIC_UI_RASTER_AND_MOUSE_PARITY_PASS", result.stdout)

    def test_modified_ui_color_rejected_without_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, jar, pins = self.fixture(root)
            swatch = source / "rs/synthetic/ColorSwatch.java"
            swatch.write_text(
                swatch.read_text(encoding="utf-8").replace(
                    "new Color(40,90,160,230)", "new Color(40,90,161,230)"
                ), encoding="utf-8",
            )
            out = root / "altered-color"
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, source, out,
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins,
                )
            self.assertFalse((out / "SOURCE-REBUILD-VERIFY.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Synthetic JDK-only UI dependency island and deterministic headless raster parity.

Real v311 UI source and original proprietary game JAR are NOT bundled.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import verify_standalone_sources
from spk_recovery.source_dependency_closure import explicit_class_references


SOURCES = {
    "rs/ui/components/w.java": (
        "package rs.ui.components; import java.awt.*;"
        " public interface w { Dimension a(Graphics2D g); }"
    ),
    "rs/ui/components/d.java": (
        "package rs.ui.components; import java.awt.*;"
        " public class d { public static final Color c ="
        " new Color(70,61,50,156); }"
    ),
    "rs/ui/components/a.java": (
        "package rs.ui.components; import java.awt.*;"
        " public class a implements w {"
        " private Color f = d.c;"
        " private Rectangle g = new Rectangle(2,3,12,11);"
        " private boolean h = true;"
        " public a() {}"
        " public a(Color color, Rectangle bounds, boolean visible)"
        " { f=color; g=bounds; h=visible; }"
        " public Dimension a(Graphics2D painter) {"
        " if (h) { painter.setColor(f); painter.fill(g); }"
        " return new Dimension(g.getSize());"
        " } }"
    ),
}


PROBE = r"""
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.security.MessageDigest;
import java.nio.ByteBuffer;

public class OriginalVsRebuiltRaster {
    private static byte[] raster(URL source) throws Exception {
        try (URLClassLoader loader =
                 new URLClassLoader(new URL[]{source}, null)) {
            Class<?> renderer = Class.forName("rs.ui.components.a", true, loader);
            Object instance = renderer.getConstructor(
                Color.class, Rectangle.class, boolean.class
            ).newInstance(new Color(100,110,120,180),
                          new Rectangle(2,3,12,11), true);
            BufferedImage img = new BufferedImage(
                20, 20, BufferedImage.TYPE_INT_ARGB
            );
            Graphics2D graphics = img.createGraphics();
            Dimension size = (Dimension) renderer.getMethod(
                "a", Graphics2D.class
            ).invoke(instance, graphics);
            graphics.dispose();
            if (size.width != 12 || size.height != 11)
                throw new AssertionError("Unexpected size");
            ByteBuffer bytes = ByteBuffer.allocate(20*20*4);
            for (int y=0; y<20; y++)
                for (int x=0; x<20; x++)
                    bytes.putInt(img.getRGB(x,y));
            return MessageDigest.getInstance("SHA-256").digest(bytes.array());
        }
    }
    public static void main(String[] args) throws Exception {
        byte[] original = raster(new File(args[0]).toURI().toURL());
        byte[] rebuilt = raster(new File(args[1]).toURI().toURL());
        if (!java.util.Arrays.equals(original, rebuilt))
            throw new AssertionError("RASTER_PARITY_FAILED");
        System.out.println("SYNTHETIC_UI_RASTER_PARITY_PASS");
    }
}
"""


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("javap") and shutil.which("java"),
    "Requires JDK for source bytecode and headless raster parity",
)
class UiBorderDependencyParityTests(unittest.TestCase):
    def test_three_original_name_ui_classes_build_without_game_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / "sources"
            for relative, code in SOURCES.items():
                file = src / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(code, encoding="utf-8")
            original_classes = root / "synthetic-original-compiled"
            original_classes.mkdir()
            originals = subprocess.run([
                "javac", "--release", "9", "-proc:none", "-g:none",
                "-classpath", str(root / "empty-classpath"),
                "-sourcepath", str(root / "empty-sourcepath"),
                "-d", str(original_classes),
                *[str(src / path) for path in sorted(SOURCES)],
            ], capture_output=True, text=True, timeout=60)
            self.assertEqual(originals.returncode, 0, originals.stderr)
            original_jar = root / "synthetic-original.jar"
            with zipfile.ZipFile(original_jar, "w") as z:
                for file in sorted(original_classes.rglob("*.class")):
                    z.writestr(file.relative_to(original_classes).as_posix(),
                               file.read_bytes())
            with zipfile.ZipFile(original_jar) as z:
                pins = {path: digest(z.read(path)) for path in z.namelist()}
                dependencies = explicit_class_references(
                    z.read("rs/ui/components/a.class")
                ) - {"rs/ui/components/a.class"}
            self.assertEqual(dependencies, {
                "rs/ui/components/d.class", "rs/ui/components/w.class",
            })
            self.assertEqual(len(pins), 3)
            out = root / "verified"
            report = verify_standalone_sources(
                original_jar, src, out,
                original_sha256=digest(original_jar.read_bytes()),
                class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 3)
            self.assertEqual(
                report["explicit_original_project_dependency_closure"][
                    "source_project_dependency_edges"
                ], 2,
            )
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            probe = root / "OriginalVsRebuiltRaster.java"
            probe.write_text(PROBE, encoding="utf-8")
            compiled = subprocess.run([
                "javac", "--release", "9", "-d", str(root), str(probe)
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([
                "java", "-Djava.awt.headless=true", "-cp", str(root),
                "OriginalVsRebuiltRaster",
                str(original_jar), str(out / "classes"),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("SYNTHETIC_UI_RASTER_PARITY_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

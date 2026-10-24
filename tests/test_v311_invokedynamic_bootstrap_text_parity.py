"""JDK-only Java9 invokedynamic recipe proof and headless text raster parity.

No proprietary client class bytes, reconstructed v311 source or game assets
are bundled. A changed StringConcatFactory recipe can retain identical
javap -c operands while displaying an entirely different text color.
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
    StandaloneSourceParityError,
    _normalize_jvm_bootstrap_methods,
    verify_standalone_sources,
)


SOURCES = {
    "rs/ui/components/w.java": (
        "package rs.ui.components; import java.awt.*;"
        " public interface w { Dimension a(Graphics2D g); }"
    ),
    "rs/ui/components/Text.java": (
        "package rs.ui.components; import java.awt.*;"
        " public final class Text implements w {"
        ' private String message = "Hello";'
        ' public void set(String s) { message=s; }'
        " public Dimension a(Graphics2D g) {"
        '   String color = "ff0000";'
        '   g.setColor(Color.decode("#" + color));'
        "   g.drawString(message, 5, 20);"
        "   return new Dimension(g.getFontMetrics().stringWidth(message),"
        "                        g.getFontMetrics().getHeight());"
        " } }"
    ),
}


PROBE = r"""
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.util.Arrays;

public final class TextPixelProbe {
    static byte[] capture(URL source, String text) throws Exception {
        try(URLClassLoader loader = new URLClassLoader(
                new URL[]{source}, ClassLoader.getPlatformClassLoader())) {
            Class<?> kind = Class.forName("rs.ui.components.Text", true, loader);
            Object instance = kind.getConstructor().newInstance();
            kind.getMethod("set", String.class).invoke(instance, text);
            BufferedImage canvas = new BufferedImage(
                    120, 45, BufferedImage.TYPE_INT_ARGB
            );
            Graphics2D g = canvas.createGraphics();
            g.setFont(new Font("Dialog", Font.PLAIN, 13));
            Dimension size = (Dimension)kind.getMethod(
                    "a", Graphics2D.class
            ).invoke(instance, g);
            g.dispose();
            if (size.width <= 0 || size.height <= 0)
                throw new AssertionError("Invalid size");
            ByteBuffer buffer = ByteBuffer.allocate(120*45*4);
            for (int y=0;y<45;y++)
                for (int x=0;x<120;x++)
                    buffer.putInt(canvas.getRGB(x,y));
            return MessageDigest.getInstance("SHA-256").digest(buffer.array());
        }
    }
    public static void main(String[] args) throws Exception {
        System.setProperty("java.awt.headless", "true");
        URL original = new File(args[0]).toURI().toURL();
        URL rebuilt = new File(args[1]).toURI().toURL();
        for (String text : new String[]{"a", "Hello", "Visual parity"}) {
            if (!Arrays.equals(capture(original, text),capture(rebuilt,text)))
                throw new AssertionError("HEADLESS_TEXT_PIXEL_MISMATCH");
        }
        System.out.println("SYNTHETIC_TEXT_PIXEL_PARITY_PASS_3");
    }
}
"""


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


@unittest.skipUnless(
    shutil.which("javac") and shutil.which("javap") and shutil.which("java"),
    "Requires installed JDK with headless Java2D support",
)
class Java9BootstrapTextParityTests(unittest.TestCase):
    def fixture(self, root: Path):
        src = root / "source"
        for name, text in SOURCES.items():
            path = src / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        out = root / "original-classfiles"
        out.mkdir()
        build = subprocess.run([
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "empty-compile-classpath"),
            "-sourcepath", str(root / "empty-sourcepath"),
            "-d", str(out), *[str(src / name) for name in sorted(SOURCES)],
        ], capture_output=True, text=True, timeout=60)
        self.assertEqual(build.returncode, 0, build.stderr)
        jar = root / "synthetic-original.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for path in sorted(out.rglob("*.class")):
                archive.writestr(path.relative_to(out).as_posix(), path.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            pins = {name: sha(archive.read(name)) for name in archive.namelist()}
        return jar, src, pins

    def test_verified_bootstrap_and_real_headless_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jar, src, pins = self.fixture(root)
            report = verify_standalone_sources(
                jar, src, root / "verified",
                original_sha256=sha(jar.read_bytes()),
                class_sha256=pins,
            )
            self.assertEqual(report["total_classes"], 2)
            by_class = {r["class_entry"]: r for r in report["results"]}
            witness = by_class["rs/ui/components/Text.class"]
            self.assertTrue(witness["invokedynamic_bootstrap_compared"])
            self.assertEqual(len(witness["invokedynamic_bootstrap_sha256"]), 64)
            self.assertFalse(by_class["rs/ui/components/w.class"][
                "invokedynamic_bootstrap_compared"
            ])
            java = root / "TextPixelProbe.java"
            java.write_text(PROBE, encoding="utf-8")
            compiled = subprocess.run([
                "javac", "--release", "9", "-d", str(root), str(java),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            replay = subprocess.run([
                "java", "-Djava.awt.headless=true", "-cp", str(root),
                "TextPixelProbe", str(jar), str(root / "verified" / "classes"),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertIn("SYNTHETIC_TEXT_PIXEL_PARITY_PASS_3", replay.stdout)

    def test_changed_color_prefix_cannot_pass_code_only_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jar, src, pins = self.fixture(root)
            text_file = src / "rs/ui/components/Text.java"
            body = text_file.read_text(encoding="utf-8")
            self.assertIn('"#" + color', body)
            text_file.write_text(body.replace('"#" + color', '"0x" + color'),
                                 encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError, "JVM_INVOKEDYNAMIC_BOOTSTRAP_MISMATCH"
            ):
                verify_standalone_sources(
                    jar, src, root / "refused",
                    original_sha256=sha(jar.read_bytes()),
                    class_sha256=pins,
                )
            self.assertFalse((root / "refused" / "SOURCE-REBUILD-VERIFY.json").exists())

    def test_refuse_missing_or_ambiguous_bootstrap_table(self):
        for source in (
            "public class Demo {}",
            "BootstrapMethods:\nInnerClasses:\n",
            "BootstrapMethods:\nBootstrapMethods:\n",
        ):
            with self.subTest(source=source[:30]):
                with self.assertRaisesRegex(
                    StandaloneSourceParityError, "JVM_BOOTSTRAP_TABLE_"
                ):
                    _normalize_jvm_bootstrap_methods(source)


if __name__ == "__main__":
    unittest.main(verbosity=2)

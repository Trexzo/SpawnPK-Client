"""Synthetic Java9 panel and inherited-interface source-parity contract.

Deliberately unrelated to original SpawnPK v311 recovered Java source.
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
    "rs/synthetic/Metrics.java": """
package rs.synthetic;
public interface Metrics { int score(); }
""",
    "rs/synthetic/Area.java": """
package rs.synthetic;
import java.awt.Rectangle;
public interface Area extends Metrics { Rectangle area(); }
""",
    "rs/synthetic/ModeBadge.java": """
package rs.synthetic;
import javax.swing.JPanel;
import java.awt.Color;
import java.awt.Rectangle;
public final class ModeBadge extends JPanel implements Area {
    private Color tone = new Color(90, 120, 150);
    private boolean active = false;
    public void mode(boolean on) { active = on; }
    public Color color() { return active ? tone.brighter() : tone; }
    public Rectangle area() { return new Rectangle(2, 3, 4, 5); }
    public int score() { return active ? 2 : 1; }
}
""",
}

PROBE = """
import java.awt.Color;import java.io.File;import java.net.URL;
import java.net.URLClassLoader;
public final class SyntheticBadgeProbe {
    static String transcript(URL url)throws Exception {
        try (URLClassLoader loader = new URLClassLoader(
            new URL[]{url}, ClassLoader.getPlatformClassLoader())) {
            Class<?> cls = loader.loadClass("rs.synthetic.ModeBadge");
            Object badge = cls.getConstructor().newInstance();
            StringBuilder out = new StringBuilder();
            for(boolean enabled: new boolean[]{false,true,false,true}) {
                cls.getMethod("mode",boolean.class).invoke(badge,enabled);
                Color color=(Color)cls.getMethod("color").invoke(badge);
                out.append(color.getRGB()).append('/')
                   .append(cls.getMethod("score").invoke(badge)).append(';');
            }
            return out.toString();
        }
    }
    public static void main(String[] args)throws Exception{
        System.setProperty("java.awt.headless","true");
        if(!transcript(new File(args[0]).toURI().toURL())
            .equals(transcript(new File(args[1]).toURI().toURL())))
            throw new AssertionError("SYNTHETIC_MODE_BADGE_BEHAVIOR_MISMATCH");
        System.out.println("SYNTHETIC_BADGE_FOUR_STATE_BEHAVIOR_PASS");
    }
}
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(
    all(shutil.which(tool) for tool in ("javac", "javap", "java")),
    "Java 9 compilation and headless JVM required",
)
class PanelInterfaceSourceParityTests(unittest.TestCase):
    def fixture(self, root: Path):
        src = root / "src"
        for name, contents in SOURCES.items():
            path = src / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        original = root / "original"
        original.mkdir()
        cmd = [
            "javac", "--release", "9", "-proc:none", "-g:none",
            "-classpath", str(root / "emptycp"),
            "-sourcepath", str(root / "emptysp"), "-d", str(original),
            *[str(src / name) for name in sorted(SOURCES)],
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        jar = root / "synthetic.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for path in sorted(original.rglob("*.class")):
                archive.writestr(path.relative_to(original).as_posix(),
                                 path.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            pins = {name: sha(archive.read(name)) for name in archive.namelist()}
        self.assertEqual(len(pins), 3)
        return src, jar, pins

    def test_three_class_java9_build_exact_instructions_and_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src, jar, pins = self.fixture(root)
            target = root / "verified"
            report = verify_standalone_sources(
                jar, src, target, original_sha256=sha(jar.read_bytes()),
                class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 3)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertGreaterEqual(report[
                "explicit_original_project_dependency_closure"
            ]["source_project_dependency_edges"], 2)
            probe = root / "SyntheticBadgeProbe.java"
            probe.write_text(PROBE, encoding="utf-8")
            built = subprocess.run([
                "javac", "--release", "9", "-d", str(root), str(probe),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(built.returncode, 0, built.stderr)
            run = subprocess.run([
                "java", "-Djava.awt.headless=true", "-cp", str(root),
                "SyntheticBadgeProbe", str(jar), str(target / "classes"),
            ], capture_output=True, text=True, timeout=45)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("SYNTHETIC_BADGE_FOUR_STATE_BEHAVIOR_PASS", run.stdout)

    def test_incomplete_interface_chain_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src, jar, pins = self.fixture(root)
            incomplete = {name: pin for name, pin in pins.items()
                          if not name.endswith("/Metrics.class")}
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION",
            ):
                verify_standalone_sources(
                    jar, src, root / "not-closed",
                    original_sha256=sha(jar.read_bytes()),
                    class_sha256=incomplete,
                )

    def test_changed_panel_color_behavior_refuses_original_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src, jar, pins = self.fixture(root)
            panel = src / "rs/synthetic/ModeBadge.java"
            panel.write_text(
                panel.read_text(encoding="utf-8").replace(
                    "tone.brighter()", "tone.darker()"
                ), encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, src, root / "not-parity",
                    original_sha256=sha(jar.read_bytes()),
                    class_sha256=pins,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

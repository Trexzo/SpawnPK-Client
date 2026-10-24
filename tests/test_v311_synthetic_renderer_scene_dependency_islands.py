"""JDK9 toy regression: no original game names, binaries, or recovered code.

Shows compiler-donor isolation and rejects actual modified JVM instructions
rather than trusting just source/compiler output SHA repinning.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def run(argv):
    result = subprocess.run(list(map(str, argv)), capture_output=True, text=True, timeout=50)
    if result.returncode:
        raise AssertionError(result.stderr[-1500:])
    return result.stdout


def build(root, mutate_mode=False, mutate_link=False):
    src = root / "src/toy/example"
    src.mkdir(parents=True)
    enums = "BETA, ALPHA, GAMMA" if mutate_mode else "ALPHA, BETA, GAMMA"
    link = "this.before.after = null;" if mutate_link else "this.before.after = this.after;"
    (src / "Display.java").write_text(
        "package toy.example; class Display { enum Mode {" + enums + "} }\n", encoding="utf8"
    )
    (src / "Base.java").write_text(
        "package toy.example; public class Base { public long stamp; }\n", encoding="utf8"
    )
    (src / "Node.java").write_text(
        "package toy.example; public class Node extends Base {"
        "public Node before,after; public final void detach(){"
        "if(this.before!=null && this.after!=null){" + link +
        "this.after.before=this.before;this.before=null;this.after=null;} } }\n",
        encoding="utf8",
    )
    out = root / "built"
    out.mkdir()
    cp = root / "empty-cp"
    sp = root / "empty-sp"
    cp.mkdir()
    sp.mkdir()
    run(["javac", "--release", "9", "-proc:none", "-g:none", "-encoding", "UTF-8",
         "-classpath", cp, "-sourcepath", sp, "-d", out,
         *sorted(src.glob("*.java"))])
    return out


@unittest.skipUnless(all(shutil.which(x) for x in ("javac", "java", "javap")), "JDK required")
class SyntheticDependencyIslands(unittest.TestCase):
    def test_repeatable_Java9_build_and_discarded_donor_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = build(base / "one")
            second = build(base / "two")
            expected = {"Display.class", "Display$Mode.class", "Base.class", "Node.class"}
            observed = {p.name for p in (first / "toy/example").glob("*.class")}
            self.assertEqual(observed, expected)
            for name in expected:
                first_hash = hashlib.sha256((first / "toy/example" / name).read_bytes()).digest()
                second_hash = hashlib.sha256((second / "toy/example" / name).read_bytes()).digest()
                self.assertEqual(first_hash, second_hash)
                self.assertEqual((first / "toy/example" / name).read_bytes()[:8],
                                 bytes.fromhex("cafebabe00000035"))
            # Donor *owner* is not a recovered class and is never selected as an output.
            (first / "toy/example/Display.class").unlink()
            self.assertEqual({p.name for p in (first / "toy/example").glob("*.class")},
                             expected - {"Display.class"})
            javap = run(["javap", "-v", "-classpath", first, "toy.example.Display$Mode"])
            self.assertIn("InnerClasses:", javap)
            self.assertIn("toy/example/Display", javap)

    def test_real_jvm_mutations_detected_even_if_hashes_repinned(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            original = build(base / "original")
            enum_changed = build(base / "enum", mutate_mode=True)
            link_changed = build(base / "node", mutate_link=True)
            for class_name, candidate in (("toy.example.Display$Mode", enum_changed),
                                           ("toy.example.Node", link_changed)):
                rel = class_name.replace(".", "/") + ".class"
                source_name = "Display.java" if "$" in class_name else "Node.java"
                orig_source = (base / "original/src/toy/example" / source_name).read_bytes()
                modified_source = (candidate.parent / "src/toy/example" / source_name).read_bytes()
                self.assertNotEqual(hashlib.sha256(orig_source).digest(),
                                    hashlib.sha256(modified_source).digest())
                # Fresh SHA pins for each internally-consistent source-generated candidate.
                self.assertNotEqual(hashlib.sha256((original / rel).read_bytes()).digest(),
                                    hashlib.sha256((candidate / rel).read_bytes()).digest())
                original_jvm = run(["javap", "-p", "-s", "-c", "-classpath", original, class_name])
                altered_jvm = run(["javap", "-p", "-s", "-c", "-classpath", candidate, class_name])
                self.assertNotEqual(original_jvm, altered_jvm,
                                    "A repinned generated class cannot certify original parity")
            # The second mutation must not corrupt independently compiled unrelated types.
            self.assertEqual((original / "toy/example/Display$Mode.class").read_bytes(),
                             (link_changed / "toy/example/Display$Mode.class").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)

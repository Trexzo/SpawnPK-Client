"""Wholly fictional Java9 formatting/bytecode regression: no original game code.

No OS adapter queries, file operations, system commands, network, or device identifiers.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def run(command):
    result = subprocess.run([str(x) for x in command],
                            text=True, capture_output=True, timeout=45)
    if result.returncode:
        raise AssertionError(result.stderr[-1400:])
    return result.stdout


def build(root, altered_condition=False, prefix="TOY-"):
    source = root / "src/demo/notebook/StringPreview.java"
    source.parent.mkdir(parents=True)
    separator_check = "<=" if altered_condition else "<"
    source.write_text(
        'package demo.notebook;public final class StringPreview {'
        'public static String location(String base,String section) {'
        'String label=".'+ '" + section.toLowerCase();'
        'StringBuilder b=new StringBuilder(base+"/"+label+"/");return b.toString();}'
        'public static String formatFakeBytes(byte[] fake) {'
        'StringBuilder b=new StringBuilder();'
        'for(int k=0;k<fake.length;k++){'
        'b.append(String.format("%02X%s",fake[k],'
        'k ' + separator_check + ' fake.length-1 ? "-" : ""));}'
        'return b.toString();}'
        'public static String receipt(String label){return "' + prefix + '"+label;}}',
        encoding="utf8")
    classes = root / "classes"
    emptycp = root / "emptycp"
    emptysp = root / "emptysp"
    for folder in (classes, emptycp, emptysp):
        folder.mkdir()
    run(["javac", "--release", "9", "-proc:none", "-g:none",
         "-classpath", emptycp, "-sourcepath", emptysp,
         "-d", classes, source])
    return source, classes


def code(classes):
    return run(["javap", "-p", "-s", "-c", "-classpath", classes,
                "demo.notebook.StringPreview"])


def verbose(classes):
    return run(["javap", "-p", "-v", "-classpath", classes,
                "demo.notebook.StringPreview"])


@unittest.skipUnless(all(shutil.which(t) for t in ("java", "javac", "javap")),
                     "JDK 9 toolchain required")
class SyntheticFormattingSourceIsland(unittest.TestCase):
    def test_deterministic_java9_build_with_empty_compiler_classpath(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, first = build(root / "first")
            _, repeat = build(root / "repeat")
            rel = Path("demo/notebook/StringPreview.class")
            self.assertEqual([p.relative_to(first).as_posix()
                              for p in first.rglob("*.class")], [rel.as_posix()])
            self.assertEqual((first / rel).read_bytes(), (repeat / rel).read_bytes())
            self.assertEqual((first / rel).read_bytes()[:8],
                             bytes.fromhex("cafebabe00000035"))
            self.assertIn("formatFakeBytes", code(first))
            self.assertIn("invokedynamic", code(first))

    def test_changed_real_formatting_branch_detected_after_two_sha_updates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before_source, before = build(root / "before")
            after_source, after = build(root / "after", altered_condition=True)
            rel = Path("demo/notebook/StringPreview.class")
            h = lambda raw: hashlib.sha256(raw).digest()
            self.assertNotEqual(h(before_source.read_bytes()), h(after_source.read_bytes()))
            self.assertNotEqual(h((before / rel).read_bytes()), h((after / rel).read_bytes()))
            self.assertNotEqual(code(before), code(after))

    def test_changed_bootstrap_recipe_with_same_visible_jvm_instruction_list(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before_source, before = build(root / "before")
            after_source, after = build(root / "after", prefix="ALTERED-")
            rel = Path("demo/notebook/StringPreview.class")
            h = lambda raw: hashlib.sha256(raw).digest()
            self.assertNotEqual(h(before_source.read_bytes()), h(after_source.read_bytes()))
            self.assertNotEqual(h((before / rel).read_bytes()), h((after / rel).read_bytes()))
            self.assertEqual(code(before), code(after))
            self.assertIn("TOY-", verbose(before))
            self.assertIn("ALTERED-", verbose(after))
            self.assertNotEqual(verbose(before), verbose(after))


if __name__ == "__main__":
    unittest.main(verbosity=2)

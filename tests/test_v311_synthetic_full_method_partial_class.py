"""Entirely fictional Java9 method/source-island regression; NO owner/game code."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def execute(args):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=40)
    if p.returncode:
        raise AssertionError(p.stderr[-1100:])
    return p.stdout


def build(root, flip=False, prefix="MOCK:"):
    src = root / "src/toy/ledger/Memo.java"
    src.parent.mkdir(parents=True)
    cond = "!= null" if flip else "== null"
    src.write_text(
        'package toy.ledger;import java.util.*;import java.io.*;'
        'public final class Memo {'
        'private static boolean active;private static String label;'
        'private static int[] codes=new int[3];'
        'private static String compilerHelper(){return "toy_option";}'
        'static {active=false;label="SYNTHETIC";codes[0]=31;codes[1]=32;}'
        'public Memo(){} public static boolean disabled(){return false;}'
        'public static void parseInMemory(String input)throws Exception{'
        'Properties p=new Properties();p.load(new StringReader(input));'
        'try{if(p.getProperty("toy_option") ' + cond + ')active=false;'
        'else active=Boolean.parseBoolean(p.getProperty("toy_option"));}'
        'catch(Exception ignored){}'
        '}'
        'public static String formatWithoutWriting(){return "' + prefix + '"+active+":"+label;}'
        '}', encoding="utf8"
    )
    out, cp, sp = (root / s for s in ("classes", "emptycp", "emptysp"))
    for folder in (out, cp, sp):
        folder.mkdir()
    execute(["javac", "--release", "9", "-proc:none", "-g:none",
             "-classpath", cp, "-sourcepath", sp, "-d", out, src])
    return src, out


def disasm(classes):
    return execute(["javap", "-p", "-s", "-c", "-classpath", classes, "toy.ledger.Memo"])


def verbose(classes):
    return execute(["javap", "-p", "-v", "-classpath", classes, "toy.ledger.Memo"])


@unittest.skipUnless(all(shutil.which(t) for t in ("java", "javac", "javap")),
                     "Java9-capable JDK required")
class SyntheticMethodWitnessNotWholeClass(unittest.TestCase):
    def test_repeatable_jdk9_build_and_extra_helper_is_visible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, first = build(root / "first")
            _, replay = build(root / "replay")
            rel = Path("toy/ledger/Memo.class")
            self.assertEqual({p.relative_to(first).as_posix()
                              for p in first.rglob("*.class")}, {rel.as_posix()})
            self.assertEqual((first / rel).read_bytes(), (replay / rel).read_bytes())
            self.assertEqual((first / rel).read_bytes()[:8],
                             bytes.fromhex("cafebabe00000035"))
            bytecode = disasm(first)
            self.assertIn("parseInMemory", bytecode)
            self.assertIn("compilerHelper", bytecode)
            self.assertIn("Exception table", bytecode)
            self.assertIn("BootstrapMethods:", verbose(first))

    def test_real_reader_jvm_branch_changes_even_after_rehash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_src, old = build(root / "old")
            new_src, new = build(root / "mutant", flip=True)
            rel = Path("toy/ledger/Memo.class")
            sha = lambda b: hashlib.sha256(b).digest()
            self.assertNotEqual(sha(old_src.read_bytes()), sha(new_src.read_bytes()))
            self.assertNotEqual(sha((old / rel).read_bytes()), sha((new / rel).read_bytes()))
            self.assertNotEqual(disasm(old), disasm(new))

    def test_changed_string_bootstrap_with_identical_visible_jvm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_src, old = build(root / "old")
            new_src, new = build(root / "mutant", prefix="ALTERED:")
            rel = Path("toy/ledger/Memo.class")
            sha = lambda b: hashlib.sha256(b).digest()
            self.assertNotEqual(sha(old_src.read_bytes()), sha(new_src.read_bytes()))
            self.assertNotEqual(sha((old / rel).read_bytes()), sha((new / rel).read_bytes()))
            self.assertEqual(disasm(old), disasm(new))
            self.assertNotEqual(verbose(old), verbose(new))
            self.assertIn("MOCK:", verbose(old))
            self.assertIn("ALTERED:", verbose(new))


if __name__ == "__main__":
    unittest.main(verbosity=2)

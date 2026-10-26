"""Completely fictional Java9 method/initializer frontier regression (NO game code).

Test harness only compiles and DISASSEMBLES a local synthetic class. It never
loads or executes the compiled class, networking, filesystem game behavior,
AudioSystem, host hardware identification, or any original client code.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def invoke(*args):
    r = subprocess.run([str(a) for a in args], text=True, capture_output=True, timeout=45)
    if r.returncode:
        raise AssertionError(r.stderr[-1600:])
    return r.stdout


def compile_toy(root, count=8, branch="<", prefix="SIM-"):
    source = root / "src/toy/frontier/LedgerWorker.java"
    source.parent.mkdir(parents=True)
    source.write_text(
        "package toy.frontier;\n"
        "public final class LedgerWorker implements Runnable {\n"
        "  private static int quota;\n"
        f"  static {{ quota = {count}; }}\n"
        "  private static void compilerOnlyStub() {}\n"
        f"  public static boolean ready(int n) {{ return n {branch} quota; }}\n"
        f'  public static String receipt(String name) {{ return "{prefix}" + name; }}\n'
        "  public void run() { int i = 0; while (i < quota) i++; }\n"
        "}\n", encoding="utf8")
    classes, cp, sp = (root / x for x in ("classes", "emptycp", "emptysp"))
    for d in (classes, cp, sp):
        d.mkdir(parents=True)
    invoke("javac", "--release", "9", "-g:none", "-proc:none",
           "-classpath", cp, "-sourcepath", sp, "-d", classes, source)
    return source, classes / "toy/frontier/LedgerWorker.class", classes


def view(classes, verbose=False):
    return invoke("javap", "-p", "-v" if verbose else "-c", "-classpath",
                  classes, "toy.frontier.LedgerWorker")


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "JDK with Java 9 release target required")
class SyntheticR144MethodFrontier(unittest.TestCase):
    def test_clean_java9_replay_deterministic_and_not_an_accepted_class(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            _, one, first = compile_toy(p / "first")
            _, two, second = compile_toy(p / "second")
            self.assertEqual(one.read_bytes(), two.read_bytes())
            self.assertEqual(one.read_bytes()[:8], bytes.fromhex("cafebabe00000035"))
            self.assertEqual(sorted(x.relative_to(first).as_posix()
                                    for x in first.rglob("*.class")),
                             ["toy/frontier/LedgerWorker.class"])
            disassembly = view(first)
            self.assertIn("public void run();", disassembly)
            self.assertIn("static {};", disassembly)
            self.assertIn("compilerOnlyStub", disassembly)
            self.assertIn("private static void compilerOnlyStub();", disassembly)
            self.assertEqual(view(first), view(second))

    def test_initialization_mutation_detected_after_changed_source_and_class_hashes(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            oldsrc, oldclass, old = compile_toy(p / "old", count=8)
            newsrc, newclass, new = compile_toy(p / "new", count=9)
            digest = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
            self.assertNotEqual(digest(oldsrc), digest(newsrc))
            self.assertNotEqual(digest(oldclass), digest(newclass))
            self.assertNotEqual(view(old), view(new))

    def test_real_method_branch_change_rejected_by_disassembly_parity(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            _, a, old = compile_toy(p / "old", branch="<")
            _, b, new = compile_toy(p / "new", branch="<=")
            self.assertNotEqual(hashlib.sha256(a.read_bytes()).digest(),
                                hashlib.sha256(b.read_bytes()).digest())
            self.assertNotEqual(view(old), view(new))

    def test_bootstrap_recipe_mutation_invisible_to_plain_instruction_listing(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            _, a, old = compile_toy(p / "old", prefix="SIM-")
            _, b, new = compile_toy(p / "new", prefix="ALT-")
            self.assertNotEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(view(old), view(new))
            self.assertIn("SIM-", view(old, verbose=True))
            self.assertIn("ALT-", view(new, verbose=True))
            self.assertNotEqual(view(old, verbose=True), view(new, verbose=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)

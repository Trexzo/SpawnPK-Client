"""Totally fictional Java9 cache/queue methods: no owner-client, hardware or IO code."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def invoke(argv):
    result = subprocess.run([str(x) for x in argv], text=True, capture_output=True, timeout=40)
    if result.returncode:
        raise AssertionError(result.stderr[-1000:])
    return result.stdout


def compile_toy(root, flip=False, recipe="STAGED-"):
    src = root / "src/com/fictional/ticket/QueueMemo.java"
    src.parent.mkdir(parents=True)
    cmp = "> 100" if flip else "> 200"
    src.write_text(
        "package com.fictional.ticket;"
        "public final class QueueMemo {"
        "private static int index;private static String token;"
        "private QueueMemo(){}"
        "public static boolean admissible(int number){return number " + cmp + ";}"
        "public static void mark(String value){token=value;index++;}"
        "public static String receipt(){return \"" + recipe + "\"+index+\"-fiction.txt\";}"
        "public static String token(){return token;}"
        "}\n", encoding="utf8")
    compiled, emptycp, emptysp = (root / p for p in ("classes", "emptycp", "emptysp"))
    for folder in (compiled, emptycp, emptysp):
        folder.mkdir()
    invoke(["javac", "--release", "9", "-g:none", "-proc:none",
            "-classpath", emptycp, "-sourcepath", emptysp,
            "-d", compiled, src])
    return src, compiled


def visible_jvm(classes):
    return invoke(["javap", "-p", "-s", "-c", "-classpath", classes,
                   "com.fictional.ticket.QueueMemo"])


def recipes(classes):
    raw = invoke(["javap", "-p", "-v", "-classpath", classes,
                  "com.fictional.ticket.QueueMemo"])
    return "\n".join(line for line in raw.splitlines()
                     if "STAGED-" in line or "ALTERED-" in line)


@unittest.skipUnless(all(shutil.which(x) for x in ("javac", "javap", "java")),
                     "Requires Java9-capable JDK")
class SyntheticQueueMethodWitness(unittest.TestCase):
    def test_reproducible_jdk_only_one_class(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, a = compile_toy(root / "a")
            _, b = compile_toy(root / "b")
            rel = Path("com/fictional/ticket/QueueMemo.class")
            self.assertEqual(
                {p.relative_to(a).as_posix() for p in a.rglob("*.class")},
                {rel.as_posix()})
            self.assertEqual((a / rel).read_bytes(), (b / rel).read_bytes())
            self.assertEqual((a / rel).read_bytes()[:8],
                             bytes.fromhex("cafebabe00000035"))
            self.assertIn("invokedynamic", visible_jvm(a))

    def test_real_changed_jvm_code_rehashed_but_not_equal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sa, a = compile_toy(root / "before")
            sb, b = compile_toy(root / "after", flip=True)
            rel = Path("com/fictional/ticket/QueueMemo.class")
            sha = lambda data: hashlib.sha256(data).hexdigest()
            self.assertNotEqual(sha(sa.read_bytes()), sha(sb.read_bytes()))
            self.assertNotEqual(sha((a / rel).read_bytes()),
                                sha((b / rel).read_bytes()))
            self.assertNotEqual(visible_jvm(a), visible_jvm(b))

    def test_string_bootstrap_change_detected_despite_identical_visible_jvm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sa, a = compile_toy(root / "before")
            sb, b = compile_toy(root / "after", recipe="ALTERED-")
            rel = Path("com/fictional/ticket/QueueMemo.class")
            sha = lambda data: hashlib.sha256(data).hexdigest()
            self.assertNotEqual(sha(sa.read_bytes()), sha(sb.read_bytes()))
            self.assertNotEqual(sha((a / rel).read_bytes()),
                                sha((b / rel).read_bytes()))
            self.assertEqual(visible_jvm(a), visible_jvm(b))
            self.assertIn("STAGED-", recipes(a))
            self.assertIn("ALTERED-", recipes(b))
            self.assertNotEqual(recipes(a), recipes(b))


if __name__ == "__main__":
    unittest.main(verbosity=2)

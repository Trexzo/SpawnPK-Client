"""Synthetic-only Java9 41-entry enum and nested owner isolation.

Toy names and toy values. NO original v311 Java source, spell data or binaries.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def run(args):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=55)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def build(root, reverse=False):
    src = root / "src/toy/fixtures"
    src.mkdir(parents=True)
    entries = [(f"SIGNAL_{i:02d}", 7000 + i * 7, i + 5) for i in range(41)]
    if reverse:
        entries[0], entries[1] = entries[1], entries[0]
    literals = ",\n".join(f"{name}({number},{level},Kind.ALPHA)" for name, number, level in entries)
    (src / "Catalog.java").write_text(
        "package toy.fixtures; class Catalog {"
        "enum Kind { ALPHA, BETA, GAMMA; }"
        "enum Signal { " + literals + ";"
        "public final int id;public final int strength;public final Kind kind;"
        "Signal(int n,int s,Kind k){id=n;strength=s;kind=k;}"
        "public static Signal byId(int id){"
        "for(Signal s:values())if(s.id==id)return s;return null;}"
        "}"
        "enum Layout { TOP, MIDDLE, BOTTOM; }"
        "}\n", encoding="utf-8")
    extra = root / "src/toy/movement"
    extra.mkdir(parents=True)
    (extra / "Container.java").write_text(
        "package toy.movement; class Container { enum Position { WEST, EAST, CENTER; } }\n",
        encoding="utf-8")
    out = root / "compiled"
    out.mkdir()
    empty = root / "empty"
    empty.mkdir()
    run(["javac", "--release", "9", "-proc:none", "-g:none",
         "-classpath", empty, "-sourcepath", empty, "-d", out,
         *sorted((root / "src").rglob("*.java"))])
    return out


@unittest.skipUnless(all(shutil.which(x) for x in ("javac", "java", "javap")),
                     "Java 9 compatible JDK required")
class SyntheticSpellTable(unittest.TestCase):
    def test_four_nested_outputs_with_discarded_donor_owners(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            first = build(root / "first")
            second = build(root / "second")
            expected = {"toy/fixtures/Catalog.class",
                        "toy/fixtures/Catalog$Kind.class",
                        "toy/fixtures/Catalog$Signal.class",
                        "toy/fixtures/Catalog$Layout.class",
                        "toy/movement/Container.class",
                        "toy/movement/Container$Position.class"}
            self.assertEqual({p.relative_to(first).as_posix()
                              for p in first.rglob("*.class")}, expected)
            for name in expected:
                self.assertEqual((first / name).read_bytes(),
                                 (second / name).read_bytes())
                self.assertEqual((first / name).read_bytes()[:8],
                                 bytes.fromhex("cafebabe00000035"))
            for owner in ("toy/fixtures/Catalog.class", "toy/movement/Container.class"):
                (first / owner).unlink()
            self.assertEqual(len(list(first.rglob("*.class"))), 4)
            text = run(["javap", "-p", "-c", "-classpath", first,
                        "toy.fixtures.Catalog$Signal"])
            self.assertIn("byId", text)
            self.assertIn("41", text)

    def test_real_enum_order_change_detected_despite_new_candidate_hashes(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            original = build(root / "original")
            changed = build(root / "changed", True)
            source = Path("src/toy/fixtures/Catalog.java")
            cls = Path("toy/fixtures/Catalog$Signal.class")
            sha = lambda raw: hashlib.sha256(raw).hexdigest()
            self.assertNotEqual(sha((root / "original" / source).read_bytes()),
                                sha((root / "changed" / source).read_bytes()))
            self.assertNotEqual(sha((original / cls).read_bytes()),
                                sha((changed / cls).read_bytes()))
            before = run(["javap", "-p", "-s", "-c", "-classpath", original,
                          "toy.fixtures.Catalog$Signal"])
            after = run(["javap", "-p", "-s", "-c", "-classpath", changed,
                         "toy.fixtures.Catalog$Signal"])
            self.assertNotEqual(before, after,
                                "Repinning both hashes cannot certify original bytecode")
            for stable in ("toy/fixtures/Catalog$Kind.class",
                           "toy/movement/Container$Position.class"):
                self.assertEqual((original / stable).read_bytes(),
                                 (changed / stable).read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)

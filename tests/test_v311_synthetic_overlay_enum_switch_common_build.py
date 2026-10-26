"""Unrelated synthetic Java9 enum/switch-map source integration regression.

Contains NO original v311 recovered Java names, binary, or original-JAR data.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def run(args):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=50)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def build(root, include_helpers=True, reordered=False):
    src = root / 'src/toy/phase'
    src.mkdir(parents=True)
    (src / 'Steady.java').write_text(
        'package toy.phase; public class Steady { public int score(){return 42;} }\n',
        encoding='utf-8')
    (src / 'Counter.java').write_text(
        'package toy.phase; public class Counter { public long value; }\n',
        encoding='utf-8')
    if include_helpers:
        constants = 'BRAVO, ALPHA, CHARLIE' if reordered else 'ALPHA, BRAVO, CHARLIE'
        (src / 'Phase.java').write_text(
            'package toy.phase; public enum Phase {' + constants + ';}\n', encoding='utf-8')
        (src / 'LeftMap.java').write_text(
            'package toy.phase; class LeftMap { static int toNumber(Phase p) { switch(p) {'
            'case ALPHA: return 1; case BRAVO: return 2; default: return 0;'
            '} } }\n', encoding='utf-8')
        (src / 'RightMap.java').write_text(
            'package toy.phase; class RightMap { static int toNumber(Phase p) { switch(p) {'
            'case CHARLIE: return 7; case BRAVO: return 8; default: return 0;'
            '} } }\n', encoding='utf-8')
    dest = root / 'classes'
    dest.mkdir()
    cp = root / 'empty-cp'
    cp.mkdir()
    sp = root / 'empty-sourcepath'
    sp.mkdir()
    run(['javac', '--release', '9', '-proc:none', '-g:none', '-encoding', 'UTF-8',
         '-classpath', cp, '-sourcepath', sp, '-d', dest, *sorted(src.glob('*.java'))])
    return dest


@unittest.skipUnless(all(shutil.which(t) for t in ('javac', 'javap', 'java')),
                     'Java9-compatible JDK required')
class SyntheticEnumSwitchMapCommonBuild(unittest.TestCase):
    def test_prior_class_hashes_stable_and_only_helpers_selected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = build(root / 'base', False)
            integrated = build(root / 'integrated')
            repeat = build(root / 'repeat')
            expected = {'Steady.class', 'Counter.class', 'Phase.class',
                        'LeftMap.class', 'LeftMap$1.class',
                        'RightMap.class', 'RightMap$1.class'}
            actual = {p.name for p in (integrated / 'toy/phase').glob('*.class')}
            self.assertEqual(actual, expected)
            for filename in ('Steady.class', 'Counter.class'):
                rel = Path('toy/phase') / filename
                self.assertEqual((base / rel).read_bytes(), (integrated / rel).read_bytes())
            for filename in expected:
                rel = Path('toy/phase') / filename
                self.assertEqual((integrated / rel).read_bytes(), (repeat / rel).read_bytes())
                self.assertEqual((integrated / rel).read_bytes()[:8],
                                 bytes.fromhex('cafebabe00000035'))
            for donor in ('LeftMap.class', 'RightMap.class'):
                (integrated / 'toy/phase' / donor).unlink()
            self.assertEqual({p.name for p in (integrated / 'toy/phase').glob('*.class')},
                             expected - {'LeftMap.class', 'RightMap.class'})
            helper = run(['javap', '-p', '-s', '-c', '-classpath', integrated,
                          'toy.phase.LeftMap$1'])
            self.assertIn('int[]', helper)

    def test_changed_generated_enum_jvm_not_hidden_by_new_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = build(root / 'original')
            mutated = build(root / 'mutated', reordered=True)
            src = Path('src/toy/phase/Phase.java')
            cls = Path('toy/phase/Phase.class')
            sha = lambda raw: hashlib.sha256(raw).hexdigest()
            self.assertNotEqual(sha((root / 'original' / src).read_bytes()),
                                sha((root / 'mutated' / src).read_bytes()))
            self.assertNotEqual(sha((original / cls).read_bytes()),
                                sha((mutated / cls).read_bytes()))
            before = run(['javap', '-p', '-s', '-c', '-classpath', original, 'toy.phase.Phase'])
            after = run(['javap', '-p', '-s', '-c', '-classpath', mutated, 'toy.phase.Phase'])
            self.assertNotEqual(before, after)
            for filename in ('Steady.class', 'LeftMap$1.class'):
                rel = Path('toy/phase') / filename
                self.assertEqual((original / rel).read_bytes(), (mutated / rel).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)

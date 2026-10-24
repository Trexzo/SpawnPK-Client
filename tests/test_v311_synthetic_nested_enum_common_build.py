"""Synthetic-only Java9 common build and discarded nested-enum owner.

Toy classes, toy enum values and sources are unrelated to any original game.
No original client binaries, names or reconstructed Java are present.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def run(args):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=55)
    if p.returncode:
        raise AssertionError(p.stderr[-1400:])
    return p.stdout


def build(root: Path, with_nested: bool, reordered: bool = False):
    src = root / "source/synthetic/work"
    src.mkdir(parents=True)
    (src / "Stable.java").write_text(
        'package synthetic.work; public class Stable { public int value(){return 23;} }\n',
        encoding="utf-8",
    )
    (src / "Marker.java").write_text(
        'package synthetic.work; public class Marker { public long id; }\n',
        encoding="utf-8",
    )
    if with_nested:
        values = 'BETA, ALPHA, GAMMA' if reordered else 'ALPHA, BETA, GAMMA'
        (src / "Container.java").write_text(
            'package synthetic.work; class Container { enum Mode { '+values+' } }\n',
            encoding="utf-8",
        )
    output = root / "compiled"
    output.mkdir()
    emptycp, emptysp = root / "empty-cp", root / "empty-sourcepath"
    emptycp.mkdir(); emptysp.mkdir()
    run(['javac', '--release', '9', '-g:none', '-proc:none', '-encoding', 'UTF-8',
         '-classpath', emptycp, '-sourcepath', emptysp, '-d', output,
         *sorted(src.glob('*.java'))])
    return output


@unittest.skipUnless(all(shutil.which(c) for c in ('java', 'javac', 'javap')),
                     'A Java9-compatible JDK is required')
class SyntheticNestedEnumSourceIntegration(unittest.TestCase):
    def test_new_enum_preserves_prior_compiled_types(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            old = build(root / 'before', False)
            new = build(root / 'after', True)
            replay = build(root / 'replay', True)
            for filename in ('Stable.class', 'Marker.class'):
                rel = Path('synthetic/work') / filename
                self.assertEqual((old / rel).read_bytes(), (new / rel).read_bytes())
                self.assertEqual((new / rel).read_bytes(), (replay / rel).read_bytes())
            enum_path = Path('synthetic/work/Container$Mode.class')
            self.assertEqual((new / enum_path).read_bytes(),
                             (replay / enum_path).read_bytes())
            self.assertEqual((new / enum_path).read_bytes()[:8],
                             bytes.fromhex('cafebabe00000035'))
            emitted = {p.relative_to(new).as_posix() for p in new.rglob('*.class')}
            self.assertEqual(emitted, {
                'synthetic/work/Stable.class', 'synthetic/work/Marker.class',
                'synthetic/work/Container.class', 'synthetic/work/Container$Mode.class',
            })
            # The donor owner is discarded; only the genuine generated nested type
            # represents one extra classfile in the toy accepted output set.
            (new / 'synthetic/work/Container.class').unlink()
            self.assertEqual(len(list(new.rglob('*.class'))), 3)
            self.assertIn('InnerClasses:', run(['javap', '-v', '-classpath', new,
                                                'synthetic.work.Container$Mode']))

    def test_real_enum_order_mutation_not_hidden_by_repinned_sha(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            before = build(root / 'original', True)
            after = build(root / 'mutated', True, reordered=True)
            rel = Path('synthetic/work/Container$Mode.class')
            source = Path('source/synthetic/work/Container.java')
            self.assertNotEqual(
                hashlib.sha256((root / 'original' / source).read_bytes()).digest(),
                hashlib.sha256((root / 'mutated' / source).read_bytes()).digest(),
            )
            self.assertNotEqual(
                hashlib.sha256((before / rel).read_bytes()).digest(),
                hashlib.sha256((after / rel).read_bytes()).digest(),
            )
            # Internally consistent newly pinned candidate hashes do not attest
            # matching ORIGINAL ordered JVM instructions.
            a = run(['javap', '-p', '-s', '-c', '-classpath', before,
                     'synthetic.work.Container$Mode'])
            b = run(['javap', '-p', '-s', '-c', '-classpath', after,
                     'synthetic.work.Container$Mode'])
            self.assertNotEqual(a, b)
            for stable in ('Stable.class', 'Marker.class'):
                path = Path('synthetic/work') / stable
                self.assertEqual((before / path).read_bytes(), (after / path).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)

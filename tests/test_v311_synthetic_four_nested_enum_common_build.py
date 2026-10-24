"""Synthetic Java9 four-enum common source integration; NO original game data.

The unrelated fixtures demonstrate preserved prior classfile hashes, precise
donor-owner exclusion, and real JVM initializer mutation detection even when
candidate source and generated-class hashes both change.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def execute(argv):
    p = subprocess.run([str(x) for x in argv], text=True, capture_output=True, timeout=60)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def build(root, add=False, reversed_enum=False):
    source = root / 'java/toy/graph'
    source.mkdir(parents=True)
    (source / 'Stable.java').write_text(
        'package toy.graph; public final class Stable { public int id(){return 19;} }\n',
        encoding='utf-8')
    (source / 'Snapshot.java').write_text(
        'package toy.graph; public class Snapshot { public long stamp; }\n',
        encoding='utf-8')
    if add:
        states = 'SECOND, FIRST, THIRD' if reversed_enum else 'FIRST, SECOND, THIRD'
        (source / 'Shell.java').write_text(
            'package toy.graph; class Shell {'
            'enum Mode { ' + states + '; }'
            'enum Weather { CLEAR, CLOUDY, RAIN; }'
            'enum Priority { LOW, MID, HIGH; }'
            'enum Source { ONE, TWO; }'
            '}\n', encoding='utf-8')
    output = root / 'compiled'
    output.mkdir()
    emptycp = root / 'empty-cp'
    emptycp.mkdir()
    emptysp = root / 'empty-sp'
    emptysp.mkdir()
    execute(['javac', '--release', '9', '-g:none', '-proc:none', '-encoding', 'UTF-8',
             '-classpath', emptycp, '-sourcepath', emptysp, '-d', output,
             *sorted(source.glob('*.java'))])
    return output


@unittest.skipUnless(all(shutil.which(x) for x in ('javac', 'java', 'javap')),
                     'Java9 compatible JDK required')
class SyntheticFourEnumCommonBuild(unittest.TestCase):
    def test_one_invocation_preserves_earlier_classes_and_discards_owner(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            baseline = build(root / 'baseline')
            integrated = build(root / 'integrated', True)
            replay = build(root / 'replay', True)
            expected = {'toy/graph/Stable.class', 'toy/graph/Snapshot.class',
                        'toy/graph/Shell.class'} | {
                f'toy/graph/Shell${name}.class'
                for name in ('Mode', 'Weather', 'Priority', 'Source')}
            self.assertEqual({x.relative_to(integrated).as_posix()
                              for x in integrated.rglob('*.class')}, expected)
            for name in expected:
                self.assertEqual((integrated / name).read_bytes(), (replay / name).read_bytes())
                self.assertEqual((integrated / name).read_bytes()[:8],
                                 bytes.fromhex('cafebabe00000035'))
            for name in ('toy/graph/Stable.class', 'toy/graph/Snapshot.class'):
                self.assertEqual((baseline / name).read_bytes(),
                                 (integrated / name).read_bytes())
            (integrated / 'toy/graph/Shell.class').unlink()
            self.assertEqual(len(list(integrated.rglob('*.class'))), 6)
            self.assertIn('InnerClasses:', execute([
                'javap', '-v', '-classpath', integrated, 'toy.graph.Shell$Mode']))

    def test_actual_enum_jvm_mutation_survives_candidate_rehashing(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            before = build(root / 'before', True)
            after = build(root / 'after', True, reversed_enum=True)
            src = Path('java/toy/graph/Shell.java')
            cls = Path('toy/graph/Shell$Mode.class')
            digest = lambda b: hashlib.sha256(b).digest()
            self.assertNotEqual(digest((root / 'before' / src).read_bytes()),
                                digest((root / 'after' / src).read_bytes()))
            self.assertNotEqual(digest((before / cls).read_bytes()),
                                digest((after / cls).read_bytes()))
            old = execute(['javap', '-p', '-s', '-c', '-classpath', before,
                           'toy.graph.Shell$Mode'])
            new = execute(['javap', '-p', '-s', '-c', '-classpath', after,
                           'toy.graph.Shell$Mode'])
            self.assertNotEqual(old, new)
            for name in ('toy/graph/Stable.class', 'toy/graph/Shell$Weather.class'):
                self.assertEqual((before / name).read_bytes(), (after / name).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)

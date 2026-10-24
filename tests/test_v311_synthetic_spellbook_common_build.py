"""Entirely fictional Java9 prior-stable nested-enum integration and JVM checks.

NO recovered original game Java source, symbols, spell IDs, client binary, or assets.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def run(argv):
    p = subprocess.run([str(x) for x in argv], capture_output=True, text=True, timeout=50)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def make(root, include_new, switched=False):
    src = root / 'source/demo/sim'
    src.mkdir(parents=True)
    (src / 'Stable.java').write_text(
        'package demo.sim; public final class Stable { public int id(){return 63;} }\n',
        encoding='utf-8')
    (src / 'Record.java').write_text(
        'package demo.sim; public class Record { public long stamp; }\n',
        encoding='utf-8')
    if include_new:
        samples = [(f'CHIME_{i:02}', i * 17 + 50000, 10 + i) for i in range(41)]
        if switched:
            samples[0], samples[1] = samples[1], samples[0]
        entries = ',\n'.join(f'{name}({number},{weight})' for name, number, weight in samples)
        (src / 'Drum.java').write_text(
            'package demo.sim; public class Drum {'
            'public enum Family { COPPER, WOOD, CRYSTAL; }'
            'public enum Chime { ' + entries + ';'
            'public final int id;public final int weight;'
            'Chime(int i,int w){id=i;weight=w;}'
            'public static Chime byId(int id){for(Chime c:values())'
            'if(c.id==id)return c;return null;}'
            '}'
            'public enum Theme { NIGHT, DAWN, NOON; }'
            '}\n', encoding='utf-8')
        (src / 'Pointer.java').write_text(
            'package demo.sim;public class Pointer {public enum Side{WEST,EAST,CENTER;}}\n',
            encoding='utf-8')
    result = root / 'classes'
    result.mkdir()
    cp, sp = root / 'empty-cp', root / 'empty-sp'
    cp.mkdir()
    sp.mkdir()
    run(['javac', '--release', '9', '-g:none', '-proc:none', '-encoding', 'UTF-8',
         '-classpath', cp, '-sourcepath', sp, '-d', result, *sorted(src.glob('*.java'))])
    return result


@unittest.skipUnless(all(shutil.which(x) for x in ('java', 'javac', 'javap')),
                     'Java9-capable JDK required')
class ToyNestedEnumIntegratedBuild(unittest.TestCase):
    def test_old_outputs_stable_four_new_nested_types_with_donor_owners_discarded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = make(root / 'old', False)
            new = make(root / 'new', True)
            replay = make(root / 'replay', True)
            parents = {'demo/sim/Drum.class', 'demo/sim/Pointer.class'}
            prior = {'demo/sim/Stable.class', 'demo/sim/Record.class'}
            nested = {'demo/sim/Drum$Family.class', 'demo/sim/Drum$Chime.class',
                      'demo/sim/Drum$Theme.class', 'demo/sim/Pointer$Side.class'}
            self.assertEqual({p.relative_to(new).as_posix() for p in new.rglob('*.class')},
                             parents | prior | nested)
            for name in prior:
                self.assertEqual((old / name).read_bytes(), (new / name).read_bytes())
            for name in parents | prior | nested:
                self.assertEqual((new / name).read_bytes(), (replay / name).read_bytes())
                self.assertEqual((new / name).read_bytes()[:8],
                                 bytes.fromhex('cafebabe00000035'))
            for parent in parents:
                (new / parent).unlink()
            self.assertEqual({p.relative_to(new).as_posix() for p in new.rglob('*.class')},
                             prior | nested)
            self.assertIn('byId', run(['javap', '-p', '-s', '-c', '-classpath', new,
                                       'demo.sim.Drum$Chime']))

    def test_real_jvm_initializer_reorder_rejected_despite_new_source_and_class_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = make(root / 'reference', True)
            changed = make(root / 'candidate', True, switched=True)
            src = Path('source/demo/sim/Drum.java')
            cls = Path('demo/sim/Drum$Chime.class')
            sha = lambda data: hashlib.sha256(data).hexdigest()
            self.assertNotEqual(sha((root / 'reference' / src).read_bytes()),
                                sha((root / 'candidate' / src).read_bytes()))
            self.assertNotEqual(sha((old / cls).read_bytes()),
                                sha((changed / cls).read_bytes()))
            before = run(['javap', '-p', '-s', '-c', '-classpath', old,
                          'demo.sim.Drum$Chime'])
            after = run(['javap', '-p', '-s', '-c', '-classpath', changed,
                         'demo.sim.Drum$Chime'])
            self.assertNotEqual(before, after,
                                'New SHA pins do not establish original JVM parity')
            for name in ('demo/sim/Stable.class', 'demo/sim/Pointer$Side.class'):
                self.assertEqual((old / name).read_bytes(), (changed / name).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)

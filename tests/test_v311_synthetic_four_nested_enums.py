"""Synthetic four-nested-enum Java9 source-island regression (NO game code)."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def run(command):
    p = subprocess.run([str(x) for x in command], text=True,
                       capture_output=True, timeout=50)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def build(root, reorder=False):
    src = root / 'src/toy/world'
    src.mkdir(parents=True)
    values = 'BLUE, RED, GREEN' if reorder else 'RED, BLUE, GREEN'
    (src / 'Owner.java').write_text(
        'package toy.world; public class Owner {'
        'public enum Weather { CLEAR, RAIN; }'
        'public enum Color { ' + values + '; }'
        'public enum Sound { MUTE, QUIET, LOUD; '
        'public static Sound lookup(String s) {'
        'for(Sound x:values()) if(x.name().equalsIgnoreCase(s)) return x;'
        'return QUIET; } }'
        'public enum Day { MON, TUE, WED, THU; }'
        '}\n', encoding='utf-8')
    output = root / 'classes'
    output.mkdir()
    empty = root / 'empty'
    empty.mkdir()
    run(['javac', '--release', '9', '-g:none', '-proc:none',
         '-classpath', empty, '-sourcepath', empty, '-d', output,
         src / 'Owner.java'])
    return output


@unittest.skipUnless(all(shutil.which(x) for x in ('javac', 'javap', 'java')),
                     'Java9-capable JDK required')
class SyntheticFourNestedEnums(unittest.TestCase):
    def test_exact_output_selection_and_repeatability(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, b = build(root / 'one'), build(root / 'two')
            expected = {'toy/world/Owner.class'} | {
                'toy/world/Owner$' + name + '.class'
                for name in ('Weather', 'Color', 'Sound', 'Day')}
            selected = {x.relative_to(a).as_posix() for x in a.rglob('*.class')}
            self.assertEqual(selected, expected)
            for name in expected:
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
                self.assertEqual((a / name).read_bytes()[:8],
                                 bytes.fromhex('cafebabe00000035'))
            (a / 'toy/world/Owner.class').unlink()
            self.assertEqual({x.relative_to(a).as_posix() for x in a.rglob('*.class')},
                             expected - {'toy/world/Owner.class'})
            self.assertIn('equalsIgnoreCase', run([
                'javap', '-p', '-s', '-c', '-classpath', a,
                'toy.world.Owner$Sound']))

    def test_real_enum_order_mutation_after_candidate_rehash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, b = build(root / 'original'), build(root / 'changed', True)
            source = Path('src/toy/world/Owner.java')
            target = Path('toy/world/Owner$Color.class')
            sha = lambda raw: hashlib.sha256(raw).hexdigest()
            self.assertNotEqual(sha((root / 'original' / source).read_bytes()),
                                sha((root / 'changed' / source).read_bytes()))
            self.assertNotEqual(sha((a / target).read_bytes()),
                                sha((b / target).read_bytes()))
            self.assertNotEqual(run(['javap', '-p', '-s', '-c', '-classpath', a,
                                     'toy.world.Owner$Color']),
                                run(['javap', '-p', '-s', '-c', '-classpath', b,
                                     'toy.world.Owner$Color']))
            for stable in ('Owner$Weather.class', 'Owner$Day.class'):
                relative = Path('toy/world') / stable
                self.assertEqual((a / relative).read_bytes(),
                                 (b / relative).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Synthetic-only Java 9 listener registration integration regression.

Invented toy Java source, identifiers and behavior. No recovered game code.
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
        raise AssertionError(p.stderr[-1000:])
    return p.stdout


def build(root, with_registry, mutated=False):
    src = root / 'src/toy/safe'
    src.mkdir(parents=True)
    (src / 'Prior.java').write_text(
        'package toy.safe; public class Prior { public int state(){return 17;} }\n',
        encoding='utf-8')
    (src / 'First.java').write_text(
        'package toy.safe; public class First { public long marker; }\n',
        encoding='utf-8')
    if with_registry:
        left = 'right' if mutated else 'left'
        (src / 'Callbacks.java').write_text(
            'package toy.safe; import java.util.*; import java.util.concurrent.*;'
            'public class Callbacks {'
            'private static final List<Action> left = new CopyOnWriteArrayList<>();'
            'private static final List<Action> right = new CopyOnWriteArrayList<>();'
            'public static List<Action> first(){return ' + left + ';}'
            'public static List<Action> second(){return right;}'
            '@FunctionalInterface public interface Action {'
            'boolean process(Object input,boolean flag); } }\n',
            encoding='utf-8')
    out = root / 'built'
    out.mkdir()
    empty = root / 'empty'
    empty.mkdir()
    run(['javac', '--release', '9', '-proc:none', '-g:none',
         '-classpath', empty, '-sourcepath', empty, '-d', out,
         *sorted(src.glob('*.java'))])
    return out


@unittest.skipUnless(all(shutil.which(x) for x in ('javac', 'javap', 'java')),
                     'Java9-compatible JDK required')
class SyntheticRegistryCommonBuild(unittest.TestCase):
    def test_added_nested_interface_preserves_previous_classfiles(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            base = build(root / 'base', False)
            new = build(root / 'new', True)
            repeat = build(root / 'repeat', True)
            names = {p.relative_to(new).as_posix() for p in new.rglob('*.class')}
            self.assertEqual(names, {
                'toy/safe/Prior.class', 'toy/safe/First.class',
                'toy/safe/Callbacks.class', 'toy/safe/Callbacks$Action.class'})
            for name in names:
                self.assertEqual((new / name).read_bytes(), (repeat / name).read_bytes())
                self.assertEqual((new / name).read_bytes()[:8],
                                 bytes.fromhex('cafebabe00000035'))
            for name in ('toy/safe/Prior.class', 'toy/safe/First.class'):
                self.assertEqual((base / name).read_bytes(), (new / name).read_bytes())
            signature = run(['javap', '-p', '-s', '-c', '-classpath', new,
                             'toy.safe.Callbacks$Action'])
            self.assertIn('(Ljava/lang/Object;Z)Z', signature)

    def test_repinned_implementation_change_detected_by_real_jvm_output(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            original = build(root / 'original', True)
            changed = build(root / 'changed', True, mutated=True)
            source = Path('src/toy/safe/Callbacks.java')
            cls = Path('toy/safe/Callbacks.class')
            sha = lambda b: hashlib.sha256(b).hexdigest()
            self.assertNotEqual(sha((root / 'original' / source).read_bytes()),
                                sha((root / 'changed' / source).read_bytes()))
            self.assertNotEqual(sha((original / cls).read_bytes()),
                                sha((changed / cls).read_bytes()))
            before = run(['javap', '-p', '-s', '-c', '-classpath', original,
                          'toy.safe.Callbacks'])
            after = run(['javap', '-p', '-s', '-c', '-classpath', changed,
                         'toy.safe.Callbacks'])
            self.assertNotEqual(before, after)
            for name in ('toy/safe/Prior.class', 'toy/safe/Callbacks$Action.class'):
                self.assertEqual((original / name).read_bytes(),
                                 (changed / name).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)

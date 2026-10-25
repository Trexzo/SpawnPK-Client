"""Fictional JDK-only Java9 cached lookup island; NO game source or machine IDs.

Tests deterministic source compilation, reflection-only seeded cache path and
real instruction mutation detection even after source and class rehashing.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def run(args):
    p = subprocess.run([str(x) for x in args], capture_output=True,
                       text=True, timeout=45)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def compile_toy(root, mutated=False):
    src = root / 'java/toy/cache'
    src.mkdir(parents=True)
    condition = '== null' if mutated else '!= null'
    (src / 'Lookup.java').write_text(
        'package toy.cache;public final class Lookup {'
        'private static String cached;'
        'public static String read(){'
        'if(cached ' + condition + ')return cached;'
        'return "FAKE-DEFAULT";'
        '} }\n', encoding='utf8')
    output, emptycp, emptysp = (root / d for d in ('compiled', 'empty-cp', 'empty-sp'))
    for d in (output, emptycp, emptysp):
        d.mkdir()
    run(['javac', '--release', '9', '-g:none', '-proc:none',
         '-classpath', emptycp, '-sourcepath', emptysp,
         '-d', output, src / 'Lookup.java'])
    return output


@unittest.skipUnless(all(shutil.which(t) for t in ('java', 'javac', 'javap')),
                     'Requires JDK9-compatible runtime/compiler')
class SyntheticCachedLookupSourceIsland(unittest.TestCase):
    def test_one_class_repeatable_and_seeded_cache_without_external_process(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            first, second = compile_toy(root / 'first'), compile_toy(root / 'second')
            relative = Path('toy/cache/Lookup.class')
            self.assertEqual({p.relative_to(first).as_posix() for p in first.rglob('*.class')},
                             {relative.as_posix()})
            self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())
            self.assertEqual((first / relative).read_bytes()[:8],
                             bytes.fromhex('cafebabe00000035'))
            probe = root / 'Probe.java'
            probe.write_text(
                'import java.lang.reflect.*;public class Probe{'
                'public static void main(String[] a)throws Exception{'
                'Class<?> c=Class.forName("toy.cache.Lookup");'
                'Field f=c.getDeclaredField("cached");f.setAccessible(true);'
                'f.set(null,"SYNTHETIC-PLACEHOLDER");'
                'System.out.println(c.getMethod("read").invoke(null));'
                '}}\n', encoding='utf8')
            probe_output = root / 'probe-classes'
            probe_output.mkdir()
            run(['javac', '--release', '9', '-d', probe_output, '-cp', first, probe])
            import os
            actual = run(['java', '-cp', str(probe_output) + os.pathsep + str(first), 'Probe'])
            self.assertEqual(actual.strip(), 'SYNTHETIC-PLACEHOLDER')

    def test_rehashed_real_jvm_condition_change_is_detectable(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            before, after = compile_toy(root / 'before'), compile_toy(root / 'after', True)
            source = Path('java/toy/cache/Lookup.java')
            cls = Path('toy/cache/Lookup.class')
            digest = lambda raw: hashlib.sha256(raw).digest()
            self.assertNotEqual(digest((root / 'before' / source).read_bytes()),
                                digest((root / 'after' / source).read_bytes()))
            self.assertNotEqual(digest((before / cls).read_bytes()),
                                digest((after / cls).read_bytes()))
            code_before = run(['javap', '-p', '-s', '-c', '-classpath', before,
                               'toy.cache.Lookup'])
            code_after = run(['javap', '-p', '-s', '-c', '-classpath', after,
                              'toy.cache.Lookup'])
            self.assertNotEqual(code_before, code_after)


if __name__ == '__main__':
    unittest.main(verbosity=2)

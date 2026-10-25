"""Original-free Java9 toy dual-fallback cache regression (no machine fingerprinting).

No SpawnPK client Java code, serial-number gathering or external commands.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def invoke(args):
    p = subprocess.run([str(a) for a in args], capture_output=True,
                       text=True, timeout=40)
    if p.returncode:
        raise AssertionError(p.stderr[-1300:])
    return p.stdout


def build(root, tampered=False):
    src = root / 'src/toy/lookup'
    src.mkdir(parents=True)
    second = '!= null' if tampered else '== null'
    (src / 'FallbackCache.java').write_text(
        'package toy.lookup; public final class FallbackCache {'
        'private static String cache;'
        'public static String get(){'
        'if(cache==null)first();'
        'if(cache ' + second + ')second();'
        'return cache;}'
        'private static void first(){cache="FAKE-FIRST";}'
        'private static void second(){cache="FAKE-SECOND";}'
        '}\n', encoding='utf-8')
    result = root / 'classes'
    cp = root / 'empty-cp'
    sp = root / 'empty-sp'
    for folder in (result, cp, sp):
        folder.mkdir()
    invoke(['javac', '--release', '9', '-g:none', '-proc:none',
            '-classpath', cp, '-sourcepath', sp, '-d', result,
            src / 'FallbackCache.java'])
    return result


@unittest.skipUnless(all(shutil.which(x) for x in ('javac', 'javap', 'java')),
                     'Java9-compatible JDK required')
class SyntheticCacheIsland(unittest.TestCase):
    def test_single_class_reproducible_and_seeded_cache(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            first, repeat = build(root / 'first'), build(root / 'repeat')
            rel = Path('toy/lookup/FallbackCache.class')
            self.assertEqual([p.relative_to(first).as_posix()
                              for p in first.rglob('*.class')], [rel.as_posix()])
            self.assertEqual((first / rel).read_bytes(), (repeat / rel).read_bytes())
            self.assertEqual((first / rel).read_bytes()[:8],
                             bytes.fromhex('cafebabe00000035'))
            probe = root / 'CacheProbe.java'
            probe.write_text(
                'import java.lang.reflect.*;'
                'public class CacheProbe{public static void main(String[] args)throws Exception{'
                'Class<?> c=Class.forName("toy.lookup.FallbackCache");'
                'Field f=c.getDeclaredField("cache"); f.setAccessible(true);'
                'f.set(null,"SYNTHETIC");'
                'System.out.println(c.getMethod("get").invoke(null));'
                '}}\n', encoding='utf-8')
            out = root / 'probe';out.mkdir()
            invoke(['javac', '--release', '9', '-cp', first, '-d', out, probe])
            import os
            result = invoke(['java', '-cp', str(out)+os.pathsep+str(first),
                             'CacheProbe'])
            self.assertEqual(result.strip(), 'SYNTHETIC')

    def test_real_jvm_branch_change_rejected_even_after_source_and_class_rehash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original, mutant = build(root / 'original'), build(root / 'mutant', True)
            src = Path('src/toy/lookup/FallbackCache.java')
            cls = Path('toy/lookup/FallbackCache.class')
            dig = lambda b: hashlib.sha256(b).hexdigest()
            self.assertNotEqual(dig((root / 'original' / src).read_bytes()),
                                dig((root / 'mutant' / src).read_bytes()))
            self.assertNotEqual(dig((original / cls).read_bytes()),
                                dig((mutant / cls).read_bytes()))
            self.assertNotEqual(
                invoke(['javap', '-p', '-s', '-c', '-classpath', original,
                        'toy.lookup.FallbackCache']),
                invoke(['javap', '-p', '-s', '-c', '-classpath', mutant,
                        'toy.lookup.FallbackCache']))


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Purely fictional Java9 prior-stable event callback integration.

NO original v311 source, client assets, binary code or real identifiers.
"""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest


def execute(args):
    p = subprocess.run([str(x) for x in args], text=True, capture_output=True, timeout=40)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def build(root, callbacks=False, changed=False):
    src = root / 'src' / 'toy' / 'signals'
    src.mkdir(parents=True)
    (src / 'OldClock.java').write_text(
        'package toy.signals;public class OldClock {public int tick(){return 43;}}\n', encoding='utf-8')
    (src / 'OldCounter.java').write_text(
        'package toy.signals;public class OldCounter {public int value(){return 17;}}\n', encoding='utf-8')
    if callbacks:
        (src / 'Oneshot.java').write_text(
            'package toy.signals;public interface Oneshot {void perform();}\n', encoding='utf-8')
        (src / 'Periodic.java').write_text(
            'package toy.signals;public interface Periodic {boolean again();}\n', encoding='utf-8')
        active = 'pending.containsKey(id)' if changed else 'periodic.containsKey(id)'
        (src / 'Dispatch.java').write_text(
            'package toy.signals;import java.util.*;import java.util.concurrent.*;'
            'public class Dispatch {'
            'private static final CopyOnWriteArrayList<Oneshot> queue=new CopyOnWriteArrayList<>();'
            'private static final ConcurrentHashMap<String,Oneshot> pending=new ConcurrentHashMap<>();'
            'private static final ConcurrentHashMap<String,Periodic> periodic=new ConcurrentHashMap<>();'
            'public static void once(Oneshot x){queue.add(x);}'
            'public static void once(String id,Oneshot x){pending.put(id,x);}'
            'public static void repeatedly(String id,Periodic x){periodic.put(id,x);}'
            'public static boolean active(String id){return ' + active + ';}'
            'public static void advance(){'
            'for(Oneshot x:queue)x.perform();queue.clear();'
            'for(String id:periodic.keySet())if(!periodic.get(id).again())periodic.remove(id);'
            'for(Oneshot x:pending.values())x.perform();pending.clear();'
            '} }\n', encoding='utf-8')
    out = root / 'classes'
    cp, sp = root / 'emptycp', root / 'emptysp'
    for folder in (out, cp, sp):
        folder.mkdir()
    execute(['javac', '--release', '9', '-proc:none', '-g:none',
             '-classpath', cp, '-sourcepath', sp, '-d', out,
             *sorted(src.glob('*.java'))])
    return out


@unittest.skipUnless(all(shutil.which(x) for x in ('java', 'javac', 'javap')),
                     'JDK9-compatible toolchain required')
class SyntheticCallbackCommonBuild(unittest.TestCase):
    def test_old_classfiles_unchanged_five_output_build_and_real_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = build(root / 'old')
            new = build(root / 'integrated', callbacks=True)
            again = build(root / 'repeat', callbacks=True)
            names = {p.relative_to(new).as_posix() for p in new.rglob('*.class')}
            expect = {f'toy/signals/{n}.class' for n in
                      ('OldClock', 'OldCounter', 'Oneshot', 'Periodic', 'Dispatch')}
            self.assertEqual(names, expect)
            for name in expect:
                self.assertEqual((new / name).read_bytes(), (again / name).read_bytes())
                self.assertEqual((new / name).read_bytes()[:8], bytes.fromhex('cafebabe00000035'))
            for name in ('OldClock', 'OldCounter'):
                rel = f'toy/signals/{name}.class'
                self.assertEqual((new / rel).read_bytes(), (old / rel).read_bytes())
            probe = root / 'ToyProbe.java'
            probe.write_text(
                'import toy.signals.*;public class ToyProbe{public static void main(String[] a){'
                'final int[] count={0,0};'
                'Dispatch.once(()->count[0]++);Dispatch.once("one",()->count[0]+=10);'
                'Dispatch.repeatedly("repeat",()->++count[1]<2);'
                'System.out.println(Dispatch.active("repeat"));'
                'Dispatch.advance();System.out.println(count[0]+":"+count[1]);'
                'Dispatch.advance();System.out.println(count[0]+":"+count[1]);'
                'System.out.println(Dispatch.active("repeat"));'
                '}}\n', encoding='utf-8')
            pdir = root / 'probe'
            pdir.mkdir()
            execute(['javac', '--release', '9', '-classpath', new, '-d', pdir, probe])
            lines = execute(['java', '-cp', str(pdir)+os.pathsep+str(new), 'ToyProbe']).splitlines()
            self.assertEqual(lines, ['true', '11:1', '11:2', 'false'])

    def test_real_callback_lookup_jvm_change_detected_after_rehash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = build(root / 'reference', callbacks=True)
            changed = build(root / 'mutant', callbacks=True, changed=True)
            source = Path('src/toy/signals/Dispatch.java')
            output = Path('toy/signals/Dispatch.class')
            digest = lambda data: hashlib.sha256(data).hexdigest()
            self.assertNotEqual(digest((root / 'reference' / source).read_bytes()),
                                digest((root / 'mutant' / source).read_bytes()))
            self.assertNotEqual(digest((original / output).read_bytes()),
                                digest((changed / output).read_bytes()))
            before = execute(['javap', '-p', '-s', '-c', '-classpath', original,
                              'toy.signals.Dispatch'])
            after = execute(['javap', '-p', '-s', '-c', '-classpath', changed,
                             'toy.signals.Dispatch'])
            self.assertNotEqual(before, after)
            for stable in ('OldClock', 'OldCounter', 'Oneshot', 'Periodic'):
                rel = f'toy/signals/{stable}.class'
                self.assertEqual((original / rel).read_bytes(), (changed / rel).read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)

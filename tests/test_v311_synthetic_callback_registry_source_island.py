"""Purely fictional Java9 callback source island; NO game source or binaries."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest


def execute(args):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=40)
    if p.returncode:
        raise AssertionError(p.stderr[-1000:])
    return p.stdout


def build(root, mutated=False):
    src = root / 'src/toy/events'
    src.mkdir(parents=True)
    (src / 'Once.java').write_text('package toy.events; public interface Once {void apply();}\n')
    (src / 'Repeat.java').write_text('package toy.events; public interface Repeat {boolean next();}\n')
    target = 'return once.containsKey(key);' if mutated else 'return repeating.containsKey(key);'
    (src / 'Scheduler.java').write_text(
        'package toy.events; import java.util.*; import java.util.concurrent.*;'
        'public final class Scheduler {'
        'private static final CopyOnWriteArrayList<Once> callbacks = new CopyOnWriteArrayList<>();'
        'private static final ConcurrentHashMap<String,Once> once = new ConcurrentHashMap<>();'
        'private static final ConcurrentHashMap<String,Repeat> repeating = new ConcurrentHashMap<>();'
        'public static void enqueue(Once x){callbacks.add(x);}'
        'public static void enqueue(String key,Once x){once.put(key,x);}'
        'public static void schedule(String key,Repeat x){repeating.put(key,x);}'
        'public static boolean active(String key){' + target + '}'
        'public static void drain(){'
        'if(!callbacks.isEmpty()){for(Once callback:callbacks)callback.apply();callbacks.clear();}'
        'if(!repeating.isEmpty()){List<String> removed=new ArrayList<>();'
        'for(String key:repeating.keySet())if(!repeating.get(key).next())removed.add(key);'
        'for(String key:removed)repeating.remove(key);}'
        'if(!once.isEmpty()){for(Once callback:once.values())callback.apply();once.clear();}'
        '} }\n',encoding='utf-8'
    )
    out = root / 'classes'
    out.mkdir()
    empty = root / 'emptycp';empty.mkdir()
    emptysrc = root / 'emptysp';emptysrc.mkdir()
    execute(['javac','--release','9','-proc:none','-g:none','-encoding','UTF-8',
             '-classpath',empty,'-sourcepath',emptysrc,'-d',out,*sorted(src.glob('*.java'))])
    return out


@unittest.skipUnless(all(shutil.which(t) for t in ('javac','java','javap')),
                     'JDK 9+ compiler/tools needed')
class SyntheticCallbackRegistrySourceIsland(unittest.TestCase):
    def test_three_class_compilation_is_reproducible_and_behavioral(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            original = build(base / 'first')
            again = build(base / 'second')
            expected = {'toy/events/Once.class','toy/events/Repeat.class',
                        'toy/events/Scheduler.class'}
            self.assertEqual({p.relative_to(original).as_posix() for p in original.rglob('*.class')},expected)
            for name in expected:
                self.assertEqual((original/name).read_bytes(),(again/name).read_bytes())
                self.assertEqual((original/name).read_bytes()[:8],bytes.fromhex('cafebabe00000035'))
            probe=base / 'EventsProbe.java'
            probe.write_text(
                'import toy.events.*; public class EventsProbe {'
                'public static void main(String[] v){final int[] counts={0,0};'
                'Scheduler.enqueue(()->counts[0]++);'
                'Scheduler.enqueue("named",()->counts[0]+=10);'
                'Scheduler.schedule("repeat",()->++counts[1]<2);'
                'System.out.println(Scheduler.active("repeat"));'
                'Scheduler.drain();System.out.println(counts[0]+":"+counts[1]);'
                'Scheduler.drain();System.out.println(counts[0]+":"+counts[1]);'
                'System.out.println(Scheduler.active("repeat"));'
                '} }\n',encoding='utf-8')
            pb=base/'probe';pb.mkdir()
            execute(['javac','--release','9','-cp',original,'-d',pb,probe])
            output=execute(['java','-cp',str(pb)+os.pathsep+str(original),'EventsProbe']).splitlines()
            self.assertEqual(output,['true','11:1','11:2','false'])

    def test_repinned_real_jvm_algorithm_change_is_not_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            reference=build(base/'reference')
            altered=build(base/'altered',True)
            source=Path('src/toy/events/Scheduler.java')
            cls=Path('toy/events/Scheduler.class')
            digest=lambda b:hashlib.sha256(b).digest()
            self.assertNotEqual(digest((base/'reference'/source).read_bytes()),
                                digest((base/'altered'/source).read_bytes()))
            self.assertNotEqual(digest((reference/cls).read_bytes()),
                                digest((altered/cls).read_bytes()))
            first=execute(['javap','-p','-s','-c','-classpath',reference,'toy.events.Scheduler'])
            other=execute(['javap','-p','-s','-c','-classpath',altered,'toy.events.Scheduler'])
            self.assertNotEqual(first,other)
            for iface in ('Once.class','Repeat.class'):
                path=Path('toy/events')/iface
                self.assertEqual((reference/path).read_bytes(),(altered/path).read_bytes())


if __name__=='__main__':
    unittest.main(verbosity=2)

"""Toy Java9 MIDI source island. Fictional Java only, no owner client code."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def run(command):
    p = subprocess.run([str(c) for c in command], capture_output=True, text=True, timeout=45)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def build(root, changed=False):
    java = root / 'src/demo/music'
    java.mkdir(parents=True)
    getter = 'second' if changed else 'first'
    (java / 'ToyMixer.java').write_text(
        'package demo.music; import javax.sound.midi.*;'
        'public final class ToyMixer {'
        'private String first, second;'
        'private int level;'
        'public void names(String a,String b){first=a;second=b;}'
        'public String selected(){return '+getter+';}'
        'public int setVolume(double fraction){'
        'level=(int)(fraction*127.0d);return level;}'
        'public int saved(){return level;}'
        'public void transmit(Receiver receiver) throws Exception {'
        'ShortMessage msg=new ShortMessage();'
        'for(int channel=0;channel<16;channel++){'
        'msg.setMessage(176,channel,7,level);receiver.send(msg,-1L);}'
        '} }\n', encoding='utf8'
    )
    cls = root / 'classes'; cls.mkdir()
    empty = root / 'emptycp'; empty.mkdir()
    emptysp = root / 'emptysp'; emptysp.mkdir()
    run(['javac','--release','9','-proc:none','-g:none','-classpath',empty,
         '-sourcepath',emptysp,'-d',cls,java/'ToyMixer.java'])
    return cls


@unittest.skipUnless(all(shutil.which(x) for x in ('javac','javap','java')),
                     'Java9 JDK is required')
class SyntheticMidiSourceIsland(unittest.TestCase):
    def test_reproducible_single_source_without_game_deps(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path)
            first,repeat=build(root/'first'),build(root/'repeat')
            p=Path('demo/music/ToyMixer.class')
            self.assertEqual({x.relative_to(first).as_posix() for x in first.rglob('*.class')},
                             {p.as_posix()})
            self.assertEqual((first/p).read_bytes(),(repeat/p).read_bytes())
            self.assertEqual((first/p).read_bytes()[:8],bytes.fromhex('cafebabe00000035'))
            probe=root/'ToyProbe.java'
            probe.write_text('import demo.music.*; import javax.sound.midi.*;'
                'public class ToyProbe{public static void main(String[] argv)throws Exception{'
                'ToyMixer m=new ToyMixer();m.names("alpha","beta");'
                'System.out.println(m.selected());System.out.println(m.setVolume(0.5));'
                'final int[] seen={0}; m.transmit(new Receiver(){'
                'public void close(){}public void send(MidiMessage message,long t){'
                'ShortMessage v=(ShortMessage)message;seen[0]++;'
                'if(v.getData2()!=63||t!=-1)throw new AssertionError();}});'
                'System.out.println(seen[0]);}}\n',encoding='utf8')
            probecls=root/'probecls';probecls.mkdir()
            run(['javac','--release','9','-cp',first,'-d',probecls,probe])
            import os
            observed=run(['java','-cp',str(probecls)+os.pathsep+str(first),'ToyProbe'])
            self.assertEqual(observed.splitlines(),['alpha','63','16'])

    def test_real_jvm_mutation_detected_after_source_and_class_repin(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path)
            reference=build(root/'reference')
            mutated=build(root/'mutated',True)
            source=Path('src/demo/music/ToyMixer.java')
            cls=Path('demo/music/ToyMixer.class')
            dig=lambda b:hashlib.sha256(b).digest()
            self.assertNotEqual(dig((root/'reference'/source).read_bytes()),
                                dig((root/'mutated'/source).read_bytes()))
            self.assertNotEqual(dig((reference/cls).read_bytes()),
                                dig((mutated/cls).read_bytes()))
            a=run(['javap','-p','-s','-c','-classpath',reference,'demo.music.ToyMixer'])
            b=run(['javap','-p','-s','-c','-classpath',mutated,'demo.music.ToyMixer'])
            self.assertNotEqual(a,b)


if __name__=='__main__':
    unittest.main(verbosity=2)

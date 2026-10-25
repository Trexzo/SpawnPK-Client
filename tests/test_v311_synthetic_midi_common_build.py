"""Independent fictional Java9 MIDI common-source-build regression. No game code."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

def run(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=45)
    if p.returncode:raise AssertionError(p.stderr[-1100:])
    return p.stdout

def build(root,added=False,changed=False):
    src=root/'src/toy/tones';src.mkdir(parents=True)
    (src/'OldA.java').write_text('package toy.tones;public class OldA {public int count(){return 12;}}\n')
    (src/'OldB.java').write_text('package toy.tones;public class OldB {public long id;}\n')
    if added:
        selected='second' if changed else 'first'
        (src/'Instrument.java').write_text(
            'package toy.tones;import javax.sound.midi.*;'
            'public class Instrument {'
            'private String first,second;'
            'public void set(String a,String b){first=a;second=b;}'
            'public String selected(){return '+selected+';}'
            'public static void message(Receiver receiver)throws Exception{'
            'ShortMessage msg=new ShortMessage();'
            'msg.setMessage(ShortMessage.CONTROL_CHANGE,3,7,64);'
            'receiver.send(msg,-1L);}}\n')
    out=root/'classes';out.mkdir()
    cp,sp=root/'emptycp',root/'emptysp'
    cp.mkdir();sp.mkdir()
    run(['javac','--release','9','-g:none','-proc:none','-classpath',cp,
         '-sourcepath',sp,'-d',out,*sorted(src.glob('*.java'))])
    return out

@unittest.skipUnless(all(shutil.which(x) for x in ('javac','java','javap')),'JDK required')
class SyntheticMidiCommonBuild(unittest.TestCase):
    def test_prior_outputs_unchanged_in_one_source_compile(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            old,new,repeat=build(root/'old'),build(root/'new',True),build(root/'repeat',True)
            self.assertEqual({p.name for p in new.rglob('*.class')},
                             {'OldA.class','OldB.class','Instrument.class'})
            for cls in ('OldA.class','OldB.class'):
                rel=Path('toy/tones')/cls
                self.assertEqual((old/rel).read_bytes(),(new/rel).read_bytes())
            for cls in ('OldA.class','OldB.class','Instrument.class'):
                rel=Path('toy/tones')/cls
                self.assertEqual((new/rel).read_bytes(),(repeat/rel).read_bytes())
                self.assertEqual((new/rel).read_bytes()[:8],bytes.fromhex('cafebabe00000035'))
            self.assertIn('javax/sound/midi/ShortMessage',
                          run(['javap','-p','-c','-classpath',new,'toy.tones.Instrument']))

    def test_repinned_real_method_change_not_original_parity(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            a,b=build(root/'reference',True),build(root/'mutated',True,True)
            java=Path('src/toy/tones/Instrument.java')
            cls=Path('toy/tones/Instrument.class')
            dig=lambda data:hashlib.sha256(data).hexdigest()
            self.assertNotEqual(dig((root/'reference'/java).read_bytes()),
                                dig((root/'mutated'/java).read_bytes()))
            self.assertNotEqual(dig((a/cls).read_bytes()),dig((b/cls).read_bytes()))
            self.assertNotEqual(
                run(['javap','-p','-s','-c','-classpath',a,'toy.tones.Instrument']),
                run(['javap','-p','-s','-c','-classpath',b,'toy.tones.Instrument']))
            for stable in ('OldA.class','OldB.class'):
                rel=Path('toy/tones')/stable
                self.assertEqual((a/rel).read_bytes(),(b/rel).read_bytes())

if __name__=='__main__':
    unittest.main(verbosity=2)

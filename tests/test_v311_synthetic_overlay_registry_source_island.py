"""Independent Java9 toy registry: no original game source or original binary."""
from pathlib import Path
import hashlib
import shutil
import struct
import subprocess
import tempfile
import unittest


def run(argv):
    p=subprocess.run([str(x) for x in argv],capture_output=True,text=True,timeout=50)
    if p.returncode:raise AssertionError(p.stderr[-1200:])
    return p.stdout


def rename_metadata(blob,interface=False):
    assert blob[:4]==bytes.fromhex('cafebabe')
    old=b'synthetic/fixture/Hub$Delegate'
    changes={old:b'synthetic/fixture/Hub$Action',b'Delegate':b'Action'}
    if interface:changes[b'(Ljava/lang/Object;Z)Z']=b'(Ljava/lang/String;Z)Z'
    counts={x:0 for x in changes}
    result=bytearray(blob[:10]);i=1;p=10;total=struct.unpack_from('>H',blob,8)[0]
    while i<total:
        tag=blob[p];result.append(tag);p+=1
        if tag==1:
            n=struct.unpack_from('>H',blob,p)[0];p+=2
            v=blob[p:p+n];p+=n
            for key,new in changes.items():
                if key in v:counts[key]+=1;v=v.replace(key,new)
            result.extend(struct.pack('>H',len(v)));result.extend(v)
        elif tag in (3,4,9,10,11,12,17,18):result.extend(blob[p:p+4]);p+=4
        elif tag in (5,6):result.extend(blob[p:p+8]);p+=8;i+=1
        elif tag in (7,8,16,19,20):result.extend(blob[p:p+2]);p+=2
        elif tag==15:result.extend(blob[p:p+3]);p+=3
        else:raise AssertionError('unexpected constant pool entry')
        i+=1
    assert all(counts.values()),counts
    result.extend(blob[p:])
    return bytes(result)


def build(root,changed=False):
    source=root/'src/synthetic/fixture';source.mkdir(parents=True)
    getter='return second;' if changed else 'return first;'
    (source/'Hub.java').write_text(
        'package synthetic.fixture; import java.util.*; import java.util.concurrent.*;'
        'public class Hub {'
        'private static final List<Delegate> first=new CopyOnWriteArrayList<>();'
        'private static final List<Delegate> second=new CopyOnWriteArrayList<>();'
        'public static List<Delegate> first(){'+getter+'}'
        'public static List<Delegate> second(){return second;}'
        '@FunctionalInterface public interface Delegate {'
        'boolean draw(Object model,boolean active); } }\n',encoding='utf-8')
    classes=root/'classes';classes.mkdir()
    empty=root/'empty';empty.mkdir()
    run(['javac','--release','9','-g:none','-proc:none','-classpath',empty,
         '-sourcepath',empty,'-d',classes,source/'Hub.java'])
    pkg=classes/'synthetic/fixture'
    (pkg/'Hub.class').write_bytes(rename_metadata((pkg/'Hub.class').read_bytes()))
    (pkg/'Hub$Action.class').write_bytes(rename_metadata((pkg/'Hub$Delegate.class').read_bytes(),True))
    (pkg/'Hub$Delegate.class').unlink()
    return classes


@unittest.skipUnless(all(shutil.which(x) for x in ('javac','javap','java')),'JDK required')
class ToyOverlayRegistrySourceIsland(unittest.TestCase):
    def test_exact_two_class_outputs_deterministic_names_and_signatures(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a,b=build(root/'a'),build(root/'b')
            expected={'synthetic/fixture/Hub.class','synthetic/fixture/Hub$Action.class'}
            self.assertEqual({p.relative_to(a).as_posix() for p in a.rglob('*.class')},expected)
            for name in expected:
                self.assertEqual((a/name).read_bytes(),(b/name).read_bytes())
                self.assertEqual((a/name).read_bytes()[:8],bytes.fromhex('cafebabe00000035'))
            owner=run(['javap','-p','-s','-c','-classpath',a,'synthetic.fixture.Hub'])
            cb=run(['javap','-p','-s','-c','-classpath',a,'synthetic.fixture.Hub$Action'])
            self.assertIn('CopyOnWriteArrayList',owner)
            self.assertIn('Hub$Action>',owner)
            self.assertIn('(Ljava/lang/String;Z)Z',cb)
            self.assertNotIn('Delegate',owner+cb)

    def test_modified_method_rejected_despite_valid_new_source_and_class_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            first,changed=build(root/'baseline'),build(root/'changed',True)
            src=lambda key:(root/key/'src/synthetic/fixture/Hub.java').read_bytes()
            a=(first/'synthetic/fixture/Hub.class').read_bytes()
            b=(changed/'synthetic/fixture/Hub.class').read_bytes()
            self.assertNotEqual(hashlib.sha256(src('baseline')).digest(),hashlib.sha256(src('changed')).digest())
            self.assertNotEqual(hashlib.sha256(a).digest(),hashlib.sha256(b).digest())
            original=run(['javap','-p','-s','-c','-classpath',first,'synthetic.fixture.Hub'])
            mutated=run(['javap','-p','-s','-c','-classpath',changed,'synthetic.fixture.Hub'])
            self.assertNotEqual(original,mutated)
            self.assertEqual((first/'synthetic/fixture/Hub$Action.class').read_bytes(),
                             (changed/'synthetic/fixture/Hub$Action.class').read_bytes())

if __name__=='__main__':unittest.main(verbosity=2)

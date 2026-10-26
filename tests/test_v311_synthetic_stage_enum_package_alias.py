"""Synthetic-only Java9 enum TYPE/package collision and stable source-build test.

All classes, values and data are invented. No original game source or binaries.
"""
from pathlib import Path
import hashlib
import shutil
import struct
import subprocess
import tempfile
import unittest

def run(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=55)
    if p.returncode:raise AssertionError(p.stderr[-1200:])
    return p.stdout

def restore(blob,old,new):
    assert blob[:4]==bytes.fromhex('cafebabe')
    count=struct.unpack_from('>H',blob,8)[0]
    out=bytearray(blob[:10]);pos=10;i=1;changed=0
    while i<count:
        tag=blob[pos];out.append(tag);pos+=1
        if tag==1:
            n=struct.unpack_from('>H',blob,pos)[0];pos+=2
            value=blob[pos:pos+n];pos+=n
            fixed=value.replace(old.encode(),new.encode())
            changed+=(value!=fixed)
            out.extend(struct.pack('>H',len(fixed)));out.extend(fixed)
        elif tag in (3,4,9,10,11,12,17,18):out.extend(blob[pos:pos+4]);pos+=4
        elif tag in (5,6):out.extend(blob[pos:pos+8]);pos+=8;i+=1
        elif tag in (7,8,16,19,20):out.extend(blob[pos:pos+2]);pos+=2
        elif tag==15:out.extend(blob[pos:pos+3]);pos+=3
        else:raise AssertionError('unexpected constant pool tag')
        i+=1
    assert changed>0
    out.extend(blob[pos:])
    return bytes(out)

def compile_fixture(root,integrated=False,mutate=False):
    src=root/'src/toy/board';src.mkdir(parents=True)
    (src/'Counter.java').write_text('package toy.board; public class Counter {public int value(){return 73;}}\n')
    values='END, BEGIN' if mutate else 'BEGIN, END'
    if integrated:
        (src/'RecoveredTray.java').write_text('package toy.board; public enum RecoveredTray {'+values+';}\n')
        for label in ('north','south','east'):
            folder=src/'tray'/label;folder.mkdir(parents=True)
            (folder/(label.title()+'.java')).write_text(
                'package toy.board.tray.'+label+'; public enum '+label.title()+' { ENABLED, DISABLED; }\n')
    else:
        (src/'tray.java').write_text('package toy.board; public enum tray {'+values+';}\n')
    out=root/'classes';out.mkdir()
    empty=root/'empty';empty.mkdir()
    run(['javac','--release','9','-g:none','-proc:none',
         '-classpath',empty,'-sourcepath',empty,'-d',out,
         *sorted(src.rglob('*.java'))])
    if integrated:
        original=out/'toy/board/RecoveredTray.class'
        (out/'toy/board/tray.class').write_bytes(
            restore(original.read_bytes(),'toy/board/RecoveredTray','toy/board/tray'))
        original.unlink()
    return out

@unittest.skipUnless(all(shutil.which(x) for x in ('java','javac','javap')),'JDK required')
class SyntheticEnumPackageAlias(unittest.TestCase):
    def test_original_enum_unchanged_with_three_new_package_enums(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            previous=compile_fixture(root/'previous')
            integrated=compile_fixture(root/'integrated',True)
            rerun=compile_fixture(root/'rerun',True)
            names={p.relative_to(integrated).as_posix() for p in integrated.rglob('*.class')}
            self.assertEqual(names,{'toy/board/tray.class','toy/board/Counter.class',
                'toy/board/tray/north/North.class','toy/board/tray/south/South.class',
                'toy/board/tray/east/East.class'})
            for name in names:
                self.assertEqual((integrated/name).read_bytes(),(rerun/name).read_bytes())
                self.assertEqual((integrated/name).read_bytes()[:8],bytes.fromhex('cafebabe00000035'))
            self.assertEqual((previous/'toy/board/Counter.class').read_bytes(),
                             (integrated/'toy/board/Counter.class').read_bytes())
            old=run(['javap','-p','-s','-c','-classpath',previous,'toy.board.tray'])
            new=run(['javap','-p','-s','-c','-classpath',integrated,'toy.board.tray'])
            self.assertEqual(old,new)

    def test_changed_real_enum_jvm_rejected_after_both_hashes_change(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            reference=compile_fixture(root/'reference',True)
            candidate=compile_fixture(root/'candidate',True,True)
            old_src=(root/'reference/src/toy/board/RecoveredTray.java').read_bytes()
            new_src=(root/'candidate/src/toy/board/RecoveredTray.java').read_bytes()
            old_class=(reference/'toy/board/tray.class').read_bytes()
            new_class=(candidate/'toy/board/tray.class').read_bytes()
            self.assertNotEqual(hashlib.sha256(old_src).digest(),hashlib.sha256(new_src).digest())
            self.assertNotEqual(hashlib.sha256(old_class).digest(),hashlib.sha256(new_class).digest())
            original=run(['javap','-p','-s','-c','-classpath',reference,'toy.board.tray'])
            altered=run(['javap','-p','-s','-c','-classpath',candidate,'toy.board.tray'])
            self.assertNotEqual(original,altered)
            for stable in ('toy/board/Counter.class','toy/board/tray/north/North.class'):
                self.assertEqual((reference/stable).read_bytes(),(candidate/stable).read_bytes())

if __name__=='__main__':
    unittest.main(verbosity=2)

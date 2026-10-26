"""Toy-only Java9 PARTIAL method witness regression; no owner game identifiers/code."""
import hashlib
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


def run(argv):
    result = subprocess.run([str(v) for v in argv],capture_output=True,text=True,timeout=45)
    if result.returncode:
        raise AssertionError(result.stderr[-1200:])
    return result.stdout


def compile_island(root, altered=False):
    root=Path(root)
    java=root/'src/lab/controls/KeyTable.java';java.parent.mkdir(parents=True)
    last='55' if altered else '54'
    java.write_text('package lab.controls; public final class KeyTable {'
        'public static final int[] buttons = new int[4];'
        'public static boolean left,right,center,remote;'
        'public KeyTable(){}'
        'public static boolean first(){return false;}'
        'public static boolean second(){return false;}'
        'public static boolean third(){return second();}'
        'public static void change(boolean yes){'
        'if(yes){left=true;right=false;center=false;remote=false;}'
        'else{left=false;right=true;center=true;remote=true;}}'
        'public static void keys(){'
        'buttons[0]=51;buttons[1]=52;buttons[2]=53;buttons[3]='+last+';}'
        '}\n',encoding='utf-8')
    out=root/'classes';cp=root/'emptycp';sp=root/'emptysp'
    for d in (out,cp,sp):d.mkdir()
    run(['javac','--release','9','-g:none','-proc:none','-encoding','UTF-8',
         '-classpath',cp,'-sourcepath',sp,'-d',out,java])
    return java,out


def instructions(javap):
    return [re.sub(r'#[0-9]+','#CP',line.strip()) for line in javap.splitlines()
            if re.match(r'^\s*\d+:',line)]


@unittest.skipUnless(all(shutil.which(x) for x in ('javac','javap','java')),
                     'Java9-compatible JDK required')
class SyntheticPartialMethodWitness(unittest.TestCase):
    def test_reproducible_partial_source_and_safe_local_executable_methods(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            _,first=compile_island(root/'first')
            _,replay=compile_island(root/'replay')
            rel=Path('lab/controls/KeyTable.class')
            self.assertEqual({p.relative_to(first).as_posix() for p in first.rglob('*.class')},
                             {rel.as_posix()})
            self.assertEqual((first/rel).read_bytes(),(replay/rel).read_bytes())
            self.assertEqual((first/rel).read_bytes()[:8],bytes.fromhex('cafebabe00000035'))
            probe=root/'Probe.java'
            probe.write_text('import lab.controls.KeyTable;import java.util.Arrays;'
                'public class Probe {public static void main(String[] x){'
                'System.out.println(KeyTable.first()+","+KeyTable.second()+","+KeyTable.third());'
                'KeyTable.keys();System.out.println(Arrays.toString(KeyTable.buttons));'
                'KeyTable.change(true);System.out.println(KeyTable.left+","+KeyTable.remote);'
                'KeyTable.change(false);System.out.println(KeyTable.right+","+KeyTable.remote);'
                '}}\n',encoding='utf8')
            dst=root/'probes';dst.mkdir()
            run(['javac','--release','9','-cp',first,'-d',dst,probe])
            self.assertEqual(run(['java','-cp',str(first)+os.pathsep+str(dst),'Probe']).splitlines(),
                             ['false,false,false','[51, 52, 53, 54]','true,false','true,true'])

    def test_rehashed_real_keycode_instruction_mutation_fails_exact_original_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            oldsource,old=compile_island(root/'original')
            newsource,new=compile_island(root/'mutant',altered=True)
            rel=Path('lab/controls/KeyTable.class')
            sha=lambda b:hashlib.sha256(b).hexdigest()
            self.assertNotEqual(sha(oldsource.read_bytes()),sha(newsource.read_bytes()))
            self.assertNotEqual(sha((old/rel).read_bytes()),sha((new/rel).read_bytes()))
            baseline=instructions(run(['javap','-p','-s','-c','-classpath',old,
                                       'lab.controls.KeyTable']))
            candidate=instructions(run(['javap','-p','-s','-c','-classpath',new,
                                        'lab.controls.KeyTable']))
            self.assertNotEqual(baseline,candidate,
                                'A repinned class with altered JVM instructions is not original parity')
            self.assertEqual(len(baseline),len(candidate),
                             'Mutation changes a constant, not the number of instructions')


if __name__=='__main__':unittest.main(verbosity=2)

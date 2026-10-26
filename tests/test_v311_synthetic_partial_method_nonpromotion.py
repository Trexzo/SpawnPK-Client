"""Unrelated synthetic Java9 fixture for fail-closed selected-method comparisons.

This contains no game code. Selected-method parity cannot certify a full class.
"""
from __future__ import annotations
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ORIGINAL = """package sample;
public final class Record {
 public int x, y;
 public static final int[] TABLE=new int[]{3,4,5};
 public Record(int one,int two){x=one;y=two;}
 public void write(int value){x=value;}
 public int read(){return x;}
 public int optional(){return Flag.enabled ? y : -1;}
}
"""
PARTIAL = """package sample;
public final class Record {
 public int x,y;
 public Record(){} // original constructor and clinit deliberately absent
 public void write(int value){x=value;}
 public int read(){return x;}
 public int optional(){return Flag.enabled ? y : -1;}
}
"""
FLAG = """package sample;
public final class Flag {public static boolean enabled;}
"""
SELECTED=('public void write(int);','public int read();','public int optional();')


def selected(javap: str):
    lines=javap.splitlines()
    found={}
    for i,line in enumerate(lines):
        name=line.strip()
        if name not in SELECTED:continue
        if name in found:raise ValueError('duplicate method')
        if not lines[i+1].strip().startswith('descriptor: '):raise ValueError('missing descriptor')
        if lines[i+2].strip()!='Code:':raise ValueError('missing code')
        parsed=[]
        for instruction in lines[i+3:]:
            if not instruction.strip() or instruction.strip()=='}':break
            match=re.fullmatch(r'\s*(\d+):\s+([a-z][a-z0-9_]*)\s*(.*)',instruction)
            if not match:raise ValueError('unexpected instruction')
            off,op,arg=match.groups()
            if '#' in arg:
                front,sep,comment=arg.partition('//')
                if not sep:raise ValueError('missing symbolic constant-pool operand')
                arg=re.sub(r'#\d+\b','#CP',front).strip()+' // '+comment.strip()
            parsed.append((int(off),op,arg))
        found[name]=(lines[i+1].strip(),parsed)
    return found


@unittest.skipUnless(all(shutil.which(name) for name in ('javac','javap')),
                     'Java9 JDK required')
class SyntheticSelectedMethodTests(unittest.TestCase):
    def fixture(self,root:Path,partial=PARTIAL):
        outputs=[]
        for label,body in [('original',ORIGINAL),('partial',partial)]:
            src=root/label/'sample';src.mkdir(parents=True)
            (src/'Record.java').write_text(body,encoding='utf-8')
            (src/'Flag.java').write_text(FLAG,encoding='utf-8')
            out=root/label/'classes';out.mkdir()
            proc=subprocess.run(['javac','--release','9','-proc:none','-g:none',
                                 '-classpath',str(root/'empty-cp'),
                                 '-sourcepath',str(root/'empty-sp'),
                                 '-d',str(out),str(src/'Flag.java'),str(src/'Record.java')],
                                capture_output=True,text=True,timeout=40)
            self.assertEqual(proc.returncode,0,proc.stderr)
            shown=subprocess.run(['javap','-p','-s','-c','-classpath',str(out),
                                  'sample.Record'],capture_output=True,text=True,timeout=40)
            self.assertEqual(shown.returncode,0,shown.stderr)
            outputs.append((out,selected(shown.stdout)))
        return outputs

    def test_selected_bytecode_matches_without_full_class_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            (original,part)=self.fixture(Path(tmp))
            self.assertEqual(original[1],part[1])
            self.assertEqual(set(part[1]),set(SELECTED))
            self.assertNotEqual((original[0]/'sample/Record.class').read_bytes(),
                                (part[0]/'sample/Record.class').read_bytes())

    def test_method_mutation_is_rejected_despite_compilation(self):
        with tempfile.TemporaryDirectory() as tmp:
            (original,part)=self.fixture(Path(tmp),PARTIAL.replace(
                'int read(){return x;}', 'int read(){return y;}'))
            self.assertNotEqual(original[1],part[1])

    def test_wrong_method_descriptor_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            (original,part)=self.fixture(Path(tmp),PARTIAL.replace(
                'int read(){return x;}', 'long read(){return x;}'))
            self.assertNotEqual(set(part[1]),set(SELECTED))
            self.assertEqual(set(original[1]),set(SELECTED))

if __name__=='__main__':unittest.main()

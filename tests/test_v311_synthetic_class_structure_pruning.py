"""Original-independent toy Java9 structure-pruning regression (NO game source)."""
from pathlib import Path
import hashlib
import shutil
import struct
import subprocess
import tempfile
import unittest


def invoke(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=45)
    if p.returncode:raise AssertionError(p.stderr[-900:])
    return p.stdout


def build(root,fixed=7,prefix='MOCK:'):
    source=root/'src/toy/OrchardLedger.java';source.parent.mkdir(parents=True)
    source.write_text('package toy;public final class OrchardLedger{'
        f'public static final int NUMBER={fixed};'
        'public OrchardLedger(){}public boolean enabled(){return true;}'
        f'public String render(String x){{return "{prefix}"+x;}}'
        'private int compilerOnlyPadding(){return 567;}'
        '}\n',encoding='utf8')
    out,cp,sp=(root/d for d in ('classes','emptycp','emptysp'))
    for d in (out,cp,sp):d.mkdir()
    invoke(['javac','--release','9','-g:none','-proc:none','-classpath',cp,
            '-sourcepath',sp,'-d',out,source])
    return source,out


def u2(b,i):return struct.unpack_from('>H',b,i)[0]


def strip_helper(raw):
    """Toy-only method_info removal, leaving every retained method's raw Code intact."""
    b=raw
    assert b[:8]==bytes.fromhex('cafebabe00000035')
    strings={};i=1;p=10
    while i<u2(b,8):
        tag=b[p];p+=1
        if tag==1:
            n=u2(b,p);strings[i]=b[p+2:p+2+n].decode('utf8');p+=2+n
        elif tag in (3,4,9,10,11,12,17,18):p+=4
        elif tag in (5,6):p+=8;i+=1
        elif tag in (7,8,16,19,20):p+=2
        elif tag==15:p+=3
        else:raise ValueError('Unexpected JVM constant')
        i+=1
    p+=6
    interfaces=u2(b,p);p+=2+2*interfaces
    def next_member(cursor):
        q=cursor+6;attrs=u2(b,q);q+=2
        for _ in range(attrs):
            q+=6+struct.unpack_from('>I',b,q+2)[0]
        return q
    fields=u2(b,p);p+=2
    for _ in range(fields):p=next_member(p)
    count_pos=p;methods=u2(b,p);p+=2;old=[];new=[]
    for _ in range(methods):
        start=p;name=strings[u2(b,p+2)];p=next_member(p)
        old.append((name,b[start:p]))
        if name!='compilerOnlyPadding':new.append((name,b[start:p]))
    if len(old)!=4 or len(new)!=3:raise ValueError('Toy class structural mismatch')
    normalized=b[:count_pos]+struct.pack('>H',len(new))+b''.join(x[1] for x in new)+b[p:]
    return normalized,old,new


@unittest.skipUnless(all(shutil.which(x) for x in ('java','javac','javap')),
                     'Java9 JDK required')
class SyntheticStructurePruning(unittest.TestCase):
    def test_compiler_helper_excluded_without_changed_genuine_method_code(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);_,one=build(root/'first');_,two=build(root/'replay')
            rel=Path('toy/OrchardLedger.class')
            self.assertEqual((one/rel).read_bytes(),(two/rel).read_bytes())
            result,before,after=strip_helper((one/rel).read_bytes())
            self.assertEqual([m[1] for m in before if m[0]!='compilerOnlyPadding'],
                             [m[1] for m in after])
            dest=root/'normalized/toy/OrchardLedger.class';dest.parent.mkdir(parents=True)
            dest.write_bytes(result)
            shown=invoke(['javap','-p','-s','-c','-classpath',root/'normalized',
                          'toy.OrchardLedger'])
            self.assertIn('enabled()',shown);self.assertIn('render(',shown)
            self.assertNotIn('compilerOnlyPadding',shown)

    def test_real_rehashed_constantvalue_mutation_is_distinct(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src,a=build(root/'old',fixed=7);changed,b=build(root/'new',fixed=8)
            rel=Path('toy/OrchardLedger.class')
            h=lambda raw:hashlib.sha256(raw).hexdigest()
            self.assertNotEqual(h(src.read_bytes()),h(changed.read_bytes()))
            self.assertNotEqual(h((a/rel).read_bytes()),h((b/rel).read_bytes()))
            self.assertNotEqual(h(strip_helper((a/rel).read_bytes())[0]),
                                h(strip_helper((b/rel).read_bytes())[0]))
            self.assertIn('ConstantValue: int 7',
                          invoke(['javap','-v','-classpath',a,'toy.OrchardLedger']))
            self.assertIn('ConstantValue: int 8',
                          invoke(['javap','-v','-classpath',b,'toy.OrchardLedger']))

    def test_bootstrap_recipe_changes_while_visible_jvm_opcodes_match(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src,a=build(root/'old',prefix='MOCK:')
            changed,b=build(root/'new',prefix='FAKE:')
            rel=Path('toy/OrchardLedger.class')
            h=lambda raw:hashlib.sha256(raw).hexdigest()
            self.assertNotEqual(h(src.read_bytes()),h(changed.read_bytes()))
            self.assertNotEqual(h((a/rel).read_bytes()),h((b/rel).read_bytes()))
            jvm=lambda p:invoke(['javap','-p','-s','-c','-classpath',p,'toy.OrchardLedger'])
            self.assertEqual(jvm(a),jvm(b))
            verbose=lambda p:invoke(['javap','-v','-classpath',p,'toy.OrchardLedger'])
            self.assertIn('MOCK:',verbose(a))
            self.assertIn('FAKE:',verbose(b))
            self.assertNotEqual(verbose(a),verbose(b))


if __name__=='__main__':unittest.main(verbosity=2)

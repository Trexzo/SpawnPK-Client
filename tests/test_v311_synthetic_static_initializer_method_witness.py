"""Original-independent Java9 <clinit> and string bootstrap source-witness regression.

All names and values fictional. No owner/game code, hardware or network resources.
No class initializer is EVER loaded or executed; only javac + javap inspect it.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def execute(argv):
    out=subprocess.run([str(x) for x in argv],capture_output=True,text=True,timeout=40)
    if out.returncode:raise AssertionError(out.stderr[-1200:])
    return out.stdout


def build(root, value=1, prefix='MOCK:'):
    src=root/'src/fable/route';src.mkdir(parents=True)
    (src/'Flags.java').write_text(
        'package fable.route;public final class Flags {'
        'public enum Scene { MORNING, NOON; }'
        'public static Scene scene;public static String caption;'
        'public static int[] code;public static boolean ready;'
        'public static int level;'
        'private static String syntheticBase(){return "fake";}'
        'static {scene=Scene.MORNING;'
        'caption="'+prefix+'" + syntheticBase() + ":done";'
        'code=new int[3];ready=true;level='+str(value)+';}'
        'public static boolean check(){return false;}'
        '}\n',encoding='utf8')
    out,cp,sp=root/'classes',root/'emptycp',root/'emptysp'
    for p in (out,cp,sp):p.mkdir()
    execute(['javac','--release','9','-g:none','-proc:none',
             '-classpath',cp,'-sourcepath',sp,'-d',out,src/'Flags.java'])
    return src/'Flags.java',out


def disasm(out):
    return execute(['javap','-p','-s','-c','-classpath',out,'fable.route.Flags'])


def verbose(out):
    return execute(['javap','-p','-v','-classpath',out,'fable.route.Flags'])


@unittest.skipUnless(all(shutil.which(t) for t in ('javac','javap')),
                     'Requires Java9-compatible JDK tools')
class SyntheticStaticInitializationWitness(unittest.TestCase):
    def test_jdk_only_compilation_deterministic_without_runtime_execution(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            _,a=build(root/'first');_,b=build(root/'repeat')
            classes={p.relative_to(a).as_posix() for p in a.rglob('*.class')}
            self.assertEqual(classes,{'fable/route/Flags.class','fable/route/Flags$Scene.class'})
            for file in classes:
                self.assertEqual((a/file).read_bytes(),(b/file).read_bytes())
                self.assertEqual((a/file).read_bytes()[:8],bytes.fromhex('cafebabe00000035'))
            self.assertIn('static {};',disasm(a))
            self.assertIn('invokedynamic',disasm(a))
            self.assertIn('MOCK:',verbose(a))

    def test_real_changed_static_jvm_instruction_even_with_repinned_sha(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            srca,a=build(root/'first');srcb,b=build(root/'mutant',value=2)
            f='fable/route/Flags.class';digest=lambda raw:hashlib.sha256(raw).hexdigest()
            self.assertNotEqual(digest(srca.read_bytes()),digest(srcb.read_bytes()))
            self.assertNotEqual(digest((a/f).read_bytes()),digest((b/f).read_bytes()))
            self.assertNotEqual(disasm(a),disasm(b))

    def test_bootstrap_recipe_change_with_identical_visible_opcodes(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            srca,a=build(root/'first');srcb,b=build(root/'mutant',prefix='ALT:')
            f='fable/route/Flags.class';digest=lambda raw:hashlib.sha256(raw).hexdigest()
            self.assertNotEqual(digest(srca.read_bytes()),digest(srcb.read_bytes()))
            self.assertNotEqual(digest((a/f).read_bytes()),digest((b/f).read_bytes()))
            self.assertEqual(disasm(a),disasm(b),
                'A StringConcatFactory recipe mutation should retain visible opcodes')
            self.assertNotEqual(verbose(a),verbose(b))
            self.assertIn('MOCK:',verbose(a));self.assertIn('ALT:',verbose(b))


if __name__=='__main__':unittest.main(verbosity=2)

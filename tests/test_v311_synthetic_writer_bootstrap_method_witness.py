"""Fictional Java9 partial-method source witness / bootstrap regression.

Contains no owner game code, game identifiers, real filesystem operations in tests,
original binaries or actual game settings. The toy writer method is NEVER invoked.
"""
from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import tempfile
import unittest


def execute(argv):
    result = subprocess.run([str(v) for v in argv], text=True, capture_output=True, timeout=40)
    if result.returncode:
        raise AssertionError(result.stderr[-1200:])
    return result.stdout


def build(root, prefix='fiction=', reverse_branch=False):
    source = root / 'src/toy/garden/Notebook.java'
    source.parent.mkdir(parents=True)
    if_condition = 'page.exists()' if reverse_branch else '!page.exists()'
    source.write_text(
        'package toy.garden;import java.io.*;import java.nio.file.*;'
        'public final class Notebook {'
        'private static String path="unused-toy-file";'
        'private static boolean enabled;'
        'public static boolean off(){return false;}'
        'public static void writeButNeverCall() {'
        'try { File page = new File(path+".draft");'
        'if(' + if_condition + ')page.createNewFile();'
        'BufferedWriter sink=new BufferedWriter(new FileWriter(page));'
        'sink.write("' + prefix + '"+enabled);sink.newLine();'
        'sink.close();Path p=Paths.get(path+".draft");'
        'Files.copy(p,Paths.get(path),StandardCopyOption.REPLACE_EXISTING);'
        'Files.delete(p);'
        '}catch(Exception ex){ex.printStackTrace();}'
        '}}\n', encoding='utf-8')
    out, cp, sp = root/'classes', root/'emptycp', root/'emptysp'
    for directory in (out, cp, sp):directory.mkdir()
    execute(['javac', '--release', '9', '-g:none', '-proc:none', '-classpath', cp,
             '-sourcepath', sp, '-d', out, source])
    return source, out


def jvm_disassembly(classes):
    return execute(['javap', '-p', '-s', '-c', '-classpath', classes, 'toy.garden.Notebook'])


def recipes(classes):
    verbose = execute(['javap','-p','-v','-classpath',classes,'toy.garden.Notebook'])
    section = verbose.split('BootstrapMethods:', 1)[1].split('InnerClasses:', 1)[0]
    return re.findall(r'(?m)^\s*#[0-9]+\s+([^\n]+)', section)


@unittest.skipUnless(all(shutil.which(v) for v in ('javac','java','javap')),
                     'JDK 9-capable tools required')
class SyntheticPartialWriterWitness(unittest.TestCase):
    def test_deterministic_java9_island_and_safe_unrelated_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            _, first=build(root/'first')
            _, again=build(root/'again')
            cls=Path('toy/garden/Notebook.class')
            self.assertEqual({p.relative_to(first).as_posix() for p in first.rglob('*.class')},
                             {cls.as_posix()})
            self.assertEqual((first/cls).read_bytes(),(again/cls).read_bytes())
            self.assertEqual((first/cls).read_bytes()[:8],bytes.fromhex('cafebabe00000035'))
            self.assertIn('BufferedWriter',jvm_disassembly(first))
            self.assertTrue(any('fiction=' in item for item in recipes(first)))
            # Only the safe constant method is executed. No toy file writing is invoked.
            probe=root/'ToyProbe.java'
            probe.write_text('public class ToyProbe {public static void main(String[] args){'
                             'System.out.println(toy.garden.Notebook.off());}}\n')
            dest=root/'probe';dest.mkdir()
            execute(['javac','--release','9','-classpath',first,'-d',dest,probe])
            import os
            self.assertEqual(execute(['java','-classpath',str(first)+os.pathsep+str(dest),
                                      'ToyProbe']).strip(),'false')

    def test_repinned_recipe_change_with_same_visible_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            src_before,before=build(root/'before')
            src_after,after=build(root/'after',prefix='different=')
            h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            cls=Path('toy/garden/Notebook.class')
            self.assertNotEqual(h(src_before),h(src_after))
            self.assertNotEqual(h(before/cls),h(after/cls))
            self.assertEqual(jvm_disassembly(before),jvm_disassembly(after))
            self.assertNotEqual(recipes(before),recipes(after))

    def test_repinned_real_jvm_condition_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            src_before,before=build(root/'before')
            src_after,after=build(root/'after',reverse_branch=True)
            h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            cls=Path('toy/garden/Notebook.class')
            self.assertNotEqual(h(src_before),h(src_after))
            self.assertNotEqual(h(before/cls),h(after/cls))
            self.assertNotEqual(jvm_disassembly(before),jvm_disassembly(after))


if __name__=='__main__':
    unittest.main(verbosity=2)

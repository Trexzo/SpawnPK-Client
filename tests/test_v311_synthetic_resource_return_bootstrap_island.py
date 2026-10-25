"""Fictional Java9 source-island compiler/bootstrap regression.

No owner game classes, code, actual machine identifiers, or external processes.
"""
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


def invoke(args):
    out = subprocess.run([str(x) for x in args], capture_output=True,
                         text=True, timeout=50)
    if out.returncode:
        raise AssertionError(out.stderr[-1200:])
    return out.stdout


def build(root, prefix='TOY '):
    source = root / 'src/fake/orbits/ResourceExample.java'
    source.parent.mkdir(parents=True)
    source.write_text(
        'package fake.orbits; import java.io.*;'
        'public class ResourceExample {'
        'public static String fold(String one,String two)throws Exception {'
        'try(BufferedReader r=new BufferedReader(new StringReader(one))){'
        'String s=r.readLine();return "' + prefix + '" + s + two;'
        '} } }\n', encoding='utf-8')
    classes = root / 'classes'
    cp, sp = root/'emptycp', root/'emptysp'
    for p in (classes, cp, sp):
        p.mkdir()
    invoke(['javac', '--release', '9', '-proc:none', '-g:none',
            '-classpath', cp, '-sourcepath', sp, '-d', classes, source])
    return source, classes


def recipe(verbose):
    found = re.findall(r'^\s*Method arguments:\s*\n\s*#\d+\s+([^\n]+)',
                       verbose, re.MULTILINE)
    if len(found) != 1:
        raise AssertionError('Exactly one toy Java9 concat recipe is required')
    return found[0]


@unittest.skipUnless(all(shutil.which(x) for x in ('javac','javap','java')),
                     'JDK9+ required')
class SyntheticResourceReturnBootstrapIsland(unittest.TestCase):
    def test_deterministic_jdk_only_source_and_resource_closure(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, first = build(base/'first')
            _, again = build(base/'again')
            cls = Path('fake/orbits/ResourceExample.class')
            self.assertEqual({p.relative_to(first).as_posix()
                              for p in first.rglob('*.class')}, {cls.as_posix()})
            self.assertEqual((first/cls).read_bytes(), (again/cls).read_bytes())
            self.assertEqual((first/cls).read_bytes()[:8],
                             bytes.fromhex('cafebabe00000035'))
            code = invoke(['javap','-p','-s','-c','-classpath',first,
                           'fake.orbits.ResourceExample'])
            self.assertIn('BufferedReader.close', code)
            self.assertIn('invokedynamic', code)
            self.assertIn('TOY ', recipe(invoke(['javap','-v','-classpath',first,
                                               'fake.orbits.ResourceExample'])))

    def test_changed_recipe_detected_even_with_same_javap_instructions_and_new_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            old_src, old = build(base/'old','TOY ')
            new_src, new = build(base/'new','ALT ')
            cls = Path('fake/orbits/ResourceExample.class')
            sha = lambda b: hashlib.sha256(b).hexdigest()
            self.assertNotEqual(sha(old_src.read_bytes()), sha(new_src.read_bytes()))
            self.assertNotEqual(sha((old/cls).read_bytes()), sha((new/cls).read_bytes()))
            old_code = invoke(['javap','-p','-s','-c','-classpath',old,
                               'fake.orbits.ResourceExample'])
            new_code = invoke(['javap','-p','-s','-c','-classpath',new,
                               'fake.orbits.ResourceExample'])
            self.assertEqual(old_code, new_code,
                             'Visible JVM opcodes are intentionally identical')
            old_recipe = recipe(invoke(['javap','-v','-classpath',old,
                                        'fake.orbits.ResourceExample']))
            new_recipe = recipe(invoke(['javap','-v','-classpath',new,
                                        'fake.orbits.ResourceExample']))
            self.assertNotEqual(old_recipe, new_recipe)
            self.assertIn('TOY ', old_recipe)
            self.assertIn('ALT ', new_recipe)


if __name__ == '__main__':
    unittest.main(verbosity=2)

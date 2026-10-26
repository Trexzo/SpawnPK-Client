"""Synthetic-only Java9 OS routing source island; NO recovered game source/data."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def run(command):
    p = subprocess.run([str(v) for v in command], capture_output=True, text=True, timeout=40)
    if p.returncode:
        raise AssertionError(p.stderr[-1200:])
    return p.stdout


def compile_toy(root, changed=False):
    src = root / 'src/demo/environment'
    src.mkdir(parents=True)
    cmp = '>= 0' if changed else '> 0'
    (src / 'PlatformGate.java').write_text(
        'package demo.environment; public class PlatformGate {'
        'private static final String os=System.getProperty("os.name","fictional").toLowerCase();'
        'public static boolean win(){return os.indexOf("win")>=0;}'
        'public static boolean mac(){return os.indexOf("mac")>=0;}'
        'public static boolean unix(){return os.indexOf("nix")>=0'
        '||os.indexOf("nux")>=0||os.indexOf("aix")' + cmp + ';}'
        'public static boolean sun(){return os.indexOf("sunos")>=0;}'
        'public static void main(String[] args){System.out.println('
        'win()+":"+mac()+":"+unix()+":"+sun());}}\n', encoding='utf8')
    out = root / 'classes'
    emptycp = root / 'emptycp'
    emptysp = root / 'emptysp'
    for d in (out, emptycp, emptysp):
        d.mkdir()
    run(['javac', '--release', '9', '-g:none', '-proc:none', '-classpath', emptycp,
         '-sourcepath', emptysp, '-d', out, src / 'PlatformGate.java'])
    return out


@unittest.skipUnless(all(shutil.which(x) for x in ('javac', 'java', 'javap')),
                     'A Java9-compatible JDK is required')
class SyntheticOsGateSourceIsland(unittest.TestCase):
    def test_reproducible_jdk_only_class_and_fake_os_routing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = compile_toy(root / 'first'), compile_toy(root / 'second')
            name = Path('demo/environment/PlatformGate.class')
            self.assertEqual({p.relative_to(a).as_posix() for p in a.rglob('*.class')},
                             {name.as_posix()})
            self.assertEqual((a/name).read_bytes(), (b/name).read_bytes())
            self.assertEqual((a/name).read_bytes()[:8], bytes.fromhex('cafebabe00000035'))
            examples = {
                'MockWindows': 'true:false:false:false',
                'MockMac': 'false:true:false:false',
                'MockLinux': 'false:false:true:false',
                'AIX': 'false:false:false:false',
                'prefix-aix-suffix': 'false:false:true:false',
                'SunOS': 'false:false:false:true',
                'Unknown': 'false:false:false:false',
            }
            for name, expected in examples.items():
                self.assertEqual(run(['java', '-Dos.name='+name, '-cp', a,
                                      'demo.environment.PlatformGate']).strip(), expected)

    def test_changed_jvm_condition_rejected_after_both_hashes_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prior = compile_toy(root / 'prior')
            changed = compile_toy(root / 'changed', changed=True)
            src = Path('src/demo/environment/PlatformGate.java')
            cls = Path('demo/environment/PlatformGate.class')
            dig = lambda b: hashlib.sha256(b).digest()
            self.assertNotEqual(dig((root/'prior'/src).read_bytes()),
                                dig((root/'changed'/src).read_bytes()))
            self.assertNotEqual(dig((prior/cls).read_bytes()),
                                dig((changed/cls).read_bytes()))
            orig_jvm = run(['javap', '-p', '-s', '-c', '-classpath', prior,
                            'demo.environment.PlatformGate'])
            altered_jvm = run(['javap', '-p', '-s', '-c', '-classpath', changed,
                               'demo.environment.PlatformGate'])
            self.assertNotEqual(orig_jvm, altered_jvm)


if __name__ == '__main__':
    unittest.main(verbosity=2)

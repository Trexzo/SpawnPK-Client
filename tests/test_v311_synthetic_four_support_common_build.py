"""Wholly fictional Java9 source integration: no game/owner/client code or OS commands."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest


def invoke(args):
    result=subprocess.run([str(a) for a in args],capture_output=True,text=True,timeout=45)
    if result.returncode:raise AssertionError(result.stderr[-900:])
    return result.stdout


def build(root,include_new=False,changed_recipe=False):
    src=root/'src/toy/ledger';src.mkdir(parents=True)
    (src/'Stable.java').write_text('package toy.ledger;public final class Stable {public int number(){return 7;}}\n')
    (src/'StableTwo.java').write_text('package toy.ledger;public final class StableTwo {public String tag(){return "fixed";}}\n')
    if include_new:
        prefix='ALT=' if changed_recipe else 'BASE='
        (src/'One.java').write_text('package toy.ledger;public final class One {private static String memo="SYNTHETIC";public static String get(){return memo;}}\n')
        (src/'Two.java').write_text('package toy.ledger;public final class Two {public static String message(String value){return "'+prefix+'"+value+"!";}}\n')
        (src/'Three.java').write_text('package toy.ledger;public final class Three {public static int parse(String n){return Integer.parseInt(n);}}\n')
        (src/'Four.java').write_text('package toy.ledger;public final class Four {public static boolean guess(String n){return n.startsWith("fake");}}\n')
    target=root/'compiled';cp=root/'emptycp';sp=root/'emptysp'
    for folder in (target,cp,sp):folder.mkdir()
    invoke(['javac','--release','9','-g:none','-proc:none','-classpath',cp,
            '-sourcepath',sp,'-d',target,*sorted(src.glob('*.java'))])
    return target


@unittest.skipUnless(all(shutil.which(t) for t in ('java','javac','javap')),'Java9 JDK required')
class SyntheticFourSupportIntegration(unittest.TestCase):
    def test_prior_class_sha_stable_and_all_six_outputs_reproducible(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            old=build(root/'old')
            compiled=build(root/'new',True)
            repeat=build(root/'repeat',True)
            relative=lambda name:Path('toy/ledger')/(name+'.class')
            self.assertEqual(len(list(compiled.rglob('*.class'))),6)
            for cls in ('Stable','StableTwo'):
                self.assertEqual((old/relative(cls)).read_bytes(),(compiled/relative(cls)).read_bytes())
            for cls in ('Stable','StableTwo','One','Two','Three','Four'):
                raw=(compiled/relative(cls)).read_bytes()
                self.assertEqual(raw,(repeat/relative(cls)).read_bytes())
                self.assertEqual(raw[:8],bytes.fromhex('cafebabe00000035'))
            self.assertIn('invokedynamic',invoke(['javap','-p','-c','-classpath',compiled,'toy.ledger.Two']))

    def test_same_visible_jvm_instructions_can_have_different_real_bootstrap_recipe(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            prior=build(root/'prior',True)
            altered=build(root/'altered',True,True)
            origsrc=(root/'prior/src/toy/ledger/Two.java').read_bytes()
            new_src=(root/'altered/src/toy/ledger/Two.java').read_bytes()
            rel=Path('toy/ledger/Two.class')
            digest=lambda b:hashlib.sha256(b).hexdigest()
            self.assertNotEqual(digest(origsrc),digest(new_src))
            self.assertNotEqual(digest((prior/rel).read_bytes()),digest((altered/rel).read_bytes()))
            first=invoke(['javap','-p','-s','-c','-classpath',prior,'toy.ledger.Two'])
            second=invoke(['javap','-p','-s','-c','-classpath',altered,'toy.ledger.Two'])
            self.assertEqual(first,second)
            detailed_prior=invoke(['javap','-p','-v','-classpath',prior,'toy.ledger.Two'])
            detailed_altered=invoke(['javap','-p','-v','-classpath',altered,'toy.ledger.Two'])
            self.assertIn('BASE=',detailed_prior)
            self.assertIn('ALT=',detailed_altered)
            self.assertNotEqual(detailed_prior,detailed_altered)
            for cls in ('Stable','StableTwo','One','Three','Four'):
                self.assertEqual((prior/Path('toy/ledger')/(cls+'.class')).read_bytes(),
                                 (altered/Path('toy/ledger')/(cls+'.class')).read_bytes())


if __name__=='__main__':unittest.main(verbosity=2)

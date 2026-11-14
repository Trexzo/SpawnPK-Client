"""Source-free R389 sorting regression. No original or private JARs needed."""
from __future__ import annotations
import hashlib, importlib.util, io, pathlib, unittest, zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNNER=ROOT/'tools/r383/verify_private_full_build.py'
WRAPPER=ROOT/'tools/r386/run_self_contained_acceptance.py'
spec=importlib.util.spec_from_file_location('r389_runner',RUNNER)
r389=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r389)

class CanonicalOrderTests(unittest.TestCase):
    names=('com/apple/eawt/FullScreenAdapter.class',
           'com/apple/eawt/event/FullScreenEvent.class',
           'com/apple/eawt/FullScreenListener.class',
           'rs/audio/Filter.class', 'rs/ChatEncoder.class')

    def test_windows_paths_sort_differently(self):
        windows=sorted(pathlib.PureWindowsPath(n) for n in self.names)
        self.assertNotEqual([x.as_posix() for x in windows], sorted(self.names))

    def test_explicit_posix_key_restores_ascii_order(self):
        windows=sorted((pathlib.PureWindowsPath(n) for n in self.names),key=lambda p:p.as_posix())
        self.assertEqual([x.as_posix() for x in windows],sorted(self.names))

    def test_corrected_source_uses_relative_posix_sort(self):
        content=RUNNER.read_text(encoding='utf-8')
        self.assertIn('classfiles=sorted(classes.rglob("*.class"), key=lambda p: p.relative_to(classes).as_posix())', content)
        self.assertNotIn('classfiles=sorted(classes.rglob("*.class"))',content)

    def test_corrected_runner_sha_pinned(self):
        observed=hashlib.sha256(RUNNER.read_bytes()).hexdigest()
        self.assertEqual(observed,'d09947d5863fc361e7f8362fbcabe5e100452d160ee69fee089f5fb6106944af')
        self.assertIn('RUNNER_SHA = \''+observed+'\'',WRAPPER.read_text(encoding='utf-8'))

    def test_zipinfo_canonical_creator(self):
        info=r389.canonical_class_zipinfo('rs/Client.class')
        self.assertEqual(info.create_system,3)
        self.assertEqual(info.date_time,(2026,10,18,0,0,0))
        self.assertEqual(info.compress_type,zipfile.ZIP_DEFLATED)

    def test_unsafe_member_rejected(self):
        for name in ('../rs/Client.class','rs\\Client.class','/rs/Client.class','rs/Client.txt'):
            with self.subTest(name=name),self.assertRaises(r389.Refused):
                r389.canonical_class_zipinfo(name)

    def test_synthetic_jar_independent_of_iteration_order(self):
        entries={n:('synthetic-'+n).encode() for n in self.names}
        def package(order):
            b=io.BytesIO()
            with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                for n in sorted(order,key=lambda x:x):
                    z.writestr(r389.canonical_class_zipinfo(n),entries[n],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
            return b.getvalue()
        self.assertEqual(package(self.names),package(reversed(self.names)))

    def test_drift_fixture_fails_without_explicit_sort(self):
        entries={n:('synthetic-'+n).encode() for n in self.names}
        def package(order):
            b=io.BytesIO()
            with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                for n in order:
                    z.writestr(r389.canonical_class_zipinfo(n),entries[n],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
            return hashlib.sha256(b.getvalue()).hexdigest()
        self.assertNotEqual(package(self.names),package(reversed(self.names)))

    def test_windows_claim_remains_strict(self):
        self.assertIn('R386_WINDOWS_FULL_BUILD_PASS', WRAPPER.read_text(encoding='utf-8'))
        self.assertIn('R386_REFUSED_OR_DRIFT', WRAPPER.read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main(verbosity=2)

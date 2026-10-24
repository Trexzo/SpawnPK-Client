#!/usr/bin/env python3
"""Independent R288 source-only release verifier; never runs a Windows GUI."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

ALLOWED = {
    'README.md',
    'tools/windows/R287-Owner-Readiness.py',
    'tests/python/r287/R287ReadinessRegression.py',
    'tests/R288ReleaseRegression.py',
}
PINNED_R287 = '19bae667ea659924375c956acd1a9628c37784298434acfcfb76c5df743e1e5d'
PINNED_R287_BLOB = '9f0a93da88b25ca1d3f78959cfe882a8312733cb'
PINNED_TEST_BLOB = 'db07ec105c8f6980f2948d5bd2fc7f13082a16f1'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def validate_package(path, expected_sha=None):
    path = Path(path)
    if expected_sha and sha256(path.read_bytes()) != expected_sha.lower():
        raise AssertionError('unverified exact release SHA256')
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise AssertionError('duplicate zip entries')
        if set(names) != ALLOWED | {'MANIFEST.json'}:
            raise AssertionError('unexpected/absent ZIP members')
        if z.testzip() is not None:
            raise AssertionError('ZIP CRC failure')
        for info in z.infolist():
            p = PurePosixPath(info.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in info.filename:
                raise AssertionError('unsafe ZIP member path')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise AssertionError('symlink forbidden')
            if info.file_size > 50_000:
                raise AssertionError('unexpected huge source member')
            if info.filename.lower().endswith(('.jar','.class','.dat','.idx','.ttf','.otf','.exe','.dll','.png')):
                raise AssertionError('private/binary member')
        manifest = json.loads(z.read('MANIFEST.json'))
        if manifest['milestone'] != 'R288' or manifest['native_windows_gui'] != 'NOT_TESTED':
            raise AssertionError('release provenance')
        if manifest['client_changes'] != 0 or manifest['private_assets_included']:
            raise AssertionError('asset isolation violation')
        if set(manifest['files']) != ALLOWED:
            raise AssertionError('incorrect manifest file list')
        for name, expected in manifest['files'].items():
            data = z.read(name)
            if len(data) != expected['bytes'] or sha256(data) != expected['sha256']:
                raise AssertionError('manifest mismatch: '+name)
        probe = z.read('tools/windows/R287-Owner-Readiness.py')
        tests = z.read('tests/python/r287/R287ReadinessRegression.py')
        if sha256(probe) != PINNED_R287 or git_blob(probe) != PINNED_R287_BLOB:
            raise AssertionError('R287 source drift')
        if git_blob(tests) != PINNED_TEST_BLOB:
            raise AssertionError('R287 regression drift')
    return {'source_files': len(ALLOWED), 'original_r287_git_sha1': PINNED_R287_BLOB,
            'native_windows': 'NOT_TESTED', 'source_only': True}


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='r288-verifier-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.real_archive = Path(__file__).resolve().parents[0] / 'SpawnPK_v309_R288_OWNER_ACCEPTANCE_GATE_SOURCE_ONLY.zip'
        if not self.real_archive.exists():
            self.real_archive = Path(sys.argv[1]) if len(sys.argv)>1 else self.real_archive

    def test_released_archive(self):
        result = validate_package(self.real_archive)
        self.assertEqual(result['source_files'],4)
        self.assertTrue(result['source_only'])

    def test_exact_sha_enforced(self):
        self.assertRaises(AssertionError, validate_package, self.real_archive, 'a'*64)

    def test_release_is_no_game_binary(self):
        with zipfile.ZipFile(self.real_archive) as z:
            self.assertFalse(any(n.lower().endswith(('.jar','.class','.exe','.dll','.png','.dat')) for n in z.namelist()))

    def test_r287_code_unchanged(self):
        with zipfile.ZipFile(self.real_archive) as z:
            data=z.read('tools/windows/R287-Owner-Readiness.py')
        self.assertEqual(git_blob(data),PINNED_R287_BLOB)

    def test_r287_regression_unchanged(self):
        with zipfile.ZipFile(self.real_archive) as z:
            data=z.read('tests/python/r287/R287ReadinessRegression.py')
        self.assertEqual(git_blob(data),PINNED_TEST_BLOB)

    def test_r287_regressions_on_clean_unpacked_sources(self):
        with zipfile.ZipFile(self.real_archive) as z:
            for name in ALLOWED:
                target = self.root / name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(z.read(name))
        result = subprocess.run([sys.executable, str(self.root/'tests/python/r287/R287ReadinessRegression.py')],
                                cwd=self.root, capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Ran 20 tests',result.stderr)
        self.assertIn('OK',result.stderr)

    def test_no_hidden_owner_assets(self):
        with zipfile.ZipFile(self.real_archive) as z:
            text = z.read('README.md').decode('utf-8')
            self.assertIn('no game code',text.lower())
            self.assertIn('unverified',text)

    def test_no_absolute_paths(self):
        with zipfile.ZipFile(self.real_archive) as z:
            for name in z.namelist():
                self.assertFalse(name.startswith('/'))
                self.assertNotIn('..', PurePosixPath(name).parts)

    def test_deterministic_zip_timestamps(self):
        with zipfile.ZipFile(self.real_archive) as z:
            dates = set(x.date_time for x in z.infolist())
            self.assertEqual(len(dates),1)

    def test_source_zip_small(self):
        self.assertLess(self.real_archive.stat().st_size,100_000)

    def test_rejection_of_unauthorized_member(self):
        new=self.root/'tampered.zip'
        with zipfile.ZipFile(self.real_archive) as src, zipfile.ZipFile(new,'w') as dst:
            for name in src.namelist():dst.writestr(name,src.read(name))
            dst.writestr('client.jar',b'bad')
        self.assertRaises(AssertionError,validate_package,new)

    def test_rejection_of_modified_source(self):
        new=self.root/'tampered-source.zip'
        with zipfile.ZipFile(self.real_archive) as src, zipfile.ZipFile(new,'w') as dst:
            for name in src.namelist():
                data=src.read(name)
                if name=='tools/windows/R287-Owner-Readiness.py':data+=b'# tampered\n'
                dst.writestr(name,data)
        self.assertRaises(AssertionError,validate_package,new)

    def test_rejection_of_duplicate_member(self):
        new=self.root/'duplicates.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(self.real_archive) as src, zipfile.ZipFile(new,'w') as dst:
                for name in src.namelist():dst.writestr(name,src.read(name))
                dst.writestr('README.md',b'duplicate')
        self.assertRaises(AssertionError,validate_package,new)


if __name__=='__main__':
    unittest.main(argv=[sys.argv[0]],verbosity=2)

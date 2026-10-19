#!/usr/bin/env python3
"""Deterministic Linux-executable R287 test suite (no private owner archives)."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[3] / 'tools/windows/R287-Owner-Readiness.py'
spec = importlib.util.spec_from_file_location('r287_readiness', SOURCE)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r287-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.inputs = self.base/'inputs'
        self.inputs.mkdir()
        self.output = self.base/'new-acceptance'
        self.package = self.inputs/'r286.zip'
        self.package.write_bytes(b'source-only public fixture')
        self.expected = {}
        for label in ('r278','r265','assets','original','r230'):
            name = label+'.zip'
            data = ('dummy-'+label).encode()
            (self.inputs/name).write_bytes(data)
            self.expected[label] = (name, r.hashlib.sha256(data).hexdigest())
        self.release = ('r286.zip', r.hashlib.sha256(self.package.read_bytes()).hexdigest())
        self.release_patch = mock.patch.object(r, 'RELEASE', self.release)
        self.release_patch.start()
        self.addCleanup(self.release_patch.stop)

    def check(self, **overrides):
        args = dict(input_dir=self.inputs, evidence=self.package, output=self.output,
                    platform_name='win32', expectations=self.expected,
                    prerequisites=lambda: {'python':True,'pillow':True,'java':True,'javac':True},
                    screen_probe=lambda: {'valid':True,'width':1400,'height':900,'dpi':96},
                    port_probe=lambda: True)
        args.update(overrides)
        return r.readiness(**args)

    def test_all_checks_good_no_output_created(self):
        result = self.check()
        self.assertTrue(result['ready'])
        self.assertEqual(len(result['checks']), 15)
        self.assertFalse(self.output.exists())
        self.assertFalse(result['client_modified'])
        self.assertFalse(result['created_output'])

    def test_missing_original_input_denied(self):
        (self.inputs/'original.zip').unlink()
        result = self.check()
        self.assertFalse(result['ready'])
        self.assertFalse(next(x for x in result['checks'] if x['check']=='sha256_original')['pass'])

    def test_tampered_archive_denied(self):
        (self.inputs/'r278.zip').write_bytes(b'tampered')
        self.assertFalse(self.check()['ready'])

    def test_tampered_release_denied(self):
        self.package.write_bytes(b'tampered')
        self.assertFalse(self.check()['ready'])

    def test_missing_release_denied(self):
        self.package.unlink()
        self.assertFalse(self.check()['ready'])

    def test_linux_cannot_claim_windows_readiness(self):
        result = self.check(platform_name='linux')
        self.assertFalse(result['ready'])
        self.assertFalse(next(x for x in result['checks'] if x['check']=='native_windows')['pass'])
        self.assertEqual(next(x for x in result['checks'] if x['check']=='primary_display')['detail'], 'not attempted off Windows')

    def test_wrong_physical_screen_denied(self):
        self.assertFalse(self.check(screen_probe=lambda: {'valid':False,'width':2560,'height':1440,'dpi':96})['ready'])

    def test_wrong_dpi_denied(self):
        self.assertFalse(self.check(screen_probe=lambda: {'valid':False,'width':1400,'height':900,'dpi':144})['ready'])

    def test_window_probe_error_denied(self):
        def broken(): raise OSError('display unavailable')
        self.assertFalse(self.check(screen_probe=broken)['ready'])

    def test_busy_loopback_port_denied(self):
        self.assertFalse(self.check(port_probe=lambda:False)['ready'])

    def test_missing_javac_denied(self):
        deps = lambda: {'python':True,'pillow':True,'java':True,'javac':False}
        self.assertFalse(self.check(prerequisites=deps)['ready'])

    def test_existing_output_never_overwritten(self):
        self.output.mkdir()
        self.assertFalse(self.check()['ready'])

    def test_nested_output_denied(self):
        self.assertFalse(self.check(output=self.inputs/'unsafe')['ready'])

    def test_missing_output_parent_denied(self):
        self.assertFalse(self.check(output=self.base/'missing'/'unsafe')['ready'])

    def test_dangling_output_symlink_denied(self):
        self.output.symlink_to(self.base/'absent')
        self.assertFalse(self.check()['ready'])

    def test_symlinked_owner_archive_denied(self):
        path=self.inputs/'r278.zip'
        path.unlink()
        path.symlink_to(self.inputs/'r265.zip')
        self.assertFalse(self.check()['ready'])

    def test_versions(self):
        self.assertEqual(r.java_major('javac 21.0.6'),21)
        self.assertEqual(r.java_major('java version "1.8.0_281"'),8)
        self.assertEqual(r.java_major('openjdk version "11.0.18" 2023-01-17'),11)
        self.assertIsNone(r.java_major('unknown'))

    def test_default_release_sha_remains_pinned(self):
        self.assertEqual(r.ARCHIVES['r278'][1], 'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280')
        self.assertEqual(len(r.ARCHIVES),5)

    def test_actual_cli_on_linux_fails_without_creation(self):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            status = r.main(['--input-dir',str(self.inputs),'--r286-evidence',str(self.package),
                             '--output',str(self.output)])
        self.assertEqual(status,2)
        out=json.loads(stream.getvalue())
        self.assertFalse(out['ready'])
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""R292 deterministic admission tests; no original game binary or GUI required."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
FILE = ROOT/'tools/windows/r292/R292-Owner-Readiness-Gate.py'
spec=importlib.util.spec_from_file_location('r292_admission', FILE)
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

class Source:
    def __init__(self, error=None):self.error=error;self.called=False
    def preflight(self, input_dir, output):
        self.called=True
        if self.error:raise ValueError(self.error)
    def main(self,args):
        raise AssertionError('test unexpectedly launched owner GUI')

class R292Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='spk-r292-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.inputs=self.root/'inputs';self.inputs.mkdir()
        self.output=self.root/'output'
        self.release=self.root/'original-r291-public.zip'
        self.loader=Source()
        self.gooddeps=lambda:dict(python=True,pillow=True,java=True,javac=True)
        self.gooddisplay=lambda:dict(ok=True,width=1400,height=900,dpi=96)
    def inspect(self,**overrides):
        data=dict(loader=lambda p:self.loader,runtime=self.gooddeps,display=self.gooddisplay,
                  port=lambda:True,platform='win32')
        data.update(overrides)
        return a.admission(self.inputs,self.release,self.output,**data)[0]
    def check(self,report,key):
        return next(x for x in report['checks'] if x['check']==key)
    def test_exact_release_sha_pin(self):
        self.assertEqual(a.R291_RELEASE[1],'f932bd9d83b0ddb94f2373d5ba06f9aa65456a6d8b06c4b62f4616992fc0763a')
    def test_exact_public_python_pin(self):
        self.assertEqual(a.R291_ENTRY_SHA,'f4142c448cd6d153b2c66c33b88c527ae9b6378ab8c183a2086dd1a82debad91')
    def test_full_positive_readiness(self):
        report=self.inspect()
        self.assertTrue(report['ready']);self.assertEqual(report['checks_count'],10)
        self.assertTrue(self.loader.called)
        self.assertFalse(self.output.exists())
    def test_windows_refusal(self):
        report=self.inspect(platform='linux')
        self.assertFalse(report['ready']);self.assertFalse(self.check(report,'win32')['pass'])
    def test_untrusted_prior_release_refusal(self):
        report=self.inspect(loader=lambda p: (_ for _ in ()).throw(ValueError('tampered')))
        self.assertFalse(self.check(report,'r291_original_source_sha256')['pass'])
        self.assertFalse(self.check(report,'seven_owner_archives_and_r290_overlay')['pass'])
    def test_missing_private_input_fail_closed(self):
        self.loader=Source('owner hash mismatch')
        report=self.inspect()
        self.assertFalse(report['ready']);self.assertIn('hash mismatch',self.check(report,'seven_owner_archives_and_r290_overlay')['detail'])
    def test_absent_python_refused(self):
        r=self.inspect(runtime=lambda:{**self.gooddeps(),'python':False})
        self.assertFalse(r['ready'])
    def test_absent_pillow_refused(self):
        r=self.inspect(runtime=lambda:{**self.gooddeps(),'pillow':False})
        self.assertFalse(r['ready'])
    def test_absent_java_refused(self):
        r=self.inspect(runtime=lambda:{**self.gooddeps(),'java':False})
        self.assertFalse(r['ready'])
    def test_absent_javac_refused(self):
        r=self.inspect(runtime=lambda:{**self.gooddeps(),'javac':False})
        self.assertFalse(r['ready'])
    def test_runtime_exception_refusal(self):
        def broken():raise TimeoutError('simulated')
        r=self.inspect(runtime=broken)
        self.assertFalse(r['ready']);self.assertEqual(sum(x['pass'] for x in r['checks'] if x['check'] in self.gooddeps()),0)
    def test_wrong_screen_refusal(self):
        r=self.inspect(display=lambda:{'ok':False,'width':1920,'height':1080,'dpi':96})
        self.assertFalse(self.check(r,'primary_1400x900_96dpi')['pass'])
    def test_wrong_dpi_refusal(self):
        r=self.inspect(display=lambda:{'ok':False,'width':1400,'height':900,'dpi':144})
        self.assertFalse(r['ready'])
    def test_display_exception_refusal(self):
        def broken():raise OSError('no display')
        self.assertFalse(self.inspect(display=broken)['ready'])
    def test_busy_localhost_refusal(self):
        self.assertFalse(self.inspect(port=lambda:False)['ready'])
    def test_socket_exception_refusal(self):
        def broken():raise OSError('busy')
        self.assertFalse(self.inspect(port=broken)['ready'])
    def test_existing_output_detection_from_original_source(self):
        self.loader=Source('R291_REFUSE_EXISTING_OR_UNSAFE_OUTPUT')
        self.assertFalse(self.inspect()['ready'])
    def test_output_ancestor_symlink_refusal(self):
        real=self.root/'real';real.mkdir()
        redirected=real/'future'
        prior=Path.is_symlink
        with mock.patch.object(Path,'is_symlink',autospec=True,
                side_effect=lambda value: value==real or prior(value)):
            r=a.admission(self.inputs,self.release,redirected,loader=lambda p:self.loader,
                        runtime=self.gooddeps,display=self.gooddisplay,port=lambda:True,platform='win32')[0]
        self.assertFalse(self.check(r,'no_output_ancestor_reparse')['pass'])
    def test_safe_output_regular_parents(self):
        self.assertEqual(a.safe_output_ancestors(self.output)[0],True)
    def test_java_major_parsing(self):
        self.assertEqual(a.java_version('javac 21.0.4'),21)
        self.assertEqual(a.java_version('openjdk version "11.0.18" 2023'),11)
        self.assertEqual(a.java_version('java version "1.8.0_291"'),8)
        self.assertIsNone(a.java_version('garbage'))
    def test_actual_linux_display_denial(self):
        if sys.platform!='win32':
            self.assertFalse(a.windows_display()['ok'])
    def test_never_claims_gui_completion(self):
        r=self.inspect()
        self.assertEqual(r['native_windows_gui'],'NOT_TESTED')
        self.assertFalse(r['client_modified']);self.assertFalse(r['created_output'])
    def test_main_no_game_on_off_windows(self):
        if sys.platform=='win32':return
        with mock.patch.object(a,'admission',return_value=(dict(ready=True),self.loader)):
            with self.assertRaisesRegex(RuntimeError,'REAL_NATIVE_WINDOWS'):
                a.main(['--input-dir',str(self.inputs),'--output',str(self.output),'--run-native-gui'])
        self.assertFalse(self.output.exists())
    def test_wrong_public_release_cannot_load(self):
        self.release.write_bytes(b'wrong-original-source')
        with self.assertRaisesRegex(ValueError,'R291_RELEASE_SHA256_MISMATCH'):
            a.load_pinned_r291(self.release)
    def test_trusted_original_public_release_when_available(self):
        bundled=ROOT/'vendor/r291'/a.R291_RELEASE[0]
        if bundled.is_file():
            original=a.load_pinned_r291(bundled)
            self.assertEqual(original.R290_JAR,'f2f914f12196705fd7233ea022742157d13deb50be85289465ce26b0dde3cd4a')
    def test_python_code_absent_binary_payload(self):
        text=FILE.read_text()
        self.assertNotIn('requests.get(',text)
        self.assertNotIn('rs.gui.Launcher',text)
        self.assertNotIn('taskkill /IM',text)
    def test_source_has_real_window_and_port_calls(self):
        text=FILE.read_text()
        self.assertIn('SetProcessDpiAwarenessContext',text)
        self.assertIn("sock.bind(('127.0.0.1', 43594))",text)
    def test_manifest_like_report_is_json_safe(self):
        obj=self.inspect()
        self.assertEqual(json.loads(json.dumps(obj))['checks_count'],10)

if __name__=='__main__':
    unittest.main(verbosity=2)

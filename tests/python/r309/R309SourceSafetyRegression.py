#!/usr/bin/env python3
"""R309 source-only Windows acceptance safety tests (no owner game binaries)."""
import importlib.util
import io
from pathlib import Path
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT=Path(__file__).resolve().parents[3]
ENTRY=ROOT/'tools/windows/r309/R309-Windows-R308-Acceptance.py'
spec=importlib.util.spec_from_file_location('r309_adapter',ENTRY)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class Safety(unittest.TestCase):
    def test_01_exact_r308_pins(self):
        self.assertEqual(r.R308_ARCHIVE_SHA256,'977645c2ed90c0936815e9da5ca609ee23480176088137f8d3e7ee3b88654d6c')
        self.assertEqual(r.R308_JAR_SHA256,'501072d504a4e03a758f44aaa32f0990d3f1599662f6f6d2fa0d83a14e6fc314')
        self.assertEqual(r.R308_JAR_MEMBER,'R308_SOURCE_BUILT_CLASS_ONLY.jar')
    def test_02_pinned_public_sources(self):
        self.assertEqual(r.ORIGINAL_GIT_BLOB,'9ce5cb9e567abe582d76996dbf3a32e64baf6cb6')
        self.assertEqual(r.READINESS_GIT_BLOB,'d75c4937349503093f669947e21de3acbce0e9b0')
        self.assertEqual(r.ORIGINAL_SHA256,'403f0c6db7ba23e5bb59a57fa029d85c541a25838fd6a213eb67ad0ccea06c72')
        self.assertEqual(len(r.PATCHES),4)
    def test_03_original_real_adapter(self):
        ready, owner=r.load_adapters()
        self.assertEqual(owner.R295,(r.R308_ARCHIVE,r.R308_ARCHIVE_SHA256))
        self.assertEqual(owner.R295_JAR,r.R308_JAR_SHA256)
        self.assertEqual(owner.R286[1],'2cacd2c551d6169be45e695f324d6c70a6d2a0b73a59b15fc5bce444f88a9877')
        self.assertTrue(callable(ready.admission))
    def test_04_four_jar_member_replacements(self):
        source=r.read_pinned(r.ORIGINAL,r.ORIGINAL_GIT_BLOB,r.ORIGINAL_SHA256)
        patched=r.rewrite_pinned_harness(source).decode()
        self.assertEqual(patched.count(r.R308_JAR_MEMBER),4)
        self.assertNotIn('R295_SOURCE_BUILT_CLASS_ONLY.jar',patched)
        self.assertNotIn('277fb5016d60e5b36bb22cede2b3b2500b9773636f433c65774db18a34e401f6',patched)
    def test_05_tampered_original_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'old.py';f.write_text('print("tampered")')
            with self.assertRaisesRegex(r.R309Refusal,'HASH_MISMATCH'):
                r.read_pinned(f,r.ORIGINAL_GIT_BLOB,r.ORIGINAL_SHA256)
    def test_06_anchor_drift_is_refused(self):
        with self.assertRaisesRegex(r.R309Refusal,'ANCHOR_DRIFT'):
            r.rewrite_pinned_harness(b'not the original harness')
    def test_07_absent_owner_archives_do_not_stage(self):
        _,owner=r.load_adapters()
        with tempfile.TemporaryDirectory() as d:
            inputs=Path(d)/'inputs';inputs.mkdir()
            output=Path(d)/'receipt'
            with self.assertRaises((owner.GuardError,OSError)):
                owner.preflight(inputs,output)
            self.assertFalse(output.exists())
    def test_08_linux_native_is_refused_before_loading(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(r.sys,'platform','linux'):
            with mock.patch.object(r,'load_adapters',side_effect=AssertionError('load forbidden')):
                with self.assertRaisesRegex(r.R309Refusal,'NON_WINDOWS'):
                    r.run(['--input-dir',d,'--output',str(Path(d)/'receipt'),'--run-native-gui'])
    def test_09_not_ready_never_launches(self):
        report={'ready':False,'native_windows_gui':'NOT_TESTED','client_modified':False}
        ready=types.SimpleNamespace(admission=lambda *_a,**_kw:(report.copy(),None))
        owner=types.SimpleNamespace(main=mock.Mock(side_effect=AssertionError('unexpected GUI')))
        with tempfile.TemporaryDirectory() as d,mock.patch.object(r,'load_adapters',return_value=(ready,owner)):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(r.run(['--input-dir',d,'--output',str(Path(d)/'receipt')]),2)
            self.assertIn('NOT_TESTED',out.getvalue())
            owner.main.assert_not_called()
    def test_10_preflight_never_launches(self):
        report={'ready':True,'native_windows_gui':'NOT_TESTED'}
        owner=types.SimpleNamespace(main=mock.Mock(side_effect=AssertionError('unexpected GUI')))
        ready=types.SimpleNamespace(admission=lambda *_a,**_kw:(report.copy(),owner))
        with tempfile.TemporaryDirectory() as d,mock.patch.object(r,'load_adapters',return_value=(ready,owner)):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r.run(['--input-dir',d,'--output',str(Path(d)/'receipt')]),0)
            owner.main.assert_not_called()
    def test_11_only_explicit_windows_optin_can_call_gui(self):
        report={'ready':True,'native_windows_gui':'NOT_TESTED'}
        owner=types.SimpleNamespace(main=mock.Mock(return_value=0))
        ready=types.SimpleNamespace(admission=lambda *_a,**_kw:(report.copy(),owner))
        with tempfile.TemporaryDirectory() as d,mock.patch.object(r,'load_adapters',return_value=(ready,owner)),mock.patch.object(r.sys,'platform','win32'):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r.run(['--input-dir',d,'--output',str(Path(d)/'receipt'),'--run-native-gui']),0)
            self.assertEqual(owner.main.call_args.args[0][-1],'--run-native-gui')
    def test_12_no_private_assets_or_downloads(self):
        s=ENTRY.read_text()
        for forbidden in ('requests.get(', 'urllib.request', 'spawnpk.net','taskkill /IM','rs.gui.Launcher'):
            self.assertNotIn(forbidden,s)
        self.assertFalse([f for f in ENTRY.parent.iterdir() if f.suffix in ('.jar','.class','.zip')])

if __name__=='__main__':
    unittest.main(verbosity=2)

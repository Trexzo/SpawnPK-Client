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
    def test_12_crlf_checkout_rehashed_to_exact_public_bytes(self):
        original=r.read_pinned(r.ORIGINAL,r.ORIGINAL_GIT_BLOB,r.ORIGINAL_SHA256)
        with tempfile.TemporaryDirectory() as d:
            changed=Path(d)/'windows-checkout.py'
            changed.write_bytes(original.replace(b'\n',b'\r\n'))
            canonical=r.read_pinned(changed,r.ORIGINAL_GIT_BLOB,r.ORIGINAL_SHA256)
            self.assertEqual(canonical,original)
    def test_13_lone_carriage_return_is_refused(self):
        original=r.read_pinned(r.ORIGINAL,r.ORIGINAL_GIT_BLOB,r.ORIGINAL_SHA256)
        with tempfile.TemporaryDirectory() as d:
            damaged=Path(d)/'damaged.py'
            damaged.write_bytes(original.replace(b'\n',b'\r\n')+b'\r')
            with self.assertRaisesRegex(r.R309Refusal,'INVALID_PUBLIC_SOURCE_LINE_ENDINGS'):
                r.read_pinned(damaged,r.ORIGINAL_GIT_BLOB,r.ORIGINAL_SHA256)
    def test_14_inventory_reports_all_seven_missing_without_writing(self):
        _,owner=r.load_adapters()
        with tempfile.TemporaryDirectory() as d:
            inputs=Path(d)/'inputs';inputs.mkdir()
            result=r.audit_inputs(inputs,owner)
            self.assertEqual(result['total'],7)
            self.assertEqual(result['verified'],0)
            self.assertFalse(result['all_verified'])
            self.assertEqual(len(result['inputs']),7)
            self.assertTrue(all(x['status']=='MISSING' for x in result['inputs']))
            self.assertEqual([x['key'] for x in result['inputs']],
                             ['r286','r295','r278','r265','assets','original','r230'])
            self.assertEqual(list(inputs.iterdir()),[])
    def test_15_inventory_detects_every_wrong_sha_without_launch(self):
        _,owner=r.load_adapters()
        with tempfile.TemporaryDirectory() as d:
            inputs=Path(d)/'inputs';inputs.mkdir()
            expected={'r286':owner.R286,'r295':owner.R295,**owner.OWNER}
            for filename,_ in expected.values():
                (inputs/filename).write_bytes(b'fabricated private input - do not trust')
            result=r.audit_inputs(inputs,owner)
            self.assertEqual(result['verified'],0)
            self.assertTrue(all(x['status']=='SHA256_MISMATCH' for x in result['inputs']))
    def test_16_inventory_exact_sha_positive_with_synthetic_hasher(self):
        _,owner=r.load_adapters()
        with tempfile.TemporaryDirectory() as d:
            inputs=Path(d)/'inputs';inputs.mkdir()
            expected={'r286':owner.R286,'r295':owner.R295,**owner.OWNER}
            lookup={filename:digest for filename,digest in expected.values()}
            for filename,_ in expected.values():
                (inputs/filename).write_bytes(b'fake fixture, not a valid owner archive')
            with mock.patch.object(owner,'sha256_file',side_effect=lambda path: lookup[path.name]):
                result=r.audit_inputs(inputs,owner)
            self.assertEqual(result['verified'],7)
            self.assertTrue(result['all_verified'])
            self.assertEqual(result['native_windows_gui'],'NOT_TESTED')
            self.assertFalse(result['client_modified'])
    def test_17_inventory_refuses_symlinked_archive(self):
        _,owner=r.load_adapters()
        with tempfile.TemporaryDirectory() as d:
            inputs=Path(d)/'inputs';inputs.mkdir()
            target=owner.R286[0]
            original=Path.is_symlink
            with mock.patch.object(Path,'is_symlink',autospec=True,
                  side_effect=lambda path: path.name==target or original(path)):
                result=r.audit_inputs(inputs,owner)
            self.assertEqual(result['inputs'][0]['status'],'SYMLINK_REFUSED')
    def test_18_inventory_cli_does_not_require_output_or_start_gui(self):
        _,owner=r.load_adapters()
        with tempfile.TemporaryDirectory() as d:
            game=mock.Mock(side_effect=AssertionError('GUI must not start'))
            with mock.patch.object(r,'load_adapters',return_value=(None,owner)),mock.patch.object(owner,'main',game,create=True):
                with redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(r.run(['--input-dir',d,'--inventory']),2)
                self.assertIn('R309_R308_INPUT_INVENTORY',out.getvalue())
                self.assertNotIn(str(d),out.getvalue())
            game.assert_not_called()
    def test_19_inventory_and_gui_optin_combination_denied(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(r,'load_adapters',side_effect=AssertionError('load forbidden')):
                with self.assertRaisesRegex(r.R309Refusal,'MUTUALLY_EXCLUSIVE'):
                    r.run(['--input-dir',d,'--inventory','--run-native-gui'])
    def test_20_r286_synthetic_entrypoint_overlay_targets_exact_r308(self):
        _,owner=r.load_adapters()
        original=(
            "    'r230': '5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125',\n"
            "R278_JAR = 'dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'\n"
            "with zipfile.ZipFile(inputs['r278']) as z:\n"
            "jar = testhome/'R278_SOURCE_BUILT_CLASS_ONLY.jar'\n"
            "z.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar')\n"
            "if digest(jar) != R278_JAR:\n"
            "    except (AttributeError, OSError):\n        dpi = 96\n"
            "    return {'pid': pid.value, 'window_rect': [rect.left, rect.top, rect.right, rect.bottom]}\n"
        )
        patched=owner.overlay('scripts/R286-Windows-Acceptance.py',original.encode()).decode()
        for token in (owner.R295_JAR, owner.R295[1], r.R308_JAR_MEMBER,
                      "with zipfile.ZipFile(inputs['r295']) as z:",
                      'R291_CLIENT_WINDOW_NOT_AT_VERIFIED_ROBOT_ANCHORS',
                      'R291_CANNOT_VERIFY_WINDOWS_DPI'):
            self.assertIn(token,patched)
        self.assertNotIn('R278_SOURCE_BUILT_CLASS_ONLY.jar',patched)
    def test_21_r286_synthetic_robot_overlay_targets_exact_r308(self):
        _,owner=r.load_adapters()
        original=("jar = base/'R278_SOURCE_BUILT_CLASS_ONLY.jar'\n"
                  "if API.digest(jar)!=API.R278_JAR:\n")
        patched=owner.overlay('scripts/probe/run_r286_windows_gui.py',original.encode()).decode()
        self.assertIn("base/'R308_SOURCE_BUILT_CLASS_ONLY.jar'",patched)
        self.assertIn('API.R295_JAR',patched)
        self.assertNotIn('R278_SOURCE_BUILT_CLASS_ONLY.jar',patched)
    def test_22_r286_synthetic_overlay_rejects_drift(self):
        _,owner=r.load_adapters()
        with self.assertRaisesRegex(owner.GuardError,'ANCHOR_NOT_UNIQUE'):
            owner.overlay('scripts/R286-Windows-Acceptance.py',b'unexpected owner source')
        with self.assertRaisesRegex(owner.GuardError,'UNLISTED_OVERLAY'):
            owner.overlay('scripts/untrusted.py',b'print("no")')
    def test_23_missing_required_directory_fail_closed(self):
        _,owner=r.load_adapters()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(r.R309Refusal,'DIRECTORY_MISSING_OR_SYMLINK'):
                r.audit_inputs(Path(d)/'absent',owner)
    def test_24_no_private_assets_or_downloads(self):
        s=ENTRY.read_text()
        for forbidden in ('requests.get(', 'urllib.request', 'spawnpk.net','taskkill /IM','rs.gui.Launcher'):
            self.assertNotIn(forbidden,s)
        self.assertFalse([f for f in ENTRY.parent.iterdir() if f.suffix in ('.jar','.class','.zip')])

if __name__=='__main__':
    unittest.main(verbosity=2)

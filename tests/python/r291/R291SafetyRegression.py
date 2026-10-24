#!/usr/bin/env python3
"""R291 source-only 23-case suite; deterministic fixtures, no game assets needed."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

R=Path(__file__).with_name('R291-Windows-R290-Acceptance.py')
if not R.exists():
 R=Path(__file__).resolve().parents[3]/'tools/windows/r291/R291-Windows-R290-Acceptance.py'
spec=importlib.util.spec_from_file_location('r291',R)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

R286_MINI='''EXPECTED = {
    'r230': '5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125',
}
R278_JAR = 'dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'
with zipfile.ZipFile(inputs['r278']) as z:
    jar = testhome/'R278_SOURCE_BUILT_CLASS_ONLY.jar'
    jar.write_bytes(z.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar'))
if digest(jar) != R278_JAR:
    pass
    except (AttributeError, OSError):
        dpi = 96
    return {'pid': pid.value, 'window_rect': [rect.left, rect.top, rect.right, rect.bottom]}
'''
GUI_MINI="jar = base/'R278_SOURCE_BUILT_CLASS_ONLY.jar'\nif API.digest(jar)!=API.R278_JAR:\n    pass\n"

class AcceptanceSafety(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='r291-test-');self.addCleanup(self.temp.cleanup)
  self.home=Path(self.temp.name);self.inputs=self.home/'inputs';self.inputs.mkdir();self.output=self.home/'output'
  self.mock_patches=[]
  self.r286_mini=R286_MINI.encode();self.gui_mini=GUI_MINI.encode()

 def patch(self,name,value):
  p=mock.patch.object(r,name,value);p.start();self.addCleanup(p.stop)

 def fixture(self):
  game=b'fake-R290-JAR-data-only'
  z286=self.inputs/'r286.zip';z290=self.inputs/'r290.zip'
  with zipfile.ZipFile(z286,'w') as z:
   z.writestr('scripts/R286-Windows-Acceptance.py',self.r286_mini)
   z.writestr('scripts/probe/run_r286_windows_gui.py',self.gui_mini)
  with zipfile.ZipFile(z290,'w') as z:z.writestr('bin/R290_SOURCE_BUILT_CLASS_ONLY.jar',game)
  self.patch('R286',('r286.zip',r.sha256_file(z286)))
  self.patch('R290',('r290.zip',r.sha256_file(z290)))
  self.patch('R290_JAR',r.sha256_bytes(game))
  self.patch('R286_FILES',{'scripts/R286-Windows-Acceptance.py':r.sha256_bytes(self.r286_mini),
                            'scripts/probe/run_r286_windows_gui.py':r.sha256_bytes(self.gui_mini)})
  owns={}
  for key in ['r278','r265','assets','original','r230']:
   path=self.inputs/(key+'.zip');path.write_bytes(('mock-'+key).encode());owns[key]=(path.name,r.sha256_file(path))
  self.patch('OWNER',owns)

 def test_01_expected_exact_r290_jar_pin(self):
  self.assertEqual(r.R290_JAR,'f2f914f12196705fd7233ea022742157d13deb50be85289465ce26b0dde3cd4a')
 def test_02_expected_exact_r290_release_pin(self):
  self.assertEqual(r.R290[1],'3bb467029ec552f7345a054dbed7ee8da2ef646bdfa2ce72707ce384b646f41c')
 def test_03_expected_exact_r286_release_pin(self):
  self.assertEqual(r.R286[1],'2cacd2c551d6169be45e695f324d6c70a6d2a0b73a59b15fc5bce444f88a9877')
 def test_04_all_five_original_owner_pins_retained(self):
  self.assertEqual(set(r.OWNER),{'r278','r265','assets','original','r230'})
 def test_05_replace_once_rejects_missing_anchor(self):
  with self.assertRaisesRegex(r.GuardError,'ANCHOR_NOT_UNIQUE'):r.replace_once('abc','x','y')
 def test_06_replace_once_rejects_duplicate_anchor(self):
  with self.assertRaisesRegex(r.GuardError,'ANCHOR_NOT_UNIQUE'):r.replace_once('xx','x','y')
 def test_07_gui_retargets_r290(self):
  result=r.overlay('scripts/probe/run_r286_windows_gui.py',self.gui_mini).decode()
  self.assertIn('API.R290_JAR',result)
  self.assertIn("base/'R290_SOURCE_BUILT_CLASS_ONLY.jar'",result)
  self.assertNotIn('API.R278_JAR',result)
 def test_08_main_retargets_private_r290(self):
  result=r.overlay('scripts/R286-Windows-Acceptance.py',self.r286_mini).decode()
  self.assertIn("with zipfile.ZipFile(inputs['r290'])",result)
  self.assertIn("testhome/'R290_SOURCE_BUILT_CLASS_ONLY.jar'",result)
  self.assertIn('R291_CLIENT_WINDOW_NOT_AT_VERIFIED_ROBOT_ANCHORS',result)
  self.assertIn("'r290': '"+r.R290[1],result)
 def test_09_reject_unknown_overlay_target(self):
  with self.assertRaisesRegex(r.GuardError,'UNLISTED_OVERLAY'):r.overlay('another.py',b'abc')
 def test_10_reject_altered_anchor(self):
  with self.assertRaisesRegex(r.GuardError,'ANCHOR_NOT_UNIQUE'):r.overlay('scripts/R286-Windows-Acceptance.py',self.r286_mini.replace(b'R278_JAR',b'OTHER_JAR'))
 def test_11_safe_output_rejects_existing(self):
  self.output.mkdir()
  with self.assertRaisesRegex(r.GuardError,'EXISTING_OR_UNSAFE'):r.safe_output(self.output,self.inputs)
 def test_12_safe_output_rejects_missing_parent(self):
  with self.assertRaisesRegex(r.GuardError,'EXISTING_OR_UNSAFE'):r.safe_output(self.home/'absent'/'out',self.inputs)
 def test_13_safe_output_rejects_nested_input(self):
  with self.assertRaisesRegex(r.GuardError,'UNSAFE_OUTPUT_LOCATION'):r.safe_output(self.inputs/'inside',self.inputs)
 def test_14_safe_output_rejects_symlink(self):
  self.output.symlink_to(self.home/'absent')
  with self.assertRaisesRegex(r.GuardError,'EXISTING_OR_UNSAFE'):r.safe_output(self.output,self.inputs)
 def test_15_missing_archives_refuse_before_writes(self):
  with self.assertRaisesRegex(r.GuardError,'MISSING_OR_SYMLINK_INPUT'):r.preflight(self.inputs,self.output)
  self.assertFalse(self.output.exists())
 def test_16_bad_owner_sha_refuses_before_writes(self):
  self.fixture();(self.inputs/'r265.zip').write_bytes(b'changed')
  with self.assertRaisesRegex(r.GuardError,'INPUT_SHA256_MISMATCH r265'):r.preflight(self.inputs,self.output)
  self.assertFalse(self.output.exists())
 def test_17_wrong_r290_embedded_jar_refused(self):
  self.fixture();self.patch('R290_JAR','f'*64)
  with self.assertRaisesRegex(r.GuardError,'R290_JAR_SHA256_MISMATCH'):r.preflight(self.inputs,self.output)
 def test_18_wrong_r286_script_sha_refused(self):
  self.fixture();self.patch('R286_FILES',{'scripts/R286-Windows-Acceptance.py':'f'*64})
  with self.assertRaisesRegex(r.GuardError,'R286_SOURCE_SHA256_MISMATCH'):r.preflight(self.inputs,self.output)
 def test_19_complete_offline_fake_fixture_pass(self):
  self.fixture();inputs=r.preflight(self.inputs,self.output)
  self.assertEqual(len(inputs),7);self.assertFalse(self.output.exists())
 def test_20_actual_read_only_cli_no_output(self):
  self.fixture()
  with contextlib.redirect_stdout(io.StringIO()) as buf:
   self.assertEqual(r.main(['--input-dir',str(self.inputs),'--output',str(self.output)]),0)
  self.assertIn('R291_PINNED_READ_ONLY_PREFLIGHT_PASS',buf.getvalue())
  self.assertFalse(self.output.exists())
 def test_21_native_gui_refused_off_windows(self):
  self.fixture()
  with mock.patch.object(r.sys,'platform','linux'):
   with self.assertRaisesRegex(r.GuardError,'NOT_NATIVE_WINDOWS'):
    r.main(['--input-dir',str(self.inputs),'--output',str(self.output),'--run-native-gui'])
  self.assertFalse(self.output.exists())
 def test_22_overlay_stage_only_whitelisted_original_zip(self):
  self.fixture();scratch=self.home/'scratch';scratch.mkdir()
  entry=r.stage_overlay(self.inputs/'r286.zip',scratch)
  self.assertTrue(entry.is_file())
  self.assertIn('R290_JAR',entry.read_text())
  self.assertFalse(self.output.exists())
 def test_23_traversal_rejected(self):
  bad=self.home/'bad.zip'
  with zipfile.ZipFile(bad,'w') as z:z.writestr('../outside.txt','test')
  scratch=self.home/'scratch';scratch.mkdir()
  with self.assertRaisesRegex(r.GuardError,'UNSAFE_R286_ZIP_MEMBER'):r.stage_overlay(bad,scratch)
  self.assertFalse((self.home/'outside.txt').exists())

if __name__=='__main__':unittest.main(verbosity=2)

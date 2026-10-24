#!/usr/bin/env python3
"""No-private-assets checks for the pinned R293 real GUI replay source."""
import hashlib,importlib.util,pathlib,tempfile,unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[3]
SCRIPT=ROOT/'tools/gui/r294/R294ReplayFromPinned.py'
spec=importlib.util.spec_from_file_location('r294_replay',SCRIPT)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class R294Safety(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='r294-fixture-');self.addCleanup(self.temp.cleanup)
  self.base=pathlib.Path(self.temp.name);self.inputs=self.base/'inputs';self.inputs.mkdir();self.output=self.base/'no-output'
 def test_pinned_private_r293_sha(self):self.assertEqual(r.PINS['r293'][1],'c6ecd187ced1f6bae2858b846b5940a58d71a08f7031e938f4a2a15bb214f2cf')
 def test_pinned_r293_jar_sha(self):self.assertEqual(r.R293_JAR,'0d0eedae92efe709b2d6eb49b1fc4432db174a6e68a7f06fd4fc2736d0f6cee9')
 def test_pinned_original_r285_source_evidence_sha(self):self.assertEqual(r.PINS['r285'][1],'99665e0404c2273b24b47935a8db6b5f169a2a1d17fff7d09fda928aaf021d33')
 def test_owner_archive_count_and_shas(self):
  self.assertEqual(set(r.PINS),{'r278','r265','assets','original','r230','r293','r285'})
  self.assertTrue(all(len(x[1])==64 for x in r.PINS.values()))
 def test_unchanged_original_harness_script_pins(self):self.assertEqual(len(r.SCRIPTS),3)
 def test_reject_missing_source_anchor(self):
  with self.assertRaisesRegex(ValueError,'SOURCE_ANCHOR_DRIFT'):r.replace_one('xyz','absent','new')
 def test_reject_double_source_anchor(self):
  with self.assertRaisesRegex(ValueError,'SOURCE_ANCHOR_DRIFT'):r.replace_one('xx','x','z')
 def test_original_probe_stays_bound_to_private_r293(self):
  s="expected='"+r.R278_JAR+"'\n"+"B/'R278_SOURCE_BUILT_CLASS_ONLY.jar'\n"*2+"'R285 private R278 JAR hash mismatch'"
  result=r.patch_probe(s)
  self.assertIn(r.R293_JAR,result)
  self.assertNotIn(r.R278_JAR,result)
  self.assertEqual(result.count("R293_SOURCE_BUILT_CLASS_ONLY.jar"),2)
 def test_probe_refuses_unexpected_old_jar_references(self):
  with self.assertRaisesRegex(ValueError,'TWO_JAR_REFERENCES_REQUIRED'):r.patch_probe('wrong')
 def test_wrapper_rejects_missing_required_anchor(self):
  with self.assertRaisesRegex(ValueError,'SOURCE_ANCHOR_DRIFT'):r.patch_wrapper('wrong')
 def test_new_output_refuses_existing(self):
  self.output.mkdir()
  with self.assertRaisesRegex(ValueError,'R294_UNSAFE_EXISTING_OR_MISSING_OUTPUT'):
   r.main(['--input-dir',str(self.inputs),'--output',str(self.output),'--preflight-only'])
 def test_missing_original_inputs_refused_before_output(self):
  with self.assertRaisesRegex(ValueError,'R294_PINNED_PRIVATE_INPUT_REFUSED'):
   r.main(['--input-dir',str(self.inputs),'--output',str(self.output),'--preflight-only'])
  self.assertFalse(self.output.exists())
 def test_output_under_owner_input_refused(self):
  with self.assertRaisesRegex(ValueError,'R294_OUTPUT_WITHIN_INPUTS'):
   r.main(['--input-dir',str(self.inputs),'--output',str(self.inputs/'nested'),'--preflight-only'])
 def test_hash_streaming(self):
  p=self.base/'fixture';p.write_bytes(b'public only')
  self.assertEqual(r.hash_file(p),hashlib.sha256(p.read_bytes()).hexdigest())
 def test_no_live_server_endpoint(self):
  s=SCRIPT.read_text();self.assertNotIn('spawnpk.net',s);self.assertNotIn('192.168.',s);self.assertIn('only',s)
 def test_no_private_classes_embedded(self):
  for root in (SCRIPT.parent, pathlib.Path(__file__).parent):
   for p in root.rglob('*'):
    if p.is_file():self.assertFalse(p.name.endswith(('.jar','.class','.dat','.idx')))
 def test_no_network_download_code(self):
  s=SCRIPT.read_text();self.assertNotIn('urllib.request',s);self.assertNotIn('requests.get(',s)
 def test_no_automatic_game_launch_on_preflight(self):
  s=SCRIPT.read_text();self.assertLess(s.index('if a.preflight_only:return 0'),s.index('subprocess.run(cmd,check=True,timeout=120)'))
if __name__=='__main__':unittest.main(verbosity=2)

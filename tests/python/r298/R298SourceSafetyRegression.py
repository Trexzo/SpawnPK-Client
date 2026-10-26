#!/usr/bin/env python3
"""R298 public source-only validation; no private game assets."""
from pathlib import Path
import hashlib,importlib.util,tempfile,unittest
from unittest import mock
SCRIPT=Path(__file__).resolve().parents[3]/'tools/recovery/r298/rebuild_r298_from_pinned.py'
spec=importlib.util.spec_from_file_location('r298_public',SCRIPT)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class SourceSafety(unittest.TestCase):
 def test_exact_pins(self):
  self.assertEqual(r.R295_SCENE_POSTIMAGE_SHA,'24790fc3aac8676df95c1cd0f830f26bc6ad749cc87435f47b9eb69c9c8ef813')
  self.assertEqual(r.R298_SCENE_POSTIMAGE_SHA,'1999066509802862ba8c7ba0e4d54cabdf0cf8da64aabbc370439eda287ceada')
  self.assertEqual(r.R298_JAR_SHA,'be86b334f9ddc471cc7353f4a9493587c8a8317ded4a3a6e538f0ba96c08fbc9')
 def test_12_independent_readers(self):
  self.assertEqual(len(r.READ_ONLY_SCENE_QUERIES),12)
  self.assertEqual(len(set(r.READ_ONLY_SCENE_QUERIES)),12)
 def test_orientation(self):
  self.assertEqual(r.READ_ONLY_SCENE_QUERIES['method2717'],('var3','var1','var2'))
  self.assertEqual(r.READ_ONLY_SCENE_QUERIES['method2918'],('var3','var2','var1'))
 def test_helper_rejects_negative_and_upper_bounds(self):
  for x in ('plane < 0','x < 0','y < 0','plane >= this.tiles.length','x >= this.tiles[plane].length','y >= this.tiles[plane][x].length'):
   self.assertIn(x,r.R298_SAFE_HELPER)
 def test_retains_empty_value_semantics(self):
  self.assertIn('return null;',r.R298_SAFE_HELPER)
 def test_original_bad_source_refused(self):
  with self.assertRaisesRegex(ValueError,'R298_R295_SCENE_SOURCE_PREIMAGE_MISMATCH'):
   r.patch_read_only_scene_queries(b'not-owner-source')
 def test_duplicate_anchor_refused(self):
  anchor='   public int method1154(int var1, int var2, int var3) {'
  src=(anchor+'\n'+anchor).encode()
  with mock.patch.object(r,'R295_SCENE_POSTIMAGE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R298_SCENE_HELPER_ANCHOR_DRIFT'):r.patch_read_only_scene_queries(src)
 def test_preimage_postimage_hash_guard_present(self):
  s=SCRIPT.read_text()
  self.assertIn('R298_SCENE_SOURCE_POSTIMAGE_MISMATCH',s)
  self.assertIn('R298_REBUILT_JAR_SHA_MISMATCH',s)
  self.assertIn('observed!=R298_JAR_SHA',s)
 def test_no_original_game_binary_in_public_tree(self):
  for p in (SCRIPT,Path(__file__)):
   self.assertNotIn(p.suffix.lower(),('.class','.jar','.dat','.idx'))
 def test_no_online_endpoint(self):
  s=SCRIPT.read_text()
  self.assertNotIn('spawnpk.net',s)
  self.assertNotIn('urllib.request',s)
 def test_exact_source_counts_preserved(self):
  s=SCRIPT.read_text()
  self.assertIn('len(sources)!=1277',s)
  self.assertIn('!=1386',s)
 def test_missing_original_inputs_fail_closed(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);output=base/'future'
   with self.assertRaisesRegex(ValueError,'R298_PRIVATE_PINNED_INPUT_REFUSED'):
    r.main(['--r278',str(base/'r278.zip'),'--r265',str(base/'r265.zip'),'--output',str(output)])
   self.assertFalse(output.exists())
 def test_existing_output_fail_closed(self):
  with tempfile.TemporaryDirectory() as t:
   base=Path(t);output=base/'existing';output.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R298_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278',str(base/'r278.zip'),'--r265',str(base/'r265.zip'),'--output',str(output)])
 def test_mutators_not_in_reader_allowlist(self):
  for name in ('clearScene','method93','method1252','method1390','method1152','method1627','addGroundDecoration'):
   self.assertNotIn(name,r.READ_ONLY_SCENE_QUERIES)
if __name__=='__main__':unittest.main(verbosity=2)

#!/usr/bin/env python3
"""R299 public-source checks; all fixtures synthetic and no owner archives."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'tools/recovery/r299/rebuild_r299_from_pinned.py'
JAVA=ROOT/'tests/java/r299/R299SceneMutationBoundsRegression.java'
spec=importlib.util.spec_from_file_location('r299_rebuilder',SOURCE)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class R299Safety(unittest.TestCase):
 def test_scene_preimage_sha(self):
  self.assertEqual(r.R299_SCENE_PREIMAGE_SHA,'1999066509802862ba8c7ba0e4d54cabdf0cf8da64aabbc370439eda287ceada')
 def test_scene_postimage_sha(self):
  self.assertEqual(r.R299_SCENE_POSTIMAGE_SHA,'007159b0b47058552150985c45f5b441df1a4bbd5a794bc41b6ad172bee8832e')
 def test_jar_sha(self):
  self.assertEqual(r.R299_JAR_SHA,'9c4d4350918c05c4a9f40d9372cab8c77088c76a43a32eb7f46b6974d57738cc')
 def test_exact_seven_scoped_methods(self):
  self.assertEqual(set(r.R299_MUTATION_GUARDS),{'method251','method3478','method93','method1252','method1390','method1152','method1627'})
 def test_no_original_mutators_changed_elsewhere(self):
  self.assertNotIn('method3235',r.R299_MUTATION_GUARDS)
  self.assertNotIn('method637',r.R299_MUTATION_GUARDS)
 def test_coordinate_order_per_method(self):
  self.assertEqual(r.R299_MUTATION_GUARDS['method3478'][1],('var4','var3','var1'))
  self.assertEqual(r.R299_MUTATION_GUARDS['method1252'][1],('var2','var3','var1'))
  self.assertEqual(r.R299_MUTATION_GUARDS['method93'][1],('var2','var1','var3'))
  self.assertEqual(r.R299_MUTATION_GUARDS['method1152'][1],('var1','var3','var2'))
 def test_helper_validates_all_borders(self):
  for expression in ('plane >= 0','plane < this.tiles.length','x >= 0','x < this.tiles[plane].length','y >= 0','y < this.tiles[plane][x].length'):
   self.assertIn(expression,r.R299_MUTATION_HELPER)
 def test_reject_unknown_source(self):
  with self.assertRaisesRegex(ValueError,'R299_SCENE_PREIMAGE_MISMATCH'):r.patch_scene_mutations(b'wrong owner source')
 def test_reject_duplicate_helper_anchor(self):
  marker='   private Tile safeQueryTile(int plane, int x, int y) {'
  stub=(marker+'\n'+marker).encode()
  with mock.patch.object(r,'R299_SCENE_PREIMAGE_SHA',hashlib.sha256(stub).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R299_HELPER_ANCHOR_DRIFT'):r.patch_scene_mutations(stub)
 def test_reject_unexpected_missing_mutator(self):
  marker='   private Tile safeQueryTile(int plane, int x, int y) {'
  stub=marker.encode()
  with mock.patch.object(r,'R299_SCENE_PREIMAGE_SHA',hashlib.sha256(stub).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R299_METHOD_ANCHOR_DRIFT'):r.patch_scene_mutations(stub)
 def test_source_output_requires_expected_digest(self):
  original=SOURCE.read_text()
  self.assertIn('R299_SCENE_POSTIMAGE_MISMATCH',original)
  self.assertIn('observed!=R299_JAR_SHA',original)
 def test_original_authority_remains(self):
  self.assertIn('(n >>> 14 & 32767) != n4',r.NEW)
  self.assertIn('safeQueryTile',r.R298_SAFE_HELPER)
 def test_java_regression_coverage(self):
  code=JAVA.read_text()
  for marker in ('R299_SCENE_MUTATION_BOUNDARY_CRASH','R299_SCENE_MUTATION_BOUNDS_PASS','R299_VALID_SCENE_TILE_MUTATION_LOST','R299_INVALID_SCENE_MUTATION_SIDE_EFFECT','R299_VALID_SCENE_MUTATION_SIDE_EFFECT_LOST'):
   self.assertIn(marker,code)
 def test_missing_private_pins_fail_before_writes(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp);out=path/'future'
   with self.assertRaisesRegex(ValueError,'R299_PRIVATE_PINNED_INPUT_REFUSED'):
    r.main(['--r278',str(path/'missing-r278.zip'),'--r265',str(path/'missing-r265.zip'),'--output',str(out)])
   self.assertFalse(out.exists())
 def test_existing_output_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp);out=path/'occupied';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R299_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278',str(path/'r278.zip'),'--r265',str(path/'r265.zip'),'--output',str(out)])
 def test_binary_assets_not_committed(self):
  for folder in (SOURCE.parent,JAVA.parent,Path(__file__).parent):
   self.assertFalse([p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in {'.jar','.class','.dat','.idx'}])
 def test_no_network_or_runtime_launch_in_builder(self):
  src=SOURCE.read_text()
  self.assertNotIn('requests.get(',src)
  self.assertNotIn('urllib.request',src)
  self.assertNotIn('rs.gui.Launcher',src)
if __name__=='__main__':unittest.main(verbosity=2)

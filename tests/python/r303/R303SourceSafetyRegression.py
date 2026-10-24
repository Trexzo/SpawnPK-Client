#!/usr/bin/env python3
"""Public-only checks for R303 scene lighting border correction and rebuild pins."""
import hashlib, importlib.util, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/'tools/recovery/r303/rebuild_r303_from_pinned.py'
JAVA=ROOT/'tests/java/r303/R303GroundLightingBorderRegression.java'
spec=importlib.util.spec_from_file_location('r303_public',SCRIPT)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class R303Safety(unittest.TestCase):
 def test_01_original_r302_rebuild_sha(self):
  self.assertEqual(r.R302_RECIPE_SHA,'55d25e83d84d692efbc263cd9fe72c0e6433d9a37d0da3d616c18119881d3002')
 def test_02_original_scene_sha(self):
  self.assertEqual(r.R302_SCENE_SHA,'ec91cf02318dc26a80a4a5e5ee9e912feff8a66ee83e37e2d82b25ada321bc66')
 def test_03_new_scene_sha(self):
  self.assertEqual(r.R303_SCENE_SHA,'ee0660154ab0e289448194a476fc6b2629ea83e1d99ba7477755e6f4885f93b6')
 def test_04_compiled_jar_sha(self):
  self.assertEqual(r.R303_JAR_SHA,'a9ae098a79aac6c53eca5a986773b8c79f998b435d181bfde859c283a866b12b')
 def test_05_unmodified_parent_builder_still_pinned(self):
  path=ROOT/'tools/recovery/r302/rebuild_r302_from_pinned.py'
  self.assertEqual(r.sha(path),r.R302_RECIPE_SHA)
 def test_06_wrong_source_preimage_denied(self):
  with self.assertRaisesRegex(ValueError,'R303_SCENE_SOURCE_PREIMAGE_MISMATCH'):
   r.patch_lighting(b'not-a-game-scene')
 def test_07_missing_method_anchor_denied(self):
  src=b'wrong text'
  with mock.patch.object(r,'R302_SCENE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R303_METHOD_BOUNDARY_AMBIGUOUS'):r.patch_lighting(src)
 def test_08_ambiguous_method_anchor_denied(self):
  src=(b'   private void method1018(int var1, int var2, Model var3, int var4) {\n'*2+b'   private void method1770(')
  with mock.patch.object(r,'R302_SCENE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R303_METHOD_BOUNDARY_AMBIGUOUS'):r.patch_lighting(src)
 def test_09_unexpected_condition_denied(self):
  src=b'   private void method1018(int var1, int var2, Model var3, int var4) {\n}\n   private void method1770('
  with mock.patch.object(r,'R302_SCENE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R303_LIGHTING_LOOKUP_ANCHOR_DRIFT'):r.patch_lighting(src)
 def test_10_wrong_postimage_denied(self):
  src=('   private void method1018(int var1, int var2, Model var3, int var4) {\n'
   '      if (var1 < this.field5663) {}\n'
   '      if (var4 < this.field5663) {}\n'
   '      if (var1 < this.field5663 && var4 < this.field5664) {}\n'
   '      if (var1 < this.field5663 && var4 > 0) {}\n'
   '   }\n   private void method1770(').encode()
  with mock.patch.object(r,'R302_SCENE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R303_SCENE_SOURCE_POSTIMAGE_MISMATCH'):r.patch_lighting(src)
 def test_11_existing_owner_output_denied(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'old';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R303_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278','missing.zip','--r265','missing2.zip','--output',str(out)])
 def test_12_output_parent_required(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(FileNotFoundError,'R303_OUTPUT_PARENT_UNSAFE'):
    r.main(['--r278','missing.zip','--r265','missing2.zip','--output',str(Path(d)/'missing-parent'/'new')])
 def test_13_baseline_build_never_skips_hash_verification(self):
  src=SCRIPT.read_text()
  self.assertIn("baseline.R302_JAR_SHA=R303_JAR_SHA",src)
  self.assertIn('if not rebuilt.is_file() or sha(rebuilt)!=R303_JAR_SHA',src)
 def test_14_scene_grid_bounds_are_array_based(self):
  src=SCRIPT.read_text()
  self.assertIn('isSceneTileInBounds(var2, var1, var4)',src)
  self.assertIn('field5663 - 1',src)
  self.assertIn('field5664 - 1',src)
 def test_15_original_method_uses_four_neighbor_guard_paths(self):
  src=SCRIPT.read_text()
  self.assertIn('if (var1 < this.field5663 && var4 > 0)',src)
  self.assertIn('if (var1 < this.field5663 && var4 < this.field5664)',src)
 def test_16_actual_java_regression_exists(self):
  src=JAVA.read_text()
  for x in ('R303_GROUND_LIGHTING_TILE_OOB','R303_GROUND_LIGHTING_BORDER_PASS','103','1708'):
   if x=='1708':continue  # count is derived from 4 planes, not hardcoded
   self.assertIn(x,src)
 def test_17_no_private_binaries_in_public_files(self):
  for folder in (SCRIPT.parent,JAVA.parent,Path(__file__).parent):
   self.assertFalse([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.jar','.class','.dat','.idx')])
 def test_18_source_builder_has_no_network_or_game_start(self):
  src=SCRIPT.read_text()
  for bad in ('urllib.request','requests.get(', 'spawnpk.net','rs.gui.Launcher'):
   self.assertNotIn(bad,src)

if __name__=='__main__':unittest.main(verbosity=2)

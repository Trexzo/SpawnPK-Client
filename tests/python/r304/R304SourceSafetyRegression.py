#!/usr/bin/env python3
"""R304 public-only original-source, radius geometry and fail-closed regression."""
import hashlib,importlib.util,tempfile,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/'tools/recovery/r304/rebuild_r304_from_pinned.py'
JAVA=ROOT/'tests/java/r304/R304VisibilityDistanceRegression.java'
spec=importlib.util.spec_from_file_location('r304_pinned',SCRIPT)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class SourceSafety(unittest.TestCase):
 def test_01_parent_recipe_hash(self):
  self.assertEqual(r.PIN_R303_RECIPE,'c808781ffd77f80c9298092d41a2cc0d6df692143332589dea95a3b72b53e3a5')
  self.assertEqual(r.sha(ROOT/'tools/recovery/r303/rebuild_r303_from_pinned.py'),r.PIN_R303_RECIPE)
 def test_02_scene_preimage(self):self.assertEqual(r.PIN_R303_SOURCE,'ee0660154ab0e289448194a476fc6b2629ea83e1d99ba7477755e6f4885f93b6')
 def test_03_scene_postimage(self):self.assertEqual(r.PIN_R304_SOURCE,'839492e3d66ea546699f18338f09135e9787ff0c40ef193517cb18e68f8accd4')
 def test_04_compiled_jar_hash(self):self.assertEqual(r.PIN_R304_JAR,'1364d7be33147b5dbe9437f2222007402db449f9b1e4a244565680b608385f20')
 def test_05_wrong_source_refused(self):
  with self.assertRaisesRegex(ValueError,'R304_REAL_SCENE_PREIMAGE_MISMATCH'):r.patch_visibility(b'foreign')
 def test_06_missing_anchor_refused(self):
  inp=b'public fixture'
  with mock.patch.object(r,'PIN_R303_SOURCE',hashlib.sha256(inp).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R304_SCENE_METHOD_ANCHOR_AMBIGUOUS'):r.patch_visibility(inp)
 def test_07_missing_viewport_loop_refused(self):
  inp=b'   public static void setViewport(\n      int[] var4 = new int[9];\n   private static boolean method455('
  with mock.patch.object(r,'PIN_R303_SOURCE',hashlib.sha256(inp).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R304_SCENE_ANCHOR_DRIFT'):r.patch_visibility(inp)
 def test_08_radius_geometry(self):
  s=SCRIPT.read_text()
  for marker in ('activeDrawDistance < 1 || activeDrawDistance > 50','activeDrawDistance * 2 + 1','activeDrawDistance * 2 + 3','-activeDrawDistance - 1','activeDrawDistance + 1'):
   self.assertIn(marker,s)
 def test_09_occluder_radius(self):
  s=SCRIPT.read_text()
  self.assertIn("body=once(body,' + field5658',' + activeDrawDistance',6)",s)
  self.assertIn("body=once(body,'<= 50','< tileVisibilityBand.length',2)",s)
 def test_10_occluder_clamp(self):
  s=SCRIPT.read_text()
  for name in ('var18','var17','var7','var9'):
   self.assertIn("f'if ({idx} > 50)'",s)
   self.assertIn("f'{idx} = tileVisibilityBand.length - 1;'",s)
 def test_11_inherited_sha_and_java_classes(self):
  s=SCRIPT.read_text()
  self.assertIn('base.R303_JAR_SHA=PIN_R304_JAR',s)
  self.assertIn('if data.get(\'compiled_classes\')!=1386 or data.get(\'java_source_files\')!=1277:',s)
 def test_12_refuse_existing_target(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'old';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R304_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278','missing-r278','--r265','missing-r265','--output',str(out)])
 def test_13_no_write_with_bad_parent(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'missing'/'result'
   with self.assertRaisesRegex(FileNotFoundError,'R304_UNSAFE_OUTPUT_PARENT'):
    r.main(['--r278','missing','--r265','missing','--output',str(p)])
 def test_14_real_jvm_regression_present(self):
  s=JAVA.read_text()
  for marker in ('R304_VIEWPORT_RADIUS_CRASH','R304_OCCLUDER_RADIUS_CRASH','R304_DYNAMIC_SCENE_VISIBILITY_PASS','Scene.setViewport(500,500,800,600)'):
   self.assertIn(marker,s)
 def test_15_proprietary_files_not_in_public_tree(self):
  for d in (SCRIPT.parent,JAVA.parent,Path(__file__).parent):
   self.assertFalse([f for f in d.iterdir() if f.is_file() and f.suffix.lower() in ('.jar','.class','.dat','.idx')])
 def test_16_no_network_or_game_runner_in_source_build(self):
  for forbidden in ('urllib.request','requests.get(', 'spawnpk.net','rs.gui.Launcher'):
   self.assertNotIn(forbidden,SCRIPT.read_text())
if __name__=='__main__':unittest.main(verbosity=2)

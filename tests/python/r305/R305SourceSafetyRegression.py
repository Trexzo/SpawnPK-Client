#!/usr/bin/env python3
"""R305 SHA-gated viewport seam/edge correction source-only tests."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/'tools/recovery/r305/rebuild_r305_from_pinned.py'
JAVA=ROOT/'tests/java/r305/R305VisibilityGridOracle.java'
spec=importlib.util.spec_from_file_location('r305_source',SCRIPT)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class R305Safety(unittest.TestCase):
 def test_01_exact_original_builder(self):
  self.assertEqual(r.PIN_R304_BUILDER,'76b62cf4518b2afd3431fd5fcad9285809d6555df646348c9f0727608627fab7')
  self.assertEqual(r.digest(ROOT/'tools/recovery/r304/rebuild_r304_from_pinned.py'),r.PIN_R304_BUILDER)
 def test_02_original_scene_preimage(self):
  self.assertEqual(r.PIN_R304_SCENE,'839492e3d66ea546699f18338f09135e9787ff0c40ef193517cb18e68f8accd4')
 def test_03_new_scene_postimage(self):
  self.assertEqual(r.PIN_R305_SCENE,'dd02b8627053d7a9dc1c6f932cb34c5e78c4c5d21103a06ca169199f8b49f17e')
 def test_04_real_jar_pin(self):
  self.assertEqual(r.PIN_R305_JAR,'df44dd354dd7df5c6cbbaa5d3093bfe1db6353009c921e7201068b94e15ceae1')
 def test_05_exact_four_tokens_only(self):
  self.assertEqual(r.PATCHES,(('var21 < activeDrawDistance','var21 <= activeDrawDistance',1),('var22 < activeDrawDistance','var22 <= activeDrawDistance',1),('(var20 + 1) % 31','(var20 + 1) % 32',2)))
 def test_06_32_complete_yaw_bands(self):
  self.assertEqual(r.PATCHES[2][1], '(var20 + 1) % 32')
 def test_07_positive_x_border_included(self):
  self.assertIn('var21 <= activeDrawDistance',r.PATCHES[0][1])
 def test_08_positive_y_border_included(self):
  self.assertIn('var22 <= activeDrawDistance',r.PATCHES[1][1])
 def test_09_reject_foreign_source_preimage(self):
  with self.assertRaisesRegex(ValueError,'R305_SCENE_PREIMAGE_SHA_MISMATCH'):
   r.patch_visibility_seams(b'not-real-source')
 def test_10_reject_absent_method_markers(self):
  src=b'not-original-source'
  with mock.patch.object(r,'PIN_R304_SCENE',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R305_VISIBILITY_SECTION_ANCHOR_DRIFT'):
    r.patch_visibility_seams(src)
 def test_11_reject_unexpected_loop_preimage(self):
  src=(b'   public static void setViewport(\n      unrelated\n   private static boolean method455(')
  with mock.patch.object(r,'PIN_R304_SCENE',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R305_VISIBILITY_TOKEN_ANCHOR_DRIFT'):
    r.patch_visibility_seams(src)
 def test_12_existing_output_refused(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'occupied';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R305_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278','missing','--r265','missing','--output',str(out)])
 def test_13_missing_output_parent_refused(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(FileNotFoundError,'R305_UNSAFE_OUTPUT_PARENT'):
    r.main(['--r278','missing','--r265','missing','--output',str(Path(d)/'absent'/'new')])
 def test_14_full_class_count_and_compiled_sha_enforced(self):
  src=SCRIPT.read_text()
  self.assertIn('base.PIN_R304_JAR=PIN_R305_JAR',src)
  self.assertIn('digest(jar)!=PIN_R305_JAR',src)
  self.assertIn("manifest.get('compiled_classes')!=1386",src)
 def test_15_real_oracle_has_every_target_radius_and_yaw_wrap(self):
  src=JAVA.read_text()
  for marker in ('new int[]{5,10,25,30,50}','new int[]{30,31}','(yaw+1)&31','R305_RENDER_VISIBILITY_GRID_MISMATCH','R305_VISIBILITY_REFERENCE_ORACLE'):
   self.assertIn(marker,src)
 def test_16_no_game_binaries_or_downloads(self):
  src=SCRIPT.read_text()
  for marker in ('requests.get(', 'urllib.request','spawnpk.net','rs.gui.Launcher'):
   self.assertNotIn(marker,src)
  for folder in (SCRIPT.parent,JAVA.parent,Path(__file__).parent):
   self.assertFalse([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.class','.jar','.dat','.idx')])

if __name__=='__main__':unittest.main(verbosity=2)

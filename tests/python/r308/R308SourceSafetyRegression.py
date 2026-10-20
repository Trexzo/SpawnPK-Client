#!/usr/bin/env python3
"""R308 public source-only checks: eight fixed scene object writers and original archive trust."""
from pathlib import Path
import hashlib,importlib.util,tempfile,unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[3] if 'tests' in Path(__file__).parts else Path(__file__).resolve().parent
BUILDER=ROOT/'tools/recovery/r308/rebuild_r308_from_pinned.py'
if not BUILDER.exists():BUILDER=ROOT/'rebuild_r308_from_pinned.py'
JAVA=ROOT/'tests/java/r308/R308ScenePlacementBoundaryRegression.java'
if not JAVA.exists():JAVA=ROOT/'R308ScenePlacementBoundaryRegression.java'
spec=importlib.util.spec_from_file_location('r308_public',BUILDER)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class Safety(unittest.TestCase):
 def test_01_preimage(self):self.assertEqual(r.PIN_R307_SCENE,'2ed273e3dd162a5b1884f776dfcec2460f49b732ea0206b6211aeca72b3ef092')
 def test_02_postimage(self):self.assertEqual(r.PIN_R308_SCENE,'baa165aacae5d9408c21235bef656ab459b41e666906991ea49ed4622d23aeae')
 def test_03_compiled_jar(self):self.assertEqual(r.PIN_R308_JAR,'501072d504a4e03a758f44aaa32f0990d3f1599662f6f6d2fa0d83a14e6fc314')
 def test_04_original_builder_pin(self):self.assertEqual(r.PIN_R307_BUILDER,'176c0322183f3180bed905d9fb71f3d0e3e9ed9098b46ab182a29aa92edd4140')
 def test_05_real_parent_source_hash(self):
  if BUILDER.parent.parent.name!='recovery':self.skipTest('flat local dev checkout')
  p=BUILDER.parents[1]/'r307'/'rebuild_r307_from_pinned.py'
  self.assertEqual(r.file_sha(p),r.PIN_R307_BUILDER)
 def test_06_exact_eight_methods(self):self.assertEqual(len(r.PLACEMENT_COORDS),8)
 def test_07_explicit_coordinate_order(self):
  self.assertEqual(r.PLACEMENT_COORDS['method1909'],('var1','var2','var3'))
  self.assertEqual(r.PLACEMENT_COORDS['method1890'],('var1','var7','var3'))
  self.assertEqual(r.PLACEMENT_COORDS['method2219'],('var10','var6','var4'))
  self.assertEqual(r.PLACEMENT_COORDS['method3074'],('var4','var8','var2'))
  self.assertEqual(r.PLACEMENT_COORDS['method1657'],('var7','var1','var8'))
 def test_08_map_has_no_existing_guard_methods(self):
  for existing in ('method251','method3408','method2959','method1154','setPlane'):
   self.assertNotIn(existing,r.PLACEMENT_COORDS)
 def test_09_wrong_scene_sha_refused(self):
  with self.assertRaisesRegex(ValueError,'R308_SCENE_PREIMAGE_SHA_MISMATCH'):r.patch_placement_bounds(b'foreign scene')
 def test_10_missing_anchor_refused(self):
  b=b'not the original renderer'
  with mock.patch.object(r,'PIN_R307_SCENE',hashlib.sha256(b).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R308_PLACEMENT_METHOD_ANCHOR_DRIFT'):
    r.patch_placement_bounds(b)
 def test_11_duplicate_anchor_refused(self):
  t=b'   public void method1909(int var1) {\n   public void method1909(int var1) {\n'
  with mock.patch.object(r,'PIN_R307_SCENE',hashlib.sha256(t).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R308_PLACEMENT_METHOD_ANCHOR_DRIFT method1909'):r.patch_placement_bounds(t)
 def test_12_existing_output_refused(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'taken';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R308_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278','missing','--r265','missing','--output',str(out)])
 def test_13_missing_output_parent_refused(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(FileNotFoundError,'R308_UNSAFE_OUTPUT_PARENT'):
    r.main(['--r278','missing','--r265','missing','--output',str(Path(d)/'not-there'/'new')])
 def test_14_bad_public_parent_refused(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'new'
   with mock.patch.object(r,'PIN_R307_BUILDER','0'*64):
    with self.assertRaisesRegex(ValueError,'R308_ORIGINAL_R307_BUILDER_SHA_DRIFT'):
     r.main(['--r278','missing','--r265','missing','--output',str(out)])
 def test_15_real_class_regression_keeps_valid_paths(self):
  s=JAVA.read_text()
  for token in ('R308_SCENE_PLACEMENT_BOUNDARY_CRASH','R308_INVALID_PLACEMENT_MUTATED_SCENE','R308_VALID_SCENE_OBJECT_NOT_STORED','R308_SCENE_PLACEMENT_BOUNDS_PASS','addGroundDecoration','method1909'):
   self.assertIn(token,s)
 def test_16_original_build_counts_and_binary_sha(self):
  s=BUILDER.read_text()
  for token in ("base.JAR_SHA=PIN_R308_JAR", "manifest.get('compiled_classes')!=1386", "manifest.get('java_source_files')!=1277",'R308_COMPILED_BINARY_SHA_MISMATCH'):
   self.assertIn(token,s)
 def test_17_public_paths_contain_no_private_binaries(self):
  if BUILDER.parent.parent.name!='recovery':return
  for d in (BUILDER.parent,JAVA.parent,Path(__file__).parent):
   self.assertFalse([f for f in d.iterdir() if f.suffix.lower() in ('.jar','.class','.dat','.idx')])
 def test_18_no_game_server_or_http_fetch(self):
  s=BUILDER.read_text()
  for token in ('spawnpk.net','urllib.request','requests.get(', 'rs.gui.Launcher'):
   self.assertNotIn(token,s)

if __name__=='__main__':unittest.main(verbosity=2)

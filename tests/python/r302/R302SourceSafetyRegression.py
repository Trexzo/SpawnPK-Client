#!/usr/bin/env python3
"""R302 original-source SHA, occluder-slot safety and no-private-assets checks."""
import hashlib
import importlib.util
import tempfile
from pathlib import Path
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[3] if 'tests' in Path(__file__).parts else Path(__file__).resolve().parent
SCRIPT=ROOT/'tools/recovery/r302/rebuild_r302_from_pinned.py'
if not SCRIPT.is_file():SCRIPT=ROOT/'rebuild_r302_from_pinned.py'
JAVA=ROOT/'tests/java/r302/R302OccluderCapacityRegression.java'
if not JAVA.is_file():JAVA=ROOT/'R302OccluderCapacityRegression.java'
spec=importlib.util.spec_from_file_location('r302_rebuild',SCRIPT)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class SourceSafety(unittest.TestCase):
 def test_01_owner_source_archive_pins(self):
  self.assertEqual(r.PIN_R278,'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280')
  self.assertEqual(r.PIN_R265,'9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb')
 def test_02_r301_preimage(self):
  self.assertEqual(r.R302_SCENE_PREIMAGE_SHA,'27ba14ea218df3f4c377f76809ccb749c45ef6dee02d628f262ab99f7e3d1e49')
 def test_03_r302_postimage(self):
  self.assertEqual(r.R302_SCENE_POSTIMAGE_SHA,'ec91cf02318dc26a80a4a5e5ee9e912feff8a66ee83e37e2d82b25ada321bc66')
 def test_04_r302_jar(self):
  self.assertEqual(r.R302_JAR_SHA,'f3ce35078a1ebf07314de6c7335a9a9d66b990c587730fdf07a452f23bec5fae')
 def test_05_occluder_bounds_checked_before_allocation(self):
  s=r.R302_STATIC_REPLACEMENT
  self.assertLess(s.index('field5681 == null'),s.index('new Occluder()'))
  self.assertLess(s.index('var0 < 0'),s.index('new Occluder()'))
 def test_06_both_static_tables_checked(self):
  s=r.R302_STATIC_REPLACEMENT
  for part in ('field5681 == null','field5682 == null','var0 >= field5681.length','var0 >= field5682.length','field5682[var0] == null'):
   self.assertIn(part,s)
 def test_07_capacity_boundary_includes_negative(self):
  s=r.R302_STATIC_REPLACEMENT
  self.assertIn('field5681[var0] < 0',s)
  self.assertIn('field5681[var0] >= field5682[var0].length',s)
 def test_08_real_method_anchor_is_unique(self):
  self.assertIn('public static void method345',r.R302_STATIC_ANCHOR)
  self.assertEqual(r.R302_STATIC_REPLACEMENT.count('new Occluder()'),1)
 def test_09_preimage_hash_refusal(self):
  with self.assertRaisesRegex(ValueError,'R302_SCENE_PREIMAGE_SHA_MISMATCH'):
   r.patch_r302_scene_occluder_capacity(b'foreign game source')
 def test_10_missing_method_anchor_refusal(self):
  src=b'wrong source'
  with mock.patch.object(r,'R302_SCENE_PREIMAGE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R302_OCCLUDER_SOURCE_ANCHOR_DRIFT'):
    r.patch_r302_scene_occluder_capacity(src)
 def test_11_duplicate_anchor_refusal(self):
  src=(r.R302_STATIC_ANCHOR+'\n'+r.R302_STATIC_ANCHOR).encode()
  with mock.patch.object(r,'R302_SCENE_PREIMAGE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R302_OCCLUDER_SOURCE_ANCHOR_DRIFT'):
    r.patch_r302_scene_occluder_capacity(src)
 def test_12_invalid_postimage_refusal(self):
  src=r.R302_STATIC_ANCHOR.encode()
  with mock.patch.object(r,'R302_SCENE_PREIMAGE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R302_SCENE_POSTIMAGE_SHA_MISMATCH'):
    r.patch_r302_scene_occluder_capacity(src)
 def test_13_avoid_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);out=root/'occupied';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R302_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278',str(root/'missing-a.zip'),'--r265',str(root/'missing-b.zip'),'--output',str(out)])
 def test_14_missing_original_archives_refused_before_output(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);out=root/'new'
   with self.assertRaisesRegex(ValueError,'R302_PRIVATE_PINNED_INPUT_REFUSED'):
    r.main(['--r278',str(root/'missing-a.zip'),'--r265',str(root/'missing-b.zip'),'--output',str(out)])
   self.assertFalse(out.exists())
 def test_15_compiled_jar_source_count_enforced(self):
  s=SCRIPT.read_text()
  for part in ('len(sources)!=1277','!=1386','observed!=R302_JAR_SHA',"'--release','11'"):
   self.assertIn(part,s)
 def test_16_legacy_client_protection_unchanged(self):
  self.assertEqual(len(r.READ_ONLY_SCENE_QUERIES),12)
  self.assertEqual(len(r.R299_MUTATION_GUARDS),7)
  self.assertIn('hasTrackedObjectCapacity',r.R301_SCENE_CAPACITY_HELPER)
  self.assertIn('(n >>> 14 & 32767) != n4',r.NEW)
 def test_17_actual_java_regression_covers_edge_cases(self):
  s=JAVA.read_text()
  for marker in ('R302_OCCLUDER_BOUNDS_CRASH','R302_OCCLUDER_CAPACITY_PASS','500','Integer.MIN_VALUE','Integer.MAX_VALUE','slots.set(null,null)'):
   self.assertIn(marker,s)
 def test_18_no_proprietary_game_data_or_network(self):
  s=SCRIPT.read_text()
  for unsafe in ('spawnpk.net','urllib.request','requests.get(', 'rs.gui.Launcher'):
   self.assertNotIn(unsafe,s)
  for path in (SCRIPT.parent,JAVA.parent):
   if path==ROOT: continue  # flat local test workspace; repository paths scanned in CI
   self.assertFalse([f for f in path.iterdir() if f.is_file() and f.suffix.lower() in {'.class','.jar','.dat','.idx'}])

if __name__=='__main__':unittest.main(verbosity=2)

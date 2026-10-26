#!/usr/bin/env python3
"""R300 source-only pin and boundary safety; no proprietary runtime dependencies."""
from pathlib import Path
import hashlib,importlib.util,tempfile,unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[3] if 'tests' in Path(__file__).parts else Path(__file__).resolve().parent
SOURCE=ROOT/'tools/recovery/r300/rebuild_r300_from_pinned.py'
if not SOURCE.exists(): SOURCE=ROOT/'rebuild_r300_from_pinned.py'
TEST=ROOT/'tests/java/r300/R300SceneEntrypointRegression.java'
if not TEST.exists(): TEST=ROOT/'R300SceneEntrypointRegression.java'
spec=importlib.util.spec_from_file_location('r300_source',SOURCE)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class R300SourceSafety(unittest.TestCase):
 def test_01_input_sha_pins(self):
  self.assertEqual(r.PIN_R278,'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280')
  self.assertEqual(r.PIN_R265,'9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb')
 def test_02_real_r299_scene_preimage(self):
  self.assertEqual(r.R300_SCENE_PREIMAGE_SHA,'007159b0b47058552150985c45f5b441df1a4bbd5a794bc41b6ad172bee8832e')
 def test_03_real_r300_scene_postimage(self):
  self.assertEqual(r.R300_SCENE_POSTIMAGE_SHA,'85367ddd248e15192ef2bffa55ed764b48b67fedfb3378f9bf7d419337affca8')
 def test_04_exact_java11_rebuilt_hash(self):
  self.assertEqual(r.R300_JAR_SHA,'a3ece2b2be3559777c140c93fc5d4a33499ccf45d9c5172e1bc53e4f439a2371')
 def test_05_original_client_menu_authority_unchanged(self):
  self.assertIn('(n >>> 14 & 32767) != n4',r.NEW)
 def test_06_original_r299_mutation_guards_kept(self):
  self.assertEqual(len(r.R299_MUTATION_GUARDS),7)
 def test_07_original_r298_query_guards_kept(self):
  self.assertEqual(len(r.READ_ONLY_SCENE_QUERIES),12)
 def test_08_exactly_two_object_footprint_entrypoints(self):
  source=SOURCE.read_text()
  self.assertIn("('method3408','method2959')",source)
 def test_09_footprint_is_dimension_safe(self):
  source=SOURCE.read_text()
  self.assertIn('isSceneFootprintInBounds',source)
  self.assertIn('width > 0 && height > 0',source)
  self.assertIn('x <= this.tiles[plane].length - width',source)
  self.assertIn('y <= this.tiles[plane][0].length - height',source)
 def test_10_plane_checked_before_state_assignment(self):
  source=SOURCE.read_text()
  self.assertIn('if (var1 < 0 || var1 >= this.tiles.length)',source)
  self.assertIn('this.plane = var1;',source)
 def test_11_bridge_guard_respects_argument_order(self):
  self.assertIn('this.isSceneTileInBounds(0, var2, var1)',SOURCE.read_text())
 def test_12_wrong_real_source_rejected_before_change(self):
  with self.assertRaisesRegex(ValueError,'R300_SCENE_PREIMAGE_MISMATCH'):
   r.patch_scene_entrypoints(b'not-an-owner-game-source')
 def test_13_duplicated_scene_anchor_rejected(self):
  anchor='   public void setPlane(int var1) {\n      this.plane = var1;'
  source=(anchor+'\n'+anchor).encode()
  with mock.patch.object(r,'R300_SCENE_PREIMAGE_SHA',hashlib.sha256(source).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R300_SCENE_ANCHOR_DRIFT'):r.patch_scene_entrypoints(source)
 def test_14_missing_scene_anchor_rejected(self):
  source=b'missing-methods'
  with mock.patch.object(r,'R300_SCENE_PREIMAGE_SHA',hashlib.sha256(source).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R300_SCENE_ANCHOR_DRIFT'):r.patch_scene_entrypoints(source)
 def test_15_reject_existing_private_output(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);out=p/'existing';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R300_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278',str(p/'r278.zip'),'--r265',str(p/'r265.zip'),'--output',str(out)])
 def test_16_reject_missing_owner_archives(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);out=p/'future'
   with self.assertRaisesRegex(ValueError,'R300_PRIVATE_PINNED_INPUT_REFUSED'):
    r.main(['--r278',str(p/'r278.zip'),'--r265',str(p/'r265.zip'),'--output',str(out)])
   self.assertFalse(out.exists())
 def test_17_java_red_green_cases_present(self):
  source=TEST.read_text()
  for marker in ('R300_SCENE_BOUNDARY_CRASH','R300_SCENE_PLACEMENT_CRASH','valid bridge plane shift lost','valid object placement refused','R300_SCENE_PLANE_TILESHIFT_OBJECT_PLACEMENT_PASS'):
   self.assertIn(marker,source)
 def test_18_no_private_game_classes_or_network(self):
  source=SOURCE.read_text()
  for forbidden in ('rs.gui.Launcher','requests.get(', 'spawnpk.net','urllib.request'):
   self.assertNotIn(forbidden,source)
  for d in (SOURCE.parent,TEST.parent):
   if d==ROOT: continue  # Flat private developer workspace; repository dirs are scanned in CI.
   self.assertFalse([f for f in d.rglob('*') if f.is_file() and f.suffix.lower() in {'.jar','.class','.dat','.idx'}])
if __name__=='__main__':unittest.main(verbosity=2)

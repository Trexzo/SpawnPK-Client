#!/usr/bin/env python3
"""Public-only R306 scene draw-radius transition provenance and refusal tests."""
from pathlib import Path
import hashlib
import importlib.util
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/'tools/recovery/r306/rebuild_r306_from_pinned.py'
JAVA=ROOT/'tests/java/r306/R306DrawRadiusTransitionRegression.java'
spec=importlib.util.spec_from_file_location('r306_pinned_source',SCRIPT)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class R306Safety(unittest.TestCase):
 def test_01_original_r305_builder_sha(self):
  self.assertEqual(r.R305_BUILDER_SHA,'be05611ced1ab591383a59358cb97049a859c0a5ff75c804a0a736b9f53afaed')
  self.assertEqual(r.digest(ROOT/'tools/recovery/r305/rebuild_r305_from_pinned.py'),r.R305_BUILDER_SHA)
 def test_02_r305_source_preimage(self):
  self.assertEqual(r.R305_SOURCE_SHA,'dd02b8627053d7a9dc1c6f932cb34c5e78c4c5d21103a06ca169199f8b49f17e')
 def test_03_r306_source_postimage(self):
  self.assertEqual(r.R306_SOURCE_SHA,'b8fa016278c1ef8def2866dbffd54bf3a78f7b3bb28985672e1609e7f6787a3d')
 def test_04_pinned_compiled_binary(self):
  self.assertEqual(r.R306_JAR_SHA,'9db9e6f3b43fc894f2e62828a67c04b00d22292d5782c9b967e3da6be3c35b14')
 def test_05_recompute_before_gpu_draw(self):
  s=r.DYNAMIC_REBUILD
  self.assertIn('tileVisibility == null',s)
  self.assertIn('tileVisibility[0][0].length != 2 * activeDrawDistance + 1',s)
  self.assertIn('setViewport(500, 800, viewportMaxX, viewportMaxY)',s)
 def test_06_no_per_frame_recompute(self):
  self.assertIn('if (tileVisibility == null ||',r.DYNAMIC_REBUILD)
 def test_07_clamp_smaller_view_radius(self):
  s=r.SAFE_TILE_LOOKUP
  for term in ('x >= 0','y >= 0','x < tileVisibilityBand.length','y < tileVisibilityBand[x].length','tileVisibilityBand[x][y]'):
   self.assertIn(term,s)
 def test_08_original_direct_unbounded_access_eliminated(self):
  self.assertIn('tileVisibilityBand[var21 - cameraTileX',r.OLD_TILE_LOOKUP)
  self.assertIn('isVisibleSceneTile(var21, var22)',SCRIPT.read_text())
 def test_09_unknown_source_rejected(self):
  with self.assertRaisesRegex(ValueError,'R306_SOURCE_PREIMAGE_SHA_MISMATCH'):r.patch_radius_transition(b'foreign')
 def test_10_missing_method_refused(self):
  src=b'no scene method'
  with mock.patch.object(r,'R305_SOURCE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R306_RENDERER_ANCHOR_DRIFT'):r.patch_radius_transition(src)
 def test_11_duplicate_method_refused(self):
  src=(r.DRAW_SIGNATURE+'\n'+r.DRAW_SIGNATURE+'\n'+r.OLD_TILE_LOOKUP).encode()
  with mock.patch.object(r,'R305_SOURCE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R306_RENDERER_ANCHOR_DRIFT'):r.patch_radius_transition(src)
 def test_12_unexpected_postimage_refused(self):
  src=(r.DRAW_SIGNATURE+'\n'+r.OLD_TILE_LOOKUP).encode()
  with mock.patch.object(r,'R305_SOURCE_SHA',hashlib.sha256(src).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R306_SOURCE_POSTIMAGE_SHA_MISMATCH'):r.patch_radius_transition(src)
 def test_13_existing_output_denied(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);out=root/'existing';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R306_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278',str(root/'a.zip'),'--r265',str(root/'b.zip'),'--output',str(out)])
 def test_14_missing_parent_denied(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'absent'/'new'
   with self.assertRaisesRegex(FileNotFoundError,'R306_UNSAFE_OUTPUT_PARENT'):
    r.main(['--r278','a.zip','--r265','b.zip','--output',str(out)])
 def test_15_inherited_class_hash_and_build_checks(self):
  s=SCRIPT.read_text()
  for marker in ('base.PIN_R305_JAR=R306_JAR_SHA',"manifest.get('compiled_classes')!=1386",'digest(jar)!=R306_JAR_SHA',"manifest.get('java_source_files')!=1277"):
   self.assertIn(marker,s)
 def test_16_real_java_render_crash_and_stability_covered(self):
  s=JAVA.read_text()
  for key in ('R306_STALE_RENDER_VISIBILITY_CRASH','draw(scene,d)','stable==visibility()', 'isVisibleSceneTile','R306_DYNAMIC_DRAW_RADIUS_TRANSITIONS_PASS'):
   self.assertIn(key,s)
 def test_17_public_scripts_contain_no_game_binaries(self):
  for directory in (SCRIPT.parent,JAVA.parent,Path(__file__).parent):
   self.assertFalse([p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in ('.jar','.class','.dat','.idx')])
 def test_18_no_remote_download_or_runtime_launch_in_builder(self):
  s=SCRIPT.read_text()
  for token in ('spawnpk.net','requests.get(', 'urllib.request','rs.gui.Launcher'):
   self.assertNotIn(token,s)

if __name__=='__main__':unittest.main(verbosity=2)

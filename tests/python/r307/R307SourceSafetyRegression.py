#!/usr/bin/env python3
"""Source-only R307 GPU/cold visibility build provenance, no private game assets."""
from pathlib import Path
import hashlib,importlib.util,tempfile,unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[3] if 'tests' in Path(__file__).parts else Path(__file__).resolve().parent
SCRIPT=ROOT/'tools/recovery/r307/rebuild_r307_from_pinned.py'
if not SCRIPT.is_file():SCRIPT=ROOT/'rebuild_r307_from_pinned.py'
mod=importlib.util.spec_from_file_location('r307_build_safe',SCRIPT)
r=importlib.util.module_from_spec(mod);mod.loader.exec_module(r)

class Safety(unittest.TestCase):
 def test_01_exact_public_script_chain(self):
  self.assertEqual(set(r.PUBLIC_SCRIPTS),set('r302 r303 r304 r305 r306'.split()))
 def test_02_local_public_script_sha_pins(self):
  if SCRIPT.parent.parent.name!='recovery':self.skipTest('developer flat-tree: tested in public repo CI')
  base=SCRIPT.parents[1]
  for name,(sha,filename) in r.PUBLIC_SCRIPTS.items():self.assertEqual(r.digest_file(base/name/filename),sha)
 def test_03_scene_preimage(self):self.assertEqual(r.PRE_SCENE,'b8fa016278c1ef8def2866dbffd54bf3a78f7b3bb28985672e1609e7f6787a3d')
 def test_04_scene_postimage(self):self.assertEqual(r.POST_SCENE,'2ed273e3dd162a5b1884f776dfcec2460f49b732ea0206b6211aeca72b3ef092')
 def test_05_client_preimage(self):self.assertEqual(r.PRE_CLIENT,'db1dfd4a4752fced78c2cb886bc50159eb8eeb8cc94d27c70b3d9e2ff1b1764c')
 def test_06_client_postimage(self):self.assertEqual(r.POST_CLIENT,'f7d8e18a5e5d0b43e25b579388d06f035e0890dc8d595c41aac56bb316fc9dcf')
 def test_07_jar_sha(self):self.assertEqual(r.JAR_SHA,'00204d4b1fe557e64054520e7f22b54bf7094b617784639d50b95c8b8af77d94')
 def test_08_gpu_path_no_longer_skips_align(self):
  self.assertIn('Scene.setViewport(500, 800, viewportWidth, viewportHeight);',r.CLIENT_NEW)
  self.assertNotIn('GpuRenderer.isActive()',r.CLIENT_NEW)
 def test_09_cold_grid_no_false_preinitialized_geometry(self):self.assertEqual(r.SCENE_FIELD_NEW,'private static boolean[][][][] tileVisibility;')
 def test_10_cold_viewport_geometry_keeps_source_dimensions(self):
  self.assertIn('viewportMaxX > 0 ? viewportMaxX : Client.viewportWidth',r.SCENE_DRAW_NEW)
  self.assertIn('viewportMaxY > 0 ? viewportMaxY : Client.viewportHeight',r.SCENE_DRAW_NEW)
 def test_11_wrong_client_source_refused(self):
  with self.assertRaisesRegex(ValueError,'R307_CLIENT_PREIMAGE_SHA_MISMATCH'):r.patch_client(b'not client')
 def test_12_wrong_scene_source_refused(self):
  with self.assertRaisesRegex(ValueError,'R307_SCENE_PREIMAGE_SHA_MISMATCH'):r.patch_scene(b'not scene')
 def test_13_duplicate_client_anchor_refused(self):
  old=(r.CLIENT_OLD+'\n'+r.CLIENT_OLD).encode()
  with mock.patch.object(r,'PRE_CLIENT',hashlib.sha256(old).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R307_CLIENT_ALIGN_ANCHOR_DRIFT'):r.patch_client(old)
 def test_14_duplicate_scene_anchor_refused(self):
  old=(r.SCENE_DRAW_OLD+'\n'+r.SCENE_DRAW_OLD+'\n'+r.SCENE_FIELD_OLD).encode()
  with mock.patch.object(r,'PRE_SCENE',hashlib.sha256(old).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R307_SCENE_ANCHOR_DRIFT'):r.patch_scene(old)
 def test_15_unexpected_client_output_refused(self):
  old=r.CLIENT_OLD.encode()
  with mock.patch.object(r,'PRE_CLIENT',hashlib.sha256(old).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R307_CLIENT_POSTIMAGE_SHA_MISMATCH'):r.patch_client(old)
 def test_16_unexpected_scene_output_refused(self):
  old=(r.SCENE_FIELD_OLD+'\n'+r.SCENE_DRAW_OLD).encode()
  with mock.patch.object(r,'PRE_SCENE',hashlib.sha256(old).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R307_SCENE_POSTIMAGE_SHA_MISMATCH'):r.patch_scene(old)
 def test_17_existing_output_refused(self):
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t);out=folder/'old';out.mkdir()
   with self.assertRaisesRegex(FileExistsError,'R307_REFUSE_EXISTING_OUTPUT'):
    r.main(['--r278',str(folder/'a.zip'),'--r265',str(folder/'b.zip'),'--output',str(out)])
 def test_18_missing_output_parent_refused(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'not-a-folder'/'new'
   with self.assertRaisesRegex(FileNotFoundError,'R307_OUTPUT_PARENT_UNSAFE'):
    r.main(['--r278','a.zip','--r265','b.zip','--output',str(out)])
 def test_19_damaged_public_recipe_refused(self):
  with tempfile.TemporaryDirectory() as t:
   f=Path(t)/'bad.py';f.write_text('untrusted')
   with self.assertRaisesRegex(ValueError,'R307_PUBLIC_SCRIPT_SHA_REFUSED'):
    r.pinned_module('r302',f,r.PUBLIC_SCRIPTS['r302'][0])
 def test_20_compilation_and_no_assets_in_public_repo(self):
  s=SCRIPT.read_text()
  for marker in ('--release','R307_CLASS_COUNT_DRIFT','R307_JAR_SHA_MISMATCH','R307_PRIVATE_INPUT_SHA_REFUSED'):
   self.assertIn(marker,s)
  for forbidden in ('requests.get(', 'urllib.request','spawnpk.net','rs.gui.Launcher'):
   self.assertNotIn(forbidden,s)
  if SCRIPT.parent.parent.name=='recovery':
   for folder in (SCRIPT.parent,Path(__file__).parent):
    self.assertFalse([p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in ('.jar','.class','.dat','.idx')])

if __name__=='__main__':unittest.main(verbosity=2)

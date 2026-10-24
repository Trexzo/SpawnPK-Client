#!/usr/bin/env python3
"""R295 public source-only regression: no private game archives required."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/'tools/recovery/r295/rebuild_r295_from_pinned.py'
JAVA=ROOT/'tests/java/r295/R295SceneHashBoundsRegression.java'
spec=importlib.util.spec_from_file_location('r295_build',SCRIPT)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class SourceSafety(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='r295-safety-');self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.output=self.root/'new-output'
  self.r278=self.root/'R278.zip';self.r265=self.root/'R265.zip'
 def test_01_pinned_r278(self):self.assertEqual(r.PIN_R278,'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280')
 def test_02_pinned_r265(self):self.assertEqual(r.PIN_R265,'9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb')
 def test_03_pinned_r293_client_postimage(self):self.assertEqual(r.PIN_R293_SOURCE,'db1dfd4a4752fced78c2cb886bc50159eb8eeb8cc94d27c70b3d9e2ff1b1764c')
 def test_04_scene_input_sha(self):self.assertEqual(r.SCENE_PREIMAGE_SHA,'5757842cf0cea18bcd99667ddeba5150ec915e450308ca07ff45ee3922fdf6b1')
 def test_05_scene_output_sha(self):self.assertEqual(r.SCENE_POSTIMAGE_SHA,'24790fc3aac8676df95c1cd0f830f26bc6ad749cc87435f47b9eb69c9c8ef813')
 def test_06_r295_compiled_jar_sha(self):self.assertEqual(r.R295_JAR_SHA,'f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35')
 def test_07_guard_precedes_scene_access(self):self.assertLess(r.SCENE_NEW.index('return -1;'),r.SCENE_NEW.index('Tile var5 ='))
 def test_08_boundaries_include_planes_and_xy(self):
  for marker in ('var1 < 0','var1 >= this.tiles.length','var2 < 0','var2 >= this.tiles[var1].length','var3 < 0','var3 >= this.tiles[var1][var2].length'):
   self.assertIn(marker,r.SCENE_NEW)
 def test_09_original_absence_sentinel_retained(self):self.assertIn('return -1;',r.SCENE_NEW)
 def test_10_foreign_source_rejected_before_patch(self):
  with self.assertRaisesRegex(ValueError,'R295_SCENE_PREIMAGE_HASH_MISMATCH'):r.patch_scene(b'not-owner-scene')
 def test_11_original_anchor_unique(self):
  pre=r.SCENE_OLD.encode();changed=pre.replace(pre,r.SCENE_NEW.encode())
  with mock.patch.object(r,'SCENE_PREIMAGE_SHA',hashlib.sha256(pre).hexdigest()),mock.patch.object(r,'SCENE_POSTIMAGE_SHA',hashlib.sha256(changed).hexdigest()):
   self.assertEqual(r.patch_scene(pre),changed)
 def test_12_duplicate_anchor_refused(self):
  inp=(r.SCENE_OLD+'\n'+r.SCENE_OLD).encode()
  with mock.patch.object(r,'SCENE_PREIMAGE_SHA',hashlib.sha256(inp).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R295_SCENE_METHOD_ANCHOR_MISMATCH'):r.patch_scene(inp)
 def test_13_tampered_postimage_refused(self):
  inp=r.SCENE_OLD.encode()
  with mock.patch.object(r,'SCENE_PREIMAGE_SHA',hashlib.sha256(inp).hexdigest()):
   with self.assertRaisesRegex(ValueError,'R295_SCENE_POSTIMAGE_HASH_MISMATCH'):r.patch_scene(inp)
 def test_14_missing_owner_inputs_refused(self):
  with self.assertRaisesRegex(ValueError,'R295_PRIVATE_PINNED_INPUT_REFUSED'):
   r.main(['--r278',str(self.r278),'--r265',str(self.r265),'--output',str(self.output)])
  self.assertFalse(self.output.exists())
 def test_15_tampered_owner_inputs_refused(self):
  self.r278.write_bytes(b'tampered');self.r265.write_bytes(b'tampered')
  with self.assertRaisesRegex(ValueError,'R295_PRIVATE_PINNED_INPUT_REFUSED'):
   r.main(['--r278',str(self.r278),'--r265',str(self.r265),'--output',str(self.output)])
  self.assertFalse(self.output.exists())
 def test_16_existing_output_refused(self):
  self.output.mkdir()
  with self.assertRaisesRegex(FileExistsError,'R295_REFUSE_EXISTING_OUTPUT'):
   r.main(['--r278',str(self.r278),'--r265',str(self.r265),'--output',str(self.output)])
 def test_17_missing_output_parent_refused(self):
  with self.assertRaisesRegex(FileNotFoundError,'R295_OUTPUT_PARENT_UNSAFE_OR_MISSING'):
   r.main(['--r278',str(self.r278),'--r265',str(self.r265),'--output',str(self.root/'absent'/'future')])
 def test_18_real_jvm_test_coverage(self):
  s=JAVA.read_text()
  for key in ('R295_SCENE_HASH_DIRECT_OOB_CRASH','R295_SCENE_HASH_BOUNDARY_PASS','-1,104,105,Integer.MIN_VALUE,Integer.MAX_VALUE','scene.getHashAtTile'):
   self.assertIn(key,s)
 def test_19_no_proprietary_build_inputs(self):
  for directory in (SCRIPT.parent,JAVA.parent,Path(__file__).parent):
   for f in directory.rglob('*'):
    if f.is_file():self.assertNotIn(f.suffix.lower(),('.class','.jar','.dat','.idx'))
 def test_20_no_remote_network_or_game_launch(self):
  src=SCRIPT.read_text()
  for key in ('requests.get(', 'urllib.request', 'rs.gui.Launcher', 'spawnpk.net'):
   self.assertNotIn(key,src)
if __name__=='__main__': unittest.main(verbosity=2)

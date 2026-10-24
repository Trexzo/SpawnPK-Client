#!/usr/bin/env python3
"""R293 zero-asset checks; cannot claim full Java/GUI runtime verification."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE=Path(__file__).resolve().parents[3]/'tools/recovery/r293/rebuild_r293_from_pinned.py'
JAVA=Path(__file__).resolve().parents[3]/'tests/java/r293/R293OutOfBoundsRegression.java'
spec=importlib.util.spec_from_file_location('r293_real_builder',SOURCE)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class R293SourceSafety(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='r293-source-safe-');self.addCleanup(self.temp.cleanup)
  self.folder=Path(self.temp.name);self.output=self.folder/'private-absent'
  self.archives=[self.folder/'r278.zip',self.folder/'r265.zip']
 def test_original_pins_intact(self):
  self.assertEqual(len(r.PIN_R278),64);self.assertEqual(len(r.PIN_R265),64)
  self.assertEqual(r.PIN_R278,'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280')
 def test_r290_source_provenance_intact(self):
  self.assertEqual(r.PIN_R290_SOURCE,'b0a1ae721da4dc2e1b0bfb7ea6e434b2f8bc41126eb1bd1ec3f776c07f56772c')
 def test_r293_source_pin(self):
  self.assertEqual(r.PIN_R293_SOURCE,'db1dfd4a4752fced78c2cb886bc50159eb8eeb8cc94d27c70b3d9e2ff1b1764c')
 def test_r293_jar_pin(self):
  self.assertEqual(r.PIN_R293_JAR,'0d0eedae92efe709b2d6eb49b1fc4432db174a6e68a7f06fd4fc2736d0f6cee9')
 def test_bounds_before_unchecked_scene_read(self):
  self.assertLess(r.R293_NEW.index('n2 >= 104'),r.R293_NEW.index('getHashAtTile'))
  self.assertLess(r.R293_NEW.index('planeLevel >= 4'),r.R293_NEW.index('getHashAtTile'))
 def test_original_object_id_guard_kept(self):
  self.assertIn('(n >>> 14 & 32767) != n4',r.NEW)
 def test_exactly_one_source_delta(self):
  self.assertIn('int n5 = this.field761.getHashAtTile',r.R293_OLD)
  self.assertIn('return false;',r.R293_NEW)
 def test_reject_unrelated_source(self):
  with self.assertRaisesRegex(ValueError,'R290_R278_SOURCE_PREIMAGE_MISMATCH'):
   r.r293_patch(b'unrelated')
 def test_accept_exact_replacement_fixture(self):
  fake=r.R293_OLD.encode();expected=fake.replace(r.R293_OLD.encode(),r.R293_NEW.encode())
  with mock.patch.object(r,'patched_client',return_value=fake),mock.patch.object(r,'PIN_R293_SOURCE',hashlib.sha256(expected).hexdigest()):
   self.assertEqual(r.r293_patch(b'test'),expected)
 def test_reject_ambiguous_anchor(self):
  with mock.patch.object(r,'patched_client',return_value=(r.R293_OLD+'\n'+r.R293_OLD).encode()):
   with self.assertRaisesRegex(ValueError,'R293_BOUNDS_GUARD_ANCHOR_DRIFT'):r.r293_patch(b'test')
 def test_reject_missing_anchor(self):
  with mock.patch.object(r,'patched_client',return_value=b'nothing'):
   with self.assertRaisesRegex(ValueError,'R293_BOUNDS_GUARD_ANCHOR_DRIFT'):r.r293_patch(b'test')
 def test_reject_false_postimage(self):
  with mock.patch.object(r,'patched_client',return_value=r.R293_OLD.encode()):
   with self.assertRaisesRegex(ValueError,'R293_POSTIMAGE_DRIFT'):r.r293_patch(b'test')
 def test_missing_archives_fails_before_output(self):
  with self.assertRaisesRegex(ValueError,'PRIVATE_PINNED_INPUT_REFUSED'):
   r.main(['--r278',str(self.archives[0]),'--r265',str(self.archives[1]),'--output',str(self.output)])
  self.assertFalse(self.output.exists())
 def test_existing_output_never_overwritten(self):
  self.output.mkdir()
  with self.assertRaisesRegex(FileExistsError,'REFUSE_EXISTING_OUTPUT'):
   r.main(['--r278',str(self.archives[0]),'--r265',str(self.archives[1]),'--output',str(self.output)])
 def test_missing_parent_refusal(self):
  with self.assertRaisesRegex(FileNotFoundError,'OUTPUT_PARENT_UNSAFE_OR_MISSING'):
   r.main(['--r278',str(self.archives[0]),'--r265',str(self.archives[1]),'--output',str(self.folder/'missing'/'future')])
 def test_source_safe_no_private_artifacts(self):
  self.assertNotIn('rs.gui.Launcher',SOURCE.read_text())
  self.assertNotIn('urllib.request',SOURCE.read_text())
 def test_java_runtime_regression_exists(self):
  java=JAVA.read_text()
  for marker in ('R293_OFF_SCENE_X_CRASH','R293_OFF_SCENE_Y_CRASH','R293_OFF_SCENE_PLANE_CRASH','R293_OFF_SCENE_MENU_CRASH','R293_OFF_SCENE_GUARD_PASS','1062,900,113,872,502,62,956'):
   self.assertIn(marker,java)
if __name__=='__main__':unittest.main(verbosity=2)

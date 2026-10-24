#!/usr/bin/env python3
"""Source-only R301 SHA and atomicity tests; no game/private assets required."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2] if HERE.parent.name == 'python' else HERE
SCRIPT = ROOT / 'tools/recovery/r301/rebuild_r301_from_pinned.py'
if not SCRIPT.exists():
    SCRIPT = ROOT / 'rebuild_r301_from_pinned.py'
JAVA = ROOT / 'tests/java/r301/R301PlacementCapacityRegression.java'
if not JAVA.exists():
    JAVA = ROOT / 'R301PlacementCapacityRegression.java'
spec = importlib.util.spec_from_file_location('r301_rebuild', SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class R301Safety(unittest.TestCase):
    def test_pinned_private_inputs(self):
        self.assertEqual(r.PIN_R278, 'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280')
        self.assertEqual(r.PIN_R265, '9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb')
    def test_pinned_preimage(self):
        self.assertEqual(r.R301_SCENE_PREIMAGE_SHA, '85367ddd248e15192ef2bffa55ed764b48b67fedfb3378f9bf7d419337affca8')
    def test_pinned_postimage(self):
        self.assertEqual(r.R301_SCENE_POSTIMAGE_SHA, '27ba14ea218df3f4c377f76809ccb749c45ef6dee02d628f262ab99f7e3d1e49')
    def test_pinned_jar(self):
        self.assertEqual(r.R301_JAR_SHA, 'e741150b360e01f0adf098c977843507a7ff4cc9c872451cf6461415ed2f58da')
    def test_exact_two_insertions(self):
        self.assertIn('hasTrackedObjectCapacity', r.R301_SCENE_CAPACITY_HELPER)
        self.assertIn('this.hasTrackedObjectCapacity()', r.R301_NEW_INSERTION_GUARD)
    def test_capacity_rejects_negative_and_both_arrays(self):
        for x in ('field5665 >= 0', 'field5665 < this.field5666.length', 'field5665 < this.field5667.length'):
            self.assertIn(x, r.R301_SCENE_CAPACITY_HELPER)
    def test_only_tracked_requests_require_capacity(self):
        self.assertIn('if (var11 && !this.hasTrackedObjectCapacity())', r.R301_NEW_INSERTION_GUARD)
    def test_check_before_footprint_insertion_loop(self):
        self.assertIn('isSceneFootprintInBounds', r.R301_OLD_INSERTION_GUARD)
    def test_bad_source_refused_before_patch(self):
        with self.assertRaisesRegex(ValueError, 'R301_SCENE_PREIMAGE_SHA_MISMATCH'):
            r.patch_r301_scene_capacity(b'foreign source')
    def test_missing_guard_anchor_refused(self):
        source = b'valid preimage but no anchor'
        with mock.patch.object(r, 'R301_SCENE_PREIMAGE_SHA', hashlib.sha256(source).hexdigest()):
            with self.assertRaisesRegex(ValueError, 'R301_SCENE_CAPACITY_ANCHOR_DRIFT'):
                r.patch_r301_scene_capacity(source)
    def test_duplicate_guard_anchor_refused(self):
        source = (r.R301_SCENE_CAPACITY_OLD + r.R301_SCENE_CAPACITY_OLD).encode()
        with mock.patch.object(r, 'R301_SCENE_PREIMAGE_SHA', hashlib.sha256(source).hexdigest()):
            with self.assertRaisesRegex(ValueError, 'R301_SCENE_CAPACITY_ANCHOR_DRIFT'):
                r.patch_r301_scene_capacity(source)
    def test_wrong_postimage_refused(self):
        text = (r.R301_SCENE_CAPACITY_OLD + '\n' + r.R301_OLD_INSERTION_GUARD * 2).encode()
        with mock.patch.object(r, 'R301_SCENE_PREIMAGE_SHA', hashlib.sha256(text).hexdigest()):
            with self.assertRaisesRegex(ValueError, 'R301_SCENE_POSTIMAGE_SHA_MISMATCH'):
                r.patch_r301_scene_capacity(text)
    def test_outfile_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t); out = base / 'old'; out.mkdir()
            with self.assertRaisesRegex(FileExistsError, 'R301_REFUSE_EXISTING_OUTPUT'):
                r.main(['--r278', str(base/'a.zip'), '--r265', str(base/'b.zip'), '--output', str(out)])
    def test_absent_owner_archives_fail_before_output(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t); out = base / 'new'
            with self.assertRaisesRegex(ValueError, 'R301_PRIVATE_PINNED_INPUT_REFUSED'):
                r.main(['--r278', str(base/'a.zip'), '--r265', str(base/'b.zip'), '--output', str(out)])
            self.assertFalse(out.exists())
    def test_original_menu_and_scene_guards_retained(self):
        self.assertIn('(n >>> 14 & 32767) != n4', r.NEW)
        self.assertEqual(len(r.READ_ONLY_SCENE_QUERIES), 12)
        self.assertEqual(len(r.R299_MUTATION_GUARDS), 7)
    def test_exact_compiler_and_output_gates(self):
        text = SCRIPT.read_text()
        self.assertIn("'--release','11'", text)
        self.assertIn('observed!=R301_JAR_SHA', text)
        self.assertIn('!=1386', text)
    def test_real_client_java_regression_exists(self):
        text = JAVA.read_text()
        for marker in ('R301_SCENE_OBJECT_CAPACITY_CRASH', 'R301_PARTIALLY_COMMITTED_BAD_CAPACITY',
                       'R301_UNTRACKED_PLACEMENT_REJECTED', 'R301_TRACKED_OBJECT_CAPACITY_PASS'):
            self.assertIn(marker, text)
    def test_no_private_binaries_in_public_r301_files(self):
        for d in (SCRIPT.parent, JAVA.parent, HERE):
            self.assertFalse([p for p in d.glob('*') if p.suffix.lower() in ('.jar', '.class', '.dat', '.idx')])

if __name__ == '__main__':
    unittest.main(verbosity=2)

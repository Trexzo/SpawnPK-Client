#!/usr/bin/env python3
"""Public source-only R290 guard regression, never stages private game assets."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'tools/recovery/r290/rebuild_r290_from_pinned.py'
JAVA_TEST = ROOT / 'tests/java/r290/R290ObjectIdAuthorityRegression.java'
spec = importlib.util.spec_from_file_location('r290_private_builder',SCRIPT)
impl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl)

class SourceSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r290-safe-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.r278 = self.home/'r278.zip'
        self.r265 = self.home/'r265.zip'
        self.output = self.home/'private-output'

    def test_exact_r265_pin(self):
        self.assertEqual(impl.PIN_R265, '9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb')

    def test_exact_r278_pin(self):
        self.assertEqual(impl.PIN_R278, 'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280')

    def test_exact_source_postimage(self):
        self.assertEqual(impl.PIN_R290_SOURCE, 'b0a1ae721da4dc2e1b0bfb7ea6e434b2f8bc41126eb1bd1ec3f776c07f56772c')

    def test_exact_jar_target(self):
        self.assertEqual(impl.PIN_R290_JAR, 'f2f914f12196705fd7233ea022742157d13deb50be85289465ce26b0dde3cd4a')

    def test_guard_requires_scene_id_match(self):
        self.assertIn('(n >>> 14 & 32767) != n4', impl.NEW)
        self.assertNotIn('(n >>> 14 & 32767) != n4', impl.OLD)

    def test_private_source_preimage_refuses_arbitrary_bytes(self):
        with self.assertRaisesRegex(ValueError,'R290_R278_SOURCE_PREIMAGE_MISMATCH'):
            impl.patched_client(b'not-a-game-client')

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        with self.assertRaisesRegex(FileExistsError,'R290_REFUSE_EXISTING_OUTPUT'):
            impl.main(['--r278',str(self.r278),'--r265',str(self.r265),'--output',str(self.output)])

    def test_missing_owner_archives_refused_before_output(self):
        with self.assertRaisesRegex(ValueError,'R290_PRIVATE_PINNED_INPUT_REFUSED R278'):
            impl.main(['--r278',str(self.r278),'--r265',str(self.r265),'--output',str(self.output)])
        self.assertFalse(self.output.exists())

    def test_wrong_archive_refused_before_output(self):
        self.r278.write_bytes(b'wrong-r278')
        self.r265.write_bytes(b'wrong-r265')
        with self.assertRaisesRegex(ValueError,'R290_PRIVATE_PINNED_INPUT_REFUSED R278'):
            impl.main(['--r278',str(self.r278),'--r265',str(self.r265),'--output',str(self.output)])
        self.assertFalse(self.output.exists())

    def test_missing_output_parent_refused(self):
        with self.assertRaisesRegex(FileNotFoundError,'R290_OUTPUT_PARENT_UNSAFE_OR_MISSING'):
            impl.main(['--r278',str(self.r278),'--r265',str(self.r265),
                       '--output',str(self.home/'missing-parent'/'private-output')])

    def test_hash_streaming(self):
        content=b'checksum-safe-fixture'
        self.r278.write_bytes(content)
        self.assertEqual(impl.digest(self.r278),hashlib.sha256(content).hexdigest())

    def test_real_client_regression_exists(self):
        java=JAVA_TEST.read_text()
        self.assertIn('R290_FOREIGN_OBJECT_ID_ACCEPTED',java)
        self.assertIn('R290_FOREIGN_OBJECT_ID_GUARD_PASS',java)
        self.assertIn('R278_AUTHORITY_FULL_REAL_CLIENT_PASS',java)
        self.assertIn('for (int option : menuOptions)',java)

    def test_no_private_game_binary_in_public_r290_paths(self):
        for directory in [ROOT/'tests/java/r290',ROOT/'tests/python/r290',ROOT/'tools/recovery/r290']:
            self.assertFalse(list(directory.rglob('*.jar')))
            self.assertFalse(list(directory.rglob('*.class')))
            self.assertFalse(list(directory.rglob('*.dat')))

    def test_no_network_or_install_invocation_in_builder(self):
        source=SCRIPT.read_text()
        for marker in ('urllib.request','requests.get','http.client','rs.gui.Launcher','powershell.exe'):
            self.assertNotIn(marker,source)

if __name__=='__main__':
    unittest.main(verbosity=2)

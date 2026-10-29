"""Original-independent fail-closed tests for the public R310 build recipe.

Never supplies, loads, compiles or executes game source or a client binary.
"""
from pathlib import Path
import importlib.util
import unittest


PUBLIC_BUILDER = Path(__file__).resolve().parents[1] / 'tools' / 'recovery' / 'r310' / 'rebuild_r310_from_pinned.py'


def module_from(path):
    spec = importlib.util.spec_from_file_location('toy_r310_builder', path)
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    return imported


class R310SourceOnlySafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = module_from(PUBLIC_BUILDER)

    def test_rejects_unknown_preimage_before_parsing_java(self):
        for candidate in (b'', b'not a Scene.java source', b'\xff\x00\x80'):
            with self.subTest(candidate=candidate[:8]):
                with self.assertRaisesRegex(ValueError, 'EXACT_R309_SCENE_PREIMAGE'):
                    self.recipe.patch_scene(candidate)

    def test_rejects_occupied_output_before_any_game_source_read(self):
        with self.assertRaisesRegex(ValueError, 'R310_OUTPUT_MUST_BE_NEW'):
            self.recipe.main(['--r278', 'deliberately-nonexistent-old.zip',
                              '--r265', 'deliberately-nonexistent-new.zip',
                              '--output', str(Path(__file__).resolve())])

    def test_pinned_hashes_have_expected_sha256_shape(self):
        for name in ('PIN_R309_BUILDER', 'PIN_R309_SCENE', 'PIN_R310_SCENE', 'PIN_R310_JAR'):
            value = getattr(self.recipe, name)
            self.assertEqual(len(value), 64)
            self.assertTrue(all(c in '0123456789abcdef' for c in value))
        self.assertNotEqual(self.recipe.PIN_R309_SCENE, self.recipe.PIN_R310_SCENE)


if __name__ == '__main__':
    unittest.main(verbosity=2)

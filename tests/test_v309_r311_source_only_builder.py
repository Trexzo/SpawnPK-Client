"""Pure source-only R311 rebuild-admission tests; no original game code/binaries."""
import importlib.util
from pathlib import Path
import unittest

BUILDER = Path(__file__).resolve().parents[1] / "tools/recovery/r311/rebuild_r311_from_pinned.py"

def load():
    spec = importlib.util.spec_from_file_location("r311_public_builder", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class R311FailClosedBuildTests(unittest.TestCase):
    def test_rejects_wrong_source_before_any_java_operations(self):
        b = load()
        for data in (b"", b"synthetic source", b"\x00\xff"):
            with self.subTest(candidate=data):
                with self.assertRaisesRegex(ValueError,"PREIMAGE_SHA_MISMATCH"):
                    b.patch_scene(data)

    def test_output_refuses_existing_file_before_loading_private_inputs(self):
        b = load()
        with self.assertRaisesRegex(ValueError,"R311_OUTPUT_MUST_BE_NEW"):
            b.main(["--r278","absent-r278.zip","--r265","absent-r265.zip",
                    "--output",str(BUILDER)])

    def test_source_and_output_hashes_are_explicit_distinct_sha256_pins(self):
        b = load()
        values = [b.OLD_SCENE,b.NEW_SCENE,b.NEW_JAR]
        for value in values:
            self.assertEqual(64,len(value))
            self.assertTrue(all(c in "0123456789abcdef" for c in value))
        self.assertEqual(len(set(values)),3)
        self.assertEqual(len(b.PREVIOUS_GIT_BLOB),40)

if __name__=="__main__":
    unittest.main(verbosity=2)

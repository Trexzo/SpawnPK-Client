"""Synthetic byte-free validation of R197 approved dependency JARs."""
import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from dependency_closure_r197 import inspect

class ClosureTests(unittest.TestCase):
    def test_valid_jar_and_pinned_hash(self):
        with tempfile.TemporaryDirectory() as d:
            jar = Path(d)/"external.jar"
            with zipfile.ZipFile(jar,"w") as z:
                z.writestr("org/example/Api.class",b"synthetic")
            sha=hashlib.sha256(jar.read_bytes()).hexdigest()
            result=inspect([jar],{"external.jar":sha})
            self.assertEqual(1,result["unique_binary_classes"])
            with self.assertRaisesRegex(ValueError,"SHA mismatch"):
                inspect([jar],{"external.jar":"0"*64})

    def test_client_binary_namespace_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            jar=Path(d)/"external.jar"
            with zipfile.ZipFile(jar,"w") as z:
                z.writestr("rs/client/Secret.class",b"synthetic")
            sha=hashlib.sha256(jar.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,"client namespace"):
                inspect([jar],{"external.jar":sha})

    def test_duplicate_classes_reported(self):
        with tempfile.TemporaryDirectory() as d:
            paths=[]
            for n in ("a.jar","b.jar"):
                jar=Path(d)/n
                with zipfile.ZipFile(jar,"w") as z:
                    z.writestr("org/example/Shared.class",b"synthetic")
                paths.append(jar)
            pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            report=inspect(paths,pins)
            self.assertEqual(["a.jar","b.jar"],report["duplicate_binary_classes"]["org.example.Shared"])

if __name__=="__main__":
    unittest.main()

"""Standalone, original-game-free Java9 synthetic family enum checks.

Completely invented fixture names and values, not recovered v311 game source.
Public checks model compiler isolation and altered-code refusal only.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tempfile
import unittest

VALUES = {
    "Phase": ("WARMUP", "ACTIVE", "RESTING"),
    "Side": ("FRONT", "BACK"),
    "Panel": ("ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX"),
}


def run(command):
    p = subprocess.run(command, capture_output=True, text=True, timeout=50)
    if p.returncode:
        raise AssertionError(f"command failed: {command[0]}: {p.stderr[-1000:]}")
    return p.stdout


def compile_island(root, swap=False):
    sources = root / "source" / "synthetic" / "isolated"
    sources.mkdir(parents=True)
    for name, members in VALUES.items():
        original = list(members)
        if swap and name == "Phase":
            original[0], original[1] = original[1], original[0]
        (sources / f"{name}.java").write_text(
            f"package synthetic.isolated; public enum {name} {{ "
            + ",".join(original) + "; }\n",
            encoding="utf-8",
        )
    classes = root / "classes"
    classes.mkdir()
    emptycp = root / "empty-classpath"
    emptycp.mkdir()
    emptysp = root / "empty-sourcepath"
    emptysp.mkdir()
    run(["javac", "--release", "9", "-proc:none", "-g:none", "-encoding", "UTF-8",
         "-classpath", str(emptycp), "-sourcepath", str(emptysp), "-d", str(classes),
         *map(str, sorted(sources.glob("*.java")))])
    return classes


@unittest.skipUnless(all(shutil.which(x) for x in ("javac", "java", "javap")),
                     "JDK required")
class SyntheticThreeEnumIslands(unittest.TestCase):
    def test_isolated_builds_are_deterministic_and_have_no_extra_classes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            first = compile_island(root / "first")
            second = compile_island(root / "second")
            names = {f"synthetic/isolated/{name}.class" for name in VALUES}
            observed = {p.relative_to(first).as_posix() for p in first.rglob("*.class")}
            self.assertEqual(observed, names)
            for name in names:
                a = (first / name).read_bytes()
                b = (second / name).read_bytes()
                self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())
                self.assertEqual(a[:8], bytes.fromhex("cafebabe00000035"))
            for name, values in VALUES.items():
                declared = run(["javap", "-p", "-c", "-classpath", str(first),
                                f"synthetic.isolated.{name}"])
                self.assertIn("values()", declared)
                self.assertIn("valueOf(java.lang.String)", declared)
                self.assertIn("clone", declared)
                for value in values:
                    self.assertIn("String " + value, declared)

    def test_repinned_source_and_class_hashes_cannot_mask_reordered_code(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            original = compile_island(root / "original")
            altered = compile_island(root / "altered", swap=True)
            source_a = (root / "original/source/synthetic/isolated/Phase.java").read_bytes()
            source_b = (root / "altered/source/synthetic/isolated/Phase.java").read_bytes()
            class_a = (original / "synthetic/isolated/Phase.class").read_bytes()
            class_b = (altered / "synthetic/isolated/Phase.class").read_bytes()
            self.assertNotEqual(hashlib.sha256(source_a).digest(), hashlib.sha256(source_b).digest())
            self.assertNotEqual(hashlib.sha256(class_a).digest(), hashlib.sha256(class_b).digest())
            # Both hashes are consistently repinned to their respective candidates.
            manifests = [{"source_sha": hashlib.sha256(s).hexdigest(),
                          "class_sha": hashlib.sha256(c).hexdigest()}
                         for s, c in ((source_a, class_a), (source_b, class_b))]
            self.assertTrue(all(manifests[i]["source_sha"] == hashlib.sha256(s).hexdigest()
                                and manifests[i]["class_sha"] == hashlib.sha256(c).hexdigest()
                                for i, (s, c) in enumerate(((source_a, class_a), (source_b, class_b)))))
            left = run(["javap", "-p", "-s", "-c", "-classpath", str(original),
                        "synthetic.isolated.Phase"])
            right = run(["javap", "-p", "-s", "-c", "-classpath", str(altered),
                         "synthetic.isolated.Phase"])
            self.assertNotEqual(left, right, "repinned byte hashes are not original-code proof")
            for name in ("Side", "Panel"):
                path = f"synthetic/isolated/{name}.class"
                self.assertEqual((original / path).read_bytes(), (altered / path).read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)

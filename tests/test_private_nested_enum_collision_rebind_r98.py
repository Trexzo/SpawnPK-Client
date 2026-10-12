"""R98: real Java 9 collision prototype and fail-closed original/binary acceptance."""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_nested_enum_collision_rebind import (
    CollisionRebindError, rebind_classfile, rebind_private_fourth_enum,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "javac/java required")
class EnumNameCollisionRebindTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source" / "p"
        self.source.mkdir(parents=True)
        self.classes = self.root / "classes"
        self.classes.mkdir()
        self.original = self.root / "original-private-fixture.jar"
        self.candidate = self.root / "compiled-private-fixture.jar"
        self.out = self.root / "accept"

    def compile(self, extra=""):
        source = (
            "package p; public final class Owner {"
            "public enum Placeholder { ALPHA(1), BETA(2); "
            "private final int weight; Placeholder(int n){weight=n;}"
            "public int getWeight(){return weight;} " + extra + "}"
            "public enum One {A,B} public enum Two {C,D}"
            "public enum Three {E,F}"
            "}"
        )
        (self.source / "Owner.java").write_text(source, encoding="utf-8")
        process = subprocess.run(
            ["javac", "--release", "9", "-proc:none", "-g:none",
             "-d", str(self.classes), str(self.source / "Owner.java")],
            capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        with ZipFile(self.candidate, "w") as z:
            for p in self.classes.rglob("*.class"):
                z.write(p, p.relative_to(self.classes).as_posix())

        # Synthetic-only baseline: make a colliding JVM identity independently,
        # so end-to-end R95 can compare an original/candidate with identical code.
        with ZipFile(self.candidate) as zin, ZipFile(self.original, "w") as out:
            for info in zin.infolist():
                data, _ = rebind_classfile(zin.read(info), "p/Owner", "Placeholder")
                name = (info.filename.replace("Owner$Placeholder.class",
                                              "Owner$Owner.class"))
                out.writestr(name, data)

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def run_gate(self, *, original_pin=None, candidate_pin=None):
        return rebind_private_fourth_enum(
            self.original, self.candidate, "p/Owner.class", "Placeholder",
            self.out, original_sha256=original_pin or self.digest(self.original),
            candidate_sha256=candidate_pin or self.digest(self.candidate),
        )

    def test_synthetic_original_four_enum_R95_acceptance(self):
        self.compile()
        result = self.run_gate()
        self.assertTrue(result["four_nested_enum_R95_parity_passed"])
        self.assertFalse(result["java_authorial_source_identity_proven"])
        self.assertFalse(result["whole_client_runtime_equivalence_certified"])
        rebound = self.out / "candidate-rebound.private.jar"
        self.assertEqual(self.digest(rebound), self.digest(self.original))
        with ZipFile(rebound) as z:
            self.assertIn("p/Owner$Owner.class", z.namelist())
            self.assertNotIn("p/Owner$Placeholder.class", z.namelist())

    def test_jvm_reflection_and_enum_behavior_after_rebind(self):
        self.compile()
        self.run_gate()
        probe = self.source / "Probe.java"
        probe.write_text(
            'package p; public class Probe {'
            'public static void main(String[] args)throws Exception {'
            'Class<?> o=Class.forName("p.Owner");'
            'Class<?> n=Class.forName("p.Owner$Owner");'
            'if(n.getEnclosingClass()!=o || !n.getSimpleName().equals("Owner"))'
            'throw new Error("metadata");'
            'Object e=Enum.valueOf((Class)n,"BETA");'
            'if((int)n.getMethod("getWeight").invoke(e)!=2)'
            'throw new Error("semantics");'
            '}}', encoding="utf-8")
        folder = self.root / "probe"
        folder.mkdir()
        proc = subprocess.run(
            ["javac", "--release", "9", "-proc:none",
             "-d", str(folder), str(probe)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        cp = str(folder) + __import__("os").pathsep + str(
            self.out / "candidate-rebound.private.jar")
        proc = subprocess.run(["java", "-cp", cp, "p.Probe"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_original_sha_mismatch_vetoes_output(self):
        self.compile()
        with self.assertRaisesRegex(CollisionRebindError,
                                    "SOURCE_JAR_SHA256_MISMATCH"):
            self.run_gate(original_pin="0" * 64)
        self.assertFalse(self.out.exists())

    def test_candidate_literal_reusing_surrogate_name_vetoes_rewrite(self):
        self.compile('public String debug(){return "Placeholder";}')
        with ZipFile(self.candidate) as z:
            raw = z.read("p/Owner$Placeholder.class")
        with self.assertRaisesRegex(CollisionRebindError,
                                    "SURROGATE_NAME_REUSED_AS_STRING_LITERAL"):
            rebind_classfile(raw, "p/Owner", "Placeholder")
        self.assertFalse(self.out.exists())

    def test_original_binary_drift_vetoes_parity(self):
        self.compile()
        src = self.source / "Owner.java"
        src.write_text(src.read_text().replace(
            "ALPHA(1), BETA(2)", "ALPHA(1), BETA(3)"), encoding="utf-8")
        proc = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(self.classes), str(src)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with ZipFile(self.candidate, "w") as z:
            for p in self.classes.rglob("*.class"):
                z.write(p, p.relative_to(self.classes).as_posix())
        with self.assertRaisesRegex(CollisionRebindError,
                                    "R95_ORIGINAL_FOUR_ENUM_PARITY_NOT_ACCEPTED"):
            self.run_gate()
        self.assertFalse(self.out.exists())

    def test_missing_candidate_fourth_nested_entry_vetoes(self):
        self.compile()
        replacement = self.root / "missing.jar"
        with ZipFile(self.candidate) as zin, ZipFile(replacement, "w") as zout:
            for i in zin.infolist():
                if i.filename != "p/Owner$Placeholder.class":
                    zout.writestr(i, zin.read(i))
        self.candidate = replacement
        with self.assertRaisesRegex(CollisionRebindError,
                                    "REQUIRED_EXACT_ORIGINAL_COLLISION"):
            self.run_gate()
        self.assertFalse(self.out.exists())

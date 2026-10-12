"""R105: compile 4 Java9 enums, simulate original obfuscated accessors, pass exact R95."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.private_nested_enum_collision_rebind import rebind_classfile
from spk_recovery.private_original_fourth_enum_accessors import _accessors
from spk_recovery.private_original_synthetic_accessor_rebind_r105 import (
    SyntheticAccessorMemberRebindError,
    assemble_original_accessor_and_r95_candidate,
    rebind_member_references,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "Java9-compatible javac/java required")
class OriginalFourthEnumMemberRenamingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "original.jar"
        self.candidate = self.root / "candidate.jar"
        self.output = self.root / "accepted"

    @staticmethod
    def hash(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def compile_fixture(self, *, candidate_bad_constant=False,
                        missing_other_nested=False):
        orig = self.root / "original-src" / "p"
        orig.mkdir(parents=True)
        (orig / "Owner.java").write_text(
            "package p; public final class Owner {"
            "public enum Placeholder {"
            ' ALPHA("One","Two"), BETA("Three","Four");'
            "private String x,y;"
            "Placeholder(String a,String b){x=a;y=b;}"
            "public String first(){return x;}"
            "public String second(){return y;}"
            "}"
            "public enum One{ A,B }"
            "public enum Two{ C }"
            "public enum Three{ D }"
            "public java.util.Map.Entry<String,String> foreignOne;"
            "public Foreign.Nested foreignTwo;"
            "public static String readX(Placeholder e){return e.x;}"
            "public static String readY(Placeholder e){return e.y;}"
            "}", encoding="utf-8")
        (orig / "Foreign.java").write_text(
            "package p; public class Foreign {public static class Nested{}}",
            encoding="utf-8")
        original_classes = self.root / "original-classes"
        original_classes.mkdir()
        process = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(original_classes),
             str(orig / "Owner.java"), str(orig / "Foreign.java")],
            capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        interim = self.root / "preoriginal.jar"
        with ZipFile(interim, "w") as z:
            for path in sorted(original_classes.rglob("*.class")):
                z.write(path, path.relative_to(original_classes).as_posix())
        shape = profile_jar_class(interim, "p/Owner$Placeholder.class")
        byfield = _accessors(shape)
        self.assertEqual(len(byfield), 2)
        aliases = {m["name"]: "original_" + field
                   for field, m in byfield.items()}
        with ZipFile(interim) as files, ZipFile(self.original, "w") as out:
            for entry in files.infolist():
                name = entry.filename
                data, _, _ = rebind_member_references(
                    files.read(entry), target_owner="p/Owner$Placeholder",
                    name_aliases=aliases,
                    rewrite_declarations=(name == "p/Owner$Placeholder.class"),
                )
                data, _ = rebind_classfile(
                    data, "p/Owner", "Placeholder")
                if name == "p/Owner$Placeholder.class":
                    entry.filename = "p/Owner$Owner.class"
                out.writestr(entry, data)

        cand = self.root / "candidate-src" / "p"
        cand.mkdir(parents=True)
        (cand / "Owner.java").write_text(
            "package p; public final class Owner {"
            "public enum Surrogate {"
            ' ALPHA("One","Two"), ' +
            ('GAMMA' if candidate_bad_constant else 'BETA') +
            '("Three","Four");'
            "private String x,y;"
            "Surrogate(String a,String b){x=a;y=b;}"
            "public String first(){return x;}"
            "public String second(){return y;}"
            "}"
            "public enum One{ A,B }"
            "public enum Two{ C }"
            "public enum Three{ D }"
            "public static String readX(Surrogate e){return e.x;}"
            "public static String readY(Surrogate e){return e.y;}"
            "}", encoding="utf-8")
        out_classes = self.root / "candidate-classes"
        out_classes.mkdir()
        process = subprocess.run(
            ["javac", "--release", "9", "-g:none", "-proc:none",
             "-d", str(out_classes), str(cand / "Owner.java")],
            capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        with ZipFile(self.candidate, "w") as z:
            for path in sorted(out_classes.rglob("*.class")):
                name = path.relative_to(out_classes).as_posix()
                if missing_other_nested and name == "p/Owner$One.class":
                    continue
                z.writestr(name, path.read_bytes())

    def gate(self, *, original_pin=None, candidate_pin=None):
        return assemble_original_accessor_and_r95_candidate(
            self.original, self.candidate, "p/Owner.class",
            "Surrogate", self.output,
            original_sha256=original_pin or self.hash(self.original),
            candidate_sha256=candidate_pin or self.hash(self.candidate),
        )

    def test_actual_java9_original_like_accessor_aliases_and_full_R95_pass(self):
        self.compile_fixture()
        proof = self.gate()
        self.assertTrue(proof["all_four_original_nested_enums_R95_passed"])
        self.assertEqual(proof["source_javac_synthetic_method_declarations_rebound"], 2)
        self.assertGreaterEqual(
            proof["candidate_original_accessor_methodref_callsites_rebound"], 2)
        self.assertEqual(proof["exact_original_private_field_accessor_aliases"], 2)
        self.assertTrue(proof["six_original_owner_InnerClasses_rows_equal"])
        self.assertFalse(proof["R97_complete_126field_10method_owner_certified"])
        accepted = self.output / "all-four-R95-r105-accepted.private.jar"
        self.assertTrue(accepted.is_file())
        probe = self.root / "Probe.java"
        probe.write_text(
            'package p;public class Probe{public static void main(String[]x)'
            'throws Exception {'
            'Class<?> e=Class.forName("p.Owner$Owner");'
            'Class<?> o=Class.forName("p.Owner");'
            'Object a=Enum.valueOf((Class)e,"ALPHA");'
            'Object b=Enum.valueOf((Class)e,"BETA");'
            'java.lang.reflect.Method m=o.getMethod("readX",e);'
            'java.lang.reflect.Method n=o.getMethod("readY",e);'
            'if(!m.invoke(null,a).equals("One"))throw new Error("x");'
            'if(!n.invoke(null,b).equals("Four"))throw new Error("y");'
            '}}', encoding="utf-8")
        cp = self.root / "probe-classes"
        cp.mkdir()
        p = subprocess.run(
            ["javac", "--release", "9", "-proc:none",
             "-d", str(cp), str(probe)],
            capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        import os
        run = subprocess.run(
            ["java", "-cp", str(cp) + os.pathsep + str(accepted), "p.Probe"],
            capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_candidate_constant_drift_vetoed_by_r95(self):
        self.compile_fixture(candidate_bad_constant=True)
        with self.assertRaisesRegex(
            SyntheticAccessorMemberRebindError,
            "R104_R95_ALL_FOUR_PRIVATE_ENUM_ACCEPTANCE_FAILED",
        ):
            self.gate()
        self.assertFalse(self.output.exists())

    def test_wrong_original_jar_pin_no_promotion(self):
        self.compile_fixture()
        with self.assertRaisesRegex(
            SyntheticAccessorMemberRebindError, "SHA256_MISMATCH"
        ):
            self.gate(original_pin="0" * 64)
        self.assertFalse(self.output.exists())

    def test_missing_one_other_nested_enum_fail_closed(self):
        self.compile_fixture(missing_other_nested=True)
        with self.assertRaisesRegex(
            SyntheticAccessorMemberRebindError,
            "R104_R95_ALL_FOUR_PRIVATE_ENUM_ACCEPTANCE_FAILED",
        ):
            self.gate()
        self.assertFalse(self.output.exists())

    def test_same_target_name_for_two_accessors_rejected(self):
        self.compile_fixture()
        with ZipFile(self.candidate) as z:
            data = z.read("p/Owner$Surrogate.class")
        with self.assertRaisesRegex(
            SyntheticAccessorMemberRebindError,
            "ALIASES_NOT_TWO_UNIQUE_SAFE",
        ):
            rebind_member_references(
                data, target_owner="p/Owner$Surrogate",
                name_aliases={"access$000": "same", "access$100": "same"},
                rewrite_declarations=True)

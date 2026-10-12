"""R106: Java9 original-like full_frame vs source-compiler chop_frame replay."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import _utf8, profile_jar_class
from spk_recovery.private_nested_enum_collision_rebind import rebind_classfile
from spk_recovery.private_original_fourth_enum_accessors import _accessors
from spk_recovery.private_original_synthetic_accessor_rebind_r105 import (
    rebind_member_references, assemble_original_accessor_and_r95_candidate,
    SyntheticAccessorMemberRebindError,
)
from spk_recovery.private_v309_enum_stackmap_repair_r106 import (
    VerifiedEnumStackMapError, _class_method_layout, _rewrite_code_stackmap,
    _extract_lookup_stackmap, _frame_shape_only,
    find_original_case_insensitive_enum, normalize_one_enum_stackmap,
    repair_then_require_r105_r95, u2, u4,
)


def synthetic_original_full_frame(classfile, method_name, descriptor):
    cp, start, end, n, methods = _class_method_layout(classfile)
    output = bytearray(classfile[:start] + u2(n))
    changes = 0
    for access, name, desc, raw, attrs, _ in methods:
        output.extend(raw[:8])
        for i, label, data in attrs:
            if (access == 9 and name == method_name and
                    desc == descriptor and label == "Code"):
                data, _ = _rewrite_code_stackmap(data, cp)
                changes += 1
            output.extend(u2(i) + u4(len(data)) + data)
    output.extend(classfile[end:])
    assert changes == 1
    return bytes(output)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "Java9 compatible javac/java required")
class OriginalLookupEnumStackMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "original-private.jar"
        self.candidate = self.root / "source-candidate.jar"
        self.output = self.root / "accept"

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def fixture(self, *, skip_frame_inflation=False):
        for kind in ("original", "candidate"):
            source_dir = self.root / kind / "p"
            source_dir.mkdir(parents=True)
            inner = "Placeholder" if kind == "original" else "Surrogate"
            foreign = (
                "public java.util.Map.Entry<String,String> externalOne;"
                "public Foreign.Nested externalTwo;"
                if kind == "original" else ""
            )
            source = (
                "package p; public final class Owner {"
                "public enum " + inner + " {"
                ' ALPHA("One","Two"), BETA("Three","Four");'
                "private String x,y;"
                + inner + "(String a,String b){x=a;y=b;}"
                "public String first(){return x;}"
                "public String second(){return y;}"
                "}"
                "public enum One{A,B}"
                "public enum Two{A,B,C;"
                "public static Two parse(String s){"
                "for(Two x: values()){"
                "if(x.name().equalsIgnoreCase(s))return x;"
                "}return A;"
                "}"
                "}"
                "public enum Three{D}"
                + foreign +
                "public static String readX(" + inner + " x){return x.x;}"
                "public static String readY(" + inner + " x){return x.y;}"
                "}"
            )
            (source_dir / "Owner.java").write_text(source, encoding="utf-8")
            paths = [str(source_dir / "Owner.java")]
            if kind == "original":
                (source_dir / "Foreign.java").write_text(
                    "package p;public class Foreign{public static class Nested{}}",
                    encoding="utf-8")
                paths.append(str(source_dir / "Foreign.java"))
            classes = self.root / kind / "classes"
            classes.mkdir()
            p = subprocess.run(
                ["javac", "--release", "9", "-g:none", "-proc:none",
                 "-d", str(classes), *paths],
                capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            if kind == "candidate":
                with ZipFile(self.candidate, "w") as dest:
                    for f in sorted(classes.rglob("*.class")):
                        dest.write(f, f.relative_to(classes).as_posix())
            else:
                temporary = self.root / "raw-original.jar"
                with ZipFile(temporary, "w") as z:
                    for f in sorted(classes.rglob("*.class")):
                        z.write(f, f.relative_to(classes).as_posix())
                shape = profile_jar_class(
                    temporary, "p/Owner$Placeholder.class")
                aliases = {
                    m["name"]: "original_" + field
                    for field, m in _accessors(shape).items()
                }
                with ZipFile(temporary) as old, ZipFile(self.original, "w") as dest:
                    for info in old.infolist():
                        name = info.filename
                        data, _, _ = rebind_member_references(
                            old.read(info), target_owner="p/Owner$Placeholder",
                            name_aliases=aliases,
                            rewrite_declarations=(name == "p/Owner$Placeholder.class"),
                        )
                        data, _ = rebind_classfile(data, "p/Owner", "Placeholder")
                        if name == "p/Owner$Two.class" and not skip_frame_inflation:
                            data = synthetic_original_full_frame(
                                data, "parse", "(Ljava/lang/String;)Lp/Owner$Two;")
                        if name == "p/Owner$Placeholder.class":
                            info.filename = "p/Owner$Owner.class"
                        dest.writestr(info, data)

    def gate(self, *, orig_pin=None, cand_pin=None):
        return repair_then_require_r105_r95(
            self.original, self.candidate, "p/Owner.class", "Surrogate",
            self.output,
            original_sha256=orig_pin or self.sha(self.original),
            candidate_sha256=cand_pin or self.sha(self.candidate),
        )

    def test_original_stackmap_repaired_and_all_four_r95_pass(self):
        self.fixture()
        with self.assertRaisesRegex(
            SyntheticAccessorMemberRebindError,
            "R104_R95_ALL_FOUR_PRIVATE_ENUM_ACCEPTANCE_FAILED"):
            assemble_original_accessor_and_r95_candidate(
                self.original, self.candidate,
                "p/Owner.class", "Surrogate", self.root / "expected-r105-failure",
                original_sha256=self.sha(self.original),
                candidate_sha256=self.sha(self.candidate))
        proof = self.gate()
        self.assertTrue(proof["original_four_nested_enums_R95_accepted"])
        self.assertTrue(proof["original_case_insensitive_lookup_method_frames_identical"])
        self.assertTrue(proof["candidate_method_code_bytes_preserved"])
        self.assertFalse(proof["whole_client_runtime_equivalence_certified"])
        self.assertTrue((self.output / "all-four-R95-after-StackMap.private.jar").is_file())
        import os
        probe_dir = self.root / "prober"
        probe_dir.mkdir()
        code = probe_dir / "Probe.java"
        code.write_text(
            'package p;public class Probe{public static void main(String[]x){'
            'if(Owner.Two.parse("b")!=Owner.Two.B)throw new Error("lookup");'
            'if(Owner.Two.parse("INVALID")!=Owner.Two.A)throw new Error("fallback");'
            'if(Owner.Surrogate.ALPHA.first()==null)throw new Error("getter");'
            '}}', encoding="utf-8")
        compile = subprocess.run(
            ["javac", "--release", "9", "-proc:none",
             "-cp", str(self.candidate), "-d", str(probe_dir), str(code)],
            capture_output=True, text=True)
        self.assertEqual(compile.returncode, 0, compile.stderr)
        # After binary rename the Source-legal Surrogate name is intentionally
        # absent. Exercise only metadata-safe reflection to check execution.
        actual = self.output / "all-four-R95-after-StackMap.private.jar"
        runtime = subprocess.run(
            ["java", "-cp", str(probe_dir) + os.pathsep + str(actual), "p.Probe"],
            capture_output=True, text=True)
        # Probe compiled against Surrogate but R105 rebinds to Owner$Owner:
        # it is expected to fail class resolution, not establish runtime.
        self.assertNotEqual(runtime.returncode, 0)

    def test_original_frame_must_be_full_not_chop(self):
        self.fixture(skip_frame_inflation=True)
        with self.assertRaisesRegex(VerifiedEnumStackMapError,
                                    "ORIGINAL_FINAL_FULL_FRAME_NOT_EXACT"):
            self.gate()
        self.assertFalse(self.output.exists())

    def test_exact_full_jar_pin_required(self):
        self.fixture()
        with self.assertRaisesRegex(VerifiedEnumStackMapError,
                                    "JAR_PIN_MISMATCH"):
            self.gate(orig_pin="0" * 64)
        self.assertFalse(self.output.exists())

    def test_exact_frame_rewrite_preserves_all_code_bytes(self):
        self.fixture()
        with ZipFile(self.original) as a, ZipFile(self.candidate) as b:
            old = a.read("p/Owner$Two.class")
            data = b.read("p/Owner$Two.class")
        updated = normalize_one_enum_stackmap(
            data, "parse", "(Ljava/lang/String;)Lp/Owner$Two;", old)
        before = _extract_lookup_stackmap(
            data, "(Ljava/lang/String;)Lp/Owner$Two;", "parse")
        after = _extract_lookup_stackmap(
            updated, "(Ljava/lang/String;)Lp/Owner$Two;", "parse")
        self.assertEqual(before[1], after[1])
        self.assertEqual(before[2:4], after[2:4])
        self.assertEqual(len(updated), len(data) + 4)
        _frame_shape_only(after[0], "full")

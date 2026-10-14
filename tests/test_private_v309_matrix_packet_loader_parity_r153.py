"""R153: source-only original Packet-dependent matrix constructor & loader tests."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_matrix_packet_loader_parity_r153 import (
    PrivateMatrixLoaderR153Error, verify_private_original_matrix_packet_loader,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required for source-only linked game owner fixture")
class R153OriginalMatrixLoaderSources(unittest.TestCase):
    def setUp(self):
        owner = tempfile.TemporaryDirectory()
        self.addCleanup(owner.cleanup)
        self.root = Path(owner.name)
        self.matrix_owner = "ext/Matrix"
        self.support_sources = {
            "rs/Buffer.java": (
                "package rs;\npublic class Buffer {\n"
                " public int read16() { return 42; }\n"
                " public float readFloat() { return 4f; }\n"
                "}\n"),
            "ext/Rotation.java": (
                "package ext;\npublic class Rotation {\n"
                " public Rotation() {}\n"
                " public void x(float x) { System.out.print(0); }\n"
                " public void y(float y) { System.out.print(0); }\n"
                " public void z(float z) { System.out.print(0); }\n"
                " public void translate(float x,float y,float z) { }\n"
                "}\n"),
            "ext/Decode.java": (
                "package ext;\npublic class Decode {\n"
                " public static float fromShort(int value) {return value * 0.5f;}\n"
                "}\n"),
        }
        self.owner_source = self.matrix_java(extra="original")
        self.original = self.original_jar()
        self.donor = self.archive(
            "private-matrix-donor.zip",
            {self.matrix_owner + ".java": self.matrix_java(extra="donor")})
        self.support = self.archive(
            "three-private-support-stubs.zip", self.stub_support())
        self.selection = self.root / "two-method-selection.json"
        self.selection.write_text(json.dumps([
            {"name": "<init>", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "read", "descriptor": "(Lrs/Buffer;Z)V"}
        ]), encoding="utf-8")

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def matrix_java(self, *, extra, transform_call="this.apply(r);"):
        return (
            "package ext;\npublic final class Matrix {\n"
            " public float[] values;\n"
            " public Matrix(rs.Buffer input, boolean transformed) {\n"
            "  this.values = new float[16];\n"
            "  this.read(input, transformed);\n"
            " }\n"
            " void read(rs.Buffer input, boolean transformed) {\n"
            "  if (transformed) {\n"
            "   ext.Rotation r = new ext.Rotation();\n"
            "   r.x(ext.Decode.fromShort(input.read16()));\n"
            "   r.y(ext.Decode.fromShort(input.read16()));\n"
            "   r.z(ext.Decode.fromShort(input.read16()));\n"
            "   r.translate((float) input.read16(), (float) input.read16(), "
            "(float) input.read16());\n"
            f"   {transform_call}\n"
            "  } else {\n"
            "   for(int i=0; i<16; i++) this.values[i] = input.readFloat();\n"
            "  }\n"
            " }\n"
            " void apply(ext.Rotation x) {\n" +
            ("   this.values[0] = 1f;\n" if extra == "original"
             else "   this.values[0] = 999f;\n") +
            " }\n"
            "}\n"
        )

    def archive(self, filename, sources):
        target = self.root / filename
        with ZipFile(target, "w") as z:
            for path, body in sorted(sources.items()):
                z.writestr("src/main/java/" + path, body)
        return target

    def stub_support(self):
        return {
            "rs/Buffer.java": (
                "package rs;\npublic class Buffer { "
                "public int read16(){return 0;} "
                "public float readFloat(){return 0f;} }\n"),
            "ext/Rotation.java": (
                "package ext;\npublic class Rotation { "
                "public Rotation() {} "
                "public void x(float f) {} "
                "public void y(float f) {} "
                "public void z(float f) {} "
                "public void translate(float f,float g,float h) {} }\n"),
            "ext/Decode.java": (
                "package ext;\npublic class Decode { "
                "public static float fromShort(int x) {return 0f;} }\n"),
        }

    def original_jar(self):
        classes = self.root / "original-completed"
        classes.mkdir()
        for rel, body in [
            *sorted(self.support_sources.items()),
            (self.matrix_owner + ".java", self.owner_source),
        ]:
            source = self.root / "original-src" / rel
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(body, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("javac"), "--release", "9", "-g:none",
                 "-proc:none", "-classpath", str(classes),
                 "-d", str(classes), str(source)],
                capture_output=True, check=False)
            self.assertEqual(
                0, result.returncode,
                result.stderr.decode("utf-8", errors="replace"))
        jar = self.root / "original-synthetic-game-linked.jar"
        with ZipFile(jar, "w") as z:
            for cls in sorted(classes.rglob("*.class")):
                z.write(cls, cls.relative_to(classes).as_posix())
        return jar

    def prove(self, *, matrix=None, support=None, selection=None):
        matrix = matrix or self.donor
        support = support or self.support
        selection = selection or self.selection
        return verify_private_original_matrix_packet_loader(
            self.original, matrix, support, selection,
            original_sha256=self.sha(self.original),
            matrix_source_sha256=self.sha(matrix),
            support_source_sha256=self.sha(support),
            selection_sha256=self.sha(selection),
            original_owner=self.matrix_owner)

    def test_constructor_and_two_branch_loader_match_original_jvm(self):
        result = self.prove()
        self.assertEqual(2, result["verified_selected_method_count"])
        self.assertEqual(1, result["verified_constructor_count"])
        self.assertEqual(3, result["source_only_supporting_class_count"])
        self.assertGreaterEqual(result["matched_opcode_count"], 40)
        self.assertTrue(result["all_selected_core_method_code_equal"])
        self.assertFalse(result["support_class_bodies_original_equivalence_accepted"])
        self.assertFalse(result["original_game_class_binary_or_jar_on_javac_classpath"])
        self.assertFalse(result["complete_original_matrix_class_source_accepted"])
        self.assertFalse(result["whole_v309_client_source_compilation_accepted"])

    def test_unverified_companion_implementations_are_not_accepted(self):
        stub = dict(self.stub_support())
        stub["rs/Buffer.java"] = stub["rs/Buffer.java"].replace(
            "return 0;", "return 1234;")
        modified = self.archive("different-buffer-behavior.zip", stub)
        result = self.prove(support=modified)
        self.assertTrue(result["all_selected_core_method_code_equal"])
        self.assertFalse(result["support_class_bodies_original_equivalence_accepted"])

    def test_loader_changed_source_instruction_is_rejected(self):
        modified = self.archive(
            "wrong-matrix-load.zip",
            {self.matrix_owner + ".java": self.matrix_java(
                extra="donor",
                transform_call="this.values[0] = 5f;")})
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove(matrix=modified)

    def test_extra_supporting_class_is_not_accepted(self):
        stubs = dict(self.stub_support())
        stubs["ext/Stray.java"] = "package ext; public class Stray {}"
        modified = self.archive("support-extra.zip", stubs)
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove(support=modified)

    def test_wrong_support_class_declaration_is_not_accepted(self):
        stubs = dict(self.stub_support())
        stubs["ext/Decode.java"] = (
            "package ext; public class NotDecode { "
            "public static float fromShort(int x){return 0f;} }"
        )
        modified = self.archive("support-wrong-owner.zip", stubs)
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove(support=modified)

    def test_member_selection_requires_exact_decoder_signature(self):
        selection = self.root / "bad-selection.json"
        selection.write_text(json.dumps([
            {"name": "<init>", "descriptor": "(Lrs/Buffer;Z)V"},
            {"name": "read", "descriptor": "(Lrs/Buffer;)V"}
        ]), encoding="utf-8")
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            self.prove(selection=selection)

    def test_sham_original_hash_is_rejected_before_java_compilation(self):
        with self.assertRaises(PrivateMatrixLoaderR153Error):
            verify_private_original_matrix_packet_loader(
                self.original, self.donor, self.support, self.selection,
                original_sha256="0" * 64,
                matrix_source_sha256=self.sha(self.donor),
                support_source_sha256=self.sha(self.support),
                selection_sha256=self.sha(self.selection),
                original_owner=self.matrix_owner)


if __name__ == "__main__":
    unittest.main()

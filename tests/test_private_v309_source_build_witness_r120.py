"""R120 source provenance: compile fresh Java9 synthetic 126-field owner and enums."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from spk_recovery.private_v309_source_build_witness_r120 import (
    PrivateJava9BuildWitnessR120Error,
    compile_private_java9_owner,
)


@unittest.skipUnless(shutil.which("javac"), "Java compiler unavailable")
class PrivateJava9BuildWitnessR120Tests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.src=self.root/"source"
        self.src.mkdir()
        self.dest=self.root/"built"
        self.owner=self.src/"p"/"Owner.java"
        self.owner.parent.mkdir()
        self.write_source()

    def source(self, *, fields=126, enums=4, valid=True):
        definitions=[
            "public enum "+name+" { A, B; }"
            for name in ("Surrogate","One","Two","Three")[:enums]
        ]
        declarations=["public static boolean f"+str(i)+";" for i in range(fields)]
        # 1 constructor, 8 explicit methods and 1 clinit = 10 JVM methods.
        methods=["public Owner() {}"]+[
            "public static void m"+str(i)+"() {}" for i in range(8)]
        clinit=["static { f0 = true; }"] if valid else ["static { bogus = ; }"]
        return (
            "package p;\npublic final class Owner {\n"
            +"\n".join(declarations+methods+clinit+definitions)
            +"\n}\n"
        )

    def write_source(self, **kwargs):
        self.owner.write_text(self.source(**kwargs),encoding="utf-8")

    def build(self):
        return compile_private_java9_owner(
            self.src,"p/Owner.class","Surrogate",self.dest)

    def test_real_javac9_compiles_owner_126_fields_10_methods_four_enums(self):
        result=self.build()
        self.assertTrue(result["candidate_from_separately_compiled_java_source"])
        self.assertFalse(result["original_v309_bytecode_parity_verified"])
        self.assertFalse(result["r119_original_acceptance_performed"])
        self.assertEqual(result["original_like_owner_fields"],126)
        self.assertEqual(result["original_like_owner_methods"],10)
        self.assertEqual(result["source_nested_enum_count"],4)
        jar=self.dest/"source-compiled.private.jar"
        self.assertEqual(hashlib.sha256(jar.read_bytes()).hexdigest(),
                         result["candidate_sha256"])
        self.assertEqual(len(list(self.dest.iterdir())),2)

    def test_repeated_source_build_has_identical_candidate_digest(self):
        proof=self.build()
        other=self.root/"rebuild"
        rebuilt=compile_private_java9_owner(
            self.src,"p/Owner.class","Surrogate",other)
        self.assertEqual(proof["candidate_sha256"],rebuilt["candidate_sha256"])

    def test_partial_owner_125_fields_is_never_promoted(self):
        self.write_source(fields=125)
        with self.assertRaisesRegex(
                PrivateJava9BuildWitnessR120Error,
                "COMPLETE_126_FIELD_TEN_METHOD_JAVA9_OWNER_REQUIRED"):
            self.build()
        self.assertFalse(self.dest.exists())

    def test_missing_fourth_enum_must_reject(self):
        self.write_source(enums=3)
        with self.assertRaisesRegex(
                PrivateJava9BuildWitnessR120Error,
                "EXACT_FOUR_SOURCE_ENUM_IDENTITIES_REQUIRED"):
            self.build()
        self.assertFalse(self.dest.exists())

    def test_compilation_failure_is_sanitized(self):
        self.write_source(valid=False)
        with self.assertRaisesRegex(
                PrivateJava9BuildWitnessR120Error,
                "JAVA9_SOURCE_COMPILE_FAILED"):
            self.build()
        self.assertFalse(self.dest.exists())

    def test_existing_output_is_not_overwritten(self):
        self.dest.mkdir()
        (self.dest/"preserve.txt").write_text("unchanged",encoding="utf-8")
        with self.assertRaisesRegex(
                PrivateJava9BuildWitnessR120Error,
                "FRESH_PRIVATE_OUTPUT_REQUIRED"):
            self.build()
        self.assertEqual((self.dest/"preserve.txt").read_text(),"unchanged")

    def test_unsafe_owner_path_is_rejected(self):
        with self.assertRaisesRegex(
                PrivateJava9BuildWitnessR120Error,
                "UNSAFE_PRIVATE_OWNER_OR_SURROGATE"):
            compile_private_java9_owner(
                self.src,"../Owner.class","Surrogate",self.dest)
        self.assertFalse(self.dest.exists())

    def test_missing_compiler_is_rejected_without_output(self):
        with self.assertRaisesRegex(
                PrivateJava9BuildWitnessR120Error,
                "JAVA_COMPILER_NOT_FOUND"):
            compile_private_java9_owner(
                self.src,"p/Owner.class","Surrogate",self.dest,
                javac="this-compiler-does-not-exist-r120")
        self.assertFalse(self.dest.exists())

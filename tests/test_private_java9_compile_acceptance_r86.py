"""R86: actual Java 9 compilation -> R66 + R81 acceptance and mutation veto."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_java9_compile_acceptance import (
    PrivateJava9AcceptanceError, compile_and_accept_private_java9,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ActualJava9CompileAcceptanceTests(unittest.TestCase):
    @staticmethod
    def source(root: Path, literal: str):
        file = root / "p" / "Owner.java"
        file.parent.mkdir(parents=True)
        file.write_text(
            'package p; public final class Owner {'
            'private static void restore() {'
            '  java.lang.System.out.println("' + literal + '");'
            '}}', encoding="utf-8")

    @staticmethod
    def original_jar(root: Path) -> tuple[Path,str]:
        origsrc = root / "original_source"
        ActualJava9CompileAcceptanceTests.source(origsrc, "same")
        classes = root / "original_classes"
        classes.mkdir()
        cp = subprocess.run([
            "javac", "--release", "9", "-g:none", "-proc:none",
            "-d", str(classes), str(origsrc / "p" / "Owner.java")
        ], capture_output=True, text=True)
        if cp.returncode:
            raise RuntimeError(cp.stdout + cp.stderr)
        jar = root / "original.jar"
        with ZipFile(jar, "w") as z:
            z.write(classes / "p" / "Owner.class", "p/Owner.class")
        return jar,hashlib.sha256(jar.read_bytes()).hexdigest()

    def test_real_compiler_and_R66_R81_positive_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar,sha=self.original_jar(root)
            src=root/"candidate"
            self.source(src,"same")
            alias=root/"alias.json"
            alias.write_text(json.dumps({"schema_version":1,"aliases":[]}))
            out=root/"private_result"
            proof=compile_and_accept_private_java9(
                jar,"p/Owner.class","restore","()V",
                src,"p/Owner.class","restore","()V",
                alias,out,original_sha256=sha)
            self.assertTrue(proof["R66_original_candidate_structural_parity"])
            self.assertTrue(proof["R81_every_parsed_JVM_operand_parity"])
            self.assertTrue((out/"candidate.private.jar").is_file())
            self.assertFalse(proof["runtime_and_filesystem_side_effects_equivalent"])

    def test_real_compiler_changed_literal_rejected_without_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar,sha=self.original_jar(root)
            src=root/"candidate"
            self.source(src,"changed")
            alias=root/"alias.json"
            alias.write_text(json.dumps({"schema_version":1,"aliases":[]}))
            out=root/"private_result"
            with self.assertRaisesRegex(PrivateJava9AcceptanceError,
                                        "R66_R81_COMPILED_ORIGINAL_METHOD_PARITY_NOT_ACCEPTED"):
                compile_and_accept_private_java9(
                    jar,"p/Owner.class","restore","()V",
                    src,"p/Owner.class","restore","()V",
                    alias,out,original_sha256=sha)
            self.assertFalse(out.exists())

    def test_wrong_whole_original_pin_rejected_before_compilation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar,sha=self.original_jar(root)
            src=root/"candidate"
            self.source(src,"same")
            alias=root/"alias.json"
            alias.write_text(json.dumps({"schema_version":1,"aliases":[]}))
            out=root/"private_result"
            with self.assertRaisesRegex(PrivateJava9AcceptanceError,
                                        "ORIGINAL_COMPLETE_JAR_PIN_MISMATCH"):
                compile_and_accept_private_java9(
                    jar,"p/Owner.class","restore","()V",
                    src,"p/Owner.class","restore","()V",
                    alias,out,original_sha256="0"*64)
            self.assertFalse(out.exists())


if __name__=="__main__":
    unittest.main()

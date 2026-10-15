"""R169: original JVM two Packet methods only; unverified delegate must stay unaccepted."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_packet_partial_methods_r169 import (
    R169OriginalPacketTwoMethodsError,
    verify_original_packet_signed_short_and_float_wrapper,
)


@unittest.skipUnless(shutil.which("javac"), "Java9 source compiler required")
class R169OriginalPacketTwoMethodsTests(unittest.TestCase):
    OWNER="rs/demo/Packet"

    def setUp(self):
        holder=tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root=Path(holder.name)
        self.original=self.original_jar()
        self.source=self.write_source(
            "candidate.zip",self.java_source(real_delegate=False))
        with ZipFile(self.original) as z:
            original_class=z.read(self.OWNER+".class")
        self.class_sha=hashlib.sha256(original_class).hexdigest()
        profile=profile_class_field_accesses(original_class)
        self.instruction_count=sum(
            len(m["instructions"]) for m in profile["methods"]
            if (m["name"],m["descriptor"]) in {
                ("signed16","()I"),("nextFloat","()F")
            })

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def java_source(*,real_delegate=False,incorrect_shift=False,
                    incorrect_float=False):
        shift="7" if incorrect_shift else "8"
        float_body=("return 0f;" if incorrect_float else
                    "return Float.intBitsToFloat(this.raw32());")
        delegate=("return 0x3f800000;" if real_delegate else
                  "return 0;")
        return (
            "package rs.demo;public class Packet{"
            "public byte[] buffer;public int cursor;"
            "public int signed16(){this.cursor+=2;"
            "int value=((this.buffer[this.cursor-2]&255)<<"+shift+")"
            "+(this.buffer[this.cursor-1]&255);"
            "if(value>32767)value-=65536;return value;}"
            "public float nextFloat(){"+float_body+"}"
            "public int raw32(){"+delegate+"}"
            "}")

    def original_jar(self):
        code=self.java_source(real_delegate=True)
        source=self.root/"source-original"/(self.OWNER+".java")
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_text(code)
        classes=self.root/"original-classes"
        classes.mkdir()
        p=subprocess.run(
            [shutil.which("javac"),"--release","9",
             "-g:none","-proc:none","-d",str(classes),str(source)],
            capture_output=True)
        self.assertEqual(0,p.returncode,p.stderr.decode(errors="replace"))
        dest=self.root/"original.jar"
        with ZipFile(dest,"w") as z:
            z.write(classes/(self.OWNER+".class"),self.OWNER+".class")
        return dest

    def write_source(self,name,source):
        archive=self.root/name
        with ZipFile(archive,"w") as z:
            z.writestr("src/main/java/"+self.OWNER+".java",source)
        return archive

    def proof(self,source=None,source_sha=None):
        source=source or self.source
        return verify_original_packet_signed_short_and_float_wrapper(
            self.original,source,
            original_sha256=self.sha(self.original),
            partial_java_sha256=source_sha or self.sha(source),
            original_owner=self.OWNER,
            original_class_sha256=self.class_sha,
            signed_short_method="signed16",
            float_wrapper_method="nextFloat",
            delegated_unrecovered_int_method="raw32",
            byte_array_field="buffer",cursor_field="cursor",
            expected_selected_methods=2,
            expected_jvm_instructions=self.instruction_count)

    def test_two_selected_methods_exact_even_with_different_delegate_body(self):
        report=self.proof()
        self.assertEqual(2,report["selected_original_packet_java_methods"])
        self.assertEqual(self.instruction_count,
                         report["original_jvm_instructions_verified"])
        self.assertTrue(report[
            "original_signed_short_two_byte_method_jvm_code_verified"])
        self.assertFalse(report[
            "float_reader_delegated_method_body_verified"])
        self.assertFalse(report["complete_original_packet_java_class_recovered"])
        self.assertFalse(report["add_partial_packet_source_to_canonical_tree"])

    def test_signed_short_shift_mutation_is_rejected(self):
        modified=self.write_source(
            "wrong-short.zip",self.java_source(incorrect_shift=True))
        with self.assertRaises(ValueError):
            self.proof(modified)

    def test_float_wrapper_mutation_is_rejected(self):
        modified=self.write_source(
            "wrong-float.zip",self.java_source(incorrect_float=True))
        with self.assertRaises(ValueError):
            self.proof(modified)

    def test_changed_source_sha_rejected(self):
        with self.assertRaises(R169OriginalPacketTwoMethodsError):
            self.proof(source_sha="0"*64)

    def test_real_unverified_delegate_body_is_not_accidentally_accepted(self):
        report=self.proof()
        self.assertFalse(report["float_reader_delegated_method_body_verified"])
        self.assertFalse(report[
            "partial_packet_original_superclass_and_all_fields_verified"])


if __name__=="__main__":
    unittest.main()

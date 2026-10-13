"""R116: source-legal 364-op saver metadata-only full_frame restoration."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import spk_recovery.private_v309_saver_one_fullframe_rebind_r116 as gate


def u2(v):
    return v.to_bytes(2,"big")


def u4(v):
    return v.to_bytes(4,"big")


def cp_utf8(v):
    b=v.encode("utf-8")
    return b"\x01"+u2(len(b))+b


def fake_saver_stackmap(*,original,wrong_writer=False):
    file_frame=b"\xfc"+u2(28)+b"\x07"+u2(10)
    second=(b"\xff"+u2(308)+u2(3)+b"\x00\x07"+u2(12)
            +b"\x01"+u2(0)) if original else (
                b"\xfd"+u2(308)+b"\x07"+u2(12)+b"\x01")
    ending=(b"\x24\xfa"+u2(5)+b"\xfb"+u2(171)
            +b"\x17\x17\xfb"+u2(158)+b"\xff"+u2(163)
            +u2(0)+u2(1)+b"\x07"+u2(14)+b"\x04")
    return u2(10)+file_frame+second+ending


def synthetic_class(*,original,wrong_writer=False):
    cp=(
        cp_utf8("p/Owner")+b"\x07"+u2(1)
        +cp_utf8("java/lang/Object")+b"\x07"+u2(3)
        +cp_utf8("g")+cp_utf8("()V")
        +cp_utf8("Code")+cp_utf8("StackMapTable")
        +cp_utf8("java/io/File")+b"\x07"+u2(9)
        +cp_utf8("java/io/BufferedWriter" if not wrong_writer
                   else "java/io/SomeOtherClass")+b"\x07"+u2(11)
        +cp_utf8("java/lang/Exception")+b"\x07"+u2(13)
    )
    code=b"\x00"*928+b"\xb1" # synthetic Code, never executable original
    sm=fake_saver_stackmap(original=original)
    code_attr=(u2(6)+u2(3)+u4(len(code))+code+
               u2(0)+u2(1)+u2(8)+u4(len(sm))+sm)
    method=(u2(10)+u2(5)+u2(6)+u2(1)
            +u2(7)+u4(len(code_attr))+code_attr)
    return (b"\xca\xfe\xba\xbe"+u2(0)+u2(53)+u2(15)+cp
            +u2(49)+u2(2)+u2(4)+u2(0)+u2(0)
            +u2(1)+method+u2(0))


def fake_original_owner_profile():
    names=[2,2,2,3,4,20,41,213,364,697]
    methods=[]
    for i,n in enumerate(names):
        methods.append({
            "name":"g" if n==364 else "m"+str(i),
            "descriptor":"()V","access":10 if n==364 else 9,
            "instructions":[{"opcode":"0xb1","offset":k} for k in range(n)],
        })
    return {
        "classfile_major":53,
        "fields":[{"name":"f"+str(i)} for i in range(126)],
        "methods":methods,
    }


class SaverFullFrameRestoreTests(unittest.TestCase):
    def setUp(self):
        self.original=synthetic_class(original=True)
        self.candidate=synthetic_class(original=False)

    def test_repaired_full_frame_only_changes_five_verifier_metadata_bytes(self):
        source,cp=gate._method_code_attribute(self.candidate,"g")
        result=gate.restore_original_saver_full_frame(
            self.original,self.candidate,"g")
        changed,cp2=gate._method_code_attribute(result,"g")
        original,ocp=gate._method_code_attribute(self.original,"g")
        self.assertEqual(changed[2],source[2])
        self.assertEqual(source[0:2],changed[0:2])
        self.assertEqual(changed[6],original[6])
        self.assertEqual(len(result),len(self.candidate)+5)
        self.assertNotEqual(changed[6],source[6])
        self.assertNotEqual(result,self.original[:1])
        self.assertEqual(len(changed[6]),len(source[6])+5)

    def test_nonoriginal_second_frame_encoding_rejected(self):
        with self.assertRaisesRegex(
            gate.SaverFullFrameR116Error,
            "JAVAC_SECOND_SAVER_APPEND_TWO_NOT_EXACT",
        ):
            gate.restore_original_saver_full_frame(
                self.original,self.original,"g")

    def test_invalid_original_fullframe_shape_rejected(self):
        with self.assertRaisesRegex(
            gate.SaverFullFrameR116Error,
            "ORIGINAL_SECOND_SAVER_FULL_FRAME_NOT_EXACT",
        ):
            gate.restore_original_saver_full_frame(
                self.candidate,self.candidate,"g")

    def test_wrong_java_buffered_writer_type_is_not_silently_aliased(self):
        changed=synthetic_class(original=False,wrong_writer=True)
        with self.assertRaisesRegex(
            gate.SaverFullFrameR116Error,
            "SAVER_SECOND_FRAME_BUFFERED_WRITER_AND_INT_NOT_EXACT",
        ):
            gate.restore_original_saver_full_frame(
                self.original,changed,"g")

    def test_missing_candidate_source_saver_denied(self):
        with self.assertRaisesRegex(
            gate.SaverFullFrameR116Error,
            "PRIVATE_STATIC_SAVER_CLASSFILE_METHOD_MISSING",
        ):
            gate.restore_original_saver_full_frame(
                self.original,self.candidate,"nonexistent")


class PrivateSaverR116CompositeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.original=self.root/"original.jar"
        self.candidate=self.root/"compiled-source.jar"
        self.output=self.root/"accepted"
        with ZipFile(self.original,"w") as z:
            z.writestr("p/Owner.class",synthetic_class(original=True))
        with ZipFile(self.candidate,"w") as z:
            z.writestr("p/Owner.class",synthetic_class(original=False))
        self.called=0

    @staticmethod
    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def mock_r113(self):
        self.addCleanup(patch.stopall)
        patch.object(gate,"profile_jar_class",
                     lambda jar,entry: fake_original_owner_profile()).start()
        def r113(original,source,entry,report,*,original_sha256,candidate_sha256):
            self.called+=1
            self.assertEqual(entry,"p/Owner.class")
            self.assertEqual(original_sha256,self.sha(self.original))
            self.assertEqual(candidate_sha256,self.sha(source))
            with ZipFile(source) as z:
                values,cp=gate._method_code_attribute(
                    z.read(entry),"g")
                gate._single_saver_frame_layout(values[6],cp,original=True)
            report.mkdir()
            (report/"dummy.aggregate.json").write_text("{}")
            return {
                "original_saver_R66_R81_all_operands_passed":True,
                "original_saver_StackMapTable_original_encoding_passed":True,
                "original_saver_jvm_StackMapTable_frames_equal":10,
            }
        patch.object(gate,"accept_original_source_recompiled_saver",r113).start()

    def call(self,sha=None):
        return gate.normalize_saver_then_require_original_r113(
            self.original,self.candidate,"p/Owner.class",self.output,
            original_sha256=sha or self.sha(self.original),
            candidate_sha256=self.sha(self.candidate))

    def test_one_frame_rewrite_then_exact_r113_acceptance_promotes(self):
        self.mock_r113()
        report=self.call()
        self.assertEqual(self.called,1)
        self.assertTrue(report["candidate_saver_Code_bytes_preserved"])
        self.assertFalse(report["saver_original_executable_Code_transferred"])
        self.assertEqual(report["original_saver_StackMapTable_frames_exact"],10)
        self.assertFalse(report["complete_original_owner_R107_accepted"])
        self.assertEqual(
            self.sha(self.output/"candidate.saver-frame.PRIVATE.jar"),
            report["saver_frame_normalized_candidate_sha256"])
        self.assertEqual(len(list(self.output.iterdir())),2)

    def test_wrong_original_pin_fails_before_loading_original(self):
        self.mock_r113()
        with self.assertRaisesRegex(
            gate.SaverFullFrameR116Error,"SHA256_MISMATCH"):
            self.call(sha="0"*64)
        self.assertEqual(self.called,0)
        self.assertFalse(self.output.exists())

    def test_r113_failure_does_not_promote(self):
        self.addCleanup(patch.stopall)
        patch.object(gate,"profile_jar_class",
                     lambda jar,entry: fake_original_owner_profile()).start()
        def deny(*args,**kw):
            raise gate.OriginalSaverMethodAcceptanceError("changed operand")
        patch.object(gate,"accept_original_source_recompiled_saver",deny).start()
        with self.assertRaisesRegex(
            gate.SaverFullFrameR116Error,"R113_POSTFRAME_PARITY_NOT_ACCEPTED"):
            self.call()
        self.assertFalse(self.output.exists())

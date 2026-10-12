"""R70: Java9 original-versus-generated outer IOException source roundtrip."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.large_method_cfg_parity import compare_large_method_cfg
from spk_recovery.outer_io_exception_envelope import (
    OuterIoSourceError, plan_original_outer_io_source_envelope,
    recover_private_outer_io_envelope,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class OriginalOuterIoSourceTests(unittest.TestCase):
    @staticmethod
    def _original_body()->str:
        return (
            "initialize();"
            "try {"
            "java.io.File originalLocalSlot0=new java.io.File(filePath);"
            "if(!originalLocalSlot0.exists())return;"
            "java.util.Properties originalLocalSlot1=new java.util.Properties();"
            "java.io.FileInputStream originalLocalSlot2="
            "new java.io.FileInputStream(originalLocalSlot0);"
            "originalLocalSlot1.load(originalLocalSlot2);"
            "originalLocalSlot2.close();"
            "}catch(java.io.IOException originalIOException){"
            "originalIOException.printStackTrace();"
            "}"
        )

    def _jar(self, root:Path,label:str,classname:str,body:str)->Path:
        src=root/label/"p"/(classname+".java")
        classes=root/label/"classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class "+classname+" {"
            'public static String filePath="example.properties";'
            "public static void initialize(){}"
            "public static void restore(){"+body+"}"
            "}",encoding="utf-8",
        )
        result=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-d",str(classes),str(src)],
            capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as z:
            z.write(classes/"p"/(classname+".class"),
                    "p/"+classname+".class")
        return jar

    @staticmethod
    def _sha(path:Path)->str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar:Path,name:str)->dict:
        return profile_jar_class(jar,"p/"+name+".class")

    def test_real_java9_two_io_handlers_and_recompiled_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            orig=self._jar(root,"original","Owner",self._original_body())
            original=self._profile(orig,"Owner")
            out=root/"private"
            aggregate=recover_private_outer_io_envelope(
                orig,"p/Owner.class","restore","()V",
                out,sha256=self._sha(orig))
            self.assertEqual(aggregate["original_io_typed_exception_handler_entries"],2)
            self.assertTrue(aggregate["shared_original_io_handler_target"])
            self.assertTrue(aggregate["original_io_catch_calls_printStackTrace_once"])
            self.assertFalse(aggregate["original_internal_protected_method_body_recovered"])
            source=(out/"outer-io-envelope.private.java.txt").read_text()
            self.assertIn("java.util.Properties originalLocalSlot1",source)
            self.assertIn("catch (java.io.IOException originalIOException)",source)
            self.assertIn("originalIOException.printStackTrace()",source)
            compiled=self._jar(root,"compiled","Recompiled",source)
            candidate=self._profile(compiled,"Recompiled")
            result=compare_large_method_cfg(
                original,"restore","()V",
                candidate,"restore","()V",[],
            )
            self.assertEqual(result["ordered_typed_exception_table_entries"],2)
            self.assertEqual(result["ordered_static_field_writes"],0)
            self.assertTrue(result["exact_exception_type_and_instruction_ordinal_ranges"])
            self.assertTrue(result["exact_branch_target_instruction_ordinals"])
            self.assertFalse(result["runtime_equivalence_certified"])
            public=(out/"outer-io-envelope.aggregate.json").read_text()
            for private in ('"filePath"','"initialize"','"Owner"',"example.properties"):
                self.assertNotIn(private,public)

    def test_handler_side_effect_and_protected_ranges_are_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._jar(root,"original","Owner",self._original_body())
            source=self._profile(jar,"Owner")
            method=next(m for m in source["methods"] if m["name"]=="restore")
            method["instructions"][-2]["name"]="fabricated"
            with self.assertRaisesRegex(
                OuterIoSourceError,"ORIGINAL_IO_EXCEPTION_HANDLER_SIDE_EFFECT"
            ):
                plan_original_outer_io_source_envelope(
                    source,"restore","()V")
            source=self._profile(jar,"Owner")
            method=next(m for m in source["methods"] if m["name"]=="restore")
            io=next(h for h in method["exception_handlers"]
                    if h["catch_type"]=="java/io/IOException")
            io["end_pc"]=method["instructions"][0]["offset"]
            with self.assertRaisesRegex(
                OuterIoSourceError,"ORIGINAL_TWO_IO_PROTECTED_RANGES"
            ):
                plan_original_outer_io_source_envelope(
                    source,"restore","()V")

    def test_wrong_sha_and_destination_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._jar(root,"original","Owner",self._original_body())
            out=root/"private"
            with self.assertRaisesRegex(
                OuterIoSourceError,"ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_outer_io_envelope(
                    jar,"p/Owner.class","restore","()V",
                    out,sha256="0"*64)
            self.assertFalse(out.exists())
            out.mkdir()
            marker=out/"KEEP"
            marker.write_text("KEEP",encoding="utf-8")
            with self.assertRaisesRegex(
                OuterIoSourceError,"OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_outer_io_envelope(
                    jar,"p/Owner.class","restore","()V",
                    out,sha256=self._sha(jar))
            self.assertEqual(marker.read_text(),"KEEP")


if __name__=="__main__":
    unittest.main()

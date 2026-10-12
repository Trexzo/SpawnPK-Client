"""R69: real Java9 File/Properties prefix source recompilation proof."""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.properties_load_prefix_source import (
    PropertiesPrefixSourceError, plan_original_properties_method_prefix,
    recover_private_properties_prefix,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class PropertiesPrefixJava9Tests(unittest.TestCase):
    def _jar(self, root:Path,label:str,classname:str,sourcebody:str)->Path:
        src=root/label/"p"/(classname+".java")
        classes=root/label/"classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class "+classname+" {"
            'public static String filePath="example.properties";'
            "public static void initialize(){}"
            "public static void restore() throws java.io.IOException {"
            +sourcebody+"}"
            "}",encoding="utf-8"
        )
        p=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-d",str(classes),str(src)],
            capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as z:
            z.write(classes/"p"/(classname+".class"),
                    "p/"+classname+".class")
        return jar

    @staticmethod
    def _sha(path:Path)->str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar:Path,name:str):
        return profile_jar_class(jar,"p/"+name+".class")

    @staticmethod
    def _body()->str:
        return (
            "initialize();"
            "java.io.File originalLocalSlot0=new java.io.File(filePath);"
            "if(!originalLocalSlot0.exists())return;"
            "java.util.Properties originalLocalSlot1=new java.util.Properties();"
            "java.io.FileInputStream originalLocalSlot2="
            "new java.io.FileInputStream(originalLocalSlot0);"
            "originalLocalSlot1.load(originalLocalSlot2);"
            "originalLocalSlot2.close();"
        )

    def test_original_prefix_recompiles_with_exact_JVM_instruction_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            original=self._jar(root,"original","Owner",self._body())
            out=root/"private"
            report=recover_private_properties_prefix(
                original,"p/Owner.class","restore","()V",out,
                original_sha256=self._sha(original))
            self.assertEqual(report["exact_original_prefix_instructions"],24)
            self.assertEqual(report["original_properties_local_slot_index"],1)
            self.assertTrue(report["original_properties_local_initialized_once"])
            self.assertTrue(report["original_getProperty_type_java_util_Properties_verified"])
            self.assertTrue(report["original_properties_load_then_stream_close_verified"])
            self.assertFalse(report["compiled_full_original_method_equivalent"])
            generated=(out/"properties-load-prefix.private.java.txt"
                       ).read_text()
            for phrase in (
                "java.io.File originalLocalSlot0",
                "java.util.Properties originalLocalSlot1",
                "java.io.FileInputStream originalLocalSlot2",
                "originalLocalSlot1.load(originalLocalSlot2)",
                "originalLocalSlot2.close()",
            ):
                self.assertIn(phrase,generated)
            candidate=self._jar(root,"candidate","Recompiled",generated)
            orig=self._profile(original,"Owner")
            repl=self._profile(candidate,"Recompiled")
            def opcodes(prof):
                m=next(x for x in prof["methods"] if x["name"]=="restore")
                return [x["opcode"] for x in m["instructions"][:24]]
            self.assertEqual(len(opcodes(orig)),24)
            self.assertEqual(opcodes(orig),opcodes(repl))
            public=(out/"properties-load-prefix.aggregate.json").read_text()
            for secret in ("filePath","initialize","p/Owner","example.properties"):
                self.assertNotIn('"'+secret+'"',public)

    def test_properties_type_and_close_call_mutations_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._jar(root,"original","Owner",self._body())
            original=self._profile(jar,"Owner")
            m=next(x for x in original["methods"] if x["name"]=="restore")
            m["instructions"][10]["type"]="java/util/Hashtable"
            with self.assertRaisesRegex(
                PropertiesPrefixSourceError,"PROPERTIES_LOCAL_ONE_CONSTRUCTOR"
            ):
                plan_original_properties_method_prefix(original,"restore","()V")
            original=self._profile(jar,"Owner")
            m=next(x for x in original["methods"] if x["name"]=="restore")
            m["instructions"][23]["name"]="notClose"
            with self.assertRaisesRegex(
                PropertiesPrefixSourceError,"PROPERTIES_LOAD_AND_STREAM_CLOSE"
            ):
                plan_original_properties_method_prefix(original,"restore","()V")

    def test_complete_original_pin_and_existing_output_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._jar(root,"original","Owner",self._body())
            out=root/"private"
            with self.assertRaisesRegex(
                PropertiesPrefixSourceError,"ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_properties_prefix(
                    jar,"p/Owner.class","restore","()V",out,
                    original_sha256="0"*64)
            self.assertFalse(out.exists())
            out.mkdir()
            marker=out/"KEEP"
            marker.write_text("KEEP",encoding="utf-8")
            with self.assertRaisesRegex(
                PropertiesPrefixSourceError,"OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_properties_prefix(
                    jar,"p/Owner.class","restore","()V",out,
                    original_sha256=self._sha(jar))
            self.assertEqual(marker.read_text(),"KEEP")


if __name__=="__main__":
    unittest.main()

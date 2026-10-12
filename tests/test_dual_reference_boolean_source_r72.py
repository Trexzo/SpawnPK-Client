"""R72: recompile recovered exact original 11-op dual-write protected Java."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.dual_reference_boolean_source_r72 import (
    DualProtectedSourceError, plan_original_dual_protected_source,
    recover_private_two_write_source,
)
from spk_recovery.large_method_cfg_parity import compare_large_method_cfg


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DualReferenceBooleanSourceR72Tests(unittest.TestCase):
    DESC="(Ljava/lang/Object;Ljava/util/Properties;I)V"

    @staticmethod
    def _body():
        return (
            "try {"
            'mode=Choice.parse(originalLocalSlot1.getProperty("mode.key"));'
            'active=Boolean.valueOf(originalLocalSlot1.getProperty("active.key")).booleanValue();'
            "} catch(Exception ignored){}"
        )

    def _jar(self,root:Path,label:str,classname:str,body:str)->Path:
        src=root/label/"p"/(classname+".java")
        classes=root/label/"classes"
        src.parent.mkdir(parents=True)
        classes.mkdir()
        src.write_text(
            "package p; public final class "+classname+" {"
            "public static Choice mode; public static boolean active;"
            "public static void restore(Object arg0,java.util.Properties originalLocalSlot1,int arg2){"
            +body+"}"
            "}"
            "enum Choice { YES; static Choice parse(String value){return YES;} }",
            encoding="utf-8")
        p=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-d",str(classes),str(src)],
            capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as archive:
            archive.write(classes/"p"/(classname+".class"),
                          "p/"+classname+".class")
        return jar

    @staticmethod
    def _sha(jar:Path)->str:
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar:Path,classname:str):
        return profile_jar_class(jar,"p/"+classname+".class")

    def test_dual_original_source_recompiles_exact_R66_cfg_handlers_and_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            original=self._jar(root,"original","Owner",self._body())
            report=recover_private_two_write_source(
                original,"p/Owner.class","restore",self.DESC,
                root/"private",whole_jar_sha256=self._sha(original))
            self.assertEqual(report["original_exact_two_write_protected_source_regions"],1)
            self.assertTrue(report["original_original_reference_converted_before_boolean"])
            self.assertFalse(report["original_full_method_compiled_equivalent"])
            source=(root/"private"/"reference-boolean-source.private.java.txt").read_text()
            self.assertIn("mode = p.Choice.parse(",source)
            self.assertIn("active = java.lang.Boolean.valueOf(",source)
            self.assertEqual(source.count("catch (java.lang.Exception ignored)"),1)
            compiled=self._jar(root,"candidate","Recompiled",source)
            aliases=[
                {"original":{"name":"mode","descriptor":"Lp/Choice;"},
                 "candidate":{"name":"mode","descriptor":"Lp/Choice;"}},
                {"original":{"name":"active","descriptor":"Z"},
                 "candidate":{"name":"active","descriptor":"Z"}}
            ]
            proof=compare_large_method_cfg(
                self._profile(original,"Owner"),"restore",self.DESC,
                self._profile(compiled,"Recompiled"),"restore",self.DESC,
                aliases)
            self.assertEqual(proof["ordered_static_field_writes"],2)
            self.assertEqual(proof["ordered_typed_exception_table_entries"],1)
            self.assertTrue(proof["exact_mapped_static_field_write_order"])
            self.assertFalse(proof["runtime_equivalence_certified"])
            public=(root/"private"/"reference-boolean-source.aggregate.json").read_text()
            for secret in ("mode.key","active.key",'"mode"','"active"',"p/Choice"):
                self.assertNotIn(secret,public)

    def test_modified_box_converter_or_two_write_order_is_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._jar(root,"original","Owner",self._body())
            p=self._profile(jar,"Owner")
            method=next(x for x in p["methods"] if x["name"]=="restore")
            calls=[r for r in method["instructions"] if r["opcode"]=="0xb8"]
            self.assertEqual(len(calls),2)
            calls[1]["descriptor"]="(Ljava/lang/String;)Ljava/lang/Object;"
            result=plan_original_dual_protected_source(p,"restore",self.DESC)
            self.assertEqual(result["original_exact_two_write_protected_source_regions"],0)
            p=self._profile(jar,"Owner")
            method=next(x for x in p["methods"] if x["name"]=="restore")
            stores=[r for r in method["instructions"] if r["opcode"]=="0xb3"]
            stores[0]["descriptor"]="Z"
            result=plan_original_dual_protected_source(p,"restore",self.DESC)
            self.assertEqual(result["original_exact_two_write_protected_source_regions"],0)

    def test_wrong_whole_jar_sha_and_output_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._jar(root,"original","Owner",self._body())
            output=root/"private"
            with self.assertRaisesRegex(
                DualProtectedSourceError,"ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH"
            ):
                recover_private_two_write_source(
                    jar,"p/Owner.class","restore",self.DESC,
                    output,whole_jar_sha256="0"*64)
            self.assertFalse(output.exists())
            output.mkdir()
            keep=output/"KEEP"
            keep.write_text("KEEP",encoding="utf-8")
            with self.assertRaisesRegex(
                DualProtectedSourceError,"OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_two_write_source(
                    jar,"p/Owner.class","restore",self.DESC,
                    output,whole_jar_sha256=self._sha(jar))
            self.assertEqual(keep.read_text(),"KEEP")


if __name__=="__main__":
    unittest.main()

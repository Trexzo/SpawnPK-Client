"""R74: Java9 original → private Boolean helper source → compiled candidate."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.boolean_helper_protected_source import (
    BooleanHelperSourceError, plan_original_boolean_helper_regions,
    private_replay_boolean_helper,
)
from spk_recovery.large_method_cfg_parity import compare_large_method_cfg


@unittest.skipUnless(shutil.which("javac"), "javac required")
class ExactBooleanHelperProtectedSourceTests(unittest.TestCase):
    DESC="(Ljava/lang/Object;Ljava/util/Properties;I)V"

    @staticmethod
    def _body():
        return (
            'try { if(originalLocalSlot1.getProperty("alpha") == null) {'
            "first=false;} else {"
            'boolean originalParsedBoolean=Boolean.valueOf(originalLocalSlot1.getProperty("alpha")).booleanValue();'
            "helper(originalParsedBoolean);}} catch(Exception ignored){}"
            'try { if(originalLocalSlot1.getProperty("beta") == null) {'
            "External.setFlag(false);second=false;} else {"
            'boolean originalParsedBoolean=Boolean.valueOf(originalLocalSlot1.getProperty("beta")).booleanValue();'
            "External.setFlag(originalParsedBoolean);"
            "second=originalParsedBoolean;"
            "}} catch(Exception ignored){}"
        )

    def _compile(self,root:Path,label:str,classname:str,body:str)->Path:
        src=root/label/"p"/(classname+".java")
        out=root/label/"classes"
        src.parent.mkdir(parents=True)
        out.mkdir()
        src.write_text(
            "package p; public final class "+classname+" {"
            "public static boolean first,second;"
            "public static void helper(boolean value){}"
            "public static void restore(Object arg0,java.util.Properties originalLocalSlot1,int arg2){"
            +body+"}"
            "}"
            "class External {public static void setFlag(boolean value) {}}",
            encoding="utf-8",
        )
        result=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-d",str(out),str(src)],
            capture_output=True,text=True,
        )
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as z:
            for cls in (classname,"External"):
                z.write(out/"p"/(cls+".class"),"p/"+cls+".class")
        return jar

    @staticmethod
    def _sha(path:Path)->str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar:Path,owner:str)->dict:
        return profile_jar_class(jar,"p/"+owner+".class")

    def test_two_original_helper_regions_extract_and_recompile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            original=self._compile(root,"original","Owner",self._body())
            private=root/"private"
            result=private_replay_boolean_helper(
                original,"p/Owner.class","restore",self.DESC,private,
                sha256=self._sha(original))
            self.assertEqual(result["original_exact_boolean_helper_source_regions"],2)
            self.assertEqual(result["source_form_counts"],{
                "nonnull_owner_boolean_helper":1,
                "boolean_helper_then_field_write":1,
            })
            self.assertFalse(result["complete_original_method_compiled"])
            recovered=(private/"boolean-helper-sources.private.java.txt").read_text()
            self.assertIn("first = false",recovered)
            self.assertIn("second = false",recovered)
            self.assertIn("helper(originalParsedBoolean)",recovered)
            self.assertIn("p.External.setFlag(false)",recovered)
            self.assertIn("p.External.setFlag(originalParsedBoolean)",recovered)
            compiled=self._compile(root,"candidate","Recompiled",recovered)
            aliases=[
                {"original":{"name":f,"descriptor":"Z"},
                 "candidate":{"name":f,"descriptor":"Z"}}
                for f in ("first","second")
            ]
            proof=compare_large_method_cfg(
                self._profile(original,"Owner"),"restore",self.DESC,
                self._profile(compiled,"Recompiled"),"restore",self.DESC,
                aliases)
            self.assertEqual(proof["ordered_typed_exception_table_entries"],2)
            self.assertEqual(proof["ordered_static_field_writes"],3)
            self.assertTrue(proof["exact_branch_target_instruction_ordinals"])
            self.assertTrue(proof["exact_exception_type_and_instruction_ordinal_ranges"])
            self.assertFalse(proof["runtime_equivalence_certified"])
            public=(private/"boolean-helper-sources.aggregate.json").read_text()
            for name in ('"alpha"','"beta"','"first"','"second"','"Owner"',"p/External"):
                self.assertNotIn(name,public)

    def test_null_branch_external_helper_order_and_owner_decl_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._body())
            original=self._profile(jar,"Owner")
            method=next(m for m in original["methods"] if m["name"]=="restore")
            calls=[row for row in method["instructions"]
                   if row.get("opcode")=="0xb8" and row.get("owner")=="p/External"]
            self.assertEqual(len(calls),2)
            calls[0]["descriptor"]="()V"
            result=plan_original_boolean_helper_regions(
                original,"restore",self.DESC)
            self.assertEqual(result["original_exact_boolean_helper_source_regions"],1)
            original=self._profile(jar,"Owner")
            helper=next(m for m in original["methods"] if m["name"]=="helper")
            helper["access"] &= ~0x0008
            result=plan_original_boolean_helper_regions(
                original,"restore",self.DESC)
            self.assertEqual(result["original_exact_boolean_helper_source_regions"],1)

    def test_complete_original_pin_and_preexisting_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._body())
            output=root/"private"
            with self.assertRaisesRegex(
                BooleanHelperSourceError,"ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                private_replay_boolean_helper(
                    jar,"p/Owner.class","restore",self.DESC,
                    output,sha256="0"*64)
            self.assertFalse(output.exists())
            output.mkdir()
            marker=output/"KEEP"
            marker.write_text("KEEP",encoding="utf-8")
            with self.assertRaisesRegex(
                BooleanHelperSourceError,"OUTPUT_ALREADY_EXISTS"
            ):
                private_replay_boolean_helper(
                    jar,"p/Owner.class","restore",self.DESC,
                    output,sha256=self._sha(jar))
            self.assertEqual(marker.read_text(),"KEEP")


if __name__=="__main__":
    unittest.main()

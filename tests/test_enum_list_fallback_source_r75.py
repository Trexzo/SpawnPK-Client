"""R75: Java9 recover/recompile exact 23-op enum/List fallback source."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.enum_list_fallback_source import (
    EnumListFallbackSourceError, plan_original_enum_list_fallback,
    recover_private_enum_list_fallback,
)
from spk_recovery.large_method_cfg_parity import compare_large_method_cfg


@unittest.skipUnless(shutil.which("javac"), "javac required")
class OriginalEnumListFallbackSourceTests(unittest.TestCase):
    METHOD="(Ljava/lang/Object;Ljava/util/Properties;I)V"

    @staticmethod
    def _body()->str:
        return (
            "try {"
            'if(originalLocalSlot1.getProperty("option")==null){'
            "External.primary=true;"
            "External.values.add(Choice.FIRST);"
            "External.values.add(Choice.SECOND);"
            "External.secondary=false;"
            "}else{"
            'External.primary=Boolean.valueOf(originalLocalSlot1.getProperty("option")).booleanValue();'
            "}"
            "}catch(Exception ignored){}"
        )

    def _compile(self,root:Path,label:str,classname:str,body:str)->Path:
        src=root/label/"p"/(classname+".java")
        output=root/label/"classes"
        src.parent.mkdir(parents=True)
        output.mkdir()
        src.write_text(
            "package p; public final class "+classname+" {"
            "public static void restore(Object arg0,"
            "java.util.Properties originalLocalSlot1,int arg2){"
            +body+"}"
            "}"
            "class External {"
            "static boolean primary,secondary;"
            "static java.util.List<Object> values=new java.util.ArrayList<>();"
            "}"
            "enum Choice {FIRST,SECOND;}",
            encoding="utf-8",
        )
        p=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-d",str(output),str(src)],
            capture_output=True,text=True,
        )
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as archive:
            for cls in (classname,"External","Choice"):
                archive.write(output/"p"/(cls+".class"),"p/"+cls+".class")
        return jar

    @staticmethod
    def _sha(p:Path)->str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar:Path,name:str)->dict:
        return profile_jar_class(jar,"p/"+name+".class")

    def test_original_source_roundtrip_with_exact_external_write_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            original=self._compile(root,"original","Owner",self._body())
            dest=root/"private"
            info=recover_private_enum_list_fallback(
                original,"p/Owner.class","restore",self.METHOD,
                dest,original_sha256=self._sha(original))
            self.assertEqual(info["exact_original_enum_list_fallback_source_regions"],1)
            self.assertTrue(info["original_two_list_add_results_discarded"])
            self.assertFalse(info["runtime_equivalence_certified"])
            fragment=(dest/"enum-list-fallback.private.java.txt").read_text()
            self.assertIn("p.External.primary = true",fragment)
            self.assertIn("p.External.secondary = false",fragment)
            self.assertIn("p.External.values.add(p.Choice.FIRST)",fragment)
            self.assertIn("p.External.values.add(p.Choice.SECOND)",fragment)
            self.assertEqual(fragment.count("catch (java.lang.Exception ignored)"),1)
            compiled=self._compile(root,"compiled","Candidate",fragment)
            proof=compare_large_method_cfg(
                self._profile(original,"Owner"),"restore",self.METHOD,
                self._profile(compiled,"Candidate"),"restore",self.METHOD,[])
            self.assertEqual(proof["ordered_typed_exception_table_entries"],1)
            self.assertEqual(proof["ordered_static_field_writes"],3)
            self.assertTrue(proof["exact_branch_target_instruction_ordinals"])
            self.assertFalse(proof["runtime_equivalence_certified"])
            pub=(dest/"enum-list-fallback.aggregate.json").read_text()
            for secret in ('"option"','"FIRST"','"SECOND"',"p/External"):
                self.assertNotIn(secret,pub)

    def test_swapped_enum_constant_and_list_descriptor_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._body())
            profile=self._profile(jar,"Owner")
            method=next(x for x in profile["methods"] if x["name"]=="restore")
            choices=[row for row in method["instructions"]
                     if row.get("opcode")=="0xb2"
                     and row.get("owner")=="p/Choice"]
            self.assertEqual(len(choices),2)
            choices[1]["name"]=choices[0]["name"]
            result=plan_original_enum_list_fallback(
                profile,"restore",self.METHOD)
            self.assertEqual(result["exact_original_enum_list_fallback_source_regions"],0)
            profile=self._profile(jar,"Owner")
            method=next(x for x in profile["methods"] if x["name"]=="restore")
            target=next(row for row in method["instructions"]
                        if row.get("opcode")=="0xb9")
            target["descriptor"]="(Ljava/lang/Object;)V"
            result=plan_original_enum_list_fallback(
                profile,"restore",self.METHOD)
            self.assertEqual(result["exact_original_enum_list_fallback_source_regions"],0)

    def test_pin_and_output_collision_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._body())
            dest=root/"private"
            with self.assertRaisesRegex(
                EnumListFallbackSourceError,"ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_enum_list_fallback(
                    jar,"p/Owner.class","restore",self.METHOD,dest,
                    original_sha256="0"*64)
            self.assertFalse(dest.exists())
            dest.mkdir()
            keep=dest/"KEEP"
            keep.write_text("KEEP",encoding="utf-8")
            with self.assertRaisesRegex(
                EnumListFallbackSourceError,"OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_enum_list_fallback(
                    jar,"p/Owner.class","restore",self.METHOD,dest,
                    original_sha256=self._sha(jar))
            self.assertEqual(keep.read_text(),"KEEP")


if __name__=="__main__":
    unittest.main()

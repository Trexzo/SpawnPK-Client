"""R76: exact final enum/string Java9 original → recovered → candidate CFG."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.enum_selection_source import (
    EnumSelectionSourceError, plan_private_final_enum_source,
    replay_private_final_enum,
)
from spk_recovery.large_method_cfg_parity import compare_large_method_cfg


@unittest.skipUnless(shutil.which("javac"), "javac required")
class FinalEnumSelectionSourceTests(unittest.TestCase):
    METHOD="(Ljava/lang/Object;Ljava/util/Properties;I)V"

    @staticmethod
    def _body()->str:
        return (
            "try {"
            "result=null;"
            'if(originalLocalSlot1.getProperty("mode")!=null){'
            'String originalPropertyText=originalLocalSlot1.getProperty("mode");'
            'if(originalPropertyText.contains(".")){'
            'String originalPrefix=originalPropertyText.split("\\\\.")[0];'
            'String originalSuffix=originalPropertyText.split("\\\\.")[1];'
            "if(originalSuffix.equalsIgnoreCase(selected.name())){"
            "current=Choice.valueOf(originalPrefix);"
            "result=current;"
            "}"
            "}"
            "}"
            "}catch(Exception ignored){}"
        )

    def _compile(self,root:Path,label:str,classname:str,body:str)->Path:
        src=root/label/"p"/(classname+".java")
        out=root/label/"classes"
        src.parent.mkdir(parents=True)
        out.mkdir()
        src.write_text(
            "package p; public final class "+classname+" {"
            "public static Choice result,current;"
            "public static Mode selected=Mode.FIRST;"
            "public static void restore(Object arg0,"
            "java.util.Properties originalLocalSlot1,int arg2){"
            +body+"}"
            "}"
            "enum Choice { ALPHA,BETA }"
            "enum Mode { FIRST,SECOND }",
            encoding="utf-8",
        )
        p=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-d",str(out),str(src)],
            capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as archive:
            for cls in (classname,"Choice","Mode"):
                archive.write(out/"p"/(cls+".class"),
                              "p/"+cls+".class")
        return jar

    @staticmethod
    def _sha(p:Path)->str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar:Path,name:str)->dict:
        return profile_jar_class(jar,"p/"+name+".class")

    def test_36_op_original_java_source_roundtrip_through_R66(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            original=self._compile(root,"original","Owner",self._body())
            private=root/"private"
            report=replay_private_final_enum(
                original,"p/Owner.class","restore",self.METHOD,private,
                original_sha256=self._sha(original))
            self.assertEqual(report["exact_original_36_op_final_enum_regions"],1)
            self.assertTrue(report["original_two_string_splits_preserved"])
            self.assertFalse(report["original_runtime_equivalence_certified"])
            fragment=(private/"enum-selection.private.java.txt").read_text()
            self.assertEqual(fragment.count("originalPropertyText.split("),2)
            self.assertEqual(fragment.count('getProperty("mode")'),2)
            self.assertIn("result = null",fragment)
            self.assertIn("current = p.Choice.valueOf(originalPrefix)",fragment)
            self.assertIn("result = current",fragment)
            # The original-qualified static read p.Owner.selected must retain its declaring owner.
            rebuild=self._compile(root,"candidate","Owner",fragment)
            aliases=[
                {"original":{"name":f,"descriptor":"Lp/Choice;"},
                 "candidate":{"name":f,"descriptor":"Lp/Choice;"}}
                for f in ("result","current")
            ]
            matched=compare_large_method_cfg(
                self._profile(original,"Owner"),"restore",self.METHOD,
                self._profile(rebuild,"Owner"),"restore",self.METHOD,
                aliases)
            self.assertEqual(matched["ordered_typed_exception_table_entries"],1)
            self.assertEqual(matched["ordered_static_field_writes"],3)
            self.assertTrue(matched["exact_branch_target_instruction_ordinals"])
            self.assertTrue(matched["exact_mapped_static_field_write_order"])
            self.assertFalse(matched["runtime_equivalence_certified"])
            aggregate=(private/"enum-selection.aggregate.json").read_text()
            for secret in ('"mode"','"result"','"current"',"p/Choice"):
                self.assertNotIn(secret,aggregate)

    def test_modified_second_split_regex_and_field_alias_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._body())
            profile=self._profile(jar,"Owner")
            method=next(m for m in profile["methods"] if m["name"]=="restore")
            regexes=[r for r in method["instructions"]
                     if r.get("opcode")=="0x12"
                     and r.get("constant")=="\\."]
            self.assertEqual(len(regexes),2)
            regexes[-1]["constant"]="forged"
            result=plan_private_final_enum_source(profile,"restore",self.METHOD)
            self.assertEqual(result["exact_original_36_op_final_enum_regions"],0)
            profile=self._profile(jar,"Owner")
            method=next(m for m in profile["methods"] if m["name"]=="restore")
            writes=[r for r in method["instructions"] if r["opcode"]=="0xb3"]
            self.assertEqual(len(writes),3)
            writes[-1]["name"]="current"
            result=plan_private_final_enum_source(profile,"restore",self.METHOD)
            self.assertEqual(result["exact_original_36_op_final_enum_regions"],0)

    def test_split_local_slot_pairings_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._body())
            profile=self._profile(jar,"Owner")
            method=next(m for m in profile["methods"] if m["name"]=="restore")
            indexed_loads=[r for r in method["instructions"]
                           if r.get("opcode")=="0x19"]
            self.assertEqual([r["local_index"] for r in indexed_loads],[5,4])
            # Re-read the prefix instead of the suffix: same opcode/CFG,
            # but a materially different Java expression.
            indexed_loads[0]["local_index"]=4
            self.assertEqual(
                plan_private_final_enum_source(profile,"restore",self.METHOD)
                ["exact_original_36_op_final_enum_regions"],0)
            profile=self._profile(jar,"Owner")
            method=next(m for m in profile["methods"] if m["name"]=="restore")
            indexed_stores=[r for r in method["instructions"]
                            if r.get("opcode")=="0x3a"]
            self.assertEqual([r["local_index"] for r in indexed_stores],[4,5])
            # Overwrite the first split result rather than preserving both.
            indexed_stores[0]["local_index"]=5
            self.assertEqual(
                plan_private_final_enum_source(profile,"restore",self.METHOD)
                ["exact_original_36_op_final_enum_regions"],0)

    def test_pin_and_output_collision_preserve_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._body())
            dest=root/"private"
            with self.assertRaisesRegex(
                EnumSelectionSourceError,"ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                replay_private_final_enum(
                    jar,"p/Owner.class","restore",self.METHOD,
                    dest,original_sha256="0"*64)
            self.assertFalse(dest.exists())
            dest.mkdir()
            marker=dest/"KEEP"
            marker.write_text("KEEP",encoding="utf-8")
            with self.assertRaisesRegex(
                EnumSelectionSourceError,"OUTPUT_ALREADY_EXISTS"
            ):
                replay_private_final_enum(
                    jar,"p/Owner.class","restore",self.METHOD,
                    dest,original_sha256=self._sha(jar))
            self.assertEqual(marker.read_text(),"KEEP")


if __name__=="__main__":
    unittest.main()

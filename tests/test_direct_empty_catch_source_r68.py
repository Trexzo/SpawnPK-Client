"""R68: Java9 source recompile and R66 parity for direct protected assignments."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.direct_empty_catch_source import (
    DirectLocalExceptionSourceError, plan_direct_empty_catch_sources,
    recover_private_direct_empty_catch_sources,
)
from spk_recovery.large_method_cfg_parity import compare_large_method_cfg


@unittest.skipUnless(shutil.which("javac"), "javac required")
class DirectEmptyCatchSourceTests(unittest.TestCase):
    DESC = "(Ljava/lang/Object;Lp/Provider;I)V"

    def _compile(self, root: Path, label: str, classname: str,
                 statements: str) -> Path:
        src=root/label/"p"/(classname+".java")
        target=root/label/"classes"
        src.parent.mkdir(parents=True)
        target.mkdir()
        src.write_text(
            "package p; public final class "+classname+" {"
            "public static boolean first, second;"
            "public static void restore(Object arg0, Provider originalLocalSlot1,"
            " int arg2){"+statements+"}"
            "}"
            "class Provider { public String get(String key){return key;} }",
            encoding="utf-8",
        )
        proc=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-d",str(target),str(src)],
            capture_output=True,text=True,
        )
        self.assertEqual(proc.returncode,0,proc.stderr+proc.stdout)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as archive:
            for n in (classname,"Provider"):
                archive.write(target/"p"/(n+".class"),"p/"+n+".class")
        return jar

    @staticmethod
    def _source()->str:
        return (
            'try{first=Boolean.valueOf(originalLocalSlot1.get("key.first")).booleanValue();}'
            'catch(Exception ignored){}'
            'try{second=Boolean.valueOf(originalLocalSlot1.get("key.second")).booleanValue();}'
            'catch(Exception ignored){}'
        )

    @staticmethod
    def _sha(p:Path)->str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    @staticmethod
    def _profile(jar:Path,name:str)->dict:
        return profile_jar_class(jar,"p/"+name+".class")

    def test_two_direct_regions_recompile_with_exact_handler_and_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._source())
            result=recover_private_direct_empty_catch_sources(
                jar,"p/Owner.class","restore",self.DESC,
                root/"private",sha256=self._sha(jar))
            self.assertEqual(result["direct_six_instruction_boolean_try_catch_regions"],2)
            self.assertEqual(result["original_local_exception_handlers"],2)
            self.assertTrue(result["original_empty_catch_and_virtual_lookup_once_proven"])
            self.assertFalse(result["real_client_runtime_equivalence_certified"])
            generated=(root/"private"/"direct-exception-source.private.java.txt"
                       ).read_text(encoding="utf-8")
            self.assertEqual(generated.count("catch (java.lang.Exception ignored)"),2)
            self.assertEqual(generated.count("originalLocalSlot1.get("),2)
            self.assertIn("first =",generated)
            self.assertIn("second =",generated)
            recompiled=self._compile(root,"candidate","Recompiled",generated)
            aliases=[
                {"original":{"name":field,"descriptor":"Z"},
                 "candidate":{"name":field,"descriptor":"Z"}}
                for field in ("first","second")
            ]
            proof=compare_large_method_cfg(
                self._profile(jar,"Owner"),"restore",self.DESC,
                self._profile(recompiled,"Recompiled"),"restore",self.DESC,
                aliases,
            )
            self.assertEqual(proof["ordered_static_field_writes"],2)
            self.assertEqual(proof["ordered_typed_exception_table_entries"],2)
            self.assertTrue(proof["exact_branch_target_instruction_ordinals"])
            self.assertTrue(proof["exact_exception_type_and_instruction_ordinal_ranges"])
            public=(root/"private"/"direct-exception.aggregate.json").read_text()
            for val in ('"key.first"','"key.second"','"first"','p/Owner'):
                self.assertNotIn(val,public)

    def test_wrong_return_descriptor_or_empty_catch_is_vetoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._source())
            profile=self._profile(jar,"Owner")
            method=next(x for x in profile["methods"] if x["name"]=="restore")
            conv=next(x for x in method["instructions"]
                      if x["opcode"]=="0xb8")
            conv["descriptor"]="(Ljava/lang/String;)Ljava/lang/Object;"
            plan=plan_direct_empty_catch_sources(profile,"restore",self.DESC)
            self.assertEqual(plan["direct_six_instruction_boolean_try_catch_regions"],1)
            profile=self._profile(jar,"Owner")
            method=next(x for x in profile["methods"] if x["name"]=="restore")
            target=method["exception_handlers"][0]["handler_pc"]
            next(x for x in method["instructions"] if x["offset"]==target
                 )["opcode"]="0x57"
            plan=plan_direct_empty_catch_sources(profile,"restore",self.DESC)
            self.assertEqual(plan["direct_six_instruction_boolean_try_catch_regions"],1)

    def test_wrong_full_jar_sha_and_output_collision_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            jar=self._compile(root,"original","Owner",self._source())
            output=root/"private"
            with self.assertRaisesRegex(
                DirectLocalExceptionSourceError,"ORIGINAL_JAR_SHA256_MISMATCH"
            ):
                recover_private_direct_empty_catch_sources(
                    jar,"p/Owner.class","restore",self.DESC,
                    output,sha256="0"*64)
            self.assertFalse(output.exists())
            output.mkdir()
            keep=output/"KEEP"
            keep.write_text("KEEP",encoding="utf-8")
            with self.assertRaisesRegex(
                DirectLocalExceptionSourceError,"OUTPUT_ALREADY_EXISTS"
            ):
                recover_private_direct_empty_catch_sources(
                    jar,"p/Owner.class","restore",self.DESC,
                    output,sha256=self._sha(jar))
            self.assertEqual(keep.read_text(),"KEEP")


if __name__=="__main__":
    unittest.main()

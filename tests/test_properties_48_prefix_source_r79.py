"""R79 original 48-op typed prefix source roundtrip and mutations."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.properties_48_prefix_source import (
    OriginalPrefix48Error, plan_private_original_48_op_prefix,
    replay_private_48_prefix,
)

@unittest.skipUnless(shutil.which("javac"),"javac required")
class OriginalPrefix48Tests(unittest.TestCase):
    SOURCE = (
        "preflight();"
        "java.io.File originalLocalSlot0 = new java.io.File(path);"
        "if (!originalLocalSlot0.exists()) return;"
        "java.util.Properties originalLocalSlot1 = new java.util.Properties();"
        "java.io.FileInputStream originalLocalSlot2 ="
        "new java.io.FileInputStream(originalLocalSlot0);"
        "originalLocalSlot1.load(originalLocalSlot2);"
        "originalLocalSlot2.close();"
        'flag1=java.lang.Boolean.parseBoolean(originalLocalSlot1.getProperty("p1","false"));'
        'flag2=java.lang.Boolean.valueOf(originalLocalSlot1.getProperty("p2")).booleanValue();'
        'value=java.lang.Integer.valueOf(originalLocalSlot1.getProperty("p3")).intValue();'
        'flag3=java.lang.Boolean.valueOf(originalLocalSlot1.getProperty("p4")).booleanValue();'
    )
    def compile(self,root,label,body):
        src=root/label/"p"/"Owner.java"
        out=root/label/"classes"
        src.parent.mkdir(parents=True)
        out.mkdir()
        src.write_text(
            "package p; public class Owner {"
            'public static String path="not-a-real-file.properties";'
            "public static boolean flag1,flag2,flag3; public static int value;"
            "public static void preflight(){}"
            "public static void restore() throws java.io.IOException {"
            +body+"}"
            "}",encoding="utf-8")
        run=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-d",str(out),str(src)],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as z:z.write(out/"p"/"Owner.class","p/Owner.class")
        return jar

    def test_actual_java9_source_recompiled_exact_first_48_opcode_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=self.compile(root,"original",self.SOURCE)
            sha=hashlib.sha256(original.read_bytes()).hexdigest()
            dest=root/"private"
            result=replay_private_48_prefix(
                original,"p/Owner.class","restore","()V",dest,sha)
            self.assertEqual(result["exact_original_48_prefix_instruction_count"],48)
            self.assertEqual(result["original_initial_typed_assignment_counts"],{
                "boolean":3,"integer":1})
            fragment=(dest/"properties-48-prefix.private.java.txt").read_text()
            self.assertEqual(fragment.count("originalLocalSlot1.getProperty("),4)
            self.assertIn("flag1 = java.lang.Boolean.parseBoolean(",fragment)
            self.assertIn("value = java.lang.Integer.valueOf(",fragment)
            candidate=self.compile(root,"candidate",fragment)
            def first(j):
                m=next(x for x in profile_jar_class(j,"p/Owner.class")["methods"]
                       if x["name"]=="restore")
                return m["instructions"][:48]
            a,b=first(original),first(candidate)
            self.assertEqual([x["opcode"] for x in a],
                             [x["opcode"] for x in b])
            for x,y in zip(a,b):
                for key in ("owner","name","descriptor","constant"):
                    self.assertEqual(x.get(key),y.get(key))
            self.assertFalse(result["complete_original_697_instruction_method_compiled"])

    def test_direct_assignment_type_and_literal_mutations_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);jar=self.compile(root,"original",self.SOURCE)
            obj=profile_jar_class(jar,"p/Owner.class")
            method=next(m for m in obj["methods"] if m["name"]=="restore")
            method["instructions"][28]["name"]="badParse"
            with self.assertRaisesRegex(OriginalPrefix48Error,
                                        "TWO_ARGUMENT_PROPERTY_BOOLEAN_PARSE"):
                plan_private_original_48_op_prefix(obj,"restore","()V")
            obj=profile_jar_class(jar,"p/Owner.class")
            method=next(m for m in obj["methods"] if m["name"]=="restore")
            method["instructions"][47]["descriptor"]="I"
            with self.assertRaisesRegex(OriginalPrefix48Error,
                                        "WRONG_ORIGINAL_FIELD_OWNER_OR_DESCRIPTOR"):
                plan_private_original_48_op_prefix(obj,"restore","()V")
            obj=profile_jar_class(jar,"p/Owner.class")
            method=next(m for m in obj["methods"] if m["name"]=="restore")
            method["instructions"][25]["constant_pool_tag"]=3
            with self.assertRaisesRegex(OriginalPrefix48Error,
                                        "TWO_ARGUMENT_PROPERTY_STRING_LITERALS"):
                plan_private_original_48_op_prefix(obj,"restore","()V")

    def test_pin_mismatch_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);jar=self.compile(root,"original",self.SOURCE)
            dest=root/"private"
            with self.assertRaisesRegex(OriginalPrefix48Error,"ORIGINAL_JAR_SHA256_MISMATCH"):
                replay_private_48_prefix(
                    jar,"p/Owner.class","restore","()V",dest,"0"*64)
            self.assertFalse(dest.exists())

if __name__=="__main__":
    unittest.main()

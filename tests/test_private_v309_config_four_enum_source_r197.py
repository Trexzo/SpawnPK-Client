"""R197: invented Java9 enum-source tests, no original SpawnPK binary/source.

The baseline and alias candidates use independently authored, unrelated
readable enum names. The verifier must accept ONLY known extra final alias
fields and corresponding initializer writes, and reject changed constants,
branch conditions, field types or original JVM method bodies.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.bytecode_profile import profile_class_field_accesses
from spk_recovery.private_v309_config_four_enum_source_r197 import (
    R197OriginalConfigEnumError,
    audit_config_enum_classfiles,
)


class R197SyntheticConfigEnums(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("Java compiler unavailable")
        cls.tmp=TemporaryDirectory(prefix="r197-invented-config-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.fixtures=[
            {
                "class_name":"E0",
                "constants":("ALPHA","BETA"),
                "extra":'    private String c;\n    private String d;\n'
                         '    E0(String title,String uri){c=title;d=uri;}\n'
                         '    public String a(){return c;}\n'
                         '    public String b(){return d;}\n'
                         '    static String a(E0 e){return e.d;}\n'
                         '    static String b(E0 e){return e.c;}\n',
                "declaration":'ALPHA("Alpha","http://example.invalid"),'
                              'BETA("Beta","http://example.invalid");\n',
                "field_names":("c","d"),
                "aliases":(("aa","ALPHA"),("bb","BETA")),
            },
            {
                "class_name":"E1",
                "constants":("NORMAL","FROST","DUSK","AUTUMN","DAY"),
                "extra":'    public int f;\n'
                         '    E1(int color){this.f=color;}\n',
                "declaration":"NORMAL(0),FROST(255),DUSK(100),"
                              "AUTUMN(12345),DAY(0xaaaaaa);\n",
                "field_names":("f",),
                "aliases":(("aa","NORMAL"),("bb","FROST"),
                           ("cc","DUSK"),("dd","AUTUMN"),("ee","DAY")),
            },
            {
                "class_name":"E2",
                "constants":("FIXED","FLEX","WIDE"),
                "extra":'    public static E2 a(String str){\n'
                         '      for(E2 value:values()){\n'
                         '        if(value.name().equalsIgnoreCase(str))\n'
                         '          return value;\n'
                         '      }\n'
                         '      return FIXED;\n'
                         '    }\n',
                "declaration":"FIXED,FLEX,WIDE;\n",
                "field_names":(),
                "aliases":(("aa","FIXED"),("bb","FLEX"),("cc","WIDE")),
            },
            {
                "class_name":"E3",
                "constants":("NONE","SUN","RAIN","ICE","WIND","SNOW"),
                "extra":"",
                "declaration":"NONE,SUN,RAIN,ICE,WIND,SNOW;\n",
                "field_names":(),
                "aliases":(("aa","NONE"),("bb","SUN"),("cc","RAIN"),
                           ("dd","ICE"),("ee","WIND"),("ff","SNOW")),
            },
        ]
        for spec in cls.fixtures:
            name=spec["class_name"]
            body=("package invented;\n"
                  "public enum "+name+" {\n"+spec["declaration"]+
                  spec["extra"]+"}\n")
            aliases="".join("    public static final "+name+" "+a+"="+v+";\n"
                            for a,v in spec["aliases"])
            candidate=body.replace(spec["declaration"],
                                   spec["declaration"]+aliases)
            spec["old_source"]=body
            spec["new_source"]=candidate
            spec["old"]=cls.compile_java(name+"-baseline",name,body)
            spec["new"]=cls.compile_java(name+"-aliases",name,candidate)
            methods=profile_class_field_accesses(spec["old"])["methods"]
            spec["config"]={
                "constants":tuple((x,x) for x in spec["constants"]),
                "aliases":spec["aliases"],
                "array_field":"$VALUES",
                "array_method":"$values",
                "other_fields":spec["field_names"],
                "method_count":len(methods),
                "original_instruction_count":
                    sum(len(x["instructions"]) for x in methods),
                "source_derived_synthetic_accessors":(),
            }

    @classmethod
    def compile_java(cls,folder,name,source):
        root=cls.root/folder
        src=root/"src/invented"/(name+".java")
        src.parent.mkdir(parents=True,exist_ok=True)
        src.write_text(source,encoding="utf-8")
        out=root/"classes";empty=root/"empty"
        out.mkdir();empty.mkdir()
        p=subprocess.run([
            "javac","--release","9","-g:none","-proc:none",
            "-implicit:none","-classpath",str(empty),
            "-sourcepath",str(empty),"-d",str(out),str(src)],
            capture_output=True,check=False,timeout=70)
        if p.returncode:
            raise AssertionError("Synthetic enum Javac failure: "+
                                 p.stderr.decode(errors="replace"))
        return (out/"invented"/(name+".class")).read_bytes()

    def check(self,spec,rebuilt=None,**changes):
        kwargs={
            "owner":"invented/"+spec["class_name"],
            "config":spec["config"],
            "original_sha256":hashlib.sha256(spec["old"]).hexdigest(),
        }
        kwargs.update(changes)
        return audit_config_enum_classfiles(
            spec["old"],rebuilt if rebuilt is not None else spec["new"],
            **kwargs)

    def test_all_four_invented_enums_match_original_jvm_semantics(self):
        for spec in self.fixtures:
            with self.subTest(enum=spec["class_name"]):
                report=self.check(spec)
                self.assertEqual(
                    spec["config"]["method_count"],
                    report["original_jvm_methods_compared"])
                self.assertEqual(
                    spec["config"]["original_instruction_count"],
                    report["matched_original_semantic_jvm_instructions"])
                self.assertEqual(len(spec["constants"]),
                                 report["source_added_alias_fields"])
                self.assertFalse(report[
                    "original_binary_classfile_identity_claimed"])
                self.assertFalse(report["original_game_or_enum_methods_executed"])

    def test_wrong_alias_assignment_rejected(self):
        spec=self.fixtures[0]
        invalid=spec["new_source"].replace("aa=ALPHA;","aa=BETA;")
        blob=self.compile_java("bad-alias",spec["class_name"],invalid)
        with self.assertRaises(R197OriginalConfigEnumError):
            self.check(spec,blob)

    def test_wrong_enum_constant_order_rejected(self):
        spec=self.fixtures[1]
        invalid=spec["new_source"].replace(
            "NORMAL(0),FROST(255)","FROST(255),NORMAL(0)")
        blob=self.compile_java("bad-ordinal",spec["class_name"],invalid)
        with self.assertRaises(R197OriginalConfigEnumError):
            self.check(spec,blob)

    def test_changed_extra_instance_field_value_rejected(self):
        spec=self.fixtures[1]
        invalid=spec["new_source"].replace(
            "FROST(255)","FROST(254)")
        blob=self.compile_java("bad-enum-color",spec["class_name"],invalid)
        with self.assertRaises(R197OriginalConfigEnumError):
            self.check(spec,blob)

    def test_changed_case_insensitive_parser_rejected(self):
        spec=self.fixtures[2]
        invalid=spec["new_source"].replace(
            "equalsIgnoreCase(str)","equals(str)")
        blob=self.compile_java("bad-name-matcher",spec["class_name"],invalid)
        with self.assertRaises(R197OriginalConfigEnumError):
            self.check(spec,blob)

    def test_missing_alias_field_rejected(self):
        spec=self.fixtures[3]
        invalid=spec["new_source"].replace(
            "    public static final E3 ff=SNOW;\n","")
        blob=self.compile_java("missing-alias",spec["class_name"],invalid)
        with self.assertRaises(R197OriginalConfigEnumError):
            self.check(spec,blob)

    def test_wrong_original_digest_and_method_count_rejected(self):
        spec=self.fixtures[0]
        for changes in (
            {"original_sha256":"0"*64},
            {"owner":"invented/Other"},
            {"config":{**spec["config"],"method_count":5}},
            {"config":{**spec["config"],
                       "original_instruction_count":1}},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(R197OriginalConfigEnumError):
                    self.check(spec,**changes)


if __name__=="__main__":
    unittest.main()

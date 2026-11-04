"""R355 synthetic-only tests; original private Java stays outside hosted CI."""
from __future__ import annotations
import hashlib
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest
from zipfile import ZipFile

from scripts import prepare_v309_r355_readable_outline_npc as m

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

class R355ReadabilityTests(unittest.TestCase):
    def example(self):
        owner=(
            b'package rs.example;\n'
            b'public class Class999 { \n'
            b'  String literal = "ReadableClass";\n'
            b'  int field912 = 5;\n'
            b'  int get(){return this.field912;}\n'
            b'}\n'
        )
        consumer=b'package rs.example; class Consumer {Class999 value;}\n'
        name="rs/example/Class999.java"
        return {
            name:owner,
            "rs/example/Consumer.java":consumer,
        },(name,"ReadableClass",sha(owner),{
            name:1,"rs/example/Consumer.java":1
        })

    def patch_plan(self,source_plan):
        # This test data is tiny fake Java; owner SHA is derived only from
        # synthetic bytes. The real plan/pins stay unchanged.
        return (
            patch.object(m,"TYPES",(source_plan,)),
            patch.object(m,"FIELDS",(
                ("rs/example/ReadableClass.java","field912","capacity",2),
            )),
            patch.object(m,"COUNT",2),
        )

    def test_exact_reverse_does_not_corrupt_preexisting_readable_name(self):
        sources,plan=self.example()
        a,b,c=self.patch_plan(plan)
        with a,b,c:
            changed,witness=m.transform(sources)
        self.assertEqual(len(changed),2)
        self.assertEqual(len(witness),2)
        s=changed["rs/example/ReadableClass.java"].decode()
        self.assertIn('String literal = "ReadableClass";',s)
        self.assertIn("public class ReadableClass",s)
        self.assertIn("int capacity = 5;",s)
        self.assertIn("this.capacity;",s)
        self.assertIn("ReadableClass value;",changed["rs/example/Consumer.java"].decode())

    def test_wrong_owner_sha_refused(self):
        sources,plan=self.example()
        broken=(plan[0],plan[1],"0"*64,plan[3])
        a,b,c=self.patch_plan(broken)
        with a,b,c,self.assertRaisesRegex(m.Refused,"CLASS_SHA_MISMATCH"):
            m.transform(sources)

    def test_unexpected_class_reference_refused(self):
        sources,plan=self.example()
        sources["rs/example/Other.java"]=b"class Other { Class999 extra; }"
        a,b,c=self.patch_plan(plan)
        with a,b,patch.object(m,"COUNT",3),self.assertRaisesRegex(
                m.Refused,"UNEXPECTED_CLASS_REFERENCES"):
            m.transform(sources)

    def test_missing_owner_refused(self):
        sources,plan=self.example()
        sources.pop("rs/example/Class999.java")
        a,b,c=self.patch_plan(plan)
        with a,b,patch.object(m,"COUNT",1),self.assertRaisesRegex(
                m.Refused,"CLASS_SHA_MISMATCH"):
            m.transform(sources)

    def test_changed_field_references_refused(self):
        sources,plan=self.example()
        sources["rs/example/Consumer.java"]+=b"// field912\n"
        a,b,c=self.patch_plan(plan)
        with a,b,c,self.assertRaisesRegex(m.Refused,"UNEXPECTED_FIELD_REFERENCES"):
            m.transform(sources)

    def test_changed_source_count_refused(self):
        sources,plan=self.example()
        sources["rs/example/Extra.java"]=b"class Extra {}"
        a,b,c=self.patch_plan(plan)
        with a,b,c,self.assertRaisesRegex(m.Refused,"SOURCE_COUNT_CHANGED"):
            m.transform(sources)

    def test_new_target_file_collision_refused(self):
        sources,plan=self.example()
        sources["rs/example/ReadableClass.java"]=b"class ReadableClass {}"
        a,b,c=self.patch_plan(plan)
        with a,b,patch.object(m,"COUNT",3),self.assertRaisesRegex(
                m.Refused,"RENAMED_OWNER_ALREADY_EXISTS"):
            m.transform(sources)

    def test_inverse_at_positions_with_preexisting_identifier(self):
        text="ReadableClass Class999 ReadableClass Class999"
        new,positions=m.substitute(text,"Class999","ReadableClass")
        self.assertEqual(len(positions),2)
        self.assertEqual(m.inverse_at_positions(
            new,positions,"ReadableClass","Class999"),text)
        self.assertEqual(new.count("ReadableClass"),4)

    def test_wrong_inverse_position_fails(self):
        with self.assertRaisesRegex(m.Refused,"REVERSE_POSITION_CHANGED"):
            m.inverse_at_positions("Different", [0],"ReadableClass","Class999")

    def test_missing_and_fake_private_zip_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaisesRegex(m.Refused,"INPUT_NOT_REGULAR"):
                m.read_verified(root/"absent.zip")
            f=root/"fake.zip"
            with ZipFile(f,"w") as z:
                z.writestr("source/rs/example/X.java","class X {}")
            with self.assertRaisesRegex(m.Refused,"INPUT_ARCHIVE_SHA_WRONG"):
                m.read_verified(f)

    def test_output_reuse_never_changes_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            target=root/"already.zip"
            target.write_bytes(b"untouched")
            with self.assertRaisesRegex(m.Refused,"OUTPUT_MUST_BE_NEW"):
                m.create_private_zip(root/"absent.zip",target)
            self.assertEqual(target.read_bytes(),b"untouched")

    def test_real_plan_is_five_types_nine_fields(self):
        self.assertEqual(m.COUNT,1277)
        self.assertEqual(len(m.TYPES),5)
        self.assertEqual(len(m.FIELDS),9)
        self.assertEqual(sum(sum(t[3].values()) for t in m.TYPES)+
                         sum(6 if f[1]=="field4118" else f[3] for f in m.FIELDS),111)
        self.assertEqual(m.INPUT_SHA,
            "e515f96d753a8e0458c21b7a4ebf16c080411ea3ddbf85d184022497bfffd768")

if __name__=="__main__":
    unittest.main(verbosity=2)

"""R357 source-only synthetic tests: no private SpawnPK Java/JAR in GitHub CI."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts import prepare_v309_r357_readable_ui_layers as r

def digest(data):return hashlib.sha256(data).hexdigest()

class R357ReadabilityTests(unittest.TestCase):
    def setUp(self):
        self.owner="rs/example/Class999.java"
        self.user="rs/example/Caller.java"
        self.files={
            self.owner:(
                b'class Class999 { String prior="NamedDescriptor";'
                b' int field999=7;'
                b' int method999(){return field999;} }\n'),
            self.user:b'class Caller { Class999 instance; int get() {return instance.method999();} }\n'
        }
        self.types=[(self.owner,"Class999","NamedDescriptor",digest(self.files[self.owner]))]
        self.fields=[("rs/example/NamedDescriptor.java","field999","value")]
        self.methods=[("rs/example/NamedDescriptor.java","method999","getValue")]
        self.counts={
            "Class999":{self.owner:1,self.user:1},
            "field999":{self.owner:2},
            "method999":{self.owner:1,self.user:1},
        }

    def transform(self,source=None,types=None,fields=None,methods=None,expected=None,count=2):
        return r.transform(
            source if source is not None else self.files,
            types=types if types is not None else self.types,
            fields=fields if fields is not None else self.fields,
            methods=methods if methods is not None else self.methods,
            expected=expected if expected is not None else self.counts,
            expected_count=count)

    def test_rewrites_type_field_method_and_preserves_prior_literal(self):
        transformed,events=self.transform()
        self.assertEqual(len(transformed),2)
        self.assertEqual(len(events),3)
        source=transformed["rs/example/NamedDescriptor.java"].decode()
        self.assertIn("class NamedDescriptor",source)
        self.assertIn('prior="NamedDescriptor"',source)
        self.assertIn("int value=7",source)
        self.assertIn("int getValue()",source)
        self.assertIn("NamedDescriptor instance",transformed[self.user].decode())
        self.assertIn("instance.getValue()",transformed[self.user].decode())

    def test_bad_owner_sha_refused(self):
        wrong=[(self.owner,"Class999","NamedDescriptor","0"*64)]
        with self.assertRaisesRegex(r.Refused,"ORIGINAL_OWNER_SHA_CHANGED"):
            self.transform(types=wrong)

    def test_extra_caller_refused(self):
        files=dict(self.files)
        files[self.user]+=b"// Class999\n"
        with self.assertRaisesRegex(r.Refused,"REFERENCE_SCOPE_OR_COUNT_DRIFT"):
            self.transform(source=files)

    def test_declared_name_missing(self):
        files=dict(self.files)
        files[self.owner]=files[self.owner].replace(b"class Class999",b"class Other999")
        adjusted=[(self.owner,"Class999","NamedDescriptor",digest(files[self.owner]))]
        with self.assertRaisesRegex(r.Refused,"DECLARATION_MISSING"):
            self.transform(source=files,types=adjusted)

    def test_destination_collision_refused(self):
        files=dict(self.files)
        files["rs/example/NamedDescriptor.java"]=b'class NamedDescriptor{}'
        with self.assertRaisesRegex(r.Refused,"RENAMED_CLASS_COLLISION"):
            self.transform(source=files,count=3)

    def test_missing_owner_refused(self):
        files={self.user:self.files[self.user]}
        with self.assertRaisesRegex(r.Refused,"MISSING_OWNER"):
            self.transform(source=files,count=1)

    def test_source_count_is_enforced(self):
        with self.assertRaisesRegex(r.Refused,"WRONG_SOURCE_COUNT"):
            self.transform(count=3)

    def test_input_zip_hash_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fake.zip"
            with ZipFile(p,"w") as z:z.writestr("source/rs/Fake.java","class Fake{}")
            with self.assertRaisesRegex(r.Refused,"PRIVATE_R356_SHA_MISMATCH"):
                r.read_source_zip(p)

    def test_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"existing.zip"
            out.write_bytes(b"unchanged")
            with self.assertRaisesRegex(r.Refused,"NEVER_OVERWRITE"):
                r.stage(Path(d)/"missing.zip",out)
            self.assertEqual(out.read_bytes(),b"unchanged")

    def test_exact_positional_inverse_does_not_rename_preexisting_text(self):
        before="NamedDescriptor Class999 NamedDescriptor Class999"
        after,locations=r.replace_words(before,"Class999","NamedDescriptor")
        self.assertEqual(len(locations),2)
        self.assertEqual(
            r.undo_word_positions(after,"Class999","NamedDescriptor",locations),
            before)

    def test_inverse_drift_fails_closed(self):
        with self.assertRaisesRegex(r.Refused,"INVERSE_POSITION_DRIFT"):
            r.undo_word_positions("WRONG","Class999","NamedDescriptor",[0])

    def test_pinned_complete_symbol_witness(self):
        self.assertEqual((len(r.TYPES),len(r.FIELDS),len(r.METHODS)),(5,9,5))
        self.assertEqual(r.COUNT,1277)
        self.assertEqual(sum(sum(x.values()) for x in r.EXPECTED.values()),108)
        self.assertEqual(len(r.INPUT_SHA),64)
        self.assertEqual(len(set(x[1] for x in r.TYPES+r.FIELDS+r.METHODS)),19)

if __name__=="__main__":
    unittest.main(verbosity=2)

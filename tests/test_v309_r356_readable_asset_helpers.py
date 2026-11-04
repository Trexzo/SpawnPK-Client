"""R356 regression tests using synthetic source only (no proprietary client Java)."""
from __future__ import annotations
import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from scripts import prepare_v309_r356_readable_asset_helpers as r

def digest(raw):return hashlib.sha256(raw).hexdigest()

class R356ReadableTests(unittest.TestCase):
    def setUp(self):
        self.owner="rs/example/Class999.java"
        self.caller="rs/example/Caller.java"
        self.source={
            self.owner:(
                b'class Class999 {String name="ReadableThing";'
                b' int field999=1;'
                b' int method999(){return field999;} }'),
            self.caller:b'class Caller {Class999 key;}'
        }
        self.types=[(self.owner,"Class999","ReadableThing",
                     digest(self.source[self.owner]),2)]
        self.fields=[("rs/example/ReadableThing.java","field999","cacheSize",2)]
        self.methods=[("rs/example/ReadableThing.java","method999","getCacheSize",1)]

    def change(self,source=None,classes=None,fields=None,methods=None,expected=2):
        return r.transform(source if source is not None else self.source,
                           expected_count=expected,
                           classes=classes if classes is not None else self.types,
                           fields=fields if fields is not None else self.fields,
                           methods=methods if methods is not None else self.methods)

    def test_type_field_method_renames_preserve_preexisting_string(self):
        out,operations=self.change()
        self.assertEqual(len(out),2)
        self.assertEqual(len(operations),3)
        self.assertNotIn(self.owner,out)
        text=out["rs/example/ReadableThing.java"].decode()
        self.assertIn("class ReadableThing",text)
        self.assertIn('name="ReadableThing"',text)
        self.assertIn("int cacheSize=1",text)
        self.assertIn("int getCacheSize()",text)
        self.assertIn(b"ReadableThing key;",out[self.caller])

    def test_wrong_owner_sha_rejected(self):
        wrong=[(self.owner,"Class999","ReadableThing","0"*64,2)]
        with self.assertRaisesRegex(r.Refused,"OWNER_SHA_CHANGED"):
            self.change(classes=wrong)

    def test_unexpected_extra_reference_rejected(self):
        source=dict(self.source)
        source[self.caller]=b'class Caller {Class999 key; Class999 other;}'
        with self.assertRaisesRegex(r.Refused,"REFERENCE_COUNT_OR_OWNER_DRIFT"):
            self.change(source=source)

    def test_missing_owner_rejected(self):
        src={self.caller:self.source[self.caller]}
        with self.assertRaisesRegex(r.Refused,"OWNER_MISSING"):
            self.change(source=src,expected=1)

    def test_existing_destination_rejected(self):
        src=dict(self.source)
        src["rs/example/ReadableThing.java"]=b'class ReadableThing {}'
        with self.assertRaisesRegex(r.Refused,"OWNER_COLLISION"):
            self.change(source=src,expected=3)

    def test_source_file_count_enforced(self):
        with self.assertRaisesRegex(r.Refused,"SOURCE_COUNT_DRIFT"):
            self.change(expected=3)

    def test_old_names_reversed_without_touching_same_text(self):
        original="ReadableThing Class999 ReadableThing Class999"
        modified,positions=r.replace(original,"Class999","ReadableThing")
        self.assertEqual(len(positions),2)
        self.assertEqual(r.reverse(modified,positions,"Class999","ReadableThing"),original)

    def test_reversal_rejects_drift(self):
        with self.assertRaisesRegex(r.Refused,"REVERSE_POSITION_DRIFT"):
            r.reverse("other",[0],"Class999","ReadableThing")

    def test_private_r355_zip_required(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(r.Refused,"R355_INPUT_SHA_INVALID"):
                r.read_input(Path(td)/"missing.zip")

    def test_modified_input_zip_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.zip"
            with ZipFile(p,"w") as z:z.writestr("source/rs/X.java",b"class X{}")
            with self.assertRaisesRegex(r.Refused,"R355_INPUT_SHA_INVALID"):
                r.read_input(p)

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"exists.zip";p.write_bytes(b"keep")
            with self.assertRaisesRegex(r.Refused,"OUTPUT_ALREADY_EXISTS"):
                r.produce(Path(td)/"missing.zip",p)
            self.assertEqual(p.read_bytes(),b"keep")

    def test_real_plan_has_required_scope(self):
        self.assertEqual((len(r.CLASSES),len(r.FIELDS),len(r.METHODS)),(7,13,13))
        self.assertEqual(sum(x[-1] for x in r.CLASSES+r.FIELDS+r.METHODS),178)
        self.assertEqual(r.SOURCE_COUNT,1277)
        self.assertEqual(r.INPUT_SHA,
                         "7b58b0cc0292aa1a573ff2d1b940eb92fbbb0c7676b9cfdb4931b6824d00ad2c")
        self.assertEqual(len({x[1] for x in r.CLASSES+r.FIELDS+r.METHODS}),33)

if __name__=="__main__":
    unittest.main(verbosity=2)

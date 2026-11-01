"""R354 public synthetic tests. Actual 1,277 Java source lives owner-private."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZIP_DEFLATED,ZipFile
from scripts.prepare_v309_r354_readable_subsystems import (
    COUNT,INPUT_SHA,OWNER_SHA,RENAMES,SourceRefused,transform,verified_input,
    create_private_zip
)

class R354Tests(unittest.TestCase):
    def setUp(self):
        # These are SMALL FAKE Java files; no original/client code in CI.
        self.sources={
            "rs/eventbus/Class87.java":b'class Class87 { /* EventBus.Subscriber getPriority() getMethod() */ }',
            "rs/eventbus/EventBus.java":b'class EventBus { Class87 subscriber; }',
            "rs/cache/osrs/util/Class49.java":(
                b'class Class49 { /* RandomAccessFile IndexStore GZIPInputStream */'
                b' int field373,field374,field375,field376;'
                b' byte[] method2942(int var1, int var2, boolean var3) {return null;} }'),
            "rs/cache/osrs/util/Class47.java":(
                b'class Class47 { final int field370=0;'
                b' final String field371="",field372=""; }'),
            "rs/cache/osrs/util/Class48.java":(
                b'interface Class48 {void accept(int var1, int var2, int var3, int var4); }'),
            "rs/config/Class50.java":(
                b'interface Class50 {String key(); String name(); int position();}'),
            "rs/cache/osrs/util/OsrsMapDependencyScanner.java":(
                b'class Scan { Class49 reader; Class47 record; Class48 visitor;'
                b' void f() { reader.method2942(1,2,true); }}'),
            "rs/config/ConfigItemDescriptor.java":b'class CI implements Class50 {}',
            "rs/config/ConfigSectionDescriptor.java":b'class CS implements Class50 {}',
            "rs/plugins/configs/ConfigPanel.java":b'class CP { Class50 element; }',
        }
    def test_synthetic_named_roles_reversible(self):
        out,receipt=transform(self.sources,strict=False)
        self.assertEqual(len(out),len(self.sources))
        self.assertEqual(len(receipt),13)
        for name in ("EventBusSubscriber","IndexedCacheFileReader",
                     "MapDependencyRecord","LandscapePlacementVisitor",
                     "ConfigElementDescriptor"):
            self.assertTrue(any(p.endswith("/"+name+".java") for p in out))
        self.assertIn(b'readIndexedFile(',out[
            "rs/cache/osrs/util/IndexedCacheFileReader.java"])
        self.assertIn(b'dependencyReference',out[
            "rs/cache/osrs/util/MapDependencyRecord.java"])
        self.assertEqual(receipt[0]["old"],"Class87")

    def test_missing_owner_refused(self):
        sources=dict(self.sources)
        sources.pop("rs/eventbus/Class87.java")
        with self.assertRaisesRegex(SourceRefused,"MISSING_OWNER"):
            transform(sources,strict=False)

    def test_unexpected_owner_reference_refused(self):
        sources=dict(self.sources)
        sources["rs/unrelated/Stranger.java"]=b"class Stranger { Class87 x; }"
        with self.assertRaisesRegex(SourceRefused,"UNEXPECTED_REFERENCE_OWNER"):
            transform(sources,strict=False)

    def test_existing_destination_rejected(self):
        sources=dict(self.sources)
        sources["rs/eventbus/EventBusSubscriber.java"]=b"class EventBusSubscriber {}"
        with self.assertRaisesRegex(SourceRefused,"TARGET_OWNER_ALREADY_EXISTS"):
            transform(sources,strict=False)

    def test_changed_cache_method_signature_rejected(self):
        sources=dict(self.sources)
        p="rs/cache/osrs/util/Class49.java"
        sources[p]=sources[p].replace(
            b"byte[] method2942(int var1, int var2, boolean var3)",
            b"byte[] method2942(int a, int b, boolean c)")
        with self.assertRaisesRegex(SourceRefused,"CACHE_READER_METHOD_SHAPE_CHANGED"):
            transform(sources,strict=False)

    def test_changed_config_descriptor_shape_rejected(self):
        sources=dict(self.sources)
        p="rs/config/Class50.java"
        sources[p]=sources[p].replace(b"int position()",b"int priority()")
        with self.assertRaisesRegex(SourceRefused,"OWNER_BEHAVIOR_SHAPE_CHANGED"):
            transform(sources,strict=False)

    def test_exact_reference_counts_required_in_full_corpus(self):
        with self.assertRaisesRegex(SourceRefused,"INPUT_SOURCE_COUNT_CHANGED"):
            transform(self.sources,strict=True)
        self.assertEqual(COUNT,1277)
        self.assertEqual(sum(sum(x[3].values()) for x in RENAMES),92)

    def test_missing_private_input_not_created(self):
        with tempfile.TemporaryDirectory() as temp:
            stage=Path(temp)
            with self.assertRaisesRegex(SourceRefused,"PRIVATE_SOURCE_ZIP_MISSING"):
                create_private_zip(stage/"missing.zip",stage/"result.zip")
            self.assertFalse((stage/"result.zip").exists())

    def test_modified_archive_sha_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            stage=Path(temp)
            f=stage/"synthetic.zip"
            with ZipFile(f,"w",ZIP_DEFLATED) as z:
                z.writestr("source/rs/Client.java",b"class Client {}")
            with self.assertRaisesRegex(SourceRefused,"ZIP_SHA_MISMATCH"):
                verified_input(f)

    def test_existing_private_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            stage=Path(temp)
            out=stage/"exists.zip"
            out.write_bytes(b"leave alone")
            with self.assertRaisesRegex(SourceRefused,"REFUSE_TO_OVERWRITE"):
                create_private_zip(stage/"missing.zip",out)
            self.assertEqual(out.read_bytes(),b"leave alone")

    def test_private_owner_hash_pins_are_complete(self):
        self.assertEqual(len(OWNER_SHA),5)
        self.assertEqual(len(INPUT_SHA),64)
        self.assertEqual(len(RENAMES),13)
        self.assertTrue(all(len(x)==64 for x in OWNER_SHA.values()))

if __name__=="__main__":
    unittest.main(verbosity=2)

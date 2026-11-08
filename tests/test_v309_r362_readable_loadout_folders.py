"""R362 synthetic-only tests; no recovered/private Java source is checked in."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts import prepare_v309_r362_readable_loadout_folders as r

def h(value):
    return hashlib.sha256(value).hexdigest()

class R362Tests(unittest.TestCase):
    def setUp(self):
        self.folder = "rs/gui/loadouts/LoadoutFolders.java"
        self.defaults = "rs/gui/loadouts/equipment/DefaultLoadout.java"
        self.sources = {
            self.folder: ("""
            class LoadoutFolders {
              Object field3277; String field3278; Object field3279;
              String label = "field3277 method2087"; // method2787 remains in a comment
              void method1237() { method1632(); }
              void method1043() { method2787(); }
              void method2787() { method2390(); }
              void method2390() { if(method2087()) field3277 = null; }
              void method1632() { field3279 = field3277; }
              boolean method2087() {return field3278 != null && DefaultLoadout.field3315.length > 0;}
            }
            """).encode(),
            self.defaults: b"class DefaultLoadout { static char[] field3315={'a'}; }",
        }
        self.witness = {
            "source_archive_sha256": r.SOURCE_SHA,
            "source_count": 2,
            "fields": {
                "field3277":"ownerLoadoutsPanel","field3278":"selectedFolderName",
                "field3279":"selectedLoadout","field3315":"allowedFolderNameCharacters",
            },
            "methods": {
                "method1237":"setSelectedFolderAndLoadout",
                "method1043":"createLoadoutInFolder",
                "method2787":"saveFolderWithOrder",
                "method2390":"saveCurrentFolder",
                "method1632":"syncEquipmentSelection",
                "method2087":"validateNewFolderName",
            },
            "owner_sha256": {p:h(raw) for p,raw in self.sources.items()},
            "token_references": r.census(self.sources, {
                "field3277","field3278","field3279","field3315",
                "method1237","method1043","method2787",
                "method2390","method1632","method2087",
            }),
        }

    def apply(self, sources=None, witness=None):
        return r.apply(sources or self.sources, witness or self.witness,
                       expected_count=2, expected_archive_sha=r.SOURCE_SHA)

    def make_zip(self, path, manifest_edit=None):
        manifest = {"source_count":2,"exact_inverse_passed":True,
                    "source_sha256":{p:h(raw) for p,raw in self.sources.items()}}
        if manifest_edit:
            manifest.update(manifest_edit)
        with ZipFile(path,"w") as archive:
            for name,raw in self.sources.items():
                archive.writestr("source/"+name,raw)
            archive.writestr(r.OLD_MANIFEST,json.dumps(manifest))
        return h(path.read_bytes())

    def test_ten_renames_source_grounded(self):
        out,n=self.apply()
        self.assertGreater(n,10)
        s=out[self.folder].decode()
        self.assertIn("ownerLoadoutsPanel",s)
        self.assertIn("setSelectedFolderAndLoadout()",s)
        self.assertIn("DefaultLoadout.allowedFolderNameCharacters",s)
        self.assertIn('"field3277 method2087"',s)
        self.assertIn("// method2787 remains",s)

    def test_source_sha_pin(self):
        self.assertEqual(r.SOURCE_SHA,
            "5905feaac54d8d449dbdb92cd3ce941d23e28e5e25c5033ea428d33d47bc3fe7")

    def test_original_owner_hash_changed_refused(self):
        self.witness["owner_sha256"][self.folder]="0"*64
        with self.assertRaisesRegex(r.Refused,"DECLARING_OWNER_SHA_CHANGED"):
            self.apply()

    def test_unlisted_reference_refused(self):
        self.sources[self.folder]+=b"\nfield3277"
        self.witness["owner_sha256"][self.folder]=h(self.sources[self.folder])
        with self.assertRaisesRegex(r.Refused,"REFERENCE_CENSUS_CHANGED"):
            self.apply()

    def test_destination_collision_refused(self):
        self.sources[self.folder]+=b"\nint selectedFolderName;"
        self.witness["owner_sha256"][self.folder]=h(self.sources[self.folder])
        with self.assertRaisesRegex(r.Refused,"DESTINATION_IDENTIFIER_COLLISION"):
            self.apply()

    def test_empty_symbols_refused(self):
        self.witness["methods"].pop("method2087")
        with self.assertRaisesRegex(r.Refused,"R362_RENAME_SCOPE_CHANGED"):
            self.apply()

    def test_declaring_owner_set_refused(self):
        self.witness["owner_sha256"].pop(self.defaults)
        with self.assertRaisesRegex(r.Refused,"R362_RENAME_SCOPE_CHANGED"):
            self.apply()

    def test_wrong_source_archive_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"fake.zip"
            self.make_zip(p)
            with self.assertRaisesRegex(r.Refused,"ARCHIVE_HASH_MISMATCH"):
                r.verified_input(p,expected_sha="0"*64,expected_count=2)

    def test_synthetic_archive_manifest_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"fake.zip"
            sha=self.make_zip(p)
            self.assertEqual(r.verified_input(p,expected_sha=sha,expected_count=2),
                             self.sources)

    def test_bad_manifest_hash_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"fake.zip"
            sha=self.make_zip(p,{"source_sha256":{x:"0"*64 for x in self.sources}})
            with self.assertRaisesRegex(r.Refused,"SOURCE_FILE_DIGEST_DRIFT"):
                r.verified_input(p,expected_sha=sha,expected_count=2)

    def test_false_prior_inverse_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"fake.zip"
            sha=self.make_zip(p,{"exact_inverse_passed":False})
            with self.assertRaisesRegex(r.Refused,"MANIFEST_COUNT_MISMATCH"):
                r.verified_input(p,expected_sha=sha,expected_count=2)

    def test_existing_private_output_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"existing.zip"
            p.write_bytes(b"preserve")
            with self.assertRaisesRegex(r.Refused,"OUTPUT_ALREADY_EXISTS"):
                r.produce(Path(tmp)/"missing.zip",Path(tmp)/"missing.json",p)
            self.assertEqual(p.read_bytes(),b"preserve")

    def test_malformed_literal_refused(self):
        with self.assertRaisesRegex(r.Refused,"UNTERMINATED_LITERAL"):
            list(r.identifiers('class X { String s="unterminated; }'))

    def test_invalid_comment_refused(self):
        with self.assertRaisesRegex(r.Refused,"UNCLOSED_BLOCK_COMMENT"):
            list(r.identifiers("class X {/* unclosed"))

    def test_no_game_runtime_or_auth_claims(self):
        self.assertEqual(r.TOTAL,1277)
        self.assertEqual(r.OLD_MANIFEST,"PRIVATE_R361_READABILITY_MANIFEST.json")
        self.assertEqual(r.NEW_MANIFEST,"PRIVATE_R362_READABILITY_MANIFEST.json")

if __name__=="__main__":
    unittest.main()

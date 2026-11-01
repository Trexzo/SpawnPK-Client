"""R351 synthetic full-source archive intake regressions (no private sources in CI)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from scripts.prepare_v309_r211_source_candidate import (
    CandidateRefused,
    prepare_candidate,
    _read_candidate,
    R211_SHA256,
    R211_JAVA_COUNT,
)

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = {
            "rs/A.java": b"package rs; class A { int field1; }\n",
            "rs/B.java": b"package rs; class B { void method2() {} }\n",
        }

    def archive(self, sources=None, *, mutate=None, name="test.zip"):
        source = self.sources if sources is None else sources
        p = self.root / name
        manifest = {
            "count": len(source),
            "files": {n: hashlib.sha256(b).hexdigest() for n,b in source.items()},
        }
        if mutate:
            mutate(manifest)
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as archive:
            for n,b in source.items():
                archive.writestr("src/" + n,b)
            archive.writestr("PRIVATE_SOURCE_SHA256_MANIFEST.json",
                             json.dumps(manifest))
        return p,hashlib.sha256(p.read_bytes()).hexdigest()

    def test_safe_archive_stages_all_private_source_bytes(self):
        archive,sha=self.archive()
        result=prepare_candidate(archive,self.root/"new",expected_sha=sha,
                                 expected_count=2)
        self.assertEqual(result["java_files"],2)
        self.assertEqual(result["readability"]["files_with_field_number"],1)
        self.assertEqual(result["readability"]["files_with_method_number"],1)
        self.assertFalse(result["buildable_client"])
        self.assertFalse(result["publishable_recovered_source"])
        for name,blob in self.sources.items():
            self.assertEqual((self.root/"new"/"src"/name).read_bytes(),blob)

    def test_stage_cannot_overwrite(self):
        archive,sha=self.archive()
        target=self.root/"new"
        target.mkdir()
        keep=target/"old"
        keep.write_text("keep")
        with self.assertRaisesRegex(CandidateRefused,"OUTPUT_MUST_BE_NEW"):
            prepare_candidate(archive,target,expected_sha=sha,expected_count=2)
        self.assertEqual(keep.read_text(),"keep")

    def test_archive_sha_pin_blocks_modified_archive(self):
        archive,sha=self.archive()
        with self.assertRaisesRegex(CandidateRefused,"SHA256"):
            prepare_candidate(archive,self.root/"out",
                              expected_sha="0"*64,expected_count=2)
        self.assertFalse((self.root/"out").exists())

    def test_wrong_file_hash_blocks_before_staging(self):
        archive,sha=self.archive(mutate=lambda m:m["files"].update(
            {"rs/B.java":"0"*64}))
        with self.assertRaisesRegex(CandidateRefused,"SOURCE_SHA"):
            prepare_candidate(archive,self.root/"out",expected_sha=sha,
                              expected_count=2)
        self.assertFalse((self.root/"out").exists())

    def test_missing_java_blocks(self):
        archive,sha=self.archive()
        with self.assertRaisesRegex(CandidateRefused,"COUNT"):
            prepare_candidate(archive,self.root/"out",expected_sha=sha,
                              expected_count=3)

    def test_unsafe_path_rejected(self):
        archive,sha=self.archive({"../outside.java":b"class X {}"})
        with self.assertRaisesRegex(CandidateRefused,"UNSAFE"):
            _read_candidate(archive,sha,1)

    def test_casefold_collision_blocks_windows(self):
        source={"rs/A.java":b"class A {}","rs/a.java":b"class a {}"}
        archive,sha=self.archive(source)
        with self.assertRaisesRegex(CandidateRefused,"WINDOWS_PATH"):
            _read_candidate(archive,sha,2)

    def test_duplicate_entry_blocks(self):
        p=self.root/"dup.zip"
        with zipfile.ZipFile(p,"w") as z:
            z.writestr("src/rs/A.java",self.sources["rs/A.java"])
            z.writestr("src/rs/A.java",self.sources["rs/A.java"])
            z.writestr("PRIVATE_SOURCE_SHA256_MANIFEST.json", "{}")
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaisesRegex(CandidateRefused,"DUPLICATE"):
            _read_candidate(p,sha,2)

    def test_manifest_entry_set_mismatch(self):
        archive,sha=self.archive(mutate=lambda m:m["files"].pop("rs/B.java"))
        with self.assertRaisesRegex(CandidateRefused,"INNER_MANIFEST"):
            _read_candidate(archive,sha,2)

    def test_utf8_required(self):
        archive,sha=self.archive({"rs/X.java":b"\xff"})
        with self.assertRaisesRegex(CandidateRefused,"UTF8"):
            prepare_candidate(archive,self.root/"out",expected_sha=sha,
                              expected_count=1)
        self.assertFalse((self.root/"out").exists())

    def test_symlink_entry_refused(self):
        archive,sha=self.archive()
        with zipfile.ZipFile(archive,"a") as z:
            info=zipfile.ZipInfo("src/rs/link.java")
            info.create_system=3
            info.external_attr=(stat.S_IFLNK | 0o777)<<16
            z.writestr(info,"../outside.java")
        sha=hashlib.sha256(archive.read_bytes()).hexdigest()
        with self.assertRaisesRegex(CandidateRefused,"SYMLINK"):
            _read_candidate(archive,sha,3)

    def test_unexpected_non_source_refused(self):
        archive,sha=self.archive({"rs/notes.txt":b"hello"})
        with self.assertRaisesRegex(CandidateRefused,"NON_SOURCE"):
            _read_candidate(archive,sha,1)

    def test_archive_pin_is_stable(self):
        self.assertEqual(R211_JAVA_COUNT,1275)
        self.assertEqual(len(R211_SHA256),64)
        self.assertEqual(R211_SHA256,
            "3f8ade7a37a1c8fe21dea367cf48660418c25a4905d943fe9358aa8846c275f0")

if __name__=="__main__":
    unittest.main(verbosity=2)

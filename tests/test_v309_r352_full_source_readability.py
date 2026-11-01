"""R352 synthetic full R315 intake tests: never upload private game/source to CI."""
from __future__ import annotations
import hashlib
from io import BytesIO
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from scripts.prepare_v309_r315_complete_readable_source import (
    R315IntakeRefused,checked_archive,stage,R315_ARCHIVE_SHA,
    R315_JAVA_COUNT,R315_REBUILT_JAR_SHA
)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def fake_jar(member="vendor/Dependency.class"):
    blob=BytesIO()
    with zipfile.ZipFile(blob,"w") as z:
        z.writestr(member,b"\xca\xfe\xba\xbe")
    return blob.getvalue()

class R352Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.sources={
            "source/rs/SourceA.java":b"package rs; class SourceA {}\n",
            "source/rs/SourceB.java":b"package rs; class SourceB {}\n",
        }
    def archive(self, *,sources=None,deps=None,mutate=None):
        sources=self.sources if sources is None else sources
        deps=deps if deps is not None else {
            "dependencies/R218.jar":fake_jar(),
            "dependencies/R239_filtered.jar":fake_jar(),
        }
        r315={"source_count":len(sources),
              "source_file_sha256":{k:sha(v) for k,v in sources.items()}}
        build={"source_sha256":{k[7:]:sha(v) for k,v in sources.items()},
               "dependency_sha256":{k.split("/")[-1]:sha(v) for k,v in deps.items()},
               "jar_sha256":"synthetic-not-original"}
        if mutate:mutate(r315,build)
        p=self.root/"fixture.zip"
        with zipfile.ZipFile(p,"w",zipfile.ZIP_DEFLATED) as z:
            for n,v in {**sources,**deps}.items():
                z.writestr(n,v)
            z.writestr("R315_MANIFEST.json",json.dumps(r315))
            z.writestr("MANIFEST.json",json.dumps(build))
        return p,sha(p.read_bytes())

    def checked(self,p,s,**kwargs):
        return checked_archive(p,expected_archive_sha=s,expected_java_count=2,**kwargs)

    def test_complete_source_and_non_rs_dependencies_checked(self):
        p,s=self.archive()
        result=self.checked(p,s)
        self.assertEqual(result, {k[7:]:v for k,v in self.sources.items()})

    def test_private_baseline_output_preserves_all_bytes(self):
        p,s=self.archive()
        out=self.root/"candidate"
        report=stage(p,out,mode="baseline",expected_archive_sha=s,
                     expected_java_count=2)
        self.assertEqual(report["source_count"],2)
        self.assertIsNone(report["semantic_rename_candidate"])
        self.assertFalse(report["source_milestone_publishable"])
        self.assertEqual((out/"source/rs/SourceA.java").read_bytes(),
                         self.sources["source/rs/SourceA.java"])
        self.assertFalse((out/"dependencies").exists())

    def test_wrong_archive_sha_refused(self):
        p,s=self.archive()
        with self.assertRaisesRegex(R315IntakeRefused,"ARCHIVE_SHA"):
            self.checked(p,"0"*64)

    def test_source_sha_mismatch_refused(self):
        p,s=self.archive(mutate=lambda r,b:r["source_file_sha256"].update(
            {"source/rs/SourceA.java":"0"*64}))
        with self.assertRaisesRegex(R315IntakeRefused,"SOURCE_SHA"):
            self.checked(p,s)

    def test_wrong_java_count_refused(self):
        p,s=self.archive()
        with self.assertRaisesRegex(R315IntakeRefused,"COUNT"):
            checked_archive(p,expected_archive_sha=s,expected_java_count=3)

    def test_source_set_mismatch_refused(self):
        p,s=self.archive(mutate=lambda r,b:r["source_file_sha256"].pop(
            "source/rs/SourceA.java"))
        with self.assertRaisesRegex(R315IntakeRefused,"COUNT"):
            self.checked(p,s)

    def test_project_class_dependency_refused(self):
        p,s=self.archive(deps={
            "dependencies/R218.jar":fake_jar("rs/Client.class"),
            "dependencies/R239_filtered.jar":fake_jar(),
        })
        with self.assertRaisesRegex(R315IntakeRefused,"PROJECT_BINARY_FALLBACK"):
            self.checked(p,s)

    def test_missing_dependency_refused(self):
        p,s=self.archive(deps={
            "dependencies/R218.jar":fake_jar(),
        })
        with self.assertRaisesRegex(R315IntakeRefused,"MISSING_DEPENDENCY"):
            self.checked(p,s)

    def test_dependency_digest_drift_refused(self):
        p,s=self.archive(mutate=lambda r,b:b["dependency_sha256"].update(
            {"R218.jar":"0"*64}))
        with self.assertRaisesRegex(R315IntakeRefused,"DEPENDENCY_SHA"):
            self.checked(p,s)

    def test_directory_traversal_refused(self):
        p,s=self.archive(sources={
            "source/../escape.java":b"class Escape {}",
        })
        with self.assertRaisesRegex(R315IntakeRefused,"UNSAFE"):
            checked_archive(p,expected_archive_sha=s,expected_java_count=1,
                            check_dependency_jars=False)

    def test_existing_private_output_untouched(self):
        p,s=self.archive()
        out=self.root/"existing"
        out.mkdir()
        (out/"keep").write_text("keep")
        with self.assertRaisesRegex(R315IntakeRefused,"OUTPUT_MUST_BE_NEW"):
            stage(p,out,mode="baseline",expected_archive_sha=s,expected_java_count=2)
        self.assertEqual((out/"keep").read_text(),"keep")

    def test_symlink_member_refused(self):
        p,s=self.archive()
        with zipfile.ZipFile(p,"a") as z:
            item=zipfile.ZipInfo("source/rs/Sneaky.java")
            item.create_system=3
            item.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(item,"../../target")
        s=sha(p.read_bytes())
        with self.assertRaisesRegex(R315IntakeRefused,"UNSAFE"):
            self.checked(p,s)

    def test_original_r315_pins_are_immutable(self):
        self.assertEqual(R315_JAVA_COUNT,1277)
        self.assertEqual(R315_REBUILT_JAR_SHA,
                         "b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721")
        self.assertEqual(R315_ARCHIVE_SHA,
                         "e46a213ba949dc0a2f420a040b5c9d38451c0923e3ea39917a5d2eb3c9b2fa28")

if __name__ == "__main__":
    unittest.main(verbosity=2)

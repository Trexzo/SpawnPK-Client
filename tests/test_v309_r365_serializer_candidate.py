"""R365 public synthetic-only provenance tests. Never load proprietary client code."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts import verify_v309_r365_serializer_candidate as r

def sha(b):
    return hashlib.sha256(b).hexdigest()

class R365Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.owner = "rs/synthetic/Codec.java"
        self.before = {self.owner:b"class Codec { int old; }",
                       "rs/synthetic/Other.java":b"class Other {}"}
        self.after = {**self.before, self.owner:b"class Codec { int repaired; }"}

    def pack(self, path, sources, manifest, attributes=None):
        report = {"source_count":len(sources),
                  "source_sha256":{p:sha(b) for p,b in sources.items()}}
        report.update(attributes or {})
        with ZipFile(path,"w") as archive:
            for p,b in sources.items():
                archive.writestr("source/"+p,b)
            archive.writestr(manifest,json.dumps(report))
        return sha(path.read_bytes())

    def pair(self, changes=None, receipt=None):
        a,b = self.root/"before.zip",self.root/"after.zip"
        old_sha = self.pack(a,self.before,"before.json")
        after = changes or self.after
        data = {"changed_source_files":[self.owner],
                "old_owner_sha256":sha(self.before[self.owner]),
                "new_owner_sha256":sha(after[self.owner]),
                "old_source_zip_sha256":old_sha,
                "serialized_format_changed":False,
                "private_source_release_approved":False,
                "original_v309_binary_parity":"NOT_TESTED",
                "real_game_runtime":"NOT_TESTED"}
        data.update(receipt or {})
        new_sha = self.pack(b,after,"after.json",data)
        opts = {"old_sha":old_sha,"new_sha":new_sha,"old_manifest":"before.json",
                "new_manifest":"after.json","count":2,"owner":self.owner,
                "old_owner":sha(self.before[self.owner]),
                "new_owner":sha(after[self.owner])}
        return a,b,opts

    def test_exact_delta_passes_with_explicit_nontested_gates(self):
        a,b,opts = self.pair()
        result = r.verify_pair(a,b,**opts)
        self.assertEqual(result["changed_source_files"],1)
        self.assertEqual(result["original_v309_binary_parity"],"NOT_TESTED")
        self.assertFalse(result["release_approved"])

    def test_two_source_changes_refused(self):
        a,b,opts = self.pair(changes={self.owner:b"class Codec {}",
                                      "rs/synthetic/Other.java":b"class Broken {}"})
        with self.assertRaisesRegex(r.Refused,"SINGLE_EXPECTED"):
            r.verify_pair(a,b,**opts)

    def test_missing_archive_refused(self):
        a,b,opts = self.pair()
        with self.assertRaisesRegex(r.Refused,"ARCHIVE_IDENTITY"):
            r.verify_pair(self.root/"missing.zip",b,**opts)

    def test_archive_digest_mismatch_refused(self):
        a,b,opts = self.pair()
        opts["old_sha"] = "f"*64
        with self.assertRaisesRegex(r.Refused,"ARCHIVE_IDENTITY"):
            r.verify_pair(a,b,**opts)

    def test_wrong_owner_digest_refused(self):
        a,b,opts = self.pair()
        opts["old_owner"] = "0"*64
        with self.assertRaisesRegex(r.Refused,"SINGLE_EXPECTED"):
            r.verify_pair(a,b,**opts)

    def test_false_game_claim_refused(self):
        a,b,opts = self.pair(receipt={"real_game_runtime":"PASS"})
        with self.assertRaisesRegex(r.Refused,"UNTRUSTED"):
            r.verify_pair(a,b,**opts)

    def test_false_binary_parity_claim_refused(self):
        a,b,opts = self.pair(receipt={"original_v309_binary_parity":"PASS"})
        with self.assertRaisesRegex(r.Refused,"UNTRUSTED"):
            r.verify_pair(a,b,**opts)

    def test_false_release_claim_refused(self):
        a,b,opts = self.pair(receipt={"private_source_release_approved":True})
        with self.assertRaisesRegex(r.Refused,"UNTRUSTED"):
            r.verify_pair(a,b,**opts)

    def test_format_claim_refused(self):
        a,b,opts = self.pair(receipt={"serialized_format_changed":True})
        with self.assertRaisesRegex(r.Refused,"UNTRUSTED"):
            r.verify_pair(a,b,**opts)

    def test_duplicate_archive_member_refused(self):
        a,b,opts = self.pair()
        with ZipFile(b,"a") as z:
            z.writestr("source/"+self.owner,b"duplicate")
        opts["new_sha"] = sha(b.read_bytes())
        with self.assertRaisesRegex(r.Refused,"UNEXPECTED_ARCHIVE_MEMBERS"):
            r.verify_pair(a,b,**opts)

    def test_extra_archive_member_refused(self):
        a,b,opts = self.pair()
        with ZipFile(b,"a") as z:
            z.writestr("source/../escape.java",b"evil")
        opts["new_sha"] = sha(b.read_bytes())
        with self.assertRaisesRegex(r.Refused,"UNEXPECTED_ARCHIVE_MEMBERS"):
            r.verify_pair(a,b,**opts)

if __name__ == "__main__":
    unittest.main(verbosity=2)

"""R366 synthetic static archive-verifier tests; not original game/client CI."""
from __future__ import annotations
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from scripts.verify_v309_r366_store_candidate import (
    OWNER, OLD_MANIFEST, NEW_MANIFEST, NEW_STATUS, Refused, evaluate,
)

sha = lambda data: hashlib.sha256(data).hexdigest()

class R366SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.before = {OWNER:b"package x; class A { int old = 1; }", "rs/Other.java":b"class Other {}"}
        self.after = dict(self.before)
        self.after[OWNER] = b"package x; class A { int newValue = 1; }"
        self.before_report = {"source_count":2,"source_sha256":{name:sha(data) for name,data in self.before.items()}}
        self.after_report = {"source_count":2,"source_sha256":{name:sha(data) for name,data in self.after.items()},
            "status":NEW_STATUS,"changed_source_paths":[OWNER],
            "prior_source_sha256":sha(self.before[OWNER]),
            "new_source_sha256":sha(self.after[OWNER]),
            "private_source_release_approved":False,
            "original_v309_binary_parity":"NOT_TESTED","live_client_acceptance":"NOT_TESTED"}
        self._write()

    def _zip(self,path,sources,report,manifest, extra=None):
        with ZipFile(path,"w") as z:
            for name,raw in sources.items():z.writestr("source/"+name,raw)
            z.writestr(manifest,json.dumps(report))
            for name,raw in (extra or []):z.writestr(name,raw)

    def _write(self):
        self.p=self.root/'before.zip';self.n=self.root/'after.zip'
        self._zip(self.p,self.before,self.before_report,OLD_MANIFEST)
        self._zip(self.n,self.after,self.after_report,NEW_MANIFEST)
        self.witness={"prior_source_archive_sha256":sha(self.p.read_bytes()),
          "new_source_archive_sha256":sha(self.n.read_bytes()),
          "prior_owner_sha256":sha(self.before[OWNER]),
          "new_owner_sha256":sha(self.after[OWNER]),
          "source_count":2,"candidate_jar_sha256":"0"*64}

    def good(self):
        return evaluate(self.p,self.n,self.witness,count=2)

    def test_valid_candidate_reports_static_only(self):
        r=self.good()
        self.assertEqual(r["status"],"R366_STATIC_SOURCE_PROVENANCE_PASS")
        self.assertEqual(r["original_v309_binary_parity"],"NOT_TESTED")
        self.assertFalse(r["private_source_release_approved"])

    def test_missing_archive_refused(self):
        self.p.unlink()
        with self.assertRaises(Refused): self.good()

    def test_wrong_archive_sha_refused(self):
        self.witness["new_source_archive_sha256"]="0"*64
        with self.assertRaises(Refused): self.good()

    def test_wrong_declaring_owner_sha_refused(self):
        self.witness["prior_owner_sha256"]="0"*64
        with self.assertRaises(Refused): self.good()

    def test_witness_additional_field_refused(self):
        self.witness["authenticated_login"]="PASS"
        with self.assertRaises(Refused): self.good()

    def test_second_source_changed_refused(self):
        self.after["rs/Other.java"]=b"class Other {int changed;}"
        self.after_report["source_sha256"]["rs/Other.java"]=sha(self.after["rs/Other.java"])
        self._write()
        with self.assertRaisesRegex(Refused,"UNEXPECTED_SOURCE_DIFF"):self.good()

    def test_manifest_digest_mismatch_refused(self):
        self.after_report["source_sha256"][OWNER]="0"*64
        self._write()
        with self.assertRaisesRegex(Refused,"SOURCE_MANIFEST_MISMATCH"):self.good()

    def test_claimed_release_approval_refused(self):
        self.after_report["private_source_release_approved"]=True
        self._write()
        with self.assertRaisesRegex(Refused,"RELEASE_GATE_OR_RECEIPT_DRIFT"):self.good()

    def test_runtime_claim_refused(self):
        self.after_report["live_client_acceptance"]="PASS"
        self._write()
        with self.assertRaisesRegex(Refused,"RELEASE_GATE_OR_RECEIPT_DRIFT"):self.good()

    def test_unexpected_member_refused(self):
        self._zip(self.n,self.after,self.after_report,NEW_MANIFEST,extra=[("extra.txt",b"no")])
        self.witness["new_source_archive_sha256"]=sha(self.n.read_bytes())
        with self.assertRaisesRegex(Refused,"UNEXPECTED_ARCHIVE_MEMBERS"):self.good()

    def test_duplicate_member_refused(self):
        self._zip(self.n,self.after,self.after_report,NEW_MANIFEST,extra=[("source/"+OWNER,b"overwrite")])
        self.witness["new_source_archive_sha256"]=sha(self.n.read_bytes())
        with self.assertRaisesRegex(Refused,"UNEXPECTED_ARCHIVE_MEMBERS"):self.good()

    def test_unsafe_member_path_refused(self):
        other = self.after.pop("rs/Other.java")
        self.after["rs/../Other.java"]=other
        self.after_report["source_sha256"]={name:sha(raw) for name,raw in self.after.items()}
        self._write()
        with self.assertRaisesRegex(Refused,"UNSAFE_JAVA_MEMBER"):self.good()

    def test_wrong_changed_file_refused(self):
        self.after_report["changed_source_paths"]=["rs/Other.java"]
        self._write()
        with self.assertRaisesRegex(Refused,"RELEASE_GATE_OR_RECEIPT_DRIFT"):self.good()

    def test_wrong_source_count_refused(self):
        self.after_report["source_count"]=3
        self._write()
        with self.assertRaisesRegex(Refused,"SOURCE_MANIFEST_MISMATCH"):self.good()

if __name__=="__main__": unittest.main()

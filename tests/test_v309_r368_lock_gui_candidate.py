"""R368 synthetic source ZIPs, never real recovered client files in public CI."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from scripts.verify_v309_r368_lock_gui_candidate import (
    OWNERS,OLD_MANIFEST,NEW_MANIFEST,STATUS,Refused,evaluate,inspect
)

def sha(data): return hashlib.sha256(data).hexdigest()

class SyntheticR368Tests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory();self.addCleanup(self.scratch.cleanup)
        self.path=Path(self.scratch.name)
        self.before={OWNERS[0]:b'class Panel { int old; }',
                     OWNERS[1]:b'class Store { int old; }',
                     'rs/Untouched.java':b'class Untouched {}'}
        self.after={**self.before,
                    OWNERS[0]:b'class Panel { int notice; }',
                    OWNERS[1]:b'class Store { int lock; }'}
        self.old={"source_count":3,"source_sha256":{p:sha(x) for p,x in self.before.items()}}
        self.new={"source_count":3,"source_sha256":{p:sha(x) for p,x in self.after.items()},
                  "status":STATUS,"changed_source_paths":list(OWNERS),
                  "prior_owner_sha256":{p:sha(self.before[p]) for p in OWNERS},
                  "new_owner_sha256":{p:sha(self.after[p]) for p in OWNERS},
                  "candidate_jar_sha256":"a"*64,"source_backed_store_assertions":44,
                  "serializer_assertions_across_two_charsets":60,
                  "cooperative_cross_jvm_lock_fixture":"PASS_OFFLINE",
                  "gui_failure_callback_fixture":"PASS_OFFLINE_STUB",
                  "original_gui_rendering":"NOT_TESTED",
                  "uncooperative_writer_exclusion":"NOT_PROVEN",
                  "crash_durability":"NOT_TESTED",
                  "original_v309_binary_parity":"NOT_TESTED",
                  "live_client_acceptance":"NOT_TESTED",
                  "private_source_release_approved":False}
        self.write()
    def zip(self,path,source,report,manifest,extra=()):
        with ZipFile(path,'w') as z:
            for name,data in source.items():z.writestr('source/'+name,data)
            z.writestr(manifest,json.dumps(report))
            for n,data in extra:z.writestr(n,data)
    def write(self):
        self.prior=self.path/'r367.zip';self.current=self.path/'r368.zip'
        self.zip(self.prior,self.before,self.old,OLD_MANIFEST)
        self.zip(self.current,self.after,self.new,NEW_MANIFEST)
        self.witness={"prior_source_archive_sha256":sha(self.prior.read_bytes()),
                     "new_source_archive_sha256":sha(self.current.read_bytes()),
                     "prior_owner_sha256":{p:sha(self.before[p]) for p in OWNERS},
                     "new_owner_sha256":{p:sha(self.after[p]) for p in OWNERS},
                     "source_count":3,"candidate_jar_sha256":"a"*64}
    def good(self):return evaluate(self.prior,self.current,self.witness,count=3)
    def refuse_report(self,key,value):
        self.new[key]=value;self.write()
        with self.assertRaisesRegex(Refused,'UNSUPPORTED_RELEASE_OR_RUNTIME_CLAIM'):self.good()
    def test_pass_is_only_static(self):
        result=self.good()
        self.assertEqual(result['status'],'R368_STATIC_SOURCE_PROVENANCE_PASS')
        self.assertEqual(result['original_gui_rendering'],'NOT_TESTED')
    def test_reject_inaccurate_game_parity(self):self.refuse_report('original_v309_binary_parity','PASS')
    def test_reject_unsupported_gui_attestation(self):self.refuse_report('original_gui_rendering','PASS')
    def test_reject_uncooperative_writer_claim(self):self.refuse_report('uncooperative_writer_exclusion','PASS')
    def test_reject_runtime_claim(self):self.refuse_report('live_client_acceptance','PASS')
    def test_reject_release_promotion(self):self.refuse_report('private_source_release_approved',True)
    def test_reject_gui_callback_not_tested(self):self.refuse_report('gui_failure_callback_fixture','NOT_TESTED')
    def test_reject_missing_cross_process_receipt(self):self.refuse_report('cooperative_cross_jvm_lock_fixture','NOT_TESTED')
    def test_reject_unproven_durability(self):self.refuse_report('crash_durability','PASS')
    def test_reject_test_count_drift(self):self.refuse_report('source_backed_store_assertions',40)
    def test_reject_wrong_second_owner(self):
        self.after[OWNERS[1]]=self.before[OWNERS[1]];self.new['source_sha256'][OWNERS[1]]=sha(self.after[OWNERS[1]]);self.write()
        with self.assertRaisesRegex(Refused,'EXACT_TWO_SOURCE_DIFF_REQUIRED'):self.good()
    def test_reject_third_changed_source(self):
        self.after['rs/Untouched.java']=b'class Untouched {int altered;}';self.new['source_sha256']['rs/Untouched.java']=sha(self.after['rs/Untouched.java']);self.write()
        with self.assertRaisesRegex(Refused,'EXACT_TWO_SOURCE_DIFF_REQUIRED'):self.good()
    def test_reject_changed_owner_hash(self):
        self.witness['prior_owner_sha256'][OWNERS[0]]='0'*64
        with self.assertRaisesRegex(Refused,'DECLARING_OWNER_HASH_DRIFT'):self.good()
    def test_reject_changed_witness_sha(self):
        self.witness['new_source_archive_sha256']='0'*64
        with self.assertRaisesRegex(Refused,'SOURCE_ARCHIVE_SHA_MISMATCH'):self.good()
    def test_reject_manifest_hash_drift(self):
        self.new['source_sha256'][OWNERS[0]]='0'*64;self.write()
        with self.assertRaisesRegex(Refused,'PRIVATE_SOURCE_MANIFEST_DRIFT'):self.good()
    def test_reject_unexpected_archive_member(self):
        self.zip(self.current,self.after,self.new,NEW_MANIFEST,[('extra.txt',b'extra')])
        self.witness['new_source_archive_sha256']=sha(self.current.read_bytes())
        with self.assertRaisesRegex(Refused,'SOURCE_ARCHIVE_MEMBER_SET_MISMATCH'):self.good()
    def test_reject_duplicate_archive_member(self):
        self.zip(self.current,self.after,self.new,NEW_MANIFEST,[('source/'+OWNERS[0],b'duplicate')])
        self.witness['new_source_archive_sha256']=sha(self.current.read_bytes())
        with self.assertRaisesRegex(Refused,'SOURCE_ARCHIVE_MEMBER_SET_MISMATCH'):self.good()
    def test_reject_path_traversal(self):
        payload=self.after.pop('rs/Untouched.java');self.after['rs/../Untouched.java']=payload
        self.new['source_sha256']={p:sha(x) for p,x in self.after.items()};self.write()
        with self.assertRaisesRegex(Refused,'UNSAFE_PRIVATE_JAVA_PATH'):self.good()
    def test_reject_missing_source(self):
        self.prior.unlink()
        with self.assertRaisesRegex(Refused,'SOURCE_ARCHIVE_SHA_MISMATCH'):self.good()

if __name__=='__main__':unittest.main()

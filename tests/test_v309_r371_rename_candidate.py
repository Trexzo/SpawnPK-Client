"""Synthetic-only verification of R371 source provenance and closed release gates.

No recovered client Java is present here; private builds/test harnesses are separate.
"""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_v309_r371_rename_candidate import (
    verify,Refused,sha,OWNERS,PREVIOUS_MANIFEST,CURRENT_MANIFEST)

class SyntheticR371Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.old={OWNERS[0]:b'old folder code',OWNERS[1]:b'old store code',
                  'rs/gui/loadouts/Other.java':b'unchanged source'}
        self.new={**self.old,OWNERS[0]:b'new folder code',OWNERS[1]:b'new store code'}
        self.witness={
          'source_count':3,'changed_files':list(OWNERS),
          'candidate_jar_sha256':'a'*64,
          'private_source_release_approved':False,
          'original_game_runtime_tested':False,
          'multi_file_transaction_proven':False,
          'power_loss_durability_tested':False,
        }
        self.rebuild()
    def rebuild(self):
        for filename,sources,manifest in [('before.zip',self.old,PREVIOUS_MANIFEST),
                                           ('after.zip',self.new,CURRENT_MANIFEST)]:
            with ZipFile(self.root/filename,'w') as archive:
                for path,data in sorted(sources.items()):archive.writestr('source/'+path,data)
                receipt={'source_count':3,'source_sha256':{p:sha(d) for p,d in sources.items()}}
                if filename=='after.zip':receipt.update(
                  changed_files=['rs/gui/loadouts/io/LoadoutStore.java','rs/gui/loadouts/LoadoutFolders.java'],
                  previous_source_zip_sha256='PENDING',
                  private_source_release_approved=False,multi_file_transaction_proven=False,
                  power_loss_durability_tested=False)
                archive.writestr(manifest,json.dumps(receipt))
        self.witness['previous_zip_sha256']=sha((self.root/'before.zip').read_bytes())
        # Regenerate the synthetic after ZIP with the prior SHA in its manifest.
        with ZipFile(self.root/'after.zip','w') as archive:
            for path,data in sorted(self.new.items()):archive.writestr('source/'+path,data)
            archive.writestr(CURRENT_MANIFEST,json.dumps({
                'source_count':3,'source_sha256':{p:sha(d) for p,d in self.new.items()},
                'changed_files':['rs/gui/loadouts/io/LoadoutStore.java','rs/gui/loadouts/LoadoutFolders.java'],
                'previous_source_zip_sha256':self.witness['previous_zip_sha256'],
                'private_source_release_approved':False,'multi_file_transaction_proven':False,
                'power_loss_durability_tested':False}))
        self.witness['candidate_zip_sha256']=sha((self.root/'after.zip').read_bytes())
        self.witness['previous_owner_sha256']={p:sha(self.old[p]) for p in OWNERS}
        self.witness['candidate_owner_sha256']={p:sha(self.new.get(p,self.old[p])) for p in OWNERS}
    def check(self):return verify(self.root/'before.zip',self.root/'after.zip',self.witness,count=3)
    def expect_rejected(self):
        with self.assertRaises((Refused,ValueError,KeyError)):self.check()
    def test_clean_source_pair(self):
        result=self.check()
        self.assertEqual(result['status'],'R371_PRIVATE_SOURCE_DELTA_PASS')
        self.assertEqual(result['changed_files'],list(OWNERS))
        self.assertFalse(result['private_source_release_approved'])
    def test_mutated_previous_archive(self):
        (self.root/'before.zip').write_bytes(b'not-a-zip');self.expect_rejected()
    def test_mutated_new_archive(self):
        (self.root/'after.zip').write_bytes(b'changed');self.expect_rejected()
    def test_extra_source_change_rejected(self):
        self.new['rs/gui/loadouts/Other.java']=b'changed too';self.rebuild();self.expect_rejected()
    def test_missing_owner_rejected(self):
        del self.new[OWNERS[0]];self.rebuild();self.expect_rejected()
    def test_invalid_old_owner_hash_rejected(self):
        self.witness['previous_owner_sha256'][OWNERS[0]]='0'*64;self.expect_rejected()
    def test_invalid_new_owner_hash_rejected(self):
        self.witness['candidate_owner_sha256'][OWNERS[1]]='0'*64;self.expect_rejected()
    def test_bad_candidate_jar_hash_rejected(self):
        self.witness['candidate_jar_sha256']='not a hash';self.expect_rejected()
    def test_extra_witness_fields_rejected(self):
        self.witness['run_live_client']=True;self.expect_rejected()
    def test_private_publication_not_permitted(self):
        self.witness['private_source_release_approved']=True;self.expect_rejected()
    def test_fake_runtime_claim_rejected(self):
        self.witness['original_game_runtime_tested']=True;self.expect_rejected()
    def test_fake_atomic_multifile_claim_rejected(self):
        self.witness['multi_file_transaction_proven']=True;self.expect_rejected()
    def test_fake_power_loss_claim_rejected(self):
        self.witness['power_loss_durability_tested']=True;self.expect_rejected()
    def test_source_count_drift_rejected(self):
        self.witness['source_count']=4;self.expect_rejected()
    def test_changed_path_scope_rejected(self):
        self.witness['changed_files']=[OWNERS[0]];self.expect_rejected()
    def test_symlink_archive_refused(self):
        link=self.root/'linked.zip'
        try:link.symlink_to(self.root/'after.zip')
        except (OSError,NotImplementedError):self.skipTest('symlink unavailable')
        with self.assertRaisesRegex(Refused,'INVALID_SOURCE_ARCHIVE'):
            verify(self.root/'before.zip',link,self.witness,count=3)
    def test_mutated_manifest_rejected(self):
        with ZipFile(self.root/'after.zip','a') as zip:
            zip.writestr('private.txt','non-source payload')
        self.witness['candidate_zip_sha256']=sha((self.root/'after.zip').read_bytes())
        self.expect_rejected()
    def test_invalid_older_manifest_hash_rejected(self):
        with ZipFile(self.root/'before.zip','a') as zip:
            zip.writestr('extra.txt','file')
        self.witness['previous_zip_sha256']=sha((self.root/'before.zip').read_bytes())
        self.expect_rejected()

if __name__=='__main__':unittest.main(verbosity=2)

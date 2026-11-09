"""Synthetic-only negative controls for SHA-pinned R372 private source receipts."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_v309_r372_rename_receipt import (
    OWNERS, PREVIOUS_MANIFEST, CURRENT_MANIFEST, Refused, sha, verify,
)

class TestR372SyntheticReceipt(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.before = {
            OWNERS[0]:b'// original folders\n',
            OWNERS[1]:b'// original store\n',
            'rs/gui/loadouts/io/Unchanged.java':b'class Unchanged {}\n',
        }
        self.after = {**self.before,
            OWNERS[0]:b'// updated folders\n',
            OWNERS[1]:b'// updated store\n'}
        self.witness = {
            'source_count':3,
            'changed_paths':list(OWNERS),
            'previous_owner_sha256':{p:sha(self.before[p]) for p in OWNERS},
            'candidate_owner_sha256':{p:sha(self.after[p]) for p in OWNERS},
            'candidate_jar_sha256':'f'*64,
            'expected_classfiles':1388,
            'private_source_release_approved':False,
            'original_game_runtime_tested':False,
            'multi_file_transaction_proven':False,
            'power_loss_durability_tested':False,
            'uncooperative_writer_safety_proven':False,
        }
        self.write_archives()

    def write_archives(self, *, malicious_path=None, extra_manifest=None):
        for filename, contents, manifest_name in (
            ('before.zip',self.before,PREVIOUS_MANIFEST),
            ('after.zip',self.after,CURRENT_MANIFEST),
        ):
            with ZipFile(self.root/filename,'w') as archive:
                for p,data in contents.items():archive.writestr('source/'+p,data)
                if filename=='after.zip' and malicious_path:
                    archive.writestr(malicious_path,b'bad')
                manifest={'source_count':len(contents),
                    'source_sha256':{p:sha(d) for p,d in contents.items()}}
                if filename=='after.zip':
                    manifest.update(
                        changed_files=list(OWNERS),
                        previous_source_zip_sha256='PENDING',
                        private_source_release_approved=False,
                        original_game_runtime_tested=False,
                        multi_file_transaction_proven=False,
                        power_loss_durability_tested=False,
                        rename_receipt_replay='SOURCE_BACKED_TEST_PASS_56',
                    )
                    if extra_manifest:manifest.update(extra_manifest)
                archive.writestr(manifest_name,json.dumps(manifest))
        self.witness['previous_zip_sha256']=sha((self.root/'before.zip').read_bytes())
        # Recreate after.zip with pinned previous hash
        with ZipFile(self.root/'after.zip','w') as archive:
            for p,data in self.after.items():archive.writestr('source/'+p,data)
            if malicious_path:archive.writestr(malicious_path,b'bad')
            manifest={'source_count':len(self.after),
                'source_sha256':{p:sha(d) for p,d in self.after.items()},
                'changed_files':list(OWNERS),
                'previous_source_zip_sha256':self.witness['previous_zip_sha256'],
                'private_source_release_approved':False,
                'original_game_runtime_tested':False,
                'multi_file_transaction_proven':False,
                'power_loss_durability_tested':False,
                'rename_receipt_replay':'SOURCE_BACKED_TEST_PASS_56',
            }
            if extra_manifest:manifest.update(extra_manifest)
            archive.writestr(CURRENT_MANIFEST,json.dumps(manifest))
        self.witness['candidate_zip_sha256']=sha((self.root/'after.zip').read_bytes())

    def check(self):
        return verify(self.root/'before.zip',self.root/'after.zip',self.witness,expected_count=3)

    def test_good_pair(self):
        self.assertEqual(self.check()['status'],'R372_PRIVATE_SOURCE_RECEIPT_PASS')
    def test_source_count(self):
        self.assertEqual(self.check()['source_count'],3)
    def test_private_release_closed(self):
        self.assertFalse(self.check()['private_source_release_approved'])
    def test_old_zip_tamper(self):
        (self.root/'before.zip').write_bytes(b'garbled')
        with self.assertRaises(Refused):self.check()
    def test_new_zip_tamper(self):
        (self.root/'after.zip').write_bytes(b'garbled')
        with self.assertRaises(Refused):self.check()
    def test_third_source_changed(self):
        self.after['rs/gui/loadouts/io/Unchanged.java']=b'class Changed {}'
        self.write_archives()
        with self.assertRaisesRegex(Refused,'UNEXPECTED_JAVA_SOURCE_DELTA'):self.check()
    def test_one_owner_missing(self):
        self.after.pop(OWNERS[0])
        self.write_archives()
        with self.assertRaises(Refused):self.check()
    def test_owner_hash_tamper(self):
        self.witness['candidate_owner_sha256'][OWNERS[0]]='0'*64
        with self.assertRaisesRegex(Refused,'DECLARING_OWNER_SHA_CHANGED'):self.check()
    def test_jar_hash_malformed(self):
        self.witness['candidate_jar_sha256']='wrong'
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_wrong_classfile_count(self):
        self.witness['expected_classfiles']=1386
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_runtime_promotion_refused(self):
        self.witness['original_game_runtime_tested']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_source_publication_refused(self):
        self.witness['private_source_release_approved']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_transaction_claim_refused(self):
        self.witness['multi_file_transaction_proven']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_powerloss_claim_refused(self):
        self.witness['power_loss_durability_tested']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_uncooperative_writer_claim_refused(self):
        self.witness['uncooperative_writer_safety_proven']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_unknown_witness_field(self):
        self.witness['allow_live_promotion']=True
        with self.assertRaisesRegex(Refused,'UNEXPECTED_WITNESS_SCHEMA'):self.check()
    def test_malicious_path(self):
        self.write_archives(malicious_path='source/../outside.java')
        with self.assertRaisesRegex(Refused,'ARCHIVE_FILE_SET_CHANGED|UNSAFE_SOURCE_MEMBER'):self.check()
    def test_candidate_manifest_promoted(self):
        self.write_archives(extra_manifest={'private_source_release_approved':True})
        with self.assertRaisesRegex(Refused,'MANIFEST_RELEASE_GATE_DRIFT'):self.check()
    def test_candidate_manifest_missing_replay(self):
        self.write_archives(extra_manifest={'rename_receipt_replay':'UNVERIFIED'})
        with self.assertRaisesRegex(Refused,'MANIFEST_RELEASE_GATE_DRIFT'):self.check()
    def test_bad_source_count(self):
        self.witness['source_count']=1277
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_symlink_archive_rejected(self):
        link=self.root/'alias.zip'
        try:link.symlink_to(self.root/'after.zip')
        except (OSError,NotImplementedError):self.skipTest('symlinks unsupported on CI runner')
        with self.assertRaisesRegex(Refused,'INVALID_PRIVATE_ARCHIVE'):
            verify(self.root/'before.zip',link,self.witness,expected_count=3)

if __name__ == '__main__':unittest.main(verbosity=2)

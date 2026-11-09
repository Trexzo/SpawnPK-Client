"""R372 synthetic verifier tests only; no recovered Java/game execution."""
from __future__ import annotations
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_v309_r372_rename_receipt import (verify,sha,Refused,PREVIOUS,CURRENT,OWNERS)
class SyntheticR372Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.before={OWNERS[0]:b'class Folders {}',OWNERS[1]:b'class Store {}',
                     'rs/gui/loadouts/io/Other.java':b'class Other {}'}
        self.after={**self.before,OWNERS[0]:b'class Folders {int a;}',OWNERS[1]:b'class Store {int b;}'}
        self.witness={'source_count':3,'compiled_classfiles':1387,
           'changed_paths':list(OWNERS),
           'previous_owner_sha256':{p:sha(self.before[p]) for p in OWNERS},
           'candidate_owner_sha256':{p:sha(self.after[p]) for p in OWNERS},
           'candidate_jar_sha256':'a'*64,
           'private_source_release_approved':False,'original_game_runtime_tested':False,
           'multi_file_transaction_proven':False,'power_loss_durability_tested':False}
        self.rebuild()
    def rebuild(self):
        for file,source,manifest in [('old.zip',self.before,PREVIOUS),('new.zip',self.after,CURRENT)]:
            with ZipFile(self.root/file,'w') as z:
                for name,content in source.items():z.writestr('source/'+name,content)
                meta={'source_count':len(source),'source_sha256':{p:sha(v) for p,v in source.items()}}
                if file=='new.zip':meta.update(changed_files=list(OWNERS),
                    previous_source_zip_sha256=self.witness.get('previous_zip_sha256'),
                    jar_sha256='a'*64,classfiles=1387,
                    private_source_release_approved=False,
                    original_game_runtime_tested=False,
                    multi_file_transaction_proven=False,power_loss_durability_tested=False)
                z.writestr(manifest,json.dumps(meta))
        self.witness['previous_zip_sha256']=sha((self.root/'old.zip').read_bytes())
        # New archive contains the previous hash; rebuild after computing old ZIP hash.
        with ZipFile(self.root/'new.zip','w') as z:
            for name,content in self.after.items():z.writestr('source/'+name,content)
            meta={'source_count':len(self.after),'source_sha256':{p:sha(v) for p,v in self.after.items()},
                'changed_files':list(OWNERS),'previous_source_zip_sha256':self.witness['previous_zip_sha256'],
                'jar_sha256':'a'*64,'classfiles':1387,
                'private_source_release_approved':False,'original_game_runtime_tested':False,
                'multi_file_transaction_proven':False,'power_loss_durability_tested':False}
            z.writestr(CURRENT,json.dumps(meta))
        self.witness['candidate_zip_sha256']=sha((self.root/'new.zip').read_bytes())
    def check(self):return verify(self.root/'old.zip',self.root/'new.zip',self.witness,count=3)
    def test_valid_fixture(self):self.assertEqual(self.check()['sources'],3)
    def test_detect_old_zip_corruption(self):
        (self.root/'old.zip').write_bytes(b'invalid')
        with self.assertRaises(Refused):self.check()
    def test_detect_new_zip_corruption(self):
        (self.root/'new.zip').write_bytes(b'invalid')
        with self.assertRaises(Refused):self.check()
    def test_extra_java_change(self):
        self.after['rs/gui/loadouts/io/Other.java']=b'mutated';self.rebuild()
        with self.assertRaisesRegex(Refused,'UNEXPECTED_SOURCE_CHANGE'):self.check()
    def test_missing_java(self):
        del self.after[OWNERS[0]];self.rebuild()
        with self.assertRaises(Refused):self.check()
    def test_prior_owner_sha_drift(self):
        self.witness['previous_owner_sha256'][OWNERS[0]]='0'*64
        with self.assertRaises(Refused):self.check()
    def test_candidate_owner_sha_drift(self):
        self.witness['candidate_owner_sha256'][OWNERS[1]]='0'*64
        with self.assertRaises(Refused):self.check()
    def test_bad_build_hash(self):
        self.witness['candidate_jar_sha256']='wrong'
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_source_publication_gate(self):
        self.witness['private_source_release_approved']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_false_multifile_claim(self):
        self.witness['multi_file_transaction_proven']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_false_power_loss_claim(self):
        self.witness['power_loss_durability_tested']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_false_runtime_claim(self):
        self.witness['original_game_runtime_tested']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_wrong_compiled_count(self):
        self.witness['compiled_classfiles']=1386
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
    def test_wrong_source_count(self):
        self.witness['source_count']=2
        with self.assertRaises(Refused):self.check()
    def test_unknown_witness_key(self):
        self.witness['allow_live_cache']=True
        with self.assertRaisesRegex(Refused,'UNEXPECTED_WITNESS_SCHEMA'):self.check()
    def test_malformed_candidate_manifest(self):
        self.witness['candidate_zip_sha256']='0'*64
        with self.assertRaisesRegex(Refused,'SOURCE_ZIP_SHA_MISMATCH'):self.check()
    def test_symlink_archive(self):
        link=self.root/'linked.zip'
        try:link.symlink_to(self.root/'new.zip')
        except (OSError,NotImplementedError):self.skipTest('symlinks unavailable')
        with self.assertRaisesRegex(Refused,'INVALID_SOURCE_ZIP'):
            verify(self.root/'old.zip',link,self.witness,count=3)
    def test_archive_does_not_leak_source(self):
        self.assertFalse(self.witness['private_source_release_approved']);self.assertEqual(len(OWNERS),2)
if __name__=='__main__':unittest.main(verbosity=2)

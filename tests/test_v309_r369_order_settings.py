"""R369 synthetic-only source archive verifier regressions; no private client code."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_v309_r369_order_settings import (verify,sha,Refused,OWNER,
  PREVIOUS_MANIFEST,CURRENT_MANIFEST)

class R369SyntheticTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  self.dir=Path(self.temp.name)
  self.before={OWNER:b'// old source only\n', 'rs/gui/loadouts/Other.java':b'class Other {}'}
  self.after={**self.before, OWNER:b'// new source only\n'}
  self.witness={'source_count':2,'owner':OWNER,'changed_paths':[OWNER],
    'previous_owner_sha256':sha(self.before[OWNER]),
    'candidate_owner_sha256':sha(self.after[OWNER]),
    'candidate_jar_sha256':'a'*64,
    'private_source_release_approved':False,'original_game_runtime_tested':False,
    'multi_file_transaction_proven':False,'power_loss_durability_tested':False}
  self.write_archives()
 def write_archives(self):
  for name,sources,manifest in [('before.zip',self.before,PREVIOUS_MANIFEST),
                                ('after.zip',self.after,CURRENT_MANIFEST)]:
   path=self.dir/name
   with ZipFile(path,'w') as z:
    for filename,data in sources.items():z.writestr('source/'+filename,data)
    receipt={'source_sha256':{p:sha(d) for p,d in sources.items()},'source_count':2}
    if name=='after.zip':receipt.update(changed_files=[OWNER],private_source_release_approved=False,
         multi_file_transaction='NOT_IMPLEMENTED',power_loss_durability='NOT_TESTED',
         same_source_built_jar_sha256='a'*64)
    z.writestr(manifest,json.dumps(receipt))
  self.witness['previous_zip_sha256']=sha((self.dir/'before.zip').read_bytes())
  self.witness['candidate_zip_sha256']=sha((self.dir/'after.zip').read_bytes())
 def check(self):return verify(self.dir/'before.zip',self.dir/'after.zip',self.witness,expected_count=2)
 def test_good_pair_private_gate_closed(self):
  result=self.check();self.assertEqual(result['status'],'R369_PRIVATE_SOURCE_RECEIPT_PASS')
  self.assertEqual(result['source_count'],2);self.assertFalse(result['original_game_runtime_tested'])
 def test_changed_previous_zip_refused(self):
  (self.dir/'before.zip').write_bytes(b'fake');
  with self.assertRaises(Refused):self.check()
 def test_changed_candidate_zip_refused(self):
  (self.dir/'after.zip').write_bytes(b'fake');
  with self.assertRaises(Refused):self.check()
 def test_extra_private_source_drift_refused(self):
  self.after['rs/gui/loadouts/Other.java']=b'class Other {int x;}'
  self.write_archives()
  with self.assertRaisesRegex(Refused,'UNEXPECTED_JAVA_CHANGES'):self.check()
 def test_owner_missing_refused(self):
  del self.after[OWNER];self.write_archives()
  with self.assertRaises(Refused):self.check()
 def test_changed_owner_sha_refused(self):
  self.witness['candidate_owner_sha256']='0'*64
  with self.assertRaises(Refused):self.check()
 def test_bad_jar_hash_refused(self):
  self.witness['candidate_jar_sha256']='wrong'
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_promoted_private_source_refused(self):
  self.witness['private_source_release_approved']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_claimed_game_runtime_refused(self):
  self.witness['original_game_runtime_tested']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_claimed_multifile_transaction_refused(self):
  self.witness['multi_file_transaction_proven']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_claimed_power_loss_refused(self):
  self.witness['power_loss_durability_tested']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_wrong_source_count_refused(self):
  self.witness['source_count']=3
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS|source_count|MANIFEST_MISMATCH'):self.check()
 def test_unexpected_witness_key_refused(self):
  self.witness['allow_live_login']=True
  with self.assertRaisesRegex(Refused,'UNEXPECTED_WITNESS_SCHEMA'):self.check()
 def test_symlink_archive_refused(self):
  original=self.dir/'after.zip';link=self.dir/'link.zip'
  try:link.symlink_to(original)
  except (OSError,NotImplementedError):self.skipTest("symlinks unavailable for this Windows runner")
  with self.assertRaisesRegex(Refused,'INVALID_PRIVATE_ARCHIVE'):
   verify(self.dir/'before.zip',link,self.witness,expected_count=2)
 def test_preexisting_source_privacy(self):
  self.assertEqual(OWNER,'rs/gui/loadouts/io/LoadoutStore.java')
  self.assertFalse(self.witness['private_source_release_approved'])

if __name__=='__main__':unittest.main(verbosity=2)

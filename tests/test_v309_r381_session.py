"""Public synthetic R381 archive-verifier tests. No private client source used."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_v309_r381_session import (
    OWNER,PREVIOUS_MANIFEST,CURRENT_MANIFEST,Refused,verify,sha)

class R381SyntheticTests(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.dir=Path(temp.name)
  self.before={OWNER:b'class Original {int a;}\n','rs/gui/loadouts/Other.java':b'class Other{}\n'}
  self.after={**self.before,OWNER:b'class Original {int b;}\n'}
  self.w={'source_count':2,'changed_paths':[OWNER],'generated_classfiles':1388,
   'candidate_jar_sha256':'a'*64,'new_source_backed_assertions':33,
   'inherited_source_backed_assertions':466,
   'folder_stage_digest_correlation_verified':True,
   'cooperative_order_lock_probe_verified':True,
   'session_tagged_stage_verified':True,'legacy_stage_backward_compatible':True,
   'lock_correlation_preserved':True,
   **{k:False for k in ('legacy_folder_staging_lock_ownership_inferred',
      'folder_lock_probe_is_stage_ownership_proof','stage_cleanup_safe_proven',
      'automatic_stage_cleanup_enabled','original_game_runtime_tested',
      'private_source_release_approved','power_loss_durability_tested',
      'multi_file_transaction_proven','active_writer_owner_identified',
      'windows_genuine_source_runtime_tested',
      'session_token_is_writer_identity','stage_cleanup_authorized',
      'writer_ownership_proven','stage_session_token_cryptographically_authenticated')}}
  self.pack()
 def pack(self,extra_after=None):
  for filename,sources,manifest in [('old.zip',self.before,PREVIOUS_MANIFEST),
                                     ('new.zip',self.after,CURRENT_MANIFEST)]:
   with ZipFile(self.dir/filename,'w') as z:
    for p,data in sources.items():z.writestr('source/'+p,data)
    receipt={'source_count':len(sources),'source_sha256':{p:sha(d) for p,d in sources.items()}}
    if filename=='new.zip':
     receipt.update(changed_files=[OWNER],previous_source_zip_sha256='PENDING',
      same_source_built_jar_sha256='a'*64,generated_classfiles=1388,
      new_source_backed_assertions_passed=33,inherited_source_backed_assertions_passed=466,
      folder_stage_digest_correlation_verified=True,cooperative_order_lock_probe_verified=True,
      session_tagged_stage_verified=True,legacy_stage_backward_compatible=True,
      lock_correlation_preserved=True,
      **{k:False for k in ('legacy_folder_staging_lock_ownership_inferred',
      'folder_lock_probe_is_stage_ownership_proof','stage_cleanup_safe_proven',
      'automatic_stage_cleanup_enabled','original_game_runtime_tested',
      'private_source_release_approved','power_loss_durability_tested',
      'multi_file_transaction_proven','active_writer_owner_identified',
      'windows_genuine_source_runtime_tested',
      'session_token_is_writer_identity','stage_cleanup_authorized',
      'writer_ownership_proven','stage_session_token_cryptographically_authenticated')})
    if filename=='new.zip' and extra_after:receipt.update(extra_after)
    z.writestr(manifest,json.dumps(receipt))
  self.w['previous_zip_sha256']=sha((self.dir/'old.zip').read_bytes())
  with ZipFile(self.dir/'new.zip') as z:all_entries=[(x.filename,z.read(x.filename)) for x in z.infolist()]
  with ZipFile(self.dir/'new.zip','w') as z:
   for name,raw in all_entries:
    if name==CURRENT_MANIFEST:
     receipt=json.loads(raw);receipt['previous_source_zip_sha256']=self.w['previous_zip_sha256'];raw=json.dumps(receipt).encode()
    z.writestr(name,raw)
  self.w['candidate_zip_sha256']=sha((self.dir/'new.zip').read_bytes())
  self.w['previous_owner_sha256']=sha(self.before[OWNER]);self.w['candidate_owner_sha256']=sha(self.after[OWNER]) if OWNER in self.after else '0'*64
 def check(self):return verify(self.dir/'old.zip',self.dir/'new.zip',self.w,expected_count=2)
 def test_valid_private_gates_closed(self):
  x=self.check();self.assertEqual(x['status'],'R381_PRIVATE_SOURCE_DELTA_PASS');self.assertFalse(x['stage_cleanup_safe_proven'])
 def test_previous_archive_modified(self):
  (self.dir/'old.zip').write_bytes(b'x');
  with self.assertRaisesRegex(Refused,'ARCHIVE_HASH_CHANGED'):self.check()
 def test_candidate_archive_modified(self):
  (self.dir/'new.zip').write_bytes(b'x');
  with self.assertRaisesRegex(Refused,'ARCHIVE_HASH_CHANGED'):self.check()
 def test_second_source_changed(self):
  self.after['rs/gui/loadouts/Other.java']=b'class Altered{}';self.pack()
  with self.assertRaisesRegex(Refused,'UNEXPECTED_SOURCE_DELTA'):self.check()
 def test_owner_not_changed(self):
  self.after[OWNER]=self.before[OWNER];self.pack()
  with self.assertRaisesRegex(Refused,'UNEXPECTED_SOURCE_DELTA'):self.check()
 def test_source_removed(self):
  del self.after['rs/gui/loadouts/Other.java'];self.pack()
  with self.assertRaises(Refused):self.check()
 def test_owner_pin_wrong(self):
  self.w['candidate_owner_sha256']='0'*64
  with self.assertRaisesRegex(Refused,'OWNER_SHA_DRIFT'):self.check()
 def test_jar_sha_not_hash(self):
  self.w['candidate_jar_sha256']='not-a-sha'
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_no_unapproved_release(self):
  self.w['private_source_release_approved']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_game_runtime_not_claimed(self):
  self.w['original_game_runtime_tested']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_cleanup_not_claimed(self):
  self.w['automatic_stage_cleanup_enabled']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_stage_cleanup_safety_not_claimed(self):
  self.w['stage_cleanup_safe_proven']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_lock_is_not_ownership(self):
  self.w['folder_lock_probe_is_stage_ownership_proof']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_no_legacy_owner_inference(self):
  self.w['legacy_folder_staging_lock_ownership_inferred']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_digest_correlation_required(self):
  self.w['folder_stage_digest_correlation_verified']=False
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_cooperative_order_baseline_required(self):
  self.w['cooperative_order_lock_probe_verified']=False
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_wrong_assertion_count(self):
  self.w['new_source_backed_assertions']=23
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_wrong_inherited_count(self):
  self.w['inherited_source_backed_assertions']=441
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_wrong_class_count(self):
  self.w['generated_classfiles']=1386
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_extra_witness_field(self):
  self.w['enable_live_login']=True
  with self.assertRaisesRegex(Refused,'WITNESS_SCHEMA_CHANGED'):self.check()
 def test_wrong_receipt_delta(self):
  self.pack({'changed_files':['rs/Other.java']})
  with self.assertRaisesRegex(Refused,'RECEIPT_DRIFT'):self.check()
 def test_receipt_digest_gate(self):
  self.pack({'folder_stage_digest_correlation_verified':False})
  with self.assertRaisesRegex(Refused,'RECEIPT_DRIFT'):self.check()
 def test_receipt_owner_claim(self):
  self.pack({'folder_lock_probe_is_stage_ownership_proof':True})
  with self.assertRaisesRegex(Refused,'RECEIPT_DRIFT'):self.check()
 def test_receipt_cleanup_claim(self):
  self.pack({'automatic_stage_cleanup_enabled':True})
  with self.assertRaisesRegex(Refused,'RECEIPT_DRIFT'):self.check()
 def test_no_powerloss_claim(self):
  self.w['power_loss_durability_tested']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_no_multifile_claim(self):
  self.w['multi_file_transaction_proven']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_symlink_archive_refused(self):
  target=self.dir/'new.zip';link=self.dir/'link.zip'
  try:link.symlink_to(target)
  except (OSError,NotImplementedError):self.skipTest('symlinks unavailable')
  with self.assertRaisesRegex(Refused,'INVALID_ARCHIVE'):
   verify(self.dir/'old.zip',link,self.w,expected_count=2)
 def test_traversal_source_rejected(self):
  self.after['../escape.java']=b'class Escape{}';self.pack()
  with self.assertRaises(Refused):self.check()
 def test_source_pin_corruption(self):
  self.pack({'source_sha256':{OWNER:'0'*64,'rs/gui/loadouts/Other.java':'0'*64}})
  with self.assertRaisesRegex(Refused,'SOURCE_PIN_DRIFT'):self.check()
 def test_writer_identity_not_claimed(self):
  self.w['active_writer_owner_identified']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_windows_runtime_not_claimed(self):
  self.w['windows_genuine_source_runtime_tested']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_session_writer_identity_not_claimed(self):
  self.w['session_token_is_writer_identity']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_stage_cleanup_not_authorized(self):
  self.w['stage_cleanup_authorized']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_session_not_authenticated(self):
  self.w['stage_session_token_cryptographically_authenticated']=True
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_session_must_be_verified(self):
  self.w['session_tagged_stage_verified']=False
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_legacy_compatibility_must_hold(self):
  self.w['legacy_stage_backward_compatible']=False
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_lock_correlation_must_hold(self):
  self.w['lock_correlation_preserved']=False
  with self.assertRaisesRegex(Refused,'WITNESS_INVALID'):self.check()
 def test_receipt_session_claim_refused(self):
  self.pack({'session_token_is_writer_identity':True})
  with self.assertRaisesRegex(Refused,'RECEIPT_DRIFT'):self.check()
 def test_receipt_missing_session_verification(self):
  self.pack({'session_tagged_stage_verified':False})
  with self.assertRaisesRegex(Refused,'RECEIPT_DRIFT'):self.check()
if __name__=='__main__':unittest.main(verbosity=2)

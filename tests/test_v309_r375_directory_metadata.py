"""Synthetic-only R375 source-receipt tests. No private Java or client execution."""
import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_v309_r375_directory_metadata import (
 OWNER,PREVIOUS_MANIFEST,CURRENT_MANIFEST,Refused,verify,sha)

class R375SyntheticTests(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.dir=Path(temp.name)
  self.before={OWNER:b'class Original {int x;}\n','rs/gui/loadouts/Other.java':b'class Other {}'}
  self.after={**self.before,OWNER:b'class Original {int renamed;}\n'}
  self.w={'source_count':2,'changed_paths':[OWNER],
   'candidate_jar_sha256':'a'*64,'generated_classfiles':1388,
   'new_source_backed_assertions':24,'inherited_source_backed_assertions':310,
   'receipt_creation_atomic_staging_verified':True,'staged_file_force_added':True,
   'directory_sync_attempt_added':True,'directory_sync_linux_probe_passed':True,
   'directory_fsync_durability_proven':False,'private_source_release_approved':False,
   'original_game_runtime_tested':False,'multi_file_transaction_proven':False,
   'power_loss_durability_tested':False,'uncooperative_writer_safety_proven':False}
  self.pack()
 def pack(self,extra_before=None,extra_after=None):
  for filename,sources,manifest_name,extra in [('old.zip',self.before,PREVIOUS_MANIFEST,extra_before),
    ('new.zip',self.after,CURRENT_MANIFEST,extra_after)]:
   with ZipFile(self.dir/filename,'w') as z:
    for p,data in sources.items():z.writestr('source/'+p,data)
    metadata={'source_count':len(sources),'source_sha256':{p:sha(b) for p,b in sources.items()}}
    if filename=='new.zip':metadata.update(changed_files=[OWNER],
     previous_source_zip_sha256='PENDING',source_backed_directory_assertions_passed=24,
     inherited_source_backed_assertions_passed=310,generated_classfiles=1388,
     directory_fsync_durability_proven=False,
     same_source_built_jar_sha256='a'*64,
     private_source_release_approved=False,original_game_runtime_tested=False,
     multi_file_transaction_proven=False,power_loss_durability_tested=False)
    if extra: metadata.update(extra)
    z.writestr(manifest_name,json.dumps(metadata))
  self.w['previous_zip_sha256']=sha((self.dir/'old.zip').read_bytes())
  # Set exact old SHA in new manifest to satisfy full witness baseline.
  with ZipFile(self.dir/'new.zip') as z: oldinfo=[(x.filename,z.read(x.filename)) for x in z.infolist()]
  with ZipFile(self.dir/'new.zip','w') as z:
   for name,raw in oldinfo:
    if name==CURRENT_MANIFEST:
     item=json.loads(raw);item['previous_source_zip_sha256']=self.w['previous_zip_sha256'];raw=json.dumps(item).encode()
    z.writestr(name,raw)
  self.w['candidate_zip_sha256']=sha((self.dir/'new.zip').read_bytes())
  self.w['previous_owner_sha256']=sha(self.before[OWNER])
  self.w['candidate_owner_sha256']=sha(self.after[OWNER]) if OWNER in self.after else '0'*64
 def check(self):return verify(self.dir/'old.zip',self.dir/'new.zip',self.w,expected_count=2)
 def test_valid(self):
  x=self.check();self.assertEqual(x['status'],'R375_PRIVATE_SOURCE_CHECK_PASS');self.assertFalse(x['private_source_release_approved'])
 def test_tampered_previous_archive(self):
  (self.dir/'old.zip').write_bytes(b'wrong')
  with self.assertRaisesRegex(Refused,'ARCHIVE_SHA256_CHANGED'):self.check()
 def test_tampered_candidate_archive(self):
  (self.dir/'new.zip').write_bytes(b'wrong')
  with self.assertRaisesRegex(Refused,'ARCHIVE_SHA256_CHANGED'):self.check()
 def test_additional_source_change_rejected(self):
  self.after['rs/gui/loadouts/Other.java']=b'class Other {int x;}';self.pack()
  with self.assertRaisesRegex(Refused,'UNEXPECTED_PRIVATE_SOURCE_DELTA'):self.check()
 def test_unchanged_owner_rejected(self):
  self.after[OWNER]=self.before[OWNER];self.pack()
  with self.assertRaisesRegex(Refused,'UNEXPECTED_PRIVATE_SOURCE_DELTA'):self.check()
 def test_deleted_source_rejected(self):
  del self.after['rs/gui/loadouts/Other.java'];self.pack()
  with self.assertRaises(Refused):self.check()
 def test_owner_hash_changed(self):
  self.w['candidate_owner_sha256']='0'*64
  with self.assertRaisesRegex(Refused,'OWNER_SHA_DRIFT'):self.check()
 def test_bad_jar_hash_rejected(self):
  self.w['candidate_jar_sha256']='notsha'
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_release_gate_closed(self):
  self.w['private_source_release_approved']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_game_runtime_not_claimed(self):
  self.w['original_game_runtime_tested']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_no_multifile_transaction_claim(self):
  self.w['multi_file_transaction_proven']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_no_powerloss_claim(self):
  self.w['power_loss_durability_tested']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_no_directory_durability_claim(self):
  self.w['directory_fsync_durability_proven']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_receipt_staging_evidence_required(self):
  self.w['receipt_creation_atomic_staging_verified']=False
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_staged_flush_evidence_required(self):
  self.w['staged_file_force_added']=False
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_no_uncooperative_writer_claim(self):
  self.w['uncooperative_writer_safety_proven']=True
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_assertion_count_pinned(self):
  self.w['new_source_backed_assertions']=23
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_class_count_pinned(self):
  self.w['generated_classfiles']=1386
  with self.assertRaisesRegex(Refused,'INVALID_WITNESS'):self.check()
 def test_extra_witness_key_rejected(self):
  self.w['allow_release']=True
  with self.assertRaisesRegex(Refused,'UNEXPECTED_WITNESS_KEYS'):self.check()
 def test_wrong_manifest_gate(self):
  self.pack(extra_after={'multi_file_transaction_proven':True})
  with self.assertRaisesRegex(Refused,'PRIVATE_RECEIPT_DRIFT'):self.check()
 def test_wrong_manifest_evidence(self):
  self.pack(extra_after={'source_backed_directory_assertions_passed':1})
  with self.assertRaisesRegex(Refused,'PRIVATE_RECEIPT_DRIFT'):self.check()
 def test_symlink_archive_rejected(self):
  target=self.dir/'new.zip';link=self.dir/'link.zip'
  try:link.symlink_to(target)
  except (OSError,NotImplementedError):self.skipTest('symlinks unavailable')
  with self.assertRaisesRegex(Refused,'INVALID_ARCHIVE_FILE'):
   verify(self.dir/'old.zip',link,self.w,expected_count=2)
 def test_archive_path_traversal(self):
  self.after['../escaped.java']=b'class Escaped{}';self.pack()
  with self.assertRaises(Refused):self.check()
 def test_malformed_source_manifest_sha(self):
  self.pack(extra_after={'source_sha256':{OWNER:'0'*64,'rs/gui/loadouts/Other.java':'0'*64}})
  with self.assertRaisesRegex(Refused,'SOURCE_SHA256_MISMATCH'):self.check()

if __name__=='__main__':unittest.main(verbosity=2)


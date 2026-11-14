"""Public synthetic tests only: never require or publish recovered Java sources."""
import hashlib, io, importlib.util, json, os, stat, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

SCRIPT=Path(__file__).resolve().parents[1]/"tools/r383/verify_private_full_build.py"
spec=importlib.util.spec_from_file_location("r383_validator",SCRIPT)
r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=r;spec.loader.exec_module(r)

class SyntheticBuildTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name); self.srcs={'rs/One.java':b'package rs; public class One {}\n','rs/Two.java':b'package rs; public class Two {}\n'}
  self.deps={'R218.jar':b'dummy jar A','R239_filtered.jar':b'dummy jar B'}
  self.manifest={'source_count':2,'build_compiled_class_expected':2,'jar_sha256':'1'*64,
    'private_source_release_approved':False,
    'source_sha256':{p:r.sha(data) for p,data in self.srcs.items()},
    'dependency_sha256':{p:r.sha(data) for p,data in self.deps.items()}}
 def kit(self,member_override=None):
  bio=io.BytesIO()
  with ZipFile(bio,'w') as z:
   z.writestr('MANIFEST.json',json.dumps(self.manifest))
   for n,b in self.srcs.items():z.writestr('source/'+n,b)
   for n,b in self.deps.items():z.writestr('dependencies/'+n,b)
   if member_override: z.writestr(*member_override)
  return bio.getvalue()
 def check(self,member_override=None):
  data=self.kit(member_override)
  with patch.object(r,'R381_BUILD_KIT_SHA',r.sha(data)),patch.object(r,'SOURCE_COUNT',2),patch.object(r,'CLASS_COUNT',2),patch.object(r,'EXPECTED_JAR_SHA','1'*64):
   return r.extract_checked_kit(data,self.root/'extracted')
 def test_valid_synthetic_kit(self):
  self.assertEqual(self.check()['source_count'],2)
  self.assertEqual((self.root/'extracted/source/rs/One.java').read_bytes(),self.srcs['rs/One.java'])
 def test_all_pins_verified(self):
  m=self.check();self.assertEqual(len(m['source_sha256']),2)
 def test_sha_helper(self):self.assertEqual(r.sha(b'x'),hashlib.sha256(b'x').hexdigest())
 def test_hash_file_helper(self):
  p=self.root/'data';p.write_bytes(b'abc');self.assertEqual(r.hash_file(p),r.sha(b'abc'))
 def test_unpinned_input_rejected(self):
  p=self.root/'fake.zip';p.write_bytes(b'not a private source')
  with self.assertRaisesRegex(r.Refused,'UNRECOGNIZED_PRIVATE_INPUT_SHA256'):r.load_private_kit(p)
 def test_missing_input_rejected(self):
  with self.assertRaisesRegex(r.Refused,'PRIVATE_INPUT_MISSING_OR_UNSAFE'):r.load_private_kit(self.root/'missing.zip')
 def test_symlink_input_rejected(self):
  p=self.root/'target';p.write_bytes(b'hi');s=self.root/'link'
  try:s.symlink_to(p)
  except (OSError,NotImplementedError):self.skipTest('Windows symlink privilege unavailable')
  with self.assertRaisesRegex(r.Refused,'PRIVATE_INPUT_MISSING_OR_UNSAFE'):r.load_private_kit(s)
 def test_bad_build_kit_sha_rejected(self):
  with self.assertRaisesRegex(r.Refused,'BUILD_KIT_SHA256_MISMATCH'):r.extract_checked_kit(self.kit(),self.root/'extracted')
 def test_modified_owner_source_rejected(self):
  self.srcs['rs/One.java']=b'wrong';data=self.kit()
  with patch.object(r,'R381_BUILD_KIT_SHA',r.sha(data)),patch.object(r,'SOURCE_COUNT',2),patch.object(r,'CLASS_COUNT',2),patch.object(r,'EXPECTED_JAR_SHA','1'*64):
   with self.assertRaisesRegex(r.Refused,'SOURCE_SHA256_DRIFT'):r.extract_checked_kit(data,self.root/'extract')
 def test_modified_dependency_rejected(self):
  self.deps['R218.jar']=b'wrong';data=self.kit()
  with patch.object(r,'R381_BUILD_KIT_SHA',r.sha(data)),patch.object(r,'SOURCE_COUNT',2),patch.object(r,'CLASS_COUNT',2),patch.object(r,'EXPECTED_JAR_SHA','1'*64):
   with self.assertRaisesRegex(r.Refused,'DEPENDENCY_SHA256_DRIFT'):r.extract_checked_kit(data,self.root/'extract')
 def test_release_approval_rejected(self):
  self.manifest['private_source_release_approved']=True;data=self.kit()
  with patch.object(r,'R381_BUILD_KIT_SHA',r.sha(data)),patch.object(r,'SOURCE_COUNT',2),patch.object(r,'CLASS_COUNT',2),patch.object(r,'EXPECTED_JAR_SHA','1'*64):
   with self.assertRaisesRegex(r.Refused,'PRIVATE_MANIFEST_AUTHORITY_CHANGED'):r.extract_checked_kit(data,self.root/'extract')
 def test_missing_source_rejected(self):
  self.manifest['source_sha256']['rs/Missing.java']='0'*64;data=self.kit()
  with patch.object(r,'R381_BUILD_KIT_SHA',r.sha(data)),patch.object(r,'SOURCE_COUNT',2),patch.object(r,'CLASS_COUNT',2),patch.object(r,'EXPECTED_JAR_SHA','1'*64):
   with self.assertRaises(r.Refused):r.extract_checked_kit(data,self.root/'extract')
 def test_path_traversal_refused(self):
  self.assertFalse(r.safe_member(ZipInfo('../escape.java')))
 def test_absolute_path_refused(self):
  self.assertFalse(r.safe_member(ZipInfo('/escape.java')))
 def test_windows_drive_path_refused(self):
  self.assertFalse(r.safe_member(ZipInfo('C:/bad.java')))
 def test_backslash_path_refused(self):
  self.assertFalse(r.safe_member(ZipInfo('..\\bad.java')))
 def test_symlink_member_refused(self):
  i=ZipInfo('source/link.java');i.external_attr=(stat.S_IFLNK|0o777)<<16
  self.assertFalse(r.safe_member(i))
 def test_duplicate_zip_member_rejected(self):
  data=self.kit(('source/rs/One.java',b'x'))
  with patch.object(r,'R381_BUILD_KIT_SHA',r.sha(data)),patch.object(r,'SOURCE_COUNT',2),patch.object(r,'CLASS_COUNT',2),patch.object(r,'EXPECTED_JAR_SHA','1'*64):
   with self.assertRaisesRegex(r.Refused,'DUPLICATE_OR_CASE_COLLISION'):r.extract_checked_kit(data,self.root/'extract')
 def test_javac_arg_path_quotes_spaces(self):
  p=self.root/'some path with spaces'/'One.java'
  got=r.javac_arg_path(p)
  self.assertTrue(got.startswith('"') and got.endswith('"'))
  self.assertIn('some path with spaces',got)
 def test_javac_arg_path_rejects_newline(self):
  with self.assertRaisesRegex(r.Refused,'UNSAFE_SOURCE_PATH'):r.javac_arg_path(self.root/'unsafe\n.java')
 def test_large_legitimate_dependency_member_allowed(self):
  i=ZipInfo('dependencies/R218.jar');i.file_size=10_279_399
  self.assertTrue(r.safe_member(i))
 def test_excessive_dependency_member_rejected(self):
  i=ZipInfo('dependencies/R218.jar');i.file_size=18_000_000
  self.assertFalse(r.safe_member(i))
 def test_existing_output_not_deleted(self):
  p=self.root/'output';p.mkdir();secret=p/'sentinel';secret.write_text('keep')
  # early refusal occurs before reading private input
  code=r.main(['--private-bundle',str(self.root/'missing'),'--javac','javac','--out-dir',str(p)])
  self.assertEqual(code,2);self.assertEqual(secret.read_text(),'keep')
 def test_evidence_never_claims_release(self):
  self.assertNotIn('automatic_stage_cleanup_enabled',r.__dict__)

if __name__=='__main__':unittest.main(verbosity=2)

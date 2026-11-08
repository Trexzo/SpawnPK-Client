"""R370 public synthetic-only tests; private sources never enter GitHub."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_v309_r370_version_receipt import (
    verify, sha, Refused, OWNERS, PREVIOUS_MANIFEST, CURRENT_MANIFEST)

class SourceWitnessTests(unittest.TestCase):
    def setUp(self):
        self.space = tempfile.TemporaryDirectory()
        self.addCleanup(self.space.cleanup)
        self.root=Path(self.space.name)
        self.original={
            OWNERS[0]:b'public synthetic source A',
            OWNERS[1]:b'public synthetic source B',
            'rs/gui/loadouts/Unchanged.java':b'class Unchanged {}',
        }
        self.changed={**self.original,
            OWNERS[0]:b'public synthetic updated A',
            OWNERS[1]:b'public synthetic updated B'}
        self.witness={
            'source_count':3,'changed_paths':list(OWNERS),
            'candidate_jar_sha256':'a'*64,
            'private_source_release_approved':False,
            'original_game_runtime_tested':False,
            'multi_file_transaction_proven':False,
            'power_loss_durability_tested':False,
            'fault_injection_verified_privately':True,
        }
        self._write_archives()

    def _write_archives(self):
        for name,sources,manifest in (
            ('old.zip',self.original,PREVIOUS_MANIFEST),
            ('new.zip',self.changed,CURRENT_MANIFEST)):
            with ZipFile(self.root/name,'w') as z:
                for path,data in sources.items():
                    z.writestr('source/'+path,data)
                props={'source_count':len(sources),'source_sha256':{
                    path:sha(data) for path,data in sources.items()}}
                if name=='new.zip':
                    props.update(changed_files=list(OWNERS),
                                 private_source_release_approved=False,
                                 multi_file_transaction='NOT_IMPLEMENTED',
                                 power_loss_durability='NOT_TESTED',
                                 same_source_built_jar_sha256='a'*64)
                z.writestr(manifest,json.dumps(props))
        self.witness['previous_zip_sha256']=sha((self.root/'old.zip').read_bytes())
        self.witness['candidate_zip_sha256']=sha((self.root/'new.zip').read_bytes())
        self.witness['previous_owner_sha256']={p:sha(self.original[p]) for p in OWNERS}
        self.witness['candidate_owner_sha256']={p:sha(self.changed.get(p,b'__MISSING__')) for p in OWNERS}

    def check(self):
        return verify(self.root/'old.zip',self.root/'new.zip',self.witness,expected_count=3)

    def test_expected_pair_passes(self):
        output=self.check()
        self.assertEqual(output['java_source_count'],3)
        self.assertFalse(output['private_source_release_approved'])
        self.assertFalse(output['multi_file_transaction_proven'])

    def test_old_archive_content_changed(self):
        (self.root/'old.zip').write_bytes(b'untrusted')
        with self.assertRaises(Refused):self.check()

    def test_new_archive_content_changed(self):
        (self.root/'new.zip').write_bytes(b'untrusted')
        with self.assertRaises(Refused):self.check()

    def test_third_source_modified(self):
        self.changed['rs/gui/loadouts/Unchanged.java']=b'class Changed {}'
        self._write_archives()
        with self.assertRaisesRegex(Refused,'UNEXPECTED_PRIVATE_JAVA_CHANGES'):
            self.check()

    def test_only_one_of_two_owners_changed(self):
        self.changed[OWNERS[1]]=self.original[OWNERS[1]]
        self._write_archives()
        with self.assertRaisesRegex(Refused,'UNEXPECTED_PRIVATE_JAVA_CHANGES'):
            self.check()

    def test_owner_missing(self):
        del self.changed[OWNERS[1]]
        self._write_archives()
        with self.assertRaises(Refused):self.check()

    def test_wrong_declaring_hash(self):
        self.witness['candidate_owner_sha256'][OWNERS[0]]='0'*64
        with self.assertRaisesRegex(Refused,'DECLARING_SOURCE_SHA_CHANGED'):
            self.check()

    def test_bad_source_count(self):
        self.witness['source_count']=5
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS_CONTENTS'):
            self.check()

    def test_bad_candidate_jar_sha(self):
        self.witness['candidate_jar_sha256']='not-a-hash'
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS_CONTENTS'):
            self.check()

    def test_disallow_private_publication_claim(self):
        self.witness['private_source_release_approved']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS_CONTENTS'):
            self.check()

    def test_disallow_unverified_game_runtime_claim(self):
        self.witness['original_game_runtime_tested']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS_CONTENTS'):
            self.check()

    def test_disallow_unverified_multifile_claim(self):
        self.witness['multi_file_transaction_proven']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS_CONTENTS'):
            self.check()

    def test_disallow_unverified_power_loss_claim(self):
        self.witness['power_loss_durability_tested']=True
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS_CONTENTS'):
            self.check()

    def test_disallow_unrecorded_schema_key(self):
        self.witness['override_all_warnings']=True
        with self.assertRaisesRegex(Refused,'WITNESS_SCHEMA_CHANGED'):
            self.check()

    def test_fault_injection_must_be_claimed_from_private(self):
        self.witness['fault_injection_verified_privately']=False
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS_CONTENTS'):
            self.check()

    def test_owner_list_must_be_exact(self):
        self.witness['changed_paths']=list(reversed(OWNERS))
        with self.assertRaisesRegex(Refused,'INVALID_WITNESS_CONTENTS'):
            self.check()

    def test_symlinked_archive_refused(self):
        original=self.root/'new.zip'
        link=self.root/'linked.zip'
        try:link.symlink_to(original)
        except (OSError,NotImplementedError):self.skipTest('Symlinks unavailable')
        with self.assertRaisesRegex(Refused,'PRIVATE_ARCHIVE_TYPE_OR_SIZE_REFUSED'):
            verify(self.root/'old.zip',link,self.witness,expected_count=3)

    def test_public_witness_does_not_contain_java_source(self):
        self.assertEqual(len(OWNERS),2)
        self.assertFalse(self.witness['private_source_release_approved'])
        self.assertEqual(len(self.witness['candidate_jar_sha256']),64)

if __name__=='__main__':unittest.main(verbosity=2)

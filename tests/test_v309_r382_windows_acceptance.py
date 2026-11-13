"""Synthetic-only tests; never import recovered proprietary Java source."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.verify_v309_r382_windows_acceptance import (
    JAR_SHA, R381_SOURCE_ZIP_SHA, EXPECTED_TESTS, Refused,
    SAFE_FLAGS, validate_witness, verify_results,
)
WITNESS_PATH=Path(__file__).resolve().parents[1] / 'research/v309-source-recovery/r382-windows-source-backed-witness.json'

class R382SyntheticOnly(unittest.TestCase):
    def setUp(self):
        self.w=json.loads(WITNESS_PATH.read_text('utf8'))
        self.report={'status':'R382_WINDOWS_SOURCE_TEST_PASS','os':'nt',
             'java':'openjdk version "21.0.12.1" 2026-08-18 LTS',
             'private_sources_sha_checked':10,
             'scripts':[{'test':n,'status':'PASS','seconds':1.0,'output':'synthetic'} for n in EXPECTED_TESTS]}

    def test_witness_has_correct_scope(self):
        self.assertEqual(validate_witness(self.w)['status'],'R382_PUBLIC_WITNESS_VALID')
    def test_baseline_source_and_jar_pinned(self):
        self.assertEqual(self.w['baseline_r381_source_zip_sha256'], R381_SOURCE_ZIP_SHA)
        self.assertEqual(self.w['baseline_r381_jar_sha256'], JAR_SHA)
    def test_no_private_source_published(self):
        self.assertEqual(self.w['private_java_source_files_changed'], [])
        self.assertFalse(self.w['private_source_release_approved'])
    def test_windows_test_matrix_is_exact(self):
        self.assertEqual(verify_results(self.report)['passed'],15)
    def test_valid_digest_mode(self):
        raw=json.dumps(self.report).encode()
        self.assertEqual(verify_results(self.report,hashlib.sha256(raw).hexdigest(),raw)['passed'],15)
    def test_modified_result_digest_refused(self):
        raw=json.dumps(self.report).encode()
        with self.assertRaisesRegex(Refused,'DIGEST_DRIFT'):
            verify_results(self.report,'0'*64,raw)
    def test_extra_or_duplicate_test_refused(self):
        self.report['scripts'][-1]['test']=EXPECTED_TESTS[0]
        with self.assertRaises(Refused):verify_results(self.report)
    def test_failed_test_refused(self):
        self.report['scripts'][3]['status']='FAIL'
        with self.assertRaisesRegex(Refused,'WINDOWS_TEST_FAILURE'):verify_results(self.report)
    def test_false_success_status_refused(self):
        self.report['status']='R382_PARTIAL'
        with self.assertRaises(Refused):verify_results(self.report)
    def test_linux_cannot_claim_windows_acceptance(self):
        self.report['os']='posix'
        with self.assertRaises(Refused):verify_results(self.report)
    def test_source_hash_count_must_match(self):
        self.report['private_sources_sha_checked']=9
        with self.assertRaises(Refused):verify_results(self.report)
    def test_bad_java_version_refused(self):
        self.report['java']='java 8'
        with self.assertRaises(Refused):verify_results(self.report)
    def test_bad_report_seconds_refused(self):
        self.report['scripts'][0]['seconds']=-1
        with self.assertRaises(Refused):verify_results(self.report)
    def test_unexpected_witness_field_refused(self):
        self.w['publish_source']=True
        with self.assertRaisesRegex(Refused,'UNEXPECTED_WITNESS_SCHEMA'):validate_witness(self.w)
    def test_no_release_gate_can_claim_pass(self):
        for flag in SAFE_FLAGS:
            with self.subTest(flag=flag):
                w=dict(self.w);w[flag]=True
                with self.assertRaises(Refused):validate_witness(w)
    def test_no_source_change_can_be_inferred(self):
        self.w['private_java_source_files_changed']=['rs/Client.java']
        with self.assertRaises(Refused):validate_witness(self.w)
    def test_bad_baseline_jar_refused(self):
        self.w['baseline_r381_jar_sha256']='0'*64
        with self.assertRaises(Refused):validate_witness(self.w)
    def test_missing_symlink_limitation_refused(self):
        self.w['symlink_test_limitations']=[]
        with self.assertRaises(Refused):validate_witness(self.w)
    def test_unknown_script_set_refused(self):
        self.w['windows_test_names'].append('test_forged.py')
        with self.assertRaises(Refused):validate_witness(self.w)

if __name__=='__main__':unittest.main(verbosity=2)

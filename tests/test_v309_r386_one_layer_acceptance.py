"""R386 synthetic-only contract tests. Never imports recovered source or binaries."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/r386/run_self_contained_acceptance.py'
spec = importlib.util.spec_from_file_location('r386_acceptance', SCRIPT)
subject = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = subject
spec.loader.exec_module(subject)


def good_build(windows: bool) -> dict:
    return {
        'source_sha256_verified': 1277,
        'dependency_sha256_verified': ['R218.jar', 'R239_filtered.jar'],
        'generated_classfiles': 1388,
        'jar_sha256': subject.REFERENCE_SHA,
        'private_source_release_approved': False,
        'platform': 'windows' if windows else 'non-windows',
        'windows_full_compile_tested': windows,
        'status': ('R383_WINDOWS_PRIVATE_FULL_BUILD_PASS' if windows else
                   'R383_LINUX_REFERENCE_REBUILD_PASS'),
    }


def good_compare() -> dict:
    return {
        'status': 'EXACT_HASH_MATCH',
        'jar_reference_sha256': subject.REFERENCE_SHA,
        'jar_candidate_sha256': subject.REFERENCE_SHA,
        'class_count_candidate': 1388,
    }


class VerdictTest(unittest.TestCase):
    def test_true_native_windows_report_only(self):
        self.assertEqual(subject.assess(good_build(True), good_compare(), 'nt'),
                         'R386_WINDOWS_FULL_BUILD_PASS')

    def test_linux_rehearsal_never_windows_pass(self):
        self.assertEqual(subject.assess(good_build(False), good_compare(), 'posix'),
                         'R386_LINUX_REHEARSAL_PASS')

    def test_linux_report_claiming_windows_fails(self):
        self.assertEqual(subject.assess(good_build(True), good_compare(), 'posix'),
                         'R386_REFUSED_OR_DRIFT')

    def test_windows_report_claiming_linux_fails(self):
        self.assertEqual(subject.assess(good_build(False), good_compare(), 'nt'),
                         'R386_REFUSED_OR_DRIFT')

    def test_windows_claim_from_synthetic_flag_false_rejected(self):
        report = good_build(True)
        report['windows_full_compile_tested'] = False
        self.assertEqual(subject.assess(report, good_compare(), 'nt'), 'R386_REFUSED_OR_DRIFT')

    def test_class_byte_drift_rejected(self):
        cmp = good_compare()
        cmp['status'] = 'CLASSFILE_BYTE_DRIFT'
        self.assertEqual(subject.assess(good_build(True), cmp, 'nt'), 'R386_REFUSED_OR_DRIFT')

    def test_archive_only_drift_rejected(self):
        cmp = good_compare()
        cmp['status'] = 'CLASS_BYTES_EQUAL_ARCHIVE_DRIFT'
        self.assertEqual(subject.assess(good_build(True), cmp, 'nt'), 'R386_REFUSED_OR_DRIFT')

    def test_changed_reference_hash_rejected(self):
        cmp = good_compare()
        cmp['jar_reference_sha256'] = '0' * 64
        self.assertEqual(subject.assess(good_build(True), cmp, 'nt'), 'R386_REFUSED_OR_DRIFT')

    def test_missing_dependency_proof_rejected(self):
        r = good_build(True)
        r['dependency_sha256_verified'] = []
        self.assertEqual(subject.assess(r, good_compare(), 'nt'), 'R386_REFUSED_OR_DRIFT')

    def test_missing_source_proof_rejected(self):
        r = good_build(True)
        r['source_sha256_verified'] = 1276
        self.assertEqual(subject.assess(r, good_compare(), 'nt'), 'R386_REFUSED_OR_DRIFT')

    def test_wrong_class_count_rejected(self):
        r = good_build(True)
        r['generated_classfiles'] = 1387
        self.assertEqual(subject.assess(r, good_compare(), 'nt'), 'R386_REFUSED_OR_DRIFT')

    def test_released_source_claim_rejected(self):
        r = good_build(True)
        r['private_source_release_approved'] = True
        self.assertEqual(subject.assess(r, good_compare(), 'nt'), 'R386_REFUSED_OR_DRIFT')

    def test_failed_runner_status_rejected(self):
        r = good_build(True)
        r['status'] = 'R383_REFUSED_OR_FAILED'
        self.assertEqual(subject.assess(r, good_compare(), 'nt'), 'R386_REFUSED_OR_DRIFT')


class PreflightTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.kit = self.root / subject.KIT_NAME
        self.ref = self.root / subject.REFERENCE_NAME
        self.kit.write_bytes(b'SYNTHETIC_KIT')
        self.ref.write_bytes(b'SYNTHETIC_JAR')
        self.pin1 = hashlib.sha256(self.kit.read_bytes()).hexdigest()
        self.pin2 = hashlib.sha256(self.ref.read_bytes()).hexdigest()

    def check(self):
        return subject.verify_private_files(self.root, self.pin1, self.pin2)

    def test_expected_paths_succeed(self):
        self.assertEqual(self.check(), (self.kit, self.ref))

    def test_corrupt_private_kit_refused(self):
        self.kit.write_bytes(b'TAMPERED')
        with self.assertRaisesRegex(subject.Refused, 'PRIVATE_SHA256_MISMATCH'):
            self.check()

    def test_corrupt_reference_jar_refused(self):
        self.ref.write_bytes(b'TAMPERED')
        with self.assertRaisesRegex(subject.Refused, 'PRIVATE_SHA256_MISMATCH'):
            self.check()

    def test_missing_kit_refused(self):
        self.kit.unlink()
        with self.assertRaisesRegex(subject.Refused, 'PRIVATE_FILE_MISSING_OR_UNSAFE'):
            self.check()

    def test_reference_symlink_refused(self):
        self.ref.unlink()
        actual = self.root / 'existing'
        actual.write_bytes(b'SYNTHETIC_JAR')
        try:
            self.ref.symlink_to(actual)
        except (OSError, NotImplementedError):
            self.skipTest('unprivileged Windows symlinks unavailable')
        with self.assertRaisesRegex(subject.Refused, 'PRIVATE_FILE_MISSING_OR_UNSAFE'):
            self.check()

    def test_existing_output_not_modified(self):
        out = self.root / 'existing-out'
        out.mkdir()
        marker = out / 'keep.txt'
        marker.write_text('KEEP', encoding='utf-8')
        self.assertEqual(subject.main(['--bundle-dir', str(self.root),
            '--javac', sys.executable, '--out-dir', str(out)]), 2)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'KEEP')

    def test_missing_bundle_preflight_creates_no_output(self):
        self.kit.unlink()
        out = self.root / 'new-result'
        self.assertEqual(subject.main(['--bundle-dir', str(self.root),
            '--javac', sys.executable, '--out-dir', str(out)]), 2)
        self.assertFalse(out.exists())

    def test_tampered_verifier_tool_refused_before_output(self):
        runner = self.root / 'tools/r383/verify_private_full_build.py'
        compare = self.root / 'tools/r385/compare_local_build_jars.py'
        runner.parent.mkdir(parents=True)
        compare.parent.mkdir(parents=True)
        runner.write_text('# test runner\n', encoding='utf-8')
        compare.write_text('# comparator\n', encoding='utf-8')
        h_runner = hashlib.sha256(runner.read_bytes()).hexdigest()
        h_comparator = hashlib.sha256(compare.read_bytes()).hexdigest()
        runner.write_text('# TAMPERED runner\n', encoding='utf-8')
        out = self.root / 'new-output'
        with mock.patch.multiple(subject, KIT_SHA=self.pin1, REFERENCE_SHA=self.pin2,
                                 RUNNER_SHA=h_runner, COMPARATOR_SHA=h_comparator):
            self.assertEqual(subject.main(['--bundle-dir', str(self.root),
                '--javac', sys.executable, '--out-dir', str(out)]), 2)
        self.assertFalse(out.exists())

    def test_missing_verifier_tool_refused_before_output(self):
        out = self.root / 'new-output'
        with mock.patch.multiple(subject, KIT_SHA=self.pin1, REFERENCE_SHA=self.pin2):
            self.assertEqual(subject.main(['--bundle-dir', str(self.root),
                '--javac', sys.executable, '--out-dir', str(out)]), 2)
        self.assertFalse(out.exists())

    def test_powershell_launcher_explicit_windows_gate(self):
        powershell = (SCRIPT.parent / 'Run-R386-Windows.ps1').read_text(encoding='utf-8')
        self.assertIn('R386_WINDOWS_ONLY', powershell)
        self.assertIn('R386_WINDOWS_FULL_BUILD_PASS', powershell)
        self.assertIn('R386_REFUSE_EXISTING_OUTPUT', powershell)
        self.assertNotIn('fullspkclient', powershell.lower().replace('production fullspkclient directory', ''))


if __name__ == '__main__':
    unittest.main(verbosity=2)

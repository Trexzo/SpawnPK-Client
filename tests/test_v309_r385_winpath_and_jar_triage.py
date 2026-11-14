"""Only synthetic fixtures; never uploads or imports private source."""
from __future__ import annotations
import io
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def import_script(path, name):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m)
    return m
run=import_script(ROOT/'tools/r383/verify_private_full_build.py','r385_runner')
triage=import_script(ROOT/'tools/r385/compare_local_build_jars.py','r385_triage')

def jar_entries(classes=None, os_marker=3, comment=b'', order=None):
    classes=classes or {'p/A.class':b'CAFEBABE-aa','p/B.class':b'CAFEBABE-bb'}
    bio=io.BytesIO()
    with zipfile.ZipFile(bio,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in (order or list(classes)):
            x=zipfile.ZipInfo(name,(2026,10,18,0,0,0))
            x.create_system=os_marker
            x.external_attr=0o644 << 16
            z.writestr(x,classes[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        z.comment=comment
    return bio.getvalue()

class WindowsPathCases(unittest.TestCase):
    def test_plain_source_archive_members_pass(self):
        for n in ('MANIFEST.json','source/rs/Foo.java','dependencies/R218.jar'):
            self.assertTrue(run.safe_member(zipfile.ZipInfo(n)))
    def test_windows_reserved_devices_rejected(self):
        for component in ('CON','con.txt','PRN.java','AuX.log','nul','com1.class','COM9.jar',
                          'LPT1','lpt9.txt','CONIN$.java','CONOUT$.java','COM¹.java','LPT².txt'):
            with self.subTest(component=component):
                self.assertFalse(run.safe_member(zipfile.ZipInfo('source/rs/'+component)))
    def test_windows_trailing_dots_spaces_and_invalid_chars_rejected(self):
        for component in ('Name.','Name ','Name. ','a?b.java','a*b.java','a<b.java','a>b.java',
                          'a|b.java','a"b.java','a\x1fb.java','a\x7fb.java',
                          'foo:bar.java'):
            with self.subTest(component=component):
                self.assertFalse(run.safe_member(zipfile.ZipInfo('source/'+component)))
    def test_zero_byte_path_component_rejected_before_zipfile_normalization(self):
        self.assertFalse(run.safe_windows_component('a\x00b.java'))
    def test_windows_valid_names_near_reserved_are_allowed(self):
        for component in ('CONNECTION.java','COM10.java','COM0.java','PRN2.java','no-con.txt',
                          'rs.gui.Main.java'):
            with self.subTest(component=component):
                self.assertTrue(run.safe_member(zipfile.ZipInfo('source/'+component)))

class JarTriageCases(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory();self.addCleanup(self.d.cleanup)
        self.root=Path(self.d.name)
        self.ref=self.root/'ref.jar';self.cand=self.root/'cand.jar'
        self.ref.write_bytes(jar_entries());self.cand.write_bytes(jar_entries())
    def classify(self):return triage.compare(self.ref,self.cand)
    def test_identical_jars(self):
        r=self.classify();self.assertEqual(r['status'],'EXACT_HASH_MATCH')
        self.assertEqual(r['class_count_reference'],2)
    def test_zip_creator_header_only(self):
        self.cand.write_bytes(jar_entries(os_marker=0))
        r=self.classify();self.assertEqual(r['status'],'CLASS_BYTES_EQUAL_ARCHIVE_DRIFT')
        self.assertFalse(r['zip_entry_metadata_equal'])
        self.assertEqual(r['changed_class_bytes'],0)
    def test_order_only(self):
        self.cand.write_bytes(jar_entries(order=['p/B.class','p/A.class']))
        r=self.classify();self.assertEqual(r['status'],'CLASS_BYTES_EQUAL_ARCHIVE_DRIFT')
        self.assertFalse(r['zip_entry_metadata_equal'])
    def test_comment_only(self):
        self.cand.write_bytes(jar_entries(comment=b'changed'))
        r=self.classify();self.assertEqual(r['status'],'CLASS_BYTES_EQUAL_ARCHIVE_DRIFT')
        self.assertFalse(r['zip_archive_comments_equal'])
    def test_actual_class_change(self):
        self.cand.write_bytes(jar_entries({'p/A.class':b'changed','p/B.class':b'CAFEBABE-bb'}))
        r=self.classify();self.assertEqual(r['status'],'CLASSFILE_BYTE_DRIFT')
        self.assertEqual(r['changed_class_bytes'],1)
        self.assertNotIn('p/A.class',json.dumps(r))
    def test_class_set_change(self):
        self.cand.write_bytes(jar_entries({'p/A.class':b'CAFEBABE-aa','p/C.class':b'CAFEBABE-cc'}))
        r=self.classify();self.assertEqual(r['status'],'CLASS_SET_DRIFT')
        self.assertEqual((r['new_classes'],r['missing_classes']),(1,1))
    def test_duplicate_entries_rejected(self):
        with zipfile.ZipFile(self.cand,'w') as z:
            z.writestr('p/A.class',b'1');z.writestr('p/A.class',b'2')
        with self.assertRaisesRegex(triage.Refused,'DUPLICATE_OR_CASE_COLLISION'):self.classify()
    def test_case_collisions_rejected(self):
        with zipfile.ZipFile(self.cand,'w') as z:
            z.writestr('p/A.class',b'1');z.writestr('p/a.class',b'2')
        with self.assertRaisesRegex(triage.Refused,'DUPLICATE_OR_CASE_COLLISION'):self.classify()
    def test_nonclass_entries_rejected(self):
        self.cand.write_bytes(jar_entries({'p/A.txt':b'bad'}))
        with self.assertRaisesRegex(triage.Refused,'UNSAFE_OR_NONCLASS_ENTRY'):self.classify()
    def test_traversal_rejected(self):
        self.cand.write_bytes(jar_entries({'../evil.class':b'bad'}))
        with self.assertRaisesRegex(triage.Refused,'UNSAFE_OR_NONCLASS_ENTRY'):self.classify()
    def test_missing_file_rejected(self):
        self.cand.unlink()
        with self.assertRaisesRegex(triage.Refused,'MISSING_UNSAFE_OR_OVERSIZED_JAR'):self.classify()
    def test_cli_refuses_existing_report(self):
        report=self.root/'report.json';report.write_text('KEEP')
        self.assertEqual(triage.main(['--reference',str(self.ref),'--candidate',str(self.cand),
                                      '--output',str(report)]),2)
        self.assertEqual(report.read_text(),'KEEP')
    def test_cli_emits_json_report(self):
        report=self.root/'new_report.json'
        self.assertEqual(triage.main(['--reference',str(self.ref),'--candidate',str(self.cand),
                                     '--output',str(report)]),0)
        d=json.loads(report.read_text());self.assertEqual(d['status'],'EXACT_HASH_MATCH')
        self.assertFalse(d['source_release_approved'])

if __name__=='__main__':unittest.main(verbosity=2)

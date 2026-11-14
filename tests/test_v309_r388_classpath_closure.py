import hashlib
import importlib.util
import io
from pathlib import Path
import struct
import tempfile
import unittest
import warnings
import zipfile

TARGET=Path(__file__).resolve().parents[1]/'tools/r388/audit_offline_classpath.py'
spec=importlib.util.spec_from_file_location('classpath', TARGET)
cp=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


def minimal_class(name, refs=()):
    # Synthetic constant pool; deliberately not a runnable or proprietary JVM class.
    values=(name, *refs)
    entries=bytearray()
    for i, n in enumerate(values,1):
        encoded=n.encode('utf-8')
        entries+=b'\x01'+struct.pack('>H',len(encoded))+encoded
    for i in range(len(values)):
        entries+=b'\x07'+struct.pack('>H',i+1)
    return b'\xca\xfe\xba\xbe\x00\x00\x00\x37'+struct.pack('>H',2*len(values)+1)+entries


def make_zip(path, entries):
    with zipfile.ZipFile(path,'w') as out:
        for name,data in entries:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                out.writestr(name,data)

class ClasspathAuditTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(cp.constant_class_refs(minimal_class('a/Test')),{'a/Test.class'})
    def test_class_references(self):
        self.assertEqual(cp.constant_class_refs(minimal_class('a/X',['a/Y','java/lang/Object'])),{'a/X.class','a/Y.class','java/lang/Object.class'})
    def test_arrays(self):
        self.assertEqual(cp.constant_class_refs(minimal_class('a/X',['[[La/Y;','[I'])),{'a/X.class','a/Y.class'})
    def test_bad_magic(self):
        with self.assertRaisesRegex(ValueError,'classfile'):cp.constant_class_refs(b'not a class')
    def test_bad_tag(self):
        d=bytearray(minimal_class('a/X'));d[10]=99
        with self.assertRaisesRegex(ValueError,'tag'):cp.constant_class_refs(d)
    def test_truncation(self):
        with self.assertRaises(ValueError):cp.constant_class_refs(minimal_class('a/X')[:17])
    def test_closure_and_platform_exclusion(self):
        g={'a/X.class':{'a/Y.class','java/lang/Object.class'},'a/Y.class':{'missing/F.class'}}
        reached,missing=cp.closure(g,'a/X.class')
        self.assertEqual(reached,set(g))
        self.assertEqual(missing,{'missing/F.class':{'a/Y.class'}})
    def test_unreachable_gap_omitted(self):
        g={'a/X.class':set(),'a/Y.class':{'missing/F.class'}}
        reached,missing=cp.closure(g,'a/X.class')
        self.assertEqual(reached,{'a/X.class'});self.assertEqual(missing,{})
    def test_primary_superset_exact(self):
        a={'a/X.class':minimal_class('a/X')}
        primary={'b/Y.class':minimal_class('b/Y'),'c/Z.class':minimal_class('c/Z')}
        alternate={'b/Y.class':primary['b/Y.class']}
        r=cp.audit(a,primary,alternate,'a/X.class')
        self.assertEqual(r['primary_only_paths'],['c/Z.class'])
        self.assertEqual(r['dependency_common_byte_differences'],0)
        self.assertEqual(r['candidate_primary_collisions'],0)
    def test_detect_changed_common_dep(self):
        r=cp.audit({}, {'a/A.class':minimal_class('a/A')},{'a/A.class':minimal_class('a/A',['a/B'])},'a/A.class')
        self.assertEqual(r['dependency_common_byte_differences'],1)
    def test_detect_missing_candidate_ref(self):
        r=cp.audit({'a/X.class':minimal_class('a/X',['unprovided/Y'])},{},{},'a/X.class')
        self.assertEqual(r['static_candidate_missing_nonplatform'],['unprovided/Y.class'])
    def test_load_zip_and_pin(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'in.jar';make_zip(p,[('a/X.class',minimal_class('a/X')),('a/notes.txt',b'hello')])
            self.assertEqual(len(cp.load_classes(p,cp.sha256(p.read_bytes()))),1)
            with self.assertRaisesRegex(ValueError,'SHA256_MISMATCH'):cp.load_classes(p,'0'*64)
    def test_refuse_duplicate_class(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'dup.jar';b=minimal_class('a/X')
            make_zip(p,[('a/X.class',b),('a/X.class',b)])
            with self.assertRaisesRegex(ValueError,'DUPLICATE_CLASS'):cp.load_classes(p)
    def test_refuse_unsafe_path(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'unsafe.jar';make_zip(p,[('../x.class',minimal_class('x'))])
            with self.assertRaisesRegex(ValueError,'UNSAFE_CLASS_PATH'):cp.load_classes(p)
    def test_advisory_flag(self):
        r=cp.audit({'a/X.class':minimal_class('a/X')},{},{},'a/X.class')
        self.assertTrue(r['advisory_only']);self.assertTrue(r['entry_present'])
        self.assertIn('NOT runtime',r['warning'])

if __name__=='__main__':unittest.main(verbosity=2)

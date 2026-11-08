"""Self-contained regression tests; only synthetic Java classes are compiled."""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile
from scan_v309_network import (
    AuditRefused, PIN, PIN_SIZE, audit_jar, bytecode_ops, interesting,
    parse_class,
)

SOURCE = r'''package rs;
public final class Client {
  public static void b(int port) throws Exception {
    java.net.InetAddress a = java.net.InetAddress.getByName("DO_NOT_LOG_THIS_HOST.example.invalid");
    java.net.Socket s = new java.net.Socket(a,port);
    s.close();
  }
  public static int switches(int x, boolean dense) throws Exception {
    if (dense) {
      switch(x) { case 0: return 1; case 1: return 2; case 2: return 3; default: return 4; }
    } else {
      switch(x) { case 100: return 5; case 10000: return 6; default: return 7; }
    }
  }
  public static Object reflect() throws Exception {
    return Class.forName("java.lang.String");
  }
}
'''

class ScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        src = cls.root/'src'/'rs'/'Client.java'
        src.parent.mkdir(parents=True)
        src.write_text(SOURCE,encoding='utf-8')
        cls.classes = cls.root/'classes'
        cls.classes.mkdir()
        p = subprocess.run(['javac','--release','8','-d',str(cls.classes),str(src)],
                           capture_output=True,text=True,timeout=30)
        if p.returncode:
            raise AssertionError(p.stderr)
        cls.data=(cls.classes/'rs'/'Client.class').read_bytes()
        cls.jar=cls.root/'synthetic.jar'
        with zipfile.ZipFile(cls.jar,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('rs/Client.class',cls.data)
        cls.hash=hashlib.sha256(cls.jar.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_method_level_invocations_not_constant_pool_only(self):
        klass, rows, indirect, internal_edges = parse_class(self.data)
        self.assertEqual(klass,'rs/Client')
        calls={(r['method'],r['target_class'],r['target_method']) for r in rows}
        self.assertIn(('b','java.net.InetAddress','getByName'),calls)
        self.assertIn(('b','java.net.Socket','<init>'),calls)
        self.assertIn(('b','java.net.Socket','close'),calls)
        self.assertTrue(all(r['method']=='b' for r in rows))
        self.assertTrue(indirect>=1)
        self.assertEqual(internal_edges,[])

    def test_report_fails_closed_with_missing_pin(self):
        with self.assertRaisesRegex(AuditRefused,'SIZE_MISMATCH'):
            audit_jar(self.jar)
        with self.assertRaisesRegex(AuditRefused,'SHA256_MISMATCH'):
            audit_jar(self.jar,expected_size=self.jar.stat().st_size,expected_pin='0'*64)

    def test_explicit_test_pin_produces_static_only_report(self):
        r=audit_jar(self.jar,expected_size=self.jar.stat().st_size,expected_pin=self.hash)
        self.assertEqual(r['classes_scanned'],1)
        self.assertEqual(r['original_jar_sha256'],self.hash)
        self.assertTrue(r['known_client_b_getByName_seen'])
        self.assertTrue(r['known_client_b_socket_init_seen'])
        self.assertFalse(r['original_jar_executed'])
        self.assertFalse(r['runtime_network_destinations_verified'])
        self.assertFalse(r['same_pid_reconnect_verified'])
        self.assertFalse(r['os_egress_attested'])
        self.assertNotIn('DO_NOT_LOG_THIS_HOST',str(r))
        self.assertEqual(r['startup_class_network_callsite_count'],0)
        self.assertEqual(r['nominal_startup_reachable_network_calls_count'],0)

    def test_switch_bytecode_parses_without_spurious_calls(self):
        klass, rows, _, internal_edges=parse_class(self.data)
        self.assertEqual(klass,'rs/Client')
        self.assertGreaterEqual(len(rows),3)

    def test_manually_encoded_switches(self):
        # op at PC0, 3 padding bytes, default=0, low=1, high=1, one jump
        t=bytes([0xaa,0,0,0])+bytes(16)
        self.assertEqual([(offset,op) for offset,op,_ in bytecode_ops(t)],[(0,0xaa)])
        # lookupswitch default=0, npairs=1, pair(1, 5)
        l=bytes([0xab,0,0,0])+bytes(4)+bytes([0,0,0,1])+bytes([0,0,0,1,0,0,0,5])
        self.assertEqual([(offset,op) for offset,op,_ in bytecode_ops(l)],[(0,0xab)])
        with self.assertRaises(AuditRefused):list(bytecode_ops(t[:-1]))
        with self.assertRaises(AuditRefused):list(bytecode_ops(l[:-1]))

    def test_nominal_launcher_to_client_network_chain(self):
        launcher_src=self.root/'src'/'rs'/'gui'/'Launcher.java'
        launcher_src.parent.mkdir(parents=True,exist_ok=True)
        launcher_src.write_text('package rs.gui; public class Launcher { public static void main(String[] args) throws Exception { rs.Client.b(43594); } }',encoding='utf-8')
        result=subprocess.run(['javac','--release','8','-cp',str(self.classes),'-d',str(self.classes),str(launcher_src)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        fake=self.root/'launcher.jar'
        with zipfile.ZipFile(fake,'w') as z:
            z.writestr('rs/Client.class',self.data)
            z.writestr('rs/gui/Launcher.class',(self.classes/'rs'/'gui'/'Launcher.class').read_bytes())
        a=audit_jar(fake,expected_size=fake.stat().st_size,
                   expected_pin=hashlib.sha256(fake.read_bytes()).hexdigest())
        self.assertGreaterEqual(a['nominal_launcher_main_roots'],1)
        self.assertGreaterEqual(a['nominal_startup_reachable_network_calls_count'],2)
        p=a['nominal_startup_network_paths'][0]
        self.assertEqual(p['nominal_hops_from_launcher_main'],1)
        self.assertEqual(len(p['path']),2)
        self.assertIn('rs.gui.Launcher#main',p['path'][0])
        self.assertIn('rs.Client#b',p['path'][-1])

    def test_wide_decode_and_refuse(self):
        self.assertEqual([(o,p) for o,p,_ in bytecode_ops(bytes([0xc4,0x15,0,1,0xb1]))],[(0,0xc4),(4,0xb1)])
        self.assertEqual([(o,p) for o,p,_ in bytecode_ops(bytes([0xc4,0x84,0,1,0,2,0xb1]))],[(0,0xc4),(6,0xb1)])
        for code in (b'\xc4', b'\xc4\x84', b'\xc4\x15\x00',b'\xc4\x01\x00\x00'):
            with self.subTest(code=code),self.assertRaises(AuditRefused):list(bytecode_ops(code))

    def test_invalid_opcode_and_bad_file(self):
        with self.assertRaises(AuditRefused): list(bytecode_ops(b'\xff'))
        with self.assertRaises(AuditRefused): list(bytecode_ops(b'\xb8\x00'))
        with self.assertRaises(AuditRefused): parse_class(b'\x00'*6)
        with self.assertRaises(AuditRefused): parse_class(self.data[:-1])

    def test_first_party_class_only(self):
        clone=self.root/'ignorelib.jar'
        with zipfile.ZipFile(clone,'w') as z:
            z.writestr('rs/Client.class',self.data)
            z.writestr('org/example/NotFirstParty.class',self.data)
        result=audit_jar(clone,expected_size=clone.stat().st_size,
                         expected_pin=hashlib.sha256(clone.read_bytes()).hexdigest())
        self.assertEqual(result['classes_scanned'],1)

    def test_duplicate_filename_refused(self):
        dup=self.root/'duplicate.jar'
        with zipfile.ZipFile(dup,'w') as z:
            z.writestr('rs/Client.class',self.data)
            z.writestr('rs/Client.class',self.data)
        with self.assertRaisesRegex(AuditRefused,'DUPLICATE'):
            audit_jar(dup,expected_size=dup.stat().st_size,
                      expected_pin=hashlib.sha256(dup.read_bytes()).hexdigest())

    def test_all_planned_network_prefixes(self):
        self.assertTrue(interesting('java/net/Socket'))
        self.assertTrue(interesting('javax/net/ssl/SSLSocket'))
        self.assertTrue(interesting('java/nio/channels/SocketChannel'))
        self.assertTrue(interesting('org/apache/http/client/HttpClient'))
        self.assertFalse(interesting('java/lang/String'))
        self.assertFalse(interesting('java/net/URI'))

    def test_no_original_jar_in_bundle(self):
        self.assertEqual(len(PIN),64)
        self.assertEqual(PIN_SIZE,17532075)
        self.assertFalse((Path(__file__).parent/'client.jar').exists())

if __name__=='__main__': unittest.main(verbosity=2)

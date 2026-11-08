"""R348 synthetic javap mutation controls; no original game JAR in CI."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from audit_original_config_bytecode import (
    EvidenceRefused, audit_cache_path, audit_socket_callsite,
    audit_texts, decode_javap, method_section, validate_original_jar
)

CACHE_JAVAP="""\
public final class rs.v.a {
  public static java.lang.String b();
    Code:
       2: ldc           #46                 // String user.home
       4: invokestatic  #177                // Method java/lang/System.getProperty:(Ljava/lang/String;)Ljava/lang/String;
       8: ldc           #38                 // String file.separator
      10: invokestatic  #177                // Method java/lang/System.getProperty:(Ljava/lang/String;)Ljava/lang/String;
      14: getstatic     #110                // Field rs/f/a.B:Ljava/lang/String;
      17: invokevirtual #172                // Method java/lang/String.toLowerCase:()Ljava/lang/String;
      68: invokevirtual #153                // Method java/io/File.mkdir:()Z
      75: areturn
  public static java.lang.String c();
    Code:
       0: aconst_null
}
"""
CLIENT_JAVAP="""\
public final class rs.Client {
  public void a(java.lang.String, java.lang.String, boolean);
    Code:
      172: aload_0
      177: ldc           #4010               // int 43594
      180: invokevirtual #3980               // Method b:(I)Ljava/net/Socket;
      186: putfield      #2600               // Field nF:Lrs/q/b;
      200: return
  public void another();
    Code:
       0: return
}
"""

class TestR348BytecodeWitness(unittest.TestCase):
    def test_evidence_positive_is_static_only(self):
        data=audit_texts(CACHE_JAVAP,CLIENT_JAVAP)
        self.assertEqual(data["cache_path"]["status"],
                         "ORIGINAL_CACHE_PATH_FORMULA_WITNESSED")
        self.assertEqual(data["cache_path"]["concrete_cache_directory_name"],
                         "UNRESOLVED")
        self.assertEqual(data["login_socket"]["observed_port_literal"],43594)
        self.assertEqual(data["login_socket"]["actual_remote_host"],"UNRESOLVED")
        self.assertFalse(data["r347_loopback_is_protocol_compatible"])
        self.assertEqual(data["original_v309_authenticated_login"],"NOT_TESTED")
        self.assertEqual(data["original_same_process_reconnect"],"NOT_TESTED")
        self.assertEqual(data["original_jar_identity"],
                         "NOT_ATTESTED_BY_TEXT_ALONE")

    def test_cache_field_required(self):
        with self.assertRaisesRegex(EvidenceRefused,"CACHE_PATH_WITNESS"):
            audit_cache_path(CACHE_JAVAP.replace("rs/f/a.B","rs/f/a.C"))

    def test_home_property_required(self):
        with self.assertRaisesRegex(EvidenceRefused,"CACHE_PATH_WITNESS"):
            audit_cache_path(CACHE_JAVAP.replace("String user.home","String user.dir"))

    def test_file_separator_required(self):
        with self.assertRaisesRegex(EvidenceRefused,"CACHE_PATH_WITNESS"):
            audit_cache_path(CACHE_JAVAP.replace("String file.separator","String path.separator"))

    def test_lowercase_required(self):
        with self.assertRaisesRegex(EvidenceRefused,"CACHE_PATH_WITNESS"):
            audit_cache_path(CACHE_JAVAP.replace("toLowerCase","toUpperCase"))

    def test_string_order_required(self):
        bad=CACHE_JAVAP.replace(
            "String user.home", "String ___").replace(
            "String file.separator","String user.home").replace(
            "String ___","String file.separator")
        with self.assertRaisesRegex(EvidenceRefused,"ORDER"):
            audit_cache_path(bad)

    def test_directory_creation_required(self):
        with self.assertRaisesRegex(EvidenceRefused,"CREATION"):
            audit_cache_path(CACHE_JAVAP.replace("java/io/File.mkdir",
                                                 "java/io/File.exists"))

    def test_return_required(self):
        with self.assertRaisesRegex(EvidenceRefused,"RETURN"):
            audit_cache_path(CACHE_JAVAP.replace("areturn","return"))

    def test_duplicate_cache_method_refused(self):
        bad=CACHE_JAVAP+CACHE_JAVAP
        with self.assertRaisesRegex(EvidenceRefused,"ONE_METHOD_2"):
            audit_cache_path(bad)

    def test_shortened_cache_disassembly_refused(self):
        with self.assertRaises(EvidenceRefused):
            audit_cache_path("public final class rs.v.a {}")

    def test_socket_port_callsite_required(self):
        with self.assertRaisesRegex(EvidenceRefused,"EXPECTED_ONE_LOGIN"):
            audit_socket_callsite(CLIENT_JAVAP.replace("43594","43595"))

    def test_socket_method_signature_required(self):
        with self.assertRaisesRegex(EvidenceRefused,"EXPECTED_ONE_LOGIN"):
            audit_socket_callsite(CLIENT_JAVAP.replace(
                "b:(I)Ljava/net/Socket;","c:(I)Ljava/net/Socket;"))

    def test_duplicate_socket_callsite_refused(self):
        with self.assertRaisesRegex(EvidenceRefused,"_2"):
            audit_socket_callsite(CLIENT_JAVAP+CLIENT_JAVAP)

    def test_nonadjacent_port_does_not_certify_callsite(self):
        lines=CLIENT_JAVAP.splitlines()
        i=next(i for i,l in enumerate(lines) if "int 43594" in l)
        lines[i+1:i+1]=["      178: nop"]*30
        with self.assertRaises(EvidenceRefused):
            audit_socket_callsite("\n".join(lines))

    def test_method_parser_exact_match(self):
        section=method_section(CACHE_JAVAP,r"public static java\.lang\.String b\(\);")
        self.assertIn("String user.home",section)
        self.assertNotIn("public static java.lang.String c();",section)

    def test_utf8_utf16_javap_acceptance(self):
        with tempfile.TemporaryDirectory() as td:
            for encoding in ("utf-8","utf-8-sig","utf-16"):
                with self.subTest(encoding=encoding):
                    p=Path(td)/"temp.javap"
                    p.write_text(CACHE_JAVAP,encoding=encoding)
                    self.assertEqual(decode_javap(p),CACHE_JAVAP)

    def test_invalid_utf_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"invalid.javap"
            p.write_bytes(b"\xff\xaa")
            with self.assertRaises(UnicodeError):
                decode_javap(p)

    def test_real_original_jar_missing_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(EvidenceRefused):
                validate_original_jar(Path(td)/"missing.jar")

    def test_short_original_jar_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"small.jar"
            p.write_bytes(b"fake")
            with self.assertRaisesRegex(EvidenceRefused,"SIZE"):
                validate_original_jar(p)

    def test_real_binary_required_by_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cache=root/"cache.txt"
            client=root/"client.txt"
            cache.write_text(CACHE_JAVAP,encoding="utf-8")
            client.write_text(CLIENT_JAVAP,encoding="utf-8")
            command=[sys.executable,str(Path(__file__).parent/
                     "audit_original_config_bytecode.py"),
                     "--cache-javap",str(cache),
                     "--client-javap",str(client)]
            run=subprocess.run(command,capture_output=True,text=True,timeout=12)
            self.assertEqual(run.returncode,2)
            self.assertIn("REAL_ORIGINAL_JAR_PROVENANCE_REQUIRED",run.stdout)
            self.assertIn("NOT_TESTED",run.stdout)

if __name__=="__main__":
    unittest.main(verbosity=2)

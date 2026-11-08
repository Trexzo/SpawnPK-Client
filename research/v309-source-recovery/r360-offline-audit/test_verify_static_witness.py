"""R350 source-only synthetic javap tests, NOT original game binary CI."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
from verify_static_witness import evaluate, original_jar_admitted, WitnessRefused

ENUM = """public final class rs.f.a$a {
  static {};
    Code:
       0: new           #9   // class rs/f/a$a
       4: ldc           #3   // String SPAWNPK
       7: ldc           #4   // String SpawnPK
      14: putstatic     #10  // Field a:Lrs/f/a$a;
}
"""
SETTINGS = """public final class rs.f.a {
  static {};
    Code:
       0: getstatic     #239 // Field rs/f/a$a.a:Lrs/f/a$a;
       3: putstatic     #158 // Field a:Lrs/f/a$a;
     110: getstatic     #158 // Field a:Lrs/f/a$a;
     113: invokestatic  #287 // Method rs/f/a$a.b:(Lrs/f/a$a;)Ljava/lang/String;
     116: putstatic     #147 // Field B:Ljava/lang/String;
}
"""
DIRS = """public final class rs.v.a {
  public static java.lang.String b();
    Code:
       2: ldc           #46 // String user.home
       8: ldc           #38 // String file.separator
      14: getstatic     #110 // Field rs/f/a.B:Ljava/lang/String;
      17: invokevirtual #172 // Method java/lang/String.toLowerCase:()Ljava/lang/String;
      20: invokedynamic #227, 0 // InvokeDynamic #3:makeConcatWithConstants:(Ljava/lang/String;)Ljava/lang/String;
      68: invokevirtual #153 // Method java/io/File.mkdir:()Z
      77: areturn
  public static java.lang.String f();
    Code:
       2: ldc           #46 // String user.home
       8: ldc           #38 // String file.separator
      14: getstatic     #110 // Field rs/f/a.B:Ljava/lang/String;
      17: invokevirtual #172 // Method java/lang/String.toLowerCase:()Ljava/lang/String;
      20: invokedynamic #229, 0 // InvokeDynamic #5:makeConcatWithConstants:(Ljava/lang/String;)Ljava/lang/String;
      68: invokevirtual #153 // Method java/io/File.mkdir:()Z
      77: areturn
}
"""
VERBOSE = r"""public final class rs.v.a
BootstrapMethods:
    3: #237 REF_invokeStatic java/lang/invoke/StringConcatFactory.makeConcatWithConstants:
      Method arguments:
        #15 .\u0001-data
    5: #237 REF_invokeStatic java/lang/invoke/StringConcatFactory.makeConcatWithConstants:
      Method arguments:
        #14 .\u0001
InnerClasses:
"""
CLIENT = """public final class rs.Client {
  public void a(java.lang.String, java.lang.String, boolean);
    Code:
     178: ldc           #109 // int 43594
     180: invokevirtual #3959 // Method b:(I)Ljava/net/Socket;
     186: putfield      #2799 // Field nF:Lrs/q/b;
  public java.net.Socket b(int);
    Code:
       0: new           #1517 // class java/net/Socket
       4: ldc_w         #1446 // String www.spawnpk.org
       7: invokestatic  #3824 // Method java/net/InetAddress.getByName:(Ljava/lang/String;)Ljava/net/InetAddress;
      10: iload_1
      11: invokespecial #3826 // Method java/net/Socket."<init>":(Ljava/net/InetAddress;I)V
      14: areturn
}
"""

class R350WitnessTests(unittest.TestCase):
    def good(self, **replace):
        fields = dict(enum_javap=ENUM, settings_javap=SETTINGS, dirs_javap=DIRS,
                      dirs_verbose=VERBOSE, client_javap=CLIENT)
        fields.update(replace)
        return evaluate(**fields)

    def test_positive_is_static_only(self):
        result = self.good()
        self.assertEqual(result["status"],"R350_STATIC_ORIGINAL_ENDPOINT_AND_CACHE_RESOLVED")
        self.assertEqual(result["original_login_host_in_socket_method"],"www.spawnpk.org")
        self.assertEqual(result["original_login_port_literal"],43594)
        self.assertEqual(result["data_directory_suffix"],".spawnpk-data")
        self.assertEqual(result["cache_directory_suffix"],".spawnpk")
        self.assertFalse(result["original_socket_method_reads_spk_properties"])
        self.assertFalse(result["owner_local_cache_identity_approved_for_r328"])
        self.assertEqual(result["same_process_reconnect"],"NOT_TESTED")

    def test_host_changed_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(client_javap=CLIENT.replace("www.spawnpk.org","127.0.0.1"))

    def test_port_changed_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(client_javap=CLIENT.replace("43594","43595"))

    def test_duplicate_login_callsite_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(client_javap=CLIENT.replace(
                        "     180: invokevirtual #3959 // Method b:(I)Ljava/net/Socket;",
                        "     180: invokevirtual #3959 // Method b:(I)Ljava/net/Socket;\n"
                        "     181: ldc #109 // int 43594\n"
                        "     182: invokevirtual #3959 // Method b:(I)Ljava/net/Socket;"))

    def test_wrong_game_variant_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(enum_javap=ENUM.replace("SPAWNPK","RUNEX"))

    def test_wrong_brand_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(enum_javap=ENUM.replace("SpawnPK","Runex"))

    def test_wrong_dir_formula_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(dirs_javap=DIRS.replace("String user.home","String user.dir"))

    def test_wrong_data_recipe_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(dirs_verbose=VERBOSE.replace(r".\u0001-data",r".\u0001-config"))

    def test_wrong_cache_recipe_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(dirs_verbose=VERBOSE.replace(r"#14 .\u0001",r"#14 x\u0001"))

    def test_property_flow_in_socket_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(client_javap=CLIENT.replace("      14: areturn",
                "      13: invokestatic // Method java/lang/System.getProperty\n      14: areturn"))

    def test_duplicate_method_fails(self):
        with self.assertRaises(WitnessRefused):
            self.good(dirs_javap=DIRS+DIRS)

    def test_missing_original_jar_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(WitnessRefused):
                original_jar_admitted(Path(tmp)/"missing.jar")

    def test_fake_jar_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"client.jar"
            f.write_bytes(b"not original")
            with self.assertRaises(WitnessRefused):
                original_jar_admitted(f)

    def test_synthetic_result_disclaims_runtime_acceptance(self):
        result = self.good()
        self.assertFalse(result["real_original_jar_execution_by_this_verifier"])
        self.assertFalse(result["arbitrary_javap_text_provenance_attested"])
        self.assertEqual(result["original_client_localhost_connection"], "NOT_TESTED")

if __name__ == "__main__":
    unittest.main()

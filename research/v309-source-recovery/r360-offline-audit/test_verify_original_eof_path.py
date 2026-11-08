"""R338 synthetic javap lifecycle witness regressions."""
import unittest
import tempfile
from pathlib import Path
from verify_original_eof_path import trace_disassembly, WitnessBlocked, read_javap_text

CLIENT = """
  public void a(java.lang.String, java.lang.String, boolean);
    Code:
       45: ldc_w #1069 // String Please wait patiently while we attempt to reconnect
      180: invokevirtual #3959 // Method b:(I)Ljava/net/Socket;
      183: invokespecial #4571 // Method rs/q/b."<init>":(Lrs/C;Ljava/net/Socket;)V
     2273: astore 4
     2302: ldc_w #941 // String Error connecting to server!
    Exception table:
       171  751  2273 Class java/io/IOException

  public void x();
    Code:
       17: ldc_w #893 // String Connection lost
       53: ldc_w #1067 // String Please wait - attempting to reestablish
      109: getfield #2799 // Field nF:Lrs/q/b;
      132: iconst_1
      133: invokevirtual #3914 // Method a:(Ljava/lang/String;Ljava/lang/String;Z)V
      148: invokevirtual #4572 // Method rs/q/b.a:()V

  private void bz();
    Code:
       20: bipush        100
       26: invokespecial #3987 // Method bP:()Z

  private boolean bP();
    Code:
       13: invokevirtual #4576 // Method rs/q/b.c:()I
       17: iload_1
       18: ifne 23
       21: iconst_0
       22: ireturn
       43: invokevirtual #4574 // Method rs/q/b.a:([BI)V
      213: iload_1
      214: aload_0
      215: getfield #2707 // Field lP:I
      218: if_icmpge 223
      221: iconst_0
      222: ireturn
    18231: astore_1
    18233: invokevirtual #4077 // Method x:()V
    Exception table:
       9  22  18231 Class java/io/IOException

  public void a(rs.o.a.a.a);
    Code:
       52: invokevirtual #4573 // Method rs/q/b.a:(I[B)V
       69: astore_2
       71: invokevirtual #4077 // Method x:()V
    Exception table:
       29 66 69 Class java/io/IOException
"""
WORKER = """
  public int c();
    Code:
       13: invokevirtual #43 // Method java/io/InputStream.available:()I

  public void a(byte[], int);
    Code:
       21: invokevirtual #46 // Method java/io/InputStream.read:([BII)I
       31: new #12 // class java/io/IOException
       35: ldc #1 // String EOF

  public void a();
    Code:
       44: invokevirtual #56 // Method java/net/Socket.close:()V
"""
class WitnessTests(unittest.TestCase):
    def test_control(self):
        result=trace_disassembly(CLIENT,WORKER)
        self.assertEqual(result["actual_original_v309_auto_reconnect"],"NOT_TESTED")
        self.assertEqual(result["short_frame_early_return"],"PRESENT_IN_BYTECODE")
        self.assertEqual(result["same_client_object_relogin_call"],"PRESENT_IN_BYTECODE")
    def test_negative_controls(self):
        mutations=[
            ("login false",CLIENT.replace("132: iconst_1","132: iconst_0"),WORKER),
            ("no reconnect UI",CLIENT.replace("attempting to reestablish","idle"),WORKER),
            ("no socket factory",CLIENT.replace('rs/q/b."<init>"','rs/q/c."<init>"'),WORKER),
            ("no inbound IOException",CLIENT.replace("18231 Class java/io/IOException","18231 Class java/lang/Exception"),WORKER),
            ("no inbound recovery",CLIENT.replace("18233: invokevirtual #4077 // Method x:()V","18233: invokevirtual #4077 // Method br:()V"),WORKER),
            ("no available",CLIENT.replace("Method rs/q/b.c:()I","Method rs/q/b.b:()I"),WORKER),
            ("no short frame gate",CLIENT.replace("218: if_icmpge 223","218: if_icmplt 223"),WORKER),
            ("no poll",CLIENT.replace("Method bP:()Z","Method xx:()Z"),WORKER),
            ("no outbound retry",CLIENT.replace("71: invokevirtual #4077 // Method x:()V","71: invokevirtual #4077 // Method br:()V"),WORKER),
            ("no outbound IO catch",CLIENT.replace("69 Class java/io/IOException","69 Class java/lang/Exception"),WORKER),
            ("no worker available",CLIENT,WORKER.replace("InputStream.available:()I","InputStream.read:()I")),
            ("no worker read",CLIENT,WORKER.replace("InputStream.read:([BII)I","InputStream.skip:(J)J")),
            ("no worker EOF",CLIENT,WORKER.replace("String EOF","String no-data")),
            ("no worker close",CLIENT,WORKER.replace("Socket.close:()V","Socket.isClosed:()Z")),
            ("duplicate reconnect method",CLIENT+CLIENT[CLIENT.index("  public void x();"):CLIENT.index("  private void bz();")],WORKER),
        ]
        for name,client,worker in mutations:
            with self.subTest(name=name):
                with self.assertRaises(WitnessBlocked):
                    trace_disassembly(client,worker)

    def test_windows_powershell_5_javap_utf16_decodes(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"v309-client.javap.txt"
            target.write_text(CLIENT,encoding="utf-16")
            self.assertEqual(read_javap_text(target),CLIENT)
            self.assertEqual(
                trace_disassembly(read_javap_text(target),WORKER)["actual_original_v309_auto_reconnect"],
                "NOT_TESTED")

    def test_unmarked_utf16_javap_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"unmarked.txt"
            target.write_bytes(CLIENT.encode("utf-16-le"))
            with self.assertRaisesRegex(WitnessBlocked,"UNMARKED_BINARY"):
                read_javap_text(target)

if __name__=="__main__":
    unittest.main()

"""R391 synthetic-only startup bytecode audit tests.

Compiles tiny mock Java classes into disposable JARs. Does not execute mock
main/start/init and never reads, runs or publishes real v309 client binaries.
"""
from __future__ import annotations
import hashlib
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

TARGET = Path(__file__).resolve().parents[1] / "tools/r391/audit_startup_bytecode.py"
spec = importlib.util.spec_from_file_location("r391_audit", TARGET)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

class TextParserTests(unittest.TestCase):
    def make_text(self, methods):
        lines = ["public class synthetic.Test {"]
        for header, instructions in methods:
            lines.extend(["  " + header, "    descriptor: ()V", "    Code:"])
            for n, instruction in enumerate(instructions):
                lines.append(f"       {n*3}: {instruction}")
        lines.append("}")
        return "\n".join(lines)

    def sample(self):
        orig_launcher = self.make_text([
            ("public static void main(java.lang.String[]);", [
                "invokestatic #1 // Method java/lang/System.setOut:(Ljava/io/PrintStream;)V",
                "invokestatic #2 // Method java/lang/System.setErr:(Ljava/io/PrintStream;)V",
                "invokevirtual #3 // Method java/io/File.delete:()Z",
            ]),
            ("public void b();", [
                "invokevirtual #4 // Method rs/Client.init:()V",
                "invokevirtual #5 // Method rs/Client.start:()V",
            ]),
        ])
        candidate_launcher = self.make_text([
            ("public static void main(java.lang.String[]);", [
                "getstatic #1 // Field rs/Configuration.field1252:Z",
                "ifeq 200",
                "invokevirtual #3 // Method java/io/File.delete:()Z",
            ]),
            ("public void b();", [
                "invokevirtual #4 // Method rs/Client.init:()V",
                "invokevirtual #5 // Method rs/Client.start:()V",
            ]),
        ])
        client = self.make_text([
            ("public void init();", [
                "invokestatic #1 // Method java/net/InetAddress.getLocalHost:()Ljava/net/InetAddress;",
            ]),
            ("public static void main(java.lang.String[]);", ["return"]),
        ])
        return (
            {"rs.gui.Launcher": orig_launcher, "rs.Client": client},
            {"rs.gui.Launcher": candidate_launcher, "rs.Client": client},
        )

    def test_proper_flags_and_no_execution(self):
        a, b = self.sample()
        result = audit.audit_text(a, b)
        self.assertEqual(result["status"], "R391_READ_ONLY_STARTUP_AUDIT")
        self.assertTrue(result["comparison"]["original_log_redirection_present"])
        self.assertFalse(result["comparison"]["reconstructed_log_redirection_present"])
        self.assertTrue(result["comparison"]["reconstructed_adds_log_configuration_guard"])
        self.assertTrue(result["comparison"]["both_client_init_resolve_localhost"])
        self.assertTrue(result["comparison"]["original_launcher_b_init_then_start"])
        self.assertFalse(result["client_code_executed"])
        self.assertFalse(result["behavioral_equivalence_proven"])
        self.assertFalse(result["runtime_launch_approved"])

    def test_reversed_start_order_is_detected(self):
        a, b = self.sample()
        b["rs.gui.Launcher"] = b["rs.gui.Launcher"].replace(
            "invokevirtual #4 // Method rs/Client.init:()V\n       3: invokevirtual #5 // Method rs/Client.start:()V",
            "invokevirtual #5 // Method rs/Client.start:()V\n       3: invokevirtual #4 // Method rs/Client.init:()V")
        self.assertFalse(audit.audit_text(a, b)["comparison"]["candidate_launcher_b_init_then_start"])

    def test_missing_class_refused(self):
        a, b = self.sample()
        del b["rs.Client"]
        with self.assertRaisesRegex(audit.Refused, "MISSING_DISASSEMBLY"):
            audit.audit_text(a, b)

    def test_missing_method_refused(self):
        a, b = self.sample()
        b["rs.Client"] = b["rs.Client"].replace("public void init()", "public void absent()")
        with self.assertRaisesRegex(audit.Refused, "MISSING_OR_AMBIGUOUS_METHOD"):
            audit.audit_text(a, b)

    def test_ambiguous_method_refused(self):
        a, b = self.sample()
        b["rs.Client"] += "\n  public void init();\n    descriptor: ()V\n    Code:\n       0: return\n"
        with self.assertRaisesRegex(audit.Refused, "MISSING_OR_AMBIGUOUS_METHOD"):
            audit.audit_text(a, b)

    def test_method_without_code_refused(self):
        a, b = self.sample()
        b["rs.Client"] = b["rs.Client"].replace("public void init();\n    descriptor: ()V\n    Code:",
                                                       "public void init();\n    descriptor: ()V\n    NoCode:")
        with self.assertRaisesRegex(audit.Refused, "METHOD_WITHOUT_CODE"):
            audit.audit_text(a, b)

    def test_branch_and_call_counts_are_distinct(self):
        a, b = self.sample()
        result = audit.audit_text(a, b)
        self.assertEqual(result["methods"]["Launcher.main(java.lang.String[])"]["original"]["invocations"], 3)
        self.assertEqual(result["methods"]["Launcher.main(java.lang.String[])"]["candidate"]["conditional_branches"], 1)

    def test_cannot_disassemble_other_classes(self):
        with self.assertRaisesRegex(audit.Refused, "INVALID_JAVAP_EXECUTABLE"):
            audit.disassemble(Path("/not-javap"), Path("/some.jar"), "java.lang.System")

    def test_nonhex_pin_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "a.jar"
            p.write_bytes(b"data")
            with self.assertRaisesRegex(audit.Refused, "INVALID_SHA256_PIN"):
                audit.pin_archive(p, "invalid")

    def test_mismatched_archive_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "a.jar"
            p.write_bytes(b"data")
            with self.assertRaisesRegex(audit.Refused, "ARCHIVE_SHA256_DRIFT"):
                audit.pin_archive(p, "0"*64)

class SyntheticJavapIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        javac, javap = shutil.which("javac"), shutil.which("javap")
        if not javac or not javap:
            raise unittest.SkipTest("JDK21 required")
        cls.javac = str(Path(javac).resolve())
        cls.javap = Path(javap).resolve()
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.archives = {}
        for variant in ("original", "candidate"):
            source = cls.root / variant / "src"
            classes = cls.root / variant / "classes"
            a = source / "rs/gui/Launcher.java"
            b = source / "rs/Client.java"
            c = source / "rs/Configuration.java"
            for f in (a, b, c):
                f.parent.mkdir(parents=True, exist_ok=True)
            base = ('System.setOut(System.out); System.setErr(System.err);'
                    if variant == "original" else 'if(rs.Configuration.field1252){System.getProperty("fixture");}')
            a.write_text('package rs.gui; public class Launcher {'
                         ' public static void main(String[] args){' + base + '}'
                         ' public void b(){ rs.Client client=new rs.Client(); client.init(); client.start(); }'
                         '}', encoding="utf-8")
            b.write_text('package rs; public class Client {'
                         ' public void init(){try{java.net.InetAddress.getLocalHost();}catch(Exception ignored){}}'
                         ' public void start(){}'
                         ' public static void main(String[] args){}'
                         '}', encoding="utf-8")
            c.write_text('package rs; public class Configuration { public static boolean field1252=true; }',
                         encoding="utf-8")
            cmd = [cls.javac, "--release", "11", "-d", str(classes), str(a), str(b), str(c)]
            subprocess.run(cmd, check=True, timeout=30, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            archive = cls.root / (variant + ".jar")
            with ZipFile(archive, "w") as z:
                for item in sorted(classes.rglob("*.class")):
                    z.write(item, item.relative_to(classes).as_posix())
            cls.archives[variant] = archive

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "temp"):
            cls.temp.cleanup()

    def test_real_javap_on_synthetic_jar_only(self):
        before = {k: audit.disassemble(self.javap, self.archives["original"], k)
                  for k in audit.TARGETS}
        after = {k: audit.disassemble(self.javap, self.archives["candidate"], k)
                 for k in audit.TARGETS}
        result = audit.audit_text(before, after)
        self.assertEqual(result["status"], "R391_READ_ONLY_STARTUP_AUDIT")
        self.assertTrue(result["comparison"]["original_log_redirection_present"])
        self.assertFalse(result["comparison"]["reconstructed_log_redirection_present"])
        self.assertTrue(result["comparison"]["original_launcher_b_init_then_start"])
        self.assertTrue(result["comparison"]["candidate_launcher_b_init_then_start"])
        self.assertTrue(result["comparison"]["both_client_init_resolve_localhost"])

    def test_cli_hash_refusal_prevents_disassembly(self):
        args = ["--original", str(self.archives["original"]),
                "--candidate", str(self.archives["candidate"]),
                "--original-sha256", "0"*64,
                "--candidate-sha256", digest(self.archives["candidate"]),
                "--javap", str(self.javap)]
        self.assertEqual(audit.main(args), 2)

    def test_cli_refuses_preexisting_output(self):
        old, new = self.archives["original"], self.archives["candidate"]
        existing = self.root/"existing.json"
        existing.write_text("KEEP", encoding="utf-8")
        args = ["--original", str(old), "--candidate", str(new),
                "--original-sha256", digest(old),
                "--candidate-sha256", digest(new), "--javap", str(self.javap),
                "--out", str(existing)]
        self.assertEqual(audit.main(args), 2)
        self.assertEqual(existing.read_text("utf-8"), "KEEP")

    def test_cli_writes_bounded_report_without_client_execution(self):
        old, new = self.archives["original"], self.archives["candidate"]
        fresh = self.root/"fresh-report.json"
        args = ["--original", str(old), "--candidate", str(new),
                "--original-sha256", digest(old),
                "--candidate-sha256", digest(new), "--javap", str(self.javap),
                "--out", str(fresh)]
        self.assertEqual(audit.main(args), 0)
        self.assertTrue(fresh.exists())
        self.assertNotIn("SYNTHETIC_LAUNCHER_INITIALIZED", fresh.read_text("utf-8"))
        self.assertNotIn(str(self.root), fresh.read_text("utf-8"))

if __name__ == "__main__":
    unittest.main()

"""R145 synthetic original-game-linked source restoration; *no* binary fallback."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_v309_game_linked_source_bridge_r145 import (
    PrivateClientSourceBridgeR145Error,
    compare_private_linked_owner_source,
)


@unittest.skipUnless(shutil.which("java") and shutil.which("javac"),
                     "JDK needed for original game-class + recovered source test")
class R145OriginalLinkedClassSourceBridge(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        original = self.root / "original"
        original.mkdir()
        def compile_java(internal, body, label, classpath=None):
            src = self.root / label / (internal + ".java")
            src.parent.mkdir(parents=True)
            src.write_text(body, encoding="utf-8")
            command = [shutil.which("javac"), "--release", "9", "-proc:none",
                       "-g:none", "-d", str(original)]
            if classpath is not None:
                command.extend(["-classpath", str(classpath)])
            cmd = subprocess.run(command + [str(src)], capture_output=True)
            self.assertEqual(0, cmd.returncode,
                             cmd.stderr.decode("utf-8", errors="replace"))
        compile_java("rs/Game",
                     "package rs; public class Game { "
                     "public int value() { return 6; }}", "game")
        compile_java("ext/Bridge",
                     "package ext; public class Bridge { "
                     "public static int get(rs.Game g) { return g.value() * 2; }}",
                     "original-bridge", original)
        compile_java("ext/Clean",
                     "package ext; public class Clean { "
                     "public static int ok() { return 1; }}", "clean")
        self.jar = self.root / "original-synthetic.jar"
        with ZipFile(self.jar, "w") as archive:
            for file in sorted(original.rglob("*.class")):
                archive.write(file, file.relative_to(original).as_posix())
        self.source = self.zip_java("client.zip", {
            "rs/Game.java":
                "package rs; public class Game { public int value() { return 6; }}",
            "rs/App.java":
                "package rs; import ext.Bridge; public class App { "
                "public int doubleValue() { return Bridge.get(new Game()); }}",
        })
        self.donor = self.zip_java("private-donor.zip", {
            "ext/Bridge.java":
                "package ext; public class Bridge { "
                "public static int get(rs.Game g) { return g.value() * 2; }}",
        })

    def zip_java(self, name, sources):
        result = self.root / name
        with ZipFile(result, "w") as archive:
            for path, source in sorted(sources.items()):
                archive.writestr("src/main/java/" + path, source)
        return result

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def replay(self, donor):
        return compare_private_linked_owner_source(
            self.source, self.jar, donor,
            source_sha256=self.sha(self.source),
            original_sha256=self.sha(self.jar),
            donor_sha256=self.sha(donor))

    def test_game_bound_binary_excluded_and_reconstructed_java_compiles(self):
        report = self.replay(self.donor)
        self.assertEqual(2, report["original_client_source_java_count"])
        self.assertEqual(1, report["private_source_bridge_added_java_count"])
        self.assertEqual(3, report["combined_private_java_file_count"])
        self.assertEqual(1, report["original_rs_classfiles_excluded"])
        self.assertEqual(1, report["original_rs_linked_nonrs_classfiles_excluded"])
        self.assertEqual(1, report["provisional_nonrs_binary_count"])
        self.assertGreater(report["original_source_observed_errors"], 0)
        self.assertEqual(0, report["donor_source_observed_errors"])
        self.assertEqual("improved", report["observed_error_delta_classification"])
        self.assertFalse(report["original_game_binary_fallback_accepted"])
        self.assertFalse(report["source_to_original_class_abi_verified"])
        self.assertFalse(report["original_method_bytecode_equivalence_verified"])
        self.assertFalse(report["whole_client_source_compilation_accepted"])

    def test_unlinked_external_donor_rejected(self):
        other = self.zip_java("unlinked-donor.zip", {
            "ext/Clean.java": "package ext; public class Clean {}",
        })
        with self.assertRaises(PrivateClientSourceBridgeR145Error):
            self.replay(other)

    def test_wrong_declared_java_type_rejected(self):
        other = self.zip_java("bad-declaration.zip", {
            "ext/Bridge.java": "package ext; public class NotBridge {}",
        })
        with self.assertRaises(PrivateClientSourceBridgeR145Error):
            self.replay(other)

    def test_multiple_donors_and_sham_hash_rejected(self):
        two = self.zip_java("multi-donor.zip", {
            "ext/Bridge.java": "package ext; public class Bridge {}",
            "ext/Other.java": "package ext; public class Other {}",
        })
        with self.assertRaises(PrivateClientSourceBridgeR145Error):
            self.replay(two)
        with self.assertRaises(PrivateClientSourceBridgeR145Error):
            compare_private_linked_owner_source(
                self.source, self.jar, self.donor,
                source_sha256="0" * 64,
                original_sha256=self.sha(self.jar),
                donor_sha256=self.sha(self.donor))


if __name__ == "__main__":
    unittest.main()

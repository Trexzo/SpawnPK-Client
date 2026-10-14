"""R163 source overlay must preserve original Java and exclude helper stubs."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from test_private_v309_complete_matrix_java_r162 import R162AllMatrixMethodSourceTest
from spk_recovery.private_v309_source_tree_matrix_overlay_r163 import (
    PrivateSourceOverlayR163Error, make_private_matrix_source_overlay)


class R163SourceTreeTest(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        f=R162AllMatrixMethodSourceTest(
            "test_full_source_class_fields_methods_and_closure")
        f.setUp()
        self.addCleanup(f.doCleanups)
        self.f=f
        self.client=self.basezip("baseline.zip",{
            "rs/Client.java":"package rs;public class Client{}",
            "rs/Settings.java":"package rs;public class Settings{}"})

    @staticmethod
    def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def basezip(self,name,sources):
        out=self.root/name
        with ZipFile(out,"w") as z:
            for name,code in sources.items():
                z.writestr("src/main/java/"+name,code)
        return out

    def replay(self,base=None,hash_value=None,count=2):
        base=base or self.client
        return make_private_matrix_source_overlay(
            self.f.original,base,self.f.candidate,
            self.f.helpers,self.f.selection,self.root/"fresh.zip",
            original_sha256=self.sha(self.f.original),
            decompiled_source_sha256=hash_value or self.sha(base),
            recovered_matrix_sha256=self.sha(self.f.candidate),
            helper_source_sha256=self.sha(self.f.helpers),
            methods_sha256=self.sha(self.f.selection),
            matrix_owner=self.f.OWNER,packet_owner=self.f.PACKET,
            matrix_class_sha256=self.f.original_owner_sha,
            expected_original_java=count,expected_methods=6,
            expected_instructions=self.f.original_instruction_count,
            expected_helpers=2,expected_self_calls=3)

    def test_original_java_preserved_and_one_verified_owner_added(self):
        result=self.replay()
        self.assertEqual(3,result["private_canonical_client_java_file_count"])
        self.assertTrue(result["one_proven_original_matrix_java_file_added"])
        self.assertFalse(result["compiler_only_scaffolds_in_canonical_source_tree"])
        self.assertFalse(result["whole_v309_client_javac_compilation_accepted"])
        with ZipFile(self.root/"fresh.zip") as z:
            self.assertEqual(3,len(z.namelist()))
            self.assertIn("recovered-source/v309/src/ext/Matrix.java",z.namelist())
            self.assertNotIn("recovered-source/v309/src/rs/Packet.java",z.namelist())

    def test_exact_owner_collision_and_helper_collision_refused(self):
        for name in ["ext/Matrix.java","rs/Packet.java"]:
            with self.subTest(name=name):
                base=self.basezip(name.replace("/","-")+".zip",{
                    name:"public class Placeholder {}",
                    "rs/Client.java":"package rs;public class Client{}"})
                with self.assertRaises(PrivateSourceOverlayR163Error):
                    self.replay(base)

    def test_wrong_original_source_digest_refused(self):
        with self.assertRaises(PrivateSourceOverlayR163Error):
            self.replay(hash_value="0"*64)


if __name__=="__main__":
    unittest.main()

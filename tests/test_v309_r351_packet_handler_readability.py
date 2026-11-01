"""R351 synthetic class-rename proof: no source archive or original JAR in CI."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.apply_v309_r351_readable_packet_handler_candidate import (
    RenameRefused, OLD_PATH, NEW_PATH, NEW, transform, apply, load_verified_stage
)

OWNER = b"""package rs.scriptpacket;
import com.google.inject.Module;
public abstract class Class260 implements Module {
  public abstract void handlePacket();
  public void setPacket(Packet p) {}
  public void setClient(Client c) {}
}
"""
CONSUMER = b"""package rs.other;
import rs.scriptpacket.Class260;
public class PacketConsumer extends Class260 {
  public void handlePacket() {}
}
"""

class ReadableRenameTests(unittest.TestCase):
    def example(self):
        return {OLD_PATH: OWNER, "rs/other/PacketConsumer.java": CONSUMER}

    def rename(self, sources):
        return transform(sources, expected_files=len(sources),
                         expected_touches=2, expected_occurrences=3)

    def test_inferred_class_rename_updates_owner_import_and_extends(self):
        out, record = self.rename(self.example())
        self.assertIn(NEW_PATH,out)
        self.assertNotIn(OLD_PATH,out)
        self.assertIn(b"abstract class AbstractScriptPacketHandler",
                      out[NEW_PATH])
        self.assertIn(b"import rs.scriptpacket.AbstractScriptPacketHandler;",
                      out["rs/other/PacketConsumer.java"])
        self.assertIn(b"extends AbstractScriptPacketHandler",
                      out["rs/other/PacketConsumer.java"])
        self.assertEqual(record["modified_java_files"],2)
        self.assertEqual(record["changed_lexical_occurrences"],3)
        self.assertTrue(record["candidate_name_not_original_identity"])
        self.assertEqual(record["original_v309_class_parity"],"NOT_TESTED")

    def test_other_java_bytes_remain_unchanged(self):
        sources=self.example()
        sources["rs/other/Untouched.java"]=b"package rs.other; class Untouched {}"
        out,_=self.rename(sources)
        self.assertEqual(out["rs/other/Untouched.java"],
                         sources["rs/other/Untouched.java"])

    def test_shape_change_fail_closed(self):
        sources=self.example()
        sources[OLD_PATH]=OWNER.replace(b"abstract class",b"final class")
        with self.assertRaisesRegex(RenameRefused,"SHAPE"):
            self.rename(sources)

    def test_unaccounted_cross_package_reference_rejected(self):
        sources=self.example()
        sources["rs/other/Stranger.java"]=b"class Stranger { Class260 value; }"
        with self.assertRaisesRegex(RenameRefused,"UNACCOUNTED"):
            transform(sources,expected_files=3,
                      expected_touches=3,expected_occurrences=4)

    def test_unexpected_reference_count_rejected(self):
        with self.assertRaisesRegex(RenameRefused,"WITNESS_CHANGED"):
            transform(self.example(),expected_files=2,
                      expected_touches=2,expected_occurrences=4)

    def test_missing_original_owner_fails(self):
        sources={"rs/scriptpacket/Other.java":b"class Other {}"}
        with self.assertRaisesRegex(RenameRefused,"MISSING_OR_DUPLICATE"):
            transform(sources,expected_files=1,
                      expected_touches=0,expected_occurrences=0)

    def test_existing_target_rejected(self):
        sources=self.example()
        sources[NEW_PATH]=b"class AbstractScriptPacketHandler {}"
        with self.assertRaisesRegex(RenameRefused,"MISSING_OR_DUPLICATE"):
            transform(sources,expected_files=3,
                      expected_touches=2,expected_occurrences=3)

    def test_no_stage_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RenameRefused,"MANIFEST_MISSING"):
                load_verified_stage(Path(tmp))

    def test_reused_output_rejected_before_reading_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"existing"
            target.mkdir()
            (target/"do-not-delete.txt").write_text("preserve")
            with self.assertRaisesRegex(RenameRefused,"OUTPUT_MUST_BE_NEW"):
                apply(Path(tmp)/"missing",target)
            self.assertEqual((target/"do-not-delete.txt").read_text(),"preserve")

    def test_fixed_corpus_witness_counts_enforced(self):
        from scripts.apply_v309_r351_readable_packet_handler_candidate import (
            EXPECTED_FILES, EXPECTED_TOUCHES, EXPECTED_OCCURRENCES
        )
        self.assertEqual((EXPECTED_FILES,EXPECTED_TOUCHES,EXPECTED_OCCURRENCES),
                         (1275,71,144))

if __name__ == "__main__":
    unittest.main(verbosity=2)

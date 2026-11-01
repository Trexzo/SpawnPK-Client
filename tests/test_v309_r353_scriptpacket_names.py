"""R353 bounded readable packet-handler renames — synthetic-only public CI."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_v309_r353_scriptpacket_names import (
    CandidateRefused, RENAMES, REGISTRY, DEBUG, EXPECTED_COUNT,
    rewrite, read_r352_stage, stage_candidate, EXPECTED_BASE_SHA
)

class R353Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        reg=[
            "package rs.scriptpacket;",
            *[f"import rs.scriptpacket.handler.{old};" for old,_,_,_,_,_ in RENAMES],
            "class ScriptPacketRegistry {",
            *[f"  void x{opcode}() {{ registerPacketHandler({opcode}, {old}.class); }}"
              for old,_,opcode,_,_,_ in RENAMES],
            "  void registerPacketHandler(int code,Class<?> klass) {}",
            "}",
        ]
        self.sources={
            REGISTRY:("\n".join(reg)+"\n").encode(),
            DEBUG:( 'class UiPacketDecoder { /* Class263 */ }' ).encode(),
        }
        for old,new,opcode,req,_,_ in RENAMES:
            lines=[
                "package rs.scriptpacket.handler;",
                f"public class {old} extends AbstractScriptPacketHandler {{",
                "  public void handlePacket() {}",
                "  public void setPacket(Packet p) {}",
                *[f"  // {r}" for r in req],
                "}",
            ]
            self.sources[f"rs/scriptpacket/handler/{old}.java"]=(
                "\n".join(lines)+"\n").encode()

    def rewrite(self,sources=None):
        # Fixture has only 5 source files, real full run demands 1,277.
        return rewrite(self.sources if sources is None else sources,
                       expected_count=5,expected_stats=False)

    def test_source_grounded_renames_are_exactly_reversible(self):
        result,witness=self.rewrite()
        self.assertEqual(len(result),5)
        self.assertEqual(len(witness),3)
        for old,new,opcode,_,_,_ in RENAMES:
            self.assertNotIn(f"rs/scriptpacket/handler/{old}.java",result)
            self.assertIn(f"rs/scriptpacket/handler/{new}.java",result)
            self.assertIn(f"registerPacketHandler({opcode}, {new}.class);",
                          result[REGISTRY].decode())
        self.assertTrue(all(w["name_authority"]=="INFERRED_CANDIDATE_ONLY"
                            for w in witness))

    def test_wrong_opcode_is_rejected(self):
        sources=dict(self.sources)
        sources[REGISTRY]=sources[REGISTRY].replace(
            b"registerPacketHandler(14, Class263.class);",
            b"registerPacketHandler(15, Class263.class);")
        with self.assertRaisesRegex(CandidateRefused,"OPCODE_OR_HANDLER"):
            self.rewrite(sources)

    def test_unverified_source_shape_refused(self):
        sources=dict(self.sources)
        p="rs/scriptpacket/handler/Class262.java"
        sources[p]=sources[p].replace(b"this.client.npcs",b"this.client.players")
        with self.assertRaisesRegex(CandidateRefused,"SOURCE_SHAPE"):
            self.rewrite(sources)

    def test_unexpected_cross_package_reference_refused(self):
        sources=dict(self.sources)
        sources["rs/fake/Stranger.java"]=b"class Stranger { Class262 field; }"
        with self.assertRaisesRegex(CandidateRefused,"UNEXPECTED_CLASS_REFERENCE"):
            rewrite(sources,expected_count=6,expected_stats=False)

    def test_numeric_identifier_counts_pinned_for_real_corpus(self):
        self.assertEqual(EXPECTED_COUNT,1277)
        self.assertEqual([(r[0],r[4],r[5]) for r in RENAMES],
                         [("Class261",2,3),("Class262",2,3),
                          ("Class263",3,5)])

    def test_rejected_fake_full_stage(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(CandidateRefused,"INPUT_MISSING"):
                read_r352_stage(Path(td))

    def test_existing_output_preserved(self):
        out=self.root/"not-new"
        out.mkdir()
        saved=out/"must-preserve"
        saved.write_text("original")
        with self.assertRaisesRegex(CandidateRefused,"OUTPUT_MUST_NOT"):
            stage_candidate(self.root/"missing",out)
        self.assertEqual(saved.read_text(),"original")

    def test_bad_source_sha_refused(self):
        stage=self.root/"stage"
        stage.mkdir()
        manifest={
            "base_archive_sha256":EXPECTED_BASE_SHA,
            "source_count":1277,
            "mode":"readable",
            "source_milestone_publishable":False,
            "source_file_sha256":{f"rs/Source{i}.java":"0"*64
                                  for i in range(1277)}
        }
        (stage/"PRIVATE_R315_SOURCE_CANDIDATE.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(CandidateRefused,"SOURCE_NOT_REGULAR"):
            read_r352_stage(stage)

    def test_input_hard_requires_readable_r352(self):
        stage=self.root/"stage"
        stage.mkdir()
        manifest={
            "base_archive_sha256":EXPECTED_BASE_SHA,
            "source_count":1277,
            "mode":"baseline",
            "source_milestone_publishable":False,
            "source_file_sha256":{f"rs/Source{i}.java":"0"*64
                                  for i in range(1277)}
        }
        (stage/"PRIVATE_R315_SOURCE_CANDIDATE.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(CandidateRefused,"PROVENANCE_NOT_PINNED"):
            read_r352_stage(stage)

    def test_no_conflicting_destination(self):
        sources=dict(self.sources)
        sources["rs/scriptpacket/handler/GrandExchangeScriptPacketHandler.java"]=b""
        with self.assertRaisesRegex(CandidateRefused,"ALREADY_RENAMED"):
            rewrite(sources,expected_count=6,expected_stats=False)

if __name__=="__main__":
    unittest.main(verbosity=2)

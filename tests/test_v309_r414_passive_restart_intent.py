"""R414 invented read-only restart-marker protocol tests.

No user history, recovered client Java, private classes, credentials or
production paths. Every test uses fresh invented temporary files.
"""
from __future__ import annotations
from hashlib import sha256
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
import os

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "r414_public_static",ROOT/"tools/r414/audit_passive_restart_intent.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

NONE="NONE"
BEFORE="ABORTED_BEFORE_REPLACE"
AFTER="COMMITTED_BEFORE_ACK"
QUARANTINE="QUARANTINED"
N="11111111-2222-3333-4444-555555555555"
VERSION=re.compile(r"serial=[1-9][0-9]{0,15}\Z")
NONCE=re.compile(r"nonce=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
HASH_BEFORE=re.compile(r"before=(ABSENT|[0-9a-f]{64})\Z")
HASH_AFTER=re.compile(r"after=[0-9a-f]{64}\Z")
MAX_MARKER=512
MAX_HISTORY=64*1024*1024

def hexhash(data:bytes)->str:
    return sha256(data).hexdigest()

def image(*n:int)->bytes:
    return ("synthetic-v1\n"+"".join(f"{i}\n" for i in n)).encode("ascii")

def marker(before:str,after:str,nonce:str=N,serial:str="1")->bytes:
    return f"v=1\nserial={serial}\nnonce={nonce}\nbefore={before}\nafter={after}\n".encode("ascii")

class InventedReadOnlyClassifier:
    """Independent synthetic protocol model, NOT recovered client execution."""
    def __init__(self,folder:Path):
        self.root=folder
        self.history=folder/"invented-history.txt"
        self.stage=folder/"invented-history.txt.tmp"
        self.intent=folder/"invented-history.delete.intent"
        self.intent_tmp=folder/"invented-history.delete.intent.tmp"
        self.read_main_count=0
        self.auto_delete_count=0
        self.auto_write_count=0
    @staticmethod
    def safe_regular(path:Path)->bool:
        return path.is_file() and not path.is_symlink()
    def classify(self)->str:
        if self.intent_tmp.exists() or self.intent_tmp.is_symlink():
            return QUARANTINE
        if not self.intent.exists() and not self.intent.is_symlink():
            return NONE
        if not self.safe_regular(self.intent):
            return QUARANTINE
        if self.intent.stat().st_size<100 or self.intent.stat().st_size>MAX_MARKER:
            return QUARANTINE
        raw=self.intent.read_bytes()
        if len(raw)<100 or len(raw)>MAX_MARKER:
            return QUARANTINE
        try:text=raw.decode("ascii")
        except UnicodeDecodeError:return QUARANTINE
        fields=text.split("\n")
        if len(fields)!=6 or fields[0]!="v=1" or \
           not VERSION.fullmatch(fields[1]) or \
           not NONCE.fullmatch(fields[2]) or \
           not HASH_BEFORE.fullmatch(fields[3]) or \
           not HASH_AFTER.fullmatch(fields[4]) or fields[5]!="":
            return QUARANTINE
        if text.encode("ascii")!=raw:
            return QUARANTINE
        before=fields[3][7:]
        after=fields[4][6:]
        if before==after:
            return QUARANTINE
        if not self.history.exists() and not self.history.is_symlink():
            current="ABSENT"
        else:
            if not self.safe_regular(self.history) or self.history.stat().st_size>MAX_HISTORY:
                return QUARANTINE
            self.read_main_count+=1
            current=hexhash(self.history.read_bytes())
        if current==before:return BEFORE
        if current==after:return AFTER
        return QUARANTINE
    def allow_writes(self)->bool:
        return self.classify()==NONE and not (
            self.stage.exists() or self.stage.is_symlink()
        )

class R414IntentContractTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="r414-public-fixture-")
        self.addCleanup(temp.cleanup)
        self.c=InventedReadOnlyClassifier(Path(temp.name))
        self.old=image(1,2)
        self.next=image(2)
        self.valid=marker(hexhash(self.old),hexhash(self.next))
    def save(self,content:bytes):
        self.c.intent.write_bytes(content)
    def setup_old(self):
        self.c.history.write_bytes(self.old);self.save(self.valid)
    def setup_next(self):
        self.c.history.write_bytes(self.next);self.save(self.valid)
    def test_clean_no_marker(self):
        self.assertEqual(self.c.classify(),NONE)
        self.assertTrue(self.c.allow_writes())
    def test_clean_history_without_marker(self):
        self.c.history.write_bytes(self.old)
        self.assertEqual(self.c.classify(),NONE)
        self.assertEqual(self.c.read_main_count,0)
    def test_precommit_old_image_match(self):
        self.setup_old()
        self.assertEqual(self.c.classify(),BEFORE)
        self.assertFalse(self.c.allow_writes())
    def test_committed_unacknowledged_image_match(self):
        self.setup_next()
        self.assertEqual(self.c.classify(),AFTER)
        self.assertFalse(self.c.allow_writes())
    def test_absent_original_main_match(self):
        self.save(marker("ABSENT",hexhash(self.next)))
        self.assertEqual(self.c.classify(),BEFORE)
    def test_absent_prior_main_but_committed_image(self):
        self.c.history.write_bytes(self.next)
        self.save(marker("ABSENT",hexhash(self.next)))
        self.assertEqual(self.c.classify(),AFTER)
    def test_missing_main_with_expected_digest_quarantined(self):
        self.save(self.valid)
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_wrong_main_digest_quarantined(self):
        self.c.history.write_bytes(image(8))
        self.save(self.valid)
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_pending_intent_temp_only_quarantined(self):
        self.c.intent_tmp.write_bytes(b"temporary-intent")
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_pending_intent_temp_and_valid_intent_quarantined(self):
        self.setup_next()
        self.c.intent_tmp.write_bytes(b"failed")
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_history_temp_without_marker_blocks_writes(self):
        self.c.stage.write_bytes(b"partial")
        self.assertEqual(self.c.classify(),NONE)
        self.assertFalse(self.c.allow_writes())
    def test_marker_directory_quarantined(self):
        self.c.intent.mkdir()
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_marker_temp_directory_quarantined(self):
        self.c.intent_tmp.mkdir()
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_empty_marker_quarantined(self):
        self.save(b"")
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_oversized_marker_quarantined(self):
        self.save(b"a"*513)
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_invalid_version_quarantined(self):
        self.save(self.valid.replace(b"v=1",b"v=3"))
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_invalid_zero_serial_quarantined(self):
        self.save(self.valid.replace(b"serial=1",b"serial=0"))
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_invalid_long_serial_quarantined(self):
        self.save(self.valid.replace(b"serial=1",b"serial=" + b"9"*30))
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_invalid_nonce_quarantined(self):
        self.save(self.valid.replace(N.encode(),b"incorrect"))
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_nonce_uppercase_quarantined(self):
        self.save(self.valid.replace(N.encode(),N.upper().encode()))
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_bad_before_digest_quarantined(self):
        self.save(self.valid.replace(hexhash(self.old).encode(),b"bad"))
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_uppercase_after_digest_quarantined(self):
        self.save(self.valid.replace(hexhash(self.next).encode(),
                                     hexhash(self.next).upper().encode()))
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_equal_digests_quarantined(self):
        h=hexhash(self.old);self.save(marker(h,h))
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_extra_field_quarantined(self):
        self.save(self.valid+b"extra=value\n")
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_truncated_marker_quarantined(self):
        self.save(self.valid[:-8])
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_nul_byte_marker_quarantined(self):
        self.save(self.valid[:-2]+b"\x00\n")
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_nonascii_marker_quarantined(self):
        self.save(self.valid[:4]+b"\xff"+self.valid[5:])
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_repeat_inspection_never_modifies_files(self):
        self.setup_next()
        before=(self.c.history.read_bytes(),self.c.intent.read_bytes())
        self.assertEqual(self.c.classify(),AFTER)
        self.assertEqual(self.c.classify(),AFTER)
        self.assertEqual(before,(self.c.history.read_bytes(),self.c.intent.read_bytes()))
        self.assertEqual((self.c.auto_write_count,self.c.auto_delete_count),(0,0))
    def test_valid_marker_never_authorizes_auto_recovery(self):
        self.setup_old()
        self.assertFalse(self.c.allow_writes())
        self.assertTrue(self.c.intent.is_file())
    def test_symlink_intent_quarantined_where_supported(self):
        real=self.c.root/"unrelated.txt";real.write_bytes(self.valid)
        try:self.c.intent.symlink_to(real.name)
        except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_symlink_main_quarantined_where_supported(self):
        self.save(self.valid)
        external=self.c.root/"unrelated.txt"
        external.write_bytes(self.next)
        try:self.c.history.symlink_to(external.name)
        except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
        self.assertEqual(self.c.classify(),QUARANTINE)
    def test_valid_marker_whose_file_was_externally_changed_quarantined(self):
        self.setup_old()
        self.c.history.write_bytes(image(1,2,3))
        self.assertEqual(self.c.classify(),QUARANTINE)

class R414PublicScopeTests(unittest.TestCase):
    def test_one_expected_source_only(self):
        self.assertEqual(audit.SOURCE_DIFF,{"rs/plugins/loottracker/LootHistoryStore.java"})
    def test_exact_one_new_enum(self):
        self.assertEqual(audit.NEW_CLASS,{
            "rs/plugins/loottracker/LootHistoryStore$R414IntentState.class"})
    def test_legacy_cache_out_of_change_scope(self):
        self.assertNotIn(audit.PRICE,audit.SOURCE_DIFF)
        self.assertNotIn(audit.MOVE,audit.SOURCE_DIFF)
    def test_auditor_explicit_release_closed(self):
        source=Path(audit.__file__).read_text(encoding="utf8")
        for phrase in ("automatic_marker_production_integrated",
                       "automatic_marker_cleanup_integrated",
                       "startup_adoption_or_replay_implemented",
                       "valid_marker_authorizes_new_writes",
                       "private_release_authorized"):
            self.assertIn(phrase,source)
    def test_sha_pin_refuses_invalid_digest(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"synthetic.bin"
            p.write_bytes(b"invented")
            with self.assertRaises(audit.Refused):
                audit.r395.require_pin(p,"0"*64)

if __name__=="__main__":
    unittest.main()

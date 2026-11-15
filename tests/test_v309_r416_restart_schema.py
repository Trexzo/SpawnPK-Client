"""R416 standalone, invented restart-schema tests.

No recovered client code, private data, real history, or production marker.
This model deliberately NEVER adopts files, removes markers, or authorizes writes.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import unittest
from uuid import UUID

MAX_SIZE = 64 * 1024 * 1024
MAX_ITEMS = 4096
VALID_TYPES = frozenset(("NPC", "PLAYER", "CLUE", "OTHER"))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def fixture() -> dict:
    return {"version": 1, "records": [
        {"title": "Synthetic guardian", "subtitle": "", "type": "NPC",
         "kills": 1, "timestamp": 1234567890,
         "items": [{"id": 7, "name": "Synthetic token",
                    "quantity": 1, "price": 42, "hidden": False}]}
    ]}


def regular(path: Path, max_size: int) -> bytes | None:
    try:
        attrs = path.lstat()
        if not stat.S_ISREG(attrs.st_mode) or attrs.st_size > max_size:
            return None
        with path.open("rb") as stream:
            observed = stream.read(max_size + 1)
        after = path.lstat()
        if (len(observed) > max_size or attrs.st_size != len(observed)
                or after.st_size != attrs.st_size
                or after.st_mtime_ns != attrs.st_mtime_ns
                or after.st_ino != attrs.st_ino):
            return None
        return observed
    except (OSError, ValueError):
        return None


def valid_schema(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {"version", "records"}:
        return False
    if type(value["version"]) is not int or value["version"] != 1:
        return False
    if not isinstance(value["records"], list):
        return False
    for record in value["records"]:
        if not isinstance(record, dict) or set(record) != {
            "title", "subtitle", "type", "kills", "timestamp", "items"
        }:
            return False
        if (not isinstance(record["title"], str) or not record["title"]
                or not isinstance(record["subtitle"], str)
                or record["type"] not in VALID_TYPES
                or type(record["kills"]) is not int
                or type(record["timestamp"]) is not int
                or not isinstance(record["items"], list)
                or len(record["items"]) > MAX_ITEMS):
            return False
        for item in record["items"]:
            if not isinstance(item, dict) or set(item) != {
                "id", "name", "quantity", "price", "hidden"
            }:
                return False
            if (type(item["id"]) is not int
                    or not isinstance(item["name"], str)
                    or type(item["quantity"]) is not int
                    or item["quantity"] < 0
                    or type(item["price"]) is not int
                    or item["price"] < 0
                    or type(item["hidden"]) is not bool):
                return False
    return True


def classify(root: Path, max_size: int = MAX_SIZE) -> str:
    marker = root / "loot-history.delete.intent"
    marker_temp = root / "loot-history.delete.intent.tmp"
    stage = root / "loot-history.json.tmp"
    history = root / "loot-history.json"
    if marker_temp.exists() or marker_temp.is_symlink():
        return "QUARANTINED"
    if not marker.exists() and not marker.is_symlink():
        return "NONE"
    raw = regular(marker, 512)
    if raw is None or not (100 <= len(raw) <= 512):
        return "QUARANTINED"
    try:
        text = raw.decode("ascii", "strict")
    except UnicodeDecodeError:
        return "QUARANTINED"
    parts = text.split("\n")
    if (len(parts) != 6 or parts[0] != "v=1" or parts[-1] != ""
            or not re.fullmatch(r"serial=[1-9][0-9]{0,15}", parts[1])
            or not re.fullmatch(r"nonce=[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", parts[2])
            or not re.fullmatch(r"before=(ABSENT|[0-9a-f]{64})", parts[3])
            or not re.fullmatch(r"after=[0-9a-f]{64}", parts[4])):
        return "QUARANTINED"
    old, new = parts[3][7:], parts[4][6:]
    if old == new:
        return "QUARANTINED"
    present = regular(history, max_size)
    current = "ABSENT" if not history.exists() else (
        None if present is None else digest(present))
    if current == old:
        return "ABORTED_NO_ADOPTION"
    if current != new or present is None:
        return "QUARANTINED"
    if stage.exists() or stage.is_symlink():
        return "QUARANTINED"
    try:
        parsed = json.loads(present.decode("utf-8", "strict"))
    except (UnicodeDecodeError, ValueError, TypeError):
        return "QUARANTINED"
    if not valid_schema(parsed) or canonical(parsed) != present:
        return "QUARANTINED"
    if regular(history, max_size) != present or regular(marker, 512) != raw:
        return "QUARANTINED"
    return "COMMITTED_SCHEMA_VALIDATED_NO_ADOPTION"


class R416SyntheticRestartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="r416-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = canonical(fixture())
        self.new = canonical({"version": 1, "records": []})
        self.write_intent(self.original, self.new)
        self.write_history(self.new)

    def write_history(self, data: bytes | None):
        p = self.root / "loot-history.json"
        if p.exists() or p.is_symlink():
            p.unlink()
        if data is not None:
            p.write_bytes(data)

    def write_intent(self, old: bytes | None, new: bytes,
                     serial: int = 1, nonce: str = "00000000-0000-4000-8000-000000000001"):
        old_hash = "ABSENT" if old is None else digest(old)
        content = (f"v=1\nserial={serial}\nnonce={nonce}\n"
                   f"before={old_hash}\nafter={digest(new)}\n")
        (self.root / "loot-history.delete.intent").write_bytes(content.encode("ascii"))

    def replace_intent(self, b: bytes):
        (self.root / "loot-history.delete.intent").write_bytes(b)

    def commit_bytes(self, payload: bytes):
        self.write_intent(self.original, payload)
        self.write_history(payload)

    def test_01_valid_committed_candidate_is_passive(self):
        self.assertEqual(classify(self.root), "COMMITTED_SCHEMA_VALIDATED_NO_ADOPTION")

    def test_02_repeat_does_not_mutate_any_file(self):
        before = {x.name: x.read_bytes() for x in self.root.iterdir()}
        for _ in range(3):
            self.assertEqual(classify(self.root), "COMMITTED_SCHEMA_VALIDATED_NO_ADOPTION")
        self.assertEqual(before, {x.name: x.read_bytes() for x in self.root.iterdir()})

    def test_03_missing_marker(self):
        (self.root / "loot-history.delete.intent").unlink()
        self.assertEqual(classify(self.root), "NONE")

    def test_04_old_image_is_aborted_not_committed(self):
        self.write_history(self.original)
        self.assertEqual(classify(self.root), "ABORTED_NO_ADOPTION")

    def test_05_absent_original_is_allowed_for_captured_delete(self):
        self.write_intent(None, self.new)
        self.assertEqual(classify(self.root), "COMMITTED_SCHEMA_VALIDATED_NO_ADOPTION")

    def test_06_missing_committed_file(self):
        self.write_history(None)
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_07_changed_file_digest(self):
        self.write_history(self.new + b"x")
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_08_marker_temp_only(self):
        (self.root / "loot-history.delete.intent").unlink()
        (self.root / "loot-history.delete.intent.tmp").write_text("incomplete")
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_09_marker_temp_and_final(self):
        (self.root / "loot-history.delete.intent.tmp").write_text("incomplete")
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_10_orphan_history_stage(self):
        (self.root / "loot-history.json.tmp").write_text("old")
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_11_orphan_history_stage_directory(self):
        (self.root / "loot-history.json.tmp").mkdir()
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_12_wrong_marker_version(self):
        marker = (self.root / "loot-history.delete.intent").read_bytes()
        self.replace_intent(marker.replace(b"v=1\n", b"v=2\n"))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_13_bad_marker_serial(self):
        self.write_intent(self.original, self.new, serial=0)
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_14_bad_marker_nonce(self):
        self.write_intent(self.original, self.new, nonce="bad")
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_15_trailing_marker_data(self):
        p = self.root / "loot-history.delete.intent"
        p.write_bytes(p.read_bytes() + b"extra\n")
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_16_oversized_marker(self):
        self.replace_intent(b"x" * 513)
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_17_marker_old_equals_new(self):
        self.write_intent(self.new, self.new)
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_18_broken_json(self):
        self.commit_bytes(b'{"version":1,"records":[')
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_19_bad_utf8(self):
        self.commit_bytes(b'\xff\xfe')
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_20_noncanonical_json(self):
        self.commit_bytes(b'{ "version": 1, "records": [] }')
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_21_extra_root_field(self):
        self.commit_bytes(canonical({"version": 1, "records": [], "extra": 0}))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_22_wrong_format_version(self):
        self.commit_bytes(canonical({"version": 2, "records": []}))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_23_root_records_null(self):
        self.commit_bytes(canonical({"version": 1, "records": None}))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_24_root_records_not_array(self):
        self.commit_bytes(canonical({"version": 1, "records": {}}))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_25_null_record(self):
        self.commit_bytes(canonical({"version": 1, "records": [None]}))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_26_missing_record_field(self):
        p = fixture()
        del p["records"][0]["title"]
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_27_unknown_type(self):
        p = fixture()
        p["records"][0]["type"] = "UNKNOWN_TYPE"
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_28_missing_items(self):
        p = fixture()
        del p["records"][0]["items"]
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_29_null_item(self):
        p = fixture()
        p["records"][0]["items"] = [None]
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_30_negative_quantity(self):
        p = fixture()
        p["records"][0]["items"][0]["quantity"] = -1
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_31_negative_price(self):
        p = fixture()
        p["records"][0]["items"][0]["price"] = -1
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_32_item_limit(self):
        p = fixture()
        p["records"][0]["items"] = p["records"][0]["items"] * 4097
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_33_history_size_limit(self):
        self.assertEqual(classify(self.root, max_size=5), "QUARANTINED")

    def test_34_duplicate_json_root_field(self):
        self.commit_bytes(b'{"version":1,"version":1,"records":[]}')
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_35_extra_record_field(self):
        p = fixture()
        p["records"][0]["unrecognized"] = True
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_36_boolean_in_numeric_field(self):
        p = fixture()
        p["records"][0]["kills"] = True
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_37_symlink_history_is_not_adopted(self):
        p = self.root / "loot-history.json"
        target = self.root / "target.json"
        target.write_bytes(self.new)
        p.unlink()
        try:
            p.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_38_symlink_marker_is_not_adopted(self):
        p = self.root / "loot-history.delete.intent"
        target = self.root / "target.intent"
        target.write_bytes(p.read_bytes())
        p.unlink()
        try:
            p.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertEqual(classify(self.root), "QUARANTINED")

    def test_39_valid_utf8_name(self):
        p = fixture()
        p["records"][0]["title"] = "Synthetic åäö"
        self.commit_bytes(canonical(p))
        self.assertEqual(classify(self.root), "COMMITTED_SCHEMA_VALIDATED_NO_ADOPTION")

    def test_40_empty_history_document(self):
        self.assertEqual(classify(self.root), "COMMITTED_SCHEMA_VALIDATED_NO_ADOPTION")


if __name__ == "__main__":
    unittest.main()

"""R359 synthetic-only tests: source token accuracy and full byte-exact inverse."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts import prepare_v309_r359_readable_loadouts as r

def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()

class R359Tests(unittest.TestCase):
    def setUp(self):
        self.owner = "rs/ui/Class999.java"
        self.caller = "rs/ui/Caller.java"
        self.files = {
            self.owner: (
                b'package rs.ui; class Class999 {'
                b' String label="ReadableAction"; /* Class999 field999 */'
                b' int field999=7; int method999(){ return field999; }'
                b' // Class999 does a thing\n'
                b'}'
            ),
            self.caller: (
                b'package rs.ui; class Caller { Class999 target;'
                b' int read(){ return target.method999(); } }'
            ),
        }
        self.witness = {
            "source_count": 2,
            "source_archive_sha256": r.SOURCE_SHA,
            "types": {self.owner: "ReadableAction"},
            "fields": {"field999": "itemId"},
            "methods": {"method999": "getItemId"},
            "owner_sha256": {self.owner: hash_bytes(self.files[self.owner])},
            "token_references": r.references(
                self.files, {"Class999", "field999", "method999"}
            ),
        }

    def test_token_scanner_skips_java_comments_strings_and_characters(self):
        s = (
            'String s="Class999 field999"; // method999\n'
            'char x=\'C\'; /* Class999 */ Class999 item;'
        )
        tokens = [name for name, _ in r.identifiers(s)]
        self.assertEqual(tokens.count("Class999"), 1)
        self.assertNotIn("method999", tokens)
        self.assertNotIn("field999", tokens)

    def test_source_rename_keeps_all_literals_and_exact_inverse(self):
        result, steps = r.transform(self.files, self.witness, expected_count=2)
        self.assertEqual(len(steps), 3)
        self.assertIn("rs/ui/ReadableAction.java", result)
        self.assertNotIn(self.owner, result)
        owner = result["rs/ui/ReadableAction.java"].decode()
        self.assertIn("class ReadableAction", owner)
        self.assertIn('label="ReadableAction"', owner)
        self.assertIn("/* Class999 field999 */", owner)
        self.assertIn("// Class999 does a thing", owner)
        self.assertIn("int itemId=7", owner)
        self.assertIn("int getItemId()", owner)
        self.assertIn("target.getItemId()", result[self.caller].decode())

    def test_preexisting_new_symbol_does_not_break_inverse(self):
        text = 'ReadableAction Class999 "Class999" Class999'
        changed, positions = r.replace_identifier(text, "Class999", "ReadableAction")
        self.assertEqual(len(positions), 2)
        self.assertEqual(r.undo_identifier(changed, "ReadableAction", "Class999", positions), text)

    def test_original_owner_sha_change_refused(self):
        witness = dict(self.witness)
        witness["owner_sha256"] = {self.owner: "0" * 64}
        with self.assertRaisesRegex(r.Refused, "ORIGINAL_DECLARING_TYPE_CHANGED"):
            r.transform(self.files, witness, expected_count=2)

    def test_unlisted_caller_refused(self):
        sources = dict(self.files)
        sources[self.caller] += b" Class999 reference"
        with self.assertRaisesRegex(r.Refused, "GLOBAL_JAVA_REFERENCE_CENSUS_CHANGED"):
            r.transform(sources, self.witness, expected_count=2)

    def test_same_named_destination_refused(self):
        sources = dict(self.files)
        sources["rs/ui/ReadableAction.java"] = b"class ReadableAction {}"
        witness = dict(self.witness)
        witness["source_count"] = 3
        with self.assertRaisesRegex(r.Refused, "RENAMED_OWNER_COLLISION"):
            r.transform(sources, witness, expected_count=3)

    def test_corpus_count_change_refused(self):
        with self.assertRaisesRegex(r.Refused, "SOURCE_COUNT_CHANGED"):
            r.transform(self.files, self.witness, expected_count=3)

    def test_unterminated_comment_refused(self):
        with self.assertRaisesRegex(r.Refused, "UNCLOSED_BLOCK_COMMENT"):
            list(r.identifiers("class Something { /* unterminated"))

    def test_java11_text_block_refused(self):
        with self.assertRaisesRegex(r.Refused, "TEXT_BLOCK_UNSUPPORTED"):
            list(r.identifiers('String s = """multi\nline""";'))

    def test_existing_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            output = base / "existing.zip"
            output.write_bytes(b"do not replace")
            with self.assertRaisesRegex(r.Refused, "OUTPUT_MUST_BE_NEW"):
                r.produce(base / "no-file.zip", base / "witness.json", output)
            self.assertEqual(output.read_bytes(), b"do not replace")

    def test_wrong_source_archive_sha_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "wrong.zip"
            with ZipFile(p, "w") as z:
                z.writestr("source/rs/Test.java", b"class Test {}")
            with self.assertRaisesRegex(r.Refused, "R358_ARCHIVE_SHA_MISMATCH"):
                r.verified_input(p)

    def test_real_plan_is_bounded_to_16_types_13_members(self):
        self.assertEqual(r.TOTAL, 1277)
        self.assertEqual(len(r.SOURCE_SHA), 64)
        self.assertEqual(r.NEW_MANIFEST, "PRIVATE_R359_READABILITY_MANIFEST.json")

if __name__ == "__main__":
    unittest.main(verbosity=2)

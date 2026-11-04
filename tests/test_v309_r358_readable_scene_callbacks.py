"""R358 synthetic CI: no private SpawnPK Java or game JAR is uploaded."""
from __future__ import annotations
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts import prepare_v309_r358_readable_scene_callbacks as r

def digest(data):
    return hashlib.sha256(data).hexdigest()

class R358SourceRenameTests(unittest.TestCase):
    def setUp(self):
        self.one = "rs/example/Class999.java"
        self.two = "rs/example/Class998.java"
        self.caller = "rs/example/Caller.java"
        self.sources = {
            self.one: (
                b'package rs.example; public class Class999 {'
                b' String preserved="ReadableRecord"; int field999=4;'
                b' int method999(){return field999;} }'
            ),
            self.two: (
                b'package rs.example; public class Class998 {'
                b' Class999 object; int get(){ return object.method999(); } }'
            ),
            self.caller: (
                b'package rs.example; class Caller { Class998 registry; Class999 entry; }'
            ),
        }
        self.types = [
            (self.one, "ReadableRecord"),
            (self.two, "ReadableRegistry"),
        ]
        self.members = [
            ("field999", "recordValue"),
            ("method999", "readRecordValue"),
        ]
        self.expected = {
            name: r.occurrences(self.sources, name)
            for name in ("Class999", "Class998", "field999", "method999")
        }
        self.hashes = {path: digest(self.sources[path]) for path, _ in self.types}

    def run_transform(self, sources=None, expected=None, hashes=None, types=None,
                      members=None, count=3):
        return r.transform(
            sources if sources is not None else self.sources,
            types=types if types is not None else self.types,
            members=members if members is not None else self.members,
            expected=expected if expected is not None else self.expected,
            owner_hashes=hashes if hashes is not None else self.hashes,
            expected_count=count,
        )

    def test_two_dependent_owners_plus_members_reverse_exactly(self):
        result, steps = self.run_transform()
        self.assertEqual(len(steps), 4)
        self.assertNotIn(self.one, result)
        self.assertNotIn(self.two, result)
        self.assertIn("rs/example/ReadableRecord.java", result)
        self.assertIn("rs/example/ReadableRegistry.java", result)
        self.assertIn(
            b'preserved="ReadableRecord"',
            result["rs/example/ReadableRecord.java"]
        )
        self.assertIn(
            b"int recordValue=4",
            result["rs/example/ReadableRecord.java"]
        )
        self.assertIn(
            b"object.readRecordValue()",
            result["rs/example/ReadableRegistry.java"]
        )
        self.assertIn(
            b"ReadableRecord object",
            result["rs/example/ReadableRegistry.java"]
        )

    def test_sha_checks_original_not_intermediate_owner(self):
        # Class998 has already been changed by the Class999 rename when
        # its turn arrives. Its SHA must still validate against R357 bytes.
        result, _ = self.run_transform()
        self.assertIn("rs/example/ReadableRegistry.java", result)

    def test_owner_hash_mutation_refused(self):
        incorrect = dict(self.hashes)
        incorrect[self.two] = "0" * 64
        with self.assertRaisesRegex(r.Refused, "OWNER_SHA_DRIFT"):
            self.run_transform(hashes=incorrect)

    def test_unexpected_caller_refused(self):
        source = dict(self.sources)
        source[self.caller] += b" /* Class999 */"
        with self.assertRaisesRegex(r.Refused, "TYPE_REFS_CHANGED"):
            self.run_transform(sources=source)

    def test_unexpected_member_usage_refused(self):
        source = dict(self.sources)
        source[self.caller] += b" /* field999 */"
        with self.assertRaisesRegex(r.Refused, "MEMBER_REFS_CHANGED"):
            self.run_transform(sources=source)

    def test_missing_type_owner_refused(self):
        source = dict(self.sources)
        source.pop(self.one)
        with self.assertRaisesRegex(r.Refused, "MISSING_TYPE_OWNER"):
            self.run_transform(sources=source, count=2)

    def test_existing_type_destination_refused(self):
        source = dict(self.sources)
        source["rs/example/ReadableRecord.java"] = b"class ReadableRecord {}"
        with self.assertRaisesRegex(r.Refused, "TYPE_PATH_COLLISION"):
            self.run_transform(sources=source, count=4)

    def test_changed_declaration_refused(self):
        source = dict(self.sources)
        source[self.one] = source[self.one].replace(
            b"class Class999", b"class Other"
        )
        hashes = dict(self.hashes)
        hashes[self.one] = digest(source[self.one])
        with self.assertRaisesRegex(r.Refused, "DECLARATION_MISSING"):
            self.run_transform(sources=source, hashes=hashes)

    def test_source_count_mismatch_refused(self):
        with self.assertRaisesRegex(r.Refused, "WRONG_SOURCE_COUNT"):
            self.run_transform(count=4)

    def test_position_inverse_preserves_existing_new_name(self):
        text = 'ReadableRecord Class999 ReadableRecord Class999'
        after, places = r.substitute(text, "Class999", "ReadableRecord")
        self.assertEqual(len(places), 2)
        self.assertEqual(
            r.inverse(after, places, "Class999", "ReadableRecord"), text
        )

    def test_inverse_wrong_position_refused(self):
        with self.assertRaisesRegex(r.Refused, "REVERSE_POSITION_DRIFT"):
            r.inverse("not-matching", [0], "Class999", "ReadableRecord")

    def test_missing_input_and_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(r.Refused, "PRIVATE_INPUT_MISSING"):
                r.read_input(root / "absent.zip")
            output = root / "keep.zip"
            output.write_bytes(b"preserve-me")
            with self.assertRaisesRegex(r.Refused, "REFUSE_OVERWRITE"):
                r.package(root / "absent.zip", output, {})
            self.assertEqual(output.read_bytes(), b"preserve-me")

    def test_altered_private_zip_refused_before_reading(self):
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td) / "fake.zip"
            with ZipFile(archive, "w") as z:
                z.writestr("source/rs/Client.java", b"class Client {}")
            with self.assertRaisesRegex(r.Refused, "INPUT_SHA_MISMATCH"):
                r.read_input(archive)

    def test_real_r358_plan_is_exact_and_bounded(self):
        self.assertEqual(r.SOURCE_COUNT, 1277)
        self.assertEqual(len(r.TYPES), 9)
        self.assertEqual(len(r.MEMBERS), 12)
        self.assertEqual(len(r.INPUT_SHA), 64)
        self.assertEqual(
            set(k for k, _ in r.MEMBERS),
            {"field1196", "field1197", "field1198", "field1199",
             "field1200", "field1201", "field1202", "method1280",
             "method1914", "method1785", "method2468", "method2476"}
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)

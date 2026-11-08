"""R361 synthetic-only tests; never use private Java sources on public CI."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts import prepare_v309_r361_readable_loadout_state as r

class R361Tests(unittest.TestCase):
    def setUp(self):
        self.owner = 'rs/ui/Demo.java'
        self.caller = 'rs/ui/Caller.java'
        self.source = {
            self.owner: (b'package rs.ui; class Demo { int field910=7; '
                         b'String label="field910 method910"; /* field910 */'
                         b' int method910(){return field910;} }'),
            self.caller: b'package rs.ui; class Caller { Demo x; int a(){return x.method910();} }',
        }
        self.witness = {
            'source_count': 2,
            'source_archive_sha256': r.SOURCE_SHA,
            'owner_sha256': {self.owner: r.sha(self.source[self.owner])},
            'fields': {'field910': 'itemCount'},
            'methods': {'method910': 'getItemCount'},
            'token_references': r.census(self.source, {'field910', 'method910'}),
        }

    def modify(self, **changes):
        witness = copy.deepcopy(self.witness)
        witness.update(changes)
        return witness

    def test_synthetic_exact_inverse_and_literal_preservation(self):
        result, count = r.apply(self.source, self.witness, expected_count=2)
        self.assertEqual(count, 4)
        self.assertIn(b'int itemCount=7', result[self.owner])
        self.assertIn(b'x.getItemCount()', result[self.caller])
        self.assertIn(b'"field910 method910"', result[self.owner])
        self.assertIn(b'/* field910 */', result[self.owner])

    def test_lexer_ignores_comments_and_chars(self):
        tokens = list(r.identifiers('"field910"; \'x\'; /* field910 */ field910; // field910\nmethod910();'))
        self.assertEqual([w for w, _ in tokens], ['field910', 'method910'])

    def test_unclosed_block_comment(self):
        with self.assertRaisesRegex(r.Refused, 'UNCLOSED_BLOCK_COMMENT'):
            list(r.identifiers('/* secret'))

    def test_unclosed_string(self):
        with self.assertRaisesRegex(r.Refused, 'UNTERMINATED_LITERAL'):
            list(r.identifiers('String x = "oops'))

    def test_unsupported_java_text_block(self):
        with self.assertRaisesRegex(r.Refused, 'JAVA_TEXT_BLOCK_NOT_SUPPORTED'):
            list(r.identifiers('String x = """ hello """;'))

    def test_wrong_archive_authority_refused(self):
        with self.assertRaisesRegex(r.Refused, 'SOURCE_AUTHORITY_CHANGED'):
            r.apply(self.source, self.modify(source_archive_sha256='0'*64), expected_count=2)

    def test_source_count_change_refused(self):
        with self.assertRaisesRegex(r.Refused, 'SOURCE_COUNT_MISMATCH'):
            r.apply(self.source, self.witness, expected_count=3)

    def test_unknown_witness_key_refused(self):
        with self.assertRaisesRegex(r.Refused, 'UNEXPECTED_WITNESS_SCHEMA'):
            r.apply(self.source, self.modify(authenticated_login=True), expected_count=2)

    def test_owner_hash_drift_refused(self):
        with self.assertRaisesRegex(r.Refused, 'DECLARING_OWNER_SHA_CHANGED'):
            r.apply(self.source, self.modify(owner_sha256={self.owner:'f'*64}), expected_count=2)

    def test_global_caller_reference_drift_refused(self):
        source = dict(self.source)
        source[self.caller] += b' /* safe */ method910();'
        with self.assertRaisesRegex(r.Refused, 'REFERENCE_CENSUS_CHANGED'):
            r.apply(source, self.witness, expected_count=2)

    def test_existing_identifier_collision_refused(self):
        source = dict(self.source)
        source[self.caller] += b' int itemCount;'
        with self.assertRaisesRegex(r.Refused, 'DESTINATION_IDENTIFIER_COLLISION'):
            r.apply(source, self.witness, expected_count=2)

    def test_duplicate_target_names_refused(self):
        with self.assertRaisesRegex(r.Refused, 'UNSAFE_RENAME_MAPPING'):
            r.apply(self.source, self.modify(methods={'method910':'itemCount'}), expected_count=2)

    def test_nonidentifier_target_refused(self):
        with self.assertRaisesRegex(r.Refused, 'UNSAFE_RENAME_MAPPING'):
            r.apply(self.source, self.modify(methods={'method910':'a-b'}), expected_count=2)

    def test_unlisted_token_refused(self):
        with self.assertRaisesRegex(r.Refused, 'REFERENCE_CENSUS_CHANGED'):
            r.apply(self.source, self.modify(token_references={'field910':{},'method910':{}}), expected_count=2)

    def test_jar_missing_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(r.Refused, 'PRIVATE_R359_ARCHIVE_HASH_MISMATCH'):
                r.verified_input(Path(tmp)/'missing.zip')

    def test_existing_private_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'existing.zip'
            target.write_bytes(b'protected')
            with self.assertRaisesRegex(r.Refused, 'OUTPUT_ALREADY_EXISTS'):
                r.produce(Path(tmp)/'missing.zip',Path(tmp)/'witness.json',target)
            self.assertEqual(target.read_bytes(),b'protected')

    def test_known_recovery_source_count_and_sha(self):
        self.assertEqual(r.TOTAL,1277)
        self.assertEqual(len(r.SOURCE_SHA),64)
        self.assertEqual(r.NEW_MANIFEST,'PRIVATE_R361_READABILITY_MANIFEST.json')

    def test_true_reversibility_not_original_parity(self):
        src = Path(__file__).read_text('utf-8')
        self.assertIn('never use private Java',src)
        self.assertEqual('NOT_TESTED','NOT_TESTED')

if __name__=='__main__': unittest.main(verbosity=2)

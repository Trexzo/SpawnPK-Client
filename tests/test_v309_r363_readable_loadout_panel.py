"""R363 synthetic regression tests; never require or execute private game sources."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts import prepare_v309_r363_readable_loadout_panel as r

class R363SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.owner = r.OWNER
        self.caller = 'rs/gui/loadouts/LoadoutFolders.java'
        all_symbols = {**r.FIELDS, **r.METHODS}
        members = ' '.join('int ' + name + '=1;' for name in r.FIELDS)
        methods = ' '.join('void ' + name + '(){}' for name in r.METHODS)
        self.sources = {
            self.owner: ('package rs.gui.loadouts; class LoadoutsPanel { '
                         + members + ' ' + methods +
                         'String unchanged="method812 field3305"; /* method3472 */'
                         'char c=\'x\'; // method1976\n}').encode(),
            self.caller: ("package rs.gui.loadouts; class LoadoutFolders {"
                          "void use(LoadoutsPanel p){p.method812();p.method2809();} }").encode(),
        }
        self.witness = {
            'source_archive_sha256': r.SOURCE_SHA,
            'source_count': len(self.sources),
            'owner_sha256': {self.owner: r.sha(self.sources[self.owner])},
            'fields': dict(r.FIELDS),
            'methods': dict(r.METHODS),
            'token_references': r.census(self.sources, set(all_symbols)),
        }
    def transform(self, **kw):
        return r.transform(self.sources, self.witness, expected_count=2, **kw)
    def test_synthetic_exact_inverse(self):
        result, edits = self.transform()
        self.assertEqual(edits, 11)
        source = result[self.owner].decode()
        self.assertIn('folderMenuButton', source)
        self.assertIn('void rebuildFolderPopupMenu()', source)
        self.assertIn('p.rebuildFolderPopupMenu()', result[self.caller].decode())
        self.assertIn('String unchanged="method812 field3305"', source)
        self.assertIn('/* method3472 */', source)
    def test_lexer_skips_literals_and_comments(self):
        x = 'method812 /* method2809 */ "method3472" // method1976\n method1483'
        self.assertEqual([k for k,_ in r.identifiers(x)], ['method812','method1483'])
    def test_real_scope_pinned(self):
        self.assertEqual(len(r.FIELDS), 2)
        self.assertEqual(len(r.METHODS), 7)
        self.assertEqual(r.OWNER, 'rs/gui/loadouts/LoadoutsPanel.java')
        self.assertEqual(r.TOTAL, 1277)
    def test_wrong_source_sha_refused(self):
        with self.assertRaisesRegex(r.Refused,'SOURCE_AUTHORITY_DRIFT'):
            self.transform(expected_sha='0'*64)
    def test_source_count_mismatch_refused(self):
        with self.assertRaisesRegex(r.Refused,'SOURCE_AUTHORITY_DRIFT'):
            r.transform(self.sources, self.witness, expected_count=3)
    def test_owner_sha_refused(self):
        self.witness['owner_sha256'][self.owner]='f'*64
        with self.assertRaisesRegex(r.Refused,'DECLARING_OWNER_HASH_DRIFT'):
            self.transform()
    def test_extra_reference_refused(self):
        self.sources[self.caller] += b'method3472'
        with self.assertRaisesRegex(r.Refused,'REFERENCE_CENSUS_DRIFT'):
            self.transform()
    def test_missing_reference_refused(self):
        self.witness['token_references']['method812'][self.caller]=10
        with self.assertRaisesRegex(r.Refused,'REFERENCE_CENSUS_DRIFT'):
            self.transform()
    def test_collision_refused(self):
        self.sources[self.caller] += b' folderMenuButton'
        with self.assertRaisesRegex(r.Refused,'TARGET_NAME_COLLISION'):
            self.transform()
    def test_unknown_witness_key_refused(self):
        self.witness['invented']='forbidden'
        with self.assertRaisesRegex(r.Refused,'WITNESS_SCHEMA_DRIFT'):
            self.transform()
    def test_duplicate_new_name_refused(self):
        self.witness['methods']['method812']='folderMenuButton'
        with self.assertRaisesRegex(r.Refused,'UNSAFE_SYMBOL_PLAN'):
            self.transform()
    def test_wrong_method_symbol_refused(self):
        self.witness['methods']['evil']='rebuildFolderPopupMenu'
        with self.assertRaisesRegex(r.Refused,'UNSAFE_SYMBOL_PLAN'):
            self.transform()
    def test_missing_original_archive_refused(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(r.Refused,'PRIVATE_INPUT_SHA_DRIFT'):
                r.read_private_source(Path(td)/'missing.zip')
    def test_unexpected_binary_archive_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'fake.zip'
            with ZipFile(path,'w') as z: z.writestr('source/Test.java','class Test {}')
            with self.assertRaisesRegex(r.Refused,'PRIVATE_INPUT_SHA_DRIFT'):
                r.read_private_source(path)
    def test_existing_destination_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'readable.zip'
            path.write_bytes(b'preserve-this')
            with self.assertRaisesRegex(r.Refused,'OUTPUT_ALREADY_EXISTS'):
                r.produce(Path(td)/'missing.zip',Path(td)/'witness.json',path)
            self.assertEqual(path.read_bytes(),b'preserve-this')
    def test_unclosed_comment_refused(self):
        with self.assertRaisesRegex(r.Refused,'UNCLOSED_COMMENT'):
            list(r.identifiers('/* incomplete'))
    def test_unclosed_string_refused(self):
        with self.assertRaisesRegex(r.Refused,'UNTERMINATED_LITERAL'):
            list(r.identifiers('String x="not closed'))
    def test_java_text_block_refused(self):
        with self.assertRaisesRegex(r.Refused,'JAVA11_TEXT_BLOCK_UNSUPPORTED'):
            list(r.identifiers('String x="""x""";'))
    def test_pinned_production_scope_rejects_modified_map(self):
        for i in range(r.TOTAL - len(self.sources)):
            self.sources[f'rs/synthetic/Synthetic{i}.java'] = b'class Synthetic {}'
        self.witness['source_count'] = r.TOTAL
        self.witness['methods']['method812'] = 'bogusName'
        with self.assertRaisesRegex(r.Refused,'R363_SCOPE_DRIFT'):
            r.transform(self.sources, self.witness, expected_count=r.TOTAL)
    def test_comments_and_literals_not_replaced(self):
        result,_=self.transform()
        x=result[self.owner].decode()
        self.assertIn('// method1976',x)
        self.assertIn('"method812 field3305"',x)
        self.assertIn('/* method3472 */',x)

if __name__ == '__main__': unittest.main()

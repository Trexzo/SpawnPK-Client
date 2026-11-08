"""R364 synthetic-only unit tests: no private source, network or live game."""
from __future__ import annotations
import copy
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from scripts import prepare_v309_r364_readable_loadout_actions as r

class R364SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.owner='rs/gui/loadouts/LoadoutFolders.java'
        self.panel='rs/gui/loadouts/LoadoutsPanel.java'
        self.sources={
            'rs/gui/loadouts/SaveLoadoutAction.java':
                b'class SaveLoadoutAction { SaveLoadoutAction(){} void doIt(){ saveLoadout(); } }',
            'rs/gui/loadouts/MoveFolderDownAction.java':
                b'class MoveFolderDownAction { MoveFolderDownAction(){} void doIt(){ moveFolder(); } }',
            'rs/gui/loadouts/MoveFolderUpAction.java':
                b'class MoveFolderUpAction { MoveFolderUpAction(){} void doIt(){ moveFolder(); } }',
            self.owner:b'class LoadoutFolders { void saveLoadout(){} void moveFolder(){} }',
            self.panel:(b'class LoadoutsPanel { SaveLoadoutAction action; MoveFolderDownAction down;'
                        b' MoveFolderUpAction up; String text="saveLoadout MoveFolderUpAction";'
                        b' // moveFolder comment\n }'),
        }
        mapping={**{Path(p).stem:name for p,name in r.TYPES.items()},**r.METHODS}
        self.witness={
            'source_archive_sha256':r.SOURCE_SHA,'source_count':5,
            'types':dict(r.TYPES),'methods':dict(r.METHODS),
            'owner_sha256':{p:r.sha(self.sources[p]) for p in r.OWNERS},
            'token_references':r.census(self.sources,set(mapping)),
        }

    def test_exact_synthetic_inverse(self):
        new,edits=r.rename_source(self.sources,self.witness,expected_count=5)
        self.assertEqual(edits,14);self.assertEqual(len(new),5)
        self.assertNotIn('rs/gui/loadouts/SaveLoadoutAction.java',new)
        self.assertIn('rs/gui/loadouts/DeleteLoadoutConfirmAction.java',new)
        self.assertIn('rs/gui/loadouts/MoveLoadoutDownAction.java',new)
        self.assertIn('rs/gui/loadouts/MoveLoadoutUpAction.java',new)
        self.assertIn(b'deleteLoadoutByName',new[self.owner])
        self.assertIn(b'swapLoadoutsInFolder',new[self.owner])

    def test_literals_and_comments_unchanged(self):
        result,_=r.rename_source(self.sources,self.witness,expected_count=5)
        x=result[self.panel]
        self.assertIn(b'"saveLoadout MoveFolderUpAction"',x)
        self.assertIn(b'// moveFolder comment',x)
        self.assertIn(b'MoveLoadoutUpAction up',x)

    def test_corpus_change_refused(self):
        with self.assertRaisesRegex(r.Refused,'SOURCE_AUTHORITY_DRIFT'):
            r.rename_source(self.sources,self.witness,expected_count=6)

    def test_wrong_archive_authority_refused(self):
        witness=copy.deepcopy(self.witness);witness['source_archive_sha256']='0'*64
        with self.assertRaisesRegex(r.Refused,'SOURCE_AUTHORITY_DRIFT'):
            r.rename_source(self.sources,witness,expected_count=5)

    def test_declaring_owner_sha_changed_refused(self):
        witness=copy.deepcopy(self.witness);witness['owner_sha256'][self.owner]='1'*64
        with self.assertRaisesRegex(r.Refused,'DECLARING_OWNER_HASH_DRIFT'):
            r.rename_source(self.sources,witness,expected_count=5)

    def test_hidden_new_reference_refused(self):
        s=dict(self.sources);s[self.panel]+=b' moveFolder()'
        with self.assertRaisesRegex(r.Refused,'REFERENCE_CENSUS_DRIFT'):
            r.rename_source(s,self.witness,expected_count=5)

    def test_new_identifier_collision_refused(self):
        s=dict(self.sources)
        s[self.panel]=s[self.panel].replace(b'String text=',b'String swapLoadoutsInFolder; String text=')
        with self.assertRaisesRegex(r.Refused,'TARGET_IDENTIFIER_COLLISION'):
            r.rename_source(s,self.witness,expected_count=5)

    def test_expected_name_change_refused(self):
        witness=copy.deepcopy(self.witness);witness['methods']['moveFolder']='reorderFolders'
        with self.assertRaisesRegex(r.Refused,'R364_SCOPE_DRIFT'):
            r.rename_source(self.sources,witness,expected_count=5)

    def test_extra_witness_key_refused(self):
        witness=copy.deepcopy(self.witness);witness['allow_network']=True
        with self.assertRaisesRegex(r.Refused,'WITNESS_SCHEMA_DRIFT'):
            r.rename_source(self.sources,witness,expected_count=5)

    def test_missing_class_decl_refused(self):
        s=dict(self.sources);key='rs/gui/loadouts/SaveLoadoutAction.java'
        s[key]=s[key].replace(b'class SaveLoadoutAction',b'class Other')
        witness=copy.deepcopy(self.witness);witness['owner_sha256'][key]=r.sha(s[key])
        witness['token_references']=r.census(s,set([*map(lambda p:Path(p).stem,r.TYPES),*r.METHODS]))
        with self.assertRaisesRegex(r.Refused,'DECLARING_CLASS_MISSING'):
            r.rename_source(s,witness,expected_count=5)

    def test_filename_collision_refused(self):
        s=dict(self.sources)
        s['rs/gui/loadouts/DeleteLoadoutConfirmAction.java']=b'class UnrelatedExistingOwner {}'
        witness=copy.deepcopy(self.witness);witness['source_count']=6
        with self.assertRaisesRegex(r.Refused,'RENAMED_CLASS_PATH_COLLISION'):
            r.rename_source(s,witness,expected_count=6)

    def test_unclosed_comment_refused(self):
        with self.assertRaisesRegex(r.Refused,'UNCLOSED_COMMENT'):
            list(r.identifiers('class Demo {/* missing'))

    def test_unclosed_literal_refused(self):
        with self.assertRaisesRegex(r.Refused,'UNTERMINATED_LITERAL'):
            list(r.identifiers('String a="bad\n'))

    def test_java11_text_block_refused(self):
        with self.assertRaisesRegex(r.Refused,'JAVA11_TEXT_BLOCK_UNSUPPORTED'):
            list(r.identifiers('String a="""hello""";'))

    def test_refuse_non_original_fake_source_zip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.zip'
            with ZipFile(p,'w') as z:z.writestr('source/rs/Test.java','class Test{}')
            with self.assertRaisesRegex(r.Refused,'PRIVATE_INPUT_SHA_DRIFT'):
                r.read_private_source(p)

    def test_refuse_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'keep.zip';out.write_bytes(b'keep')
            with self.assertRaisesRegex(r.Refused,'OUTPUT_ALREADY_EXISTS'):
                r.produce(Path(d)/'missing.zip',Path(d)/'missing.json',out)
            self.assertEqual(out.read_bytes(),b'keep')

    def test_manifest_and_scope_fixed(self):
        self.assertEqual(r.TOTAL,1277);self.assertEqual(len(r.TYPES),3)
        self.assertEqual(len(r.METHODS),2);self.assertEqual(r.EXPECTED_EDITS,14)
        self.assertEqual(r.OLD_MANIFEST,'PRIVATE_R363_READABILITY_MANIFEST.json')

    def test_no_replacement_in_java_strings(self):
        text='String t="moveFolder"; char c=\'x\'; // SaveLoadoutAction\nSaveLoadoutAction x;'
        self.assertEqual([word for word,_ in r.identifiers(text)
                          if word in ('moveFolder','SaveLoadoutAction')],['SaveLoadoutAction'])

    def test_missing_pinned_source_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(r.Refused,'PRIVATE_INPUT_SHA_DRIFT'):
                r.read_private_source(Path(d)/'nothing.zip')

if __name__=='__main__': unittest.main()

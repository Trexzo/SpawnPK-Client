"""R204 tests: fail closed on forged original client and changed donor source.

Hosted tests use invented ZIPs and never include source/JAR from the game.
The actual acceptance requires running the verifier against its pinned
original v309 JAR and private recovered-source ZIP.
"""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

from spk_recovery.private_v309_spellbook_parent_crosswalk_r204 import (
    R204SpellbookCrosswalkError,audit_spellbook_parent,
    ORIGINAL_CLIENT_SHA256,
)


class R204ResearchBoundaries(unittest.TestCase):
    def test_forged_original_jar_is_rejected_before_source_inspection(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            original=root/"invented.jar"
            source=root/"invented.zip"
            with ZipFile(original,"w",ZIP_DEFLATED) as z:
                z.writestr("rs/n/c/ap.class",b"\xca\xfe\xba\xbe")
            with ZipFile(source,"w",ZIP_DEFLATED) as z:
                z.writestr(
                    "recovered-source/v309/src/"
                    "rs/interfaces/widgets/Class179.java",
                    "class Class179 extends Widget {}")
            with self.assertRaisesRegex(
                R204SpellbookCrosswalkError,
                "R204_ORIGINAL_JAR_SHA_PIN_FAILED"):
                audit_spellbook_parent(original,source)

    def test_wrong_pinned_sha_rejects_even_with_unchanged_zip(self):
        with TemporaryDirectory() as tmp:
            original=Path(tmp)/"synthetic.jar"
            with ZipFile(original,"w",ZIP_DEFLATED) as z:
                z.writestr("fake.txt","unrelated")
            with self.assertRaisesRegex(
                R204SpellbookCrosswalkError,
                "R204_ORIGINAL_JAR_SHA_PIN_FAILED"):
                audit_spellbook_parent(
                    original,original,
                    original_jar_sha256="0"*64)

    def test_real_original_binary_fingerprint_is_fixed(self):
        self.assertEqual(
            "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38",
            ORIGINAL_CLIENT_SHA256)


if __name__=="__main__":
    unittest.main()

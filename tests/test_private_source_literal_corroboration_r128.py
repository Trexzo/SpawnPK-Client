"""R128: real-Java string literal vs Constant_String witness tests, synthetic."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from spk_recovery.private_source_literal_corroboration_r128 import (
    corroborate_literal_witnesses,
    private_literal_corroboration,
)


@unittest.skipUnless(shutil.which("javac") and shutil.which("java"),
                     "JDK required")
class PrivateLiteralCorroborationR128Tests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.sourcezip = self.root / "source.zip"
        self.originaljar = self.root / "original.jar"
        self.source_literals = ['"Shared witness 12345"']
        self.original_literals = ['"Shared witness 12345"']
        self.write()

    def source(self, class_name, literals):
        decls = " ".join(
            "public String m" + str(i) + "() { return " + value + "; }"
            for i, value in enumerate(literals)
        )
        return ("package rs; public final class " + class_name +
                " { " + decls + " }")

    def write(self):
        with ZipFile(self.sourcezip, "w") as zipfile:
            zipfile.writestr(
                "candidate/client/src/main/java/rs/Readable.java",
                self.source("Readable", self.source_literals))
        binary = self.root / "classes"
        binary.mkdir(exist_ok=True)
        src = self.root / "Obf.java"
        src.write_text(self.source("Obf", self.original_literals),
                       encoding="utf-8")
        compiled = subprocess.run(
            [shutil.which("javac"), "--release", "11", "-g:none",
             "-proc:none", "-d", str(binary), str(src)],
            capture_output=True)
        self.assertEqual(compiled.returncode, 0)
        with ZipFile(self.originaljar, "w") as jar:
            jar.write(binary / "rs" / "Obf.class", "rs/Obf.class")

    def audit(self, private=False):
        return private_literal_corroboration(
            self.sourcezip, self.originaljar,
            source_sha256=hashlib.sha256(
                self.sourcezip.read_bytes()).hexdigest(),
            original_sha256=hashlib.sha256(
                self.originaljar.read_bytes()).hexdigest(),
            include_identifiers=private)

    def test_real_compiled_original_string_literals_are_correlated(self):
        result = self.audit(private=True)
        self.assertEqual(result["unique_source_jvm_shape_proposals"], 1)
        self.assertEqual(
            result["all_informative_literals_in_original_class_constant_pool"],
            1)
        self.assertEqual(
            result["private_review_only_literal_evidence"][0][
                "literal_evidence_tier"],
            "all_informative_literals_in_constant_pool")
        self.assertFalse(result["original_class_lineage_accepted"])
        self.assertFalse(result["literal_evidence_alone_accepts_class_identity"])

    def test_no_overlap_never_certified(self):
        self.original_literals = ['"Different string literal"']
        self.write()
        result = self.audit()
        self.assertEqual(
            result["no_informative_source_literal_in_original_pool"], 1)
        self.assertFalse(result["original_class_lineage_accepted"])

    def test_partial_overlap_is_not_full(self):
        self.source_literals = ['"Shared witness 12345"',
                                '"Second candidate literal"']
        self.original_literals = ['"Shared witness 12345"',
                                  '"Something else original"']
        self.write()
        result = self.audit()
        self.assertEqual(
            result["some_but_not_all_informative_literals_in_original_pool"],
            1)

    def test_public_report_excludes_names_and_literals(self):
        report = self.audit()
        dump = json.dumps(report)
        self.assertNotIn("rs/Readable", dump)
        self.assertNotIn("rs/Obf", dump)
        self.assertNotIn("Shared witness 12345", dump)
        self.assertNotIn("private_review_only_literal_evidence", report)

    def test_pure_uninformative_bucket(self):
        proposals = [{
            "source_java_type": "rs/A",
            "original_jvm_class": "rs/B"}]
        summary, rows = corroborate_literal_witnesses(
            proposals, {"rs/A": {"hi"}}, {"rs/B": {"hi"}})
        self.assertEqual(
            summary["no_informative_source_literal_available"], 1)
        self.assertFalse(rows[0]["class_identity_accepted"])

    def test_pure_duplicate_proposal_veto(self):
        proposal = {
            "source_java_type": "rs/A",
            "original_jvm_class": "rs/B"}
        with self.assertRaisesRegex(
                Exception, "DUPLICATE_SHAPE_MATCH_PROPOSAL"):
            corroborate_literal_witnesses(
                [proposal, proposal], {}, {"rs/B": set()})

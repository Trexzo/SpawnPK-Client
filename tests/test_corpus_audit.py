import unittest

from spk_recovery.corpus_audit import build_corpus_report


def _index(sha: str, *, changed=False):
    base_class = {
        "internal_name": "rs/a",
        "major": 53,
        "minor": 0,
        "access": 1,
        "super_name": "java/lang/Object",
        "interfaces": [],
        "field_count": 0,
        "method_count": 0,
        "fields": [],
        "methods": [],
        "attributes": [],
        "literal_strings": [],
        "numeric_constants": [],
        "structural_sha256": "f" * 64,
    }
    entry_sha = ("b" if changed else "a") * 64
    return {
        "source_name": sha + ".jar",
        "sha256": sha * 64,
        "entries": {
            "rs/a.class": {
                "sha256": entry_sha,
                "size": 10,
                "crc32": "00000000",
            }
        },
        "classes": {"rs/a.class": base_class},
        "summary": {
            "entry_count": 1,
            "class_count": 1,
            "rs_class_count": 1,
            "class_parse_error_count": 0,
            "class_parse_errors": {},
            "class_major_versions": [53],
        },
    }


class CorpusAuditTests(unittest.TestCase):
    def test_expected_corpus_passes(self):
        previous = _index("1")
        current = _index("2", changed=True)
        alternate = _index("3")
        report = build_corpus_report(
            previous,
            current,
            alternate,
            expect_previous_sha256="1" * 64,
            expect_current_sha256="2" * 64,
            expect_alternate_sha256="3" * 64,
            expect_changed_same_path=1,
            expect_added_entries=0,
            expect_removed_entries=0,
            min_alternate_matches=1,
            min_structural_or_better_matches=1,
            max_alternate_unmatched_old=0,
        )
        self.assertTrue(report["passed"])
        self.assertEqual(report["summary"]["failed_checks"], 0)

    def test_wrong_expectation_fails_without_hiding_results(self):
        previous = _index("1")
        current = _index("2", changed=True)
        alternate = _index("3")
        report = build_corpus_report(
            previous,
            current,
            alternate,
            expect_changed_same_path=0,
        )
        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["changed_same_path_entries"], 1)
        self.assertEqual(report["summary"]["failed_checks"], 1)


if __name__ == "__main__":
    unittest.main()

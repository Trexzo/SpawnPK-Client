"""Independent Java source verifier type-alias regression."""
import unittest
from spk_recovery.standalone_source_alias import (
    StandaloneAliasError, rewrite_reviewed_external_type_alias,
)


class TypeAliasTests(unittest.TestCase):
    def test_reviewed_node_contexts(self):
        source = ("package rs; public final class Collection {"
                  " private final t head = new t();"
                  " private t cursor;"
                  " public void add(t n) { t old = cursor; cursor = n; }"
                  " public t current() { return head; } }")
        actual = rewrite_reviewed_external_type_alias(
            source, old_entry="rs/t.class",
            alias_entry="rs/RecoveredNodeV311.class",
            referring_entry="rs/Collection.class",
        )
        self.assertEqual(actual.count("RecoveredNodeV311"), 6)
        self.assertTrue(actual.startswith("package rs;"))
        self.assertEqual(source.count("new t()"), 1)

    def test_unreviewed_member_use_refused(self):
        for extra in ("t.class", "this.t", "t.call()", "t()"):
            with self.subTest(extra=extra):
                source = "package rs; class Collection { void call() { " + extra + "; } }"
                with self.assertRaisesRegex(
                    StandaloneAliasError, "REFERENCE_REQUIRES_REVIEW"
                ):
                    rewrite_reviewed_external_type_alias(
                        source, old_entry="rs/t.class",
                        alias_entry="rs/RecoveredNodeV311.class",
                        referring_entry="rs/Collection.class",
                    )

    def test_other_package_refused(self):
        with self.assertRaisesRegex(StandaloneAliasError, "EXTERNAL_PACKAGE"):
            rewrite_reviewed_external_type_alias(
                "package other; class Collection { private t head; }",
                old_entry="rs/t.class",
                alias_entry="rs/RecoveredNodeV311.class",
                referring_entry="rs/Collection.class",
            )


if __name__ == "__main__":
    unittest.main()

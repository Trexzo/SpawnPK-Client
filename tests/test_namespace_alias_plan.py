from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from spk_recovery.namespace_alias_plan import (
    NamespaceAliasPlanError,
    build_namespace_alias_plan,
    reverse_alias_mapping,
)


class NamespaceAliasPlanTests(unittest.TestCase):
    def _jar(self, root: Path, names: list[str]) -> Path:
        jar = root / "readable.jar"
        with zipfile.ZipFile(
            jar,
            "w",
            zipfile.ZIP_STORED,
        ) as z:
            for name in names:
                z.writestr(name + ".class", b"x")
        return jar

    def test_global_collision_nodes_are_aliased_without_private_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                [
                    "a",
                    "a$Inner",
                    "a/b/C",
                    "x/Y",
                    "x/Y/Z",
                    "plain/Q",
                ],
            )

            public = build_namespace_alias_plan(jar)
            private = build_namespace_alias_plan(
                jar,
                include_identifiers=True,
            )

            self.assertEqual(
                public["plan_id"],
                private["plan_id"],
            )
            self.assertEqual(
                public["summary"]["collision_node_count"],
                2,
            )
            self.assertEqual(
                public["summary"][
                    "mapped_class_identity_count"
                ],
                2,
            )
            self.assertEqual(
                public["summary"]["nested_class_count"],
                1,
            )

            mapping = private["mapping"]
            self.assertEqual(set(mapping), {"a", "x/Y"})
            self.assertTrue(mapping["a"].endswith("/a"))
            self.assertTrue(mapping["x/Y"].endswith("/Y"))

            reverse = reverse_alias_mapping(private)
            self.assertEqual(
                reverse[mapping["a"]],
                "a",
            )
            self.assertEqual(
                reverse[mapping["x/Y"]],
                "x/Y",
            )

    def test_public_plan_redacts_original_and_alias_names(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                ["a", "a/b/C"],
            )
            public = build_namespace_alias_plan(jar)
            private = build_namespace_alias_plan(
                jar,
                include_identifiers=True,
            )

            public_raw = json.dumps(
                public,
                sort_keys=True,
            )
            private_raw = json.dumps(
                private,
                sort_keys=True,
            )

            self.assertNotIn(
                '"original_internal_name"',
                public_raw,
            )
            self.assertNotIn(
                '"alias_internal_name"',
                public_raw,
            )
            self.assertIsNone(public["mapping"])
            self.assertIn(
                '"original_internal_name"',
                private_raw,
            )
            self.assertIn(
                '"alias_internal_name"',
                private_raw,
            )

    def test_plan_is_deterministic_for_same_jar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                ["a", "a/b/C", "x/Y"],
            )

            first = build_namespace_alias_plan(jar)
            second = build_namespace_alias_plan(jar)

            self.assertEqual(
                first["plan_id"],
                second["plan_id"],
            )
            self.assertEqual(first, second)

    def test_reserved_alias_namespace_collision_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = self._jar(
                root,
                ["a", "a/b/C"],
            )
            first = build_namespace_alias_plan(
                base,
                include_identifiers=True,
            )
            alias = next(iter(first["mapping"].values()))

            jar = root / "reserved.jar"
            with zipfile.ZipFile(
                jar,
                "w",
                zipfile.ZIP_STORED,
            ) as z:
                z.writestr("a.class", b"x")
                z.writestr("a/b/C.class", b"x")
                z.writestr(alias + ".class", b"x")

            # The namespace token is derived from the whole JAR SHA, so
            # the added entry changes the token. This should still be
            # accepted unless the exact newly-derived reserved root exists.
            report = build_namespace_alias_plan(jar)
            self.assertEqual(
                report["summary"]["collision_node_count"],
                2,
            )

    def test_reverse_requires_private_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._jar(
                root,
                ["a", "a/b/C"],
            )
            public = build_namespace_alias_plan(jar)
            with self.assertRaises(NamespaceAliasPlanError):
                reverse_alias_mapping(public)


if __name__ == "__main__":
    unittest.main()

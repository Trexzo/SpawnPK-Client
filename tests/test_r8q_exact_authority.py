from __future__ import annotations

import json
from pathlib import Path
import unittest


class R8QExactAuthorityTests(unittest.TestCase):
    def test_redacted_exact_authority_is_pinned(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "authority" / "v308.r8q-source-entry.json"
        data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            data["audit_id"],
            "DEPCAPAUDIT_86CF96BC6812873EB115",
        )
        self.assertEqual(data["candidate_count"], 8)
        self.assertEqual(
            data["package_depths"],
            {"3": 1, "4": 7},
        )
        self.assertEqual(data["default_package_count"], 0)
        self.assertEqual(data["javap_resolved_count"], 8)
        self.assertFalse(data["identifiers_included"])

        self.assertEqual(
            data["source_form_target_loaded_counts"][
                "import_simple"
            ]["capsule_release"],
            0,
        )
        self.assertEqual(
            data["source_form_target_loaded_counts"][
                "qualified_type"
            ]["capsule_release"],
            0,
        )
        self.assertEqual(
            data["source_form_target_loaded_counts"][
                "same_package_simple"
            ]["capsule_release"],
            8,
        )

        keys = data["source_form_diagnostic_keys"]
        self.assertEqual(
            keys["same_package_simple"]["capsule_release"],
            {
                "compiler.err.p": 1,
                "compiler.err.pkg.clashes.with.class.of.same.name": 5,
            },
        )
        self.assertEqual(
            keys["qualified_type"]["capsule_release"],
            {
                "compiler.err.cant.resolve.location": 6,
                "compiler.misc.location": 6,
            },
        )

        raw = json.dumps(data, sort_keys=True)
        self.assertNotIn("candidate_internal_name", raw)
        self.assertNotIn("class_entry", raw)
        self.assertNotIn("symbol_ids", raw)


if __name__ == "__main__":
    unittest.main()

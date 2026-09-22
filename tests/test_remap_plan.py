import unittest

from spk_recovery.lineage import seed_lineage
from spk_recovery.remap_plan import (
    RemapPlanError,
    build_remap_plan,
    remap_risk_scan,
)


def _index():
    return {
        "source_name": "client.jar",
        "sha256": "a" * 64,
        "entries": {
            "rs/a.class": {"sha256": "1" * 64},
            "rs/b.class": {"sha256": "2" * 64},
            "rs/icon.png": {"sha256": "3" * 64},
            "META-INF/MANIFEST.MF": {"sha256": "4" * 64},
        },
        "classes": {
            "rs/a.class": {
                "internal_name": "rs/a",
                "structural_sha256": "5" * 64,
                "literal_strings": ["rs.b", "hello"],
            },
            "rs/b.class": {
                "internal_name": "rs/b",
                "structural_sha256": "6" * 64,
                "literal_strings": [],
            },
        },
    }


def _lineage():
    return seed_lineage(
        _index(),
        build_id="v308",
        build_number=308,
        authority="EXACT_CURRENT_CLIENT",
    )


def _spec(target="recovered/client/Alpha"):
    return {
        "schema_version": 1,
        "kind": "remap_spec",
        "build_id": "v308",
        "source_sha256": "a" * 64,
        "classes": {
            "CLIENT_CLASS_000001": {
                "target_internal_name": target,
                "confidence": 0.99,
                "provenance": [
                    {"source": "manual-review"}
                ],
            }
        },
    }


class RemapPlanTests(unittest.TestCase):
    def test_builds_resolved_plan(self):
        plan = build_remap_plan(
            _lineage(),
            _spec(),
        )
        self.assertEqual(plan["class_count"], 1)
        self.assertEqual(
            plan["classes"][0]["source_internal_name"],
            "rs/a",
        )
        self.assertEqual(
            plan["classes"][0]["target_internal_name"],
            "recovered/client/Alpha",
        )

    def test_rejects_collision_with_existing_class(self):
        with self.assertRaises(RemapPlanError):
            build_remap_plan(
                _lineage(),
                _spec("rs/b"),
            )

    def test_rejects_dotted_target(self):
        with self.assertRaises(RemapPlanError):
            build_remap_plan(
                _lineage(),
                _spec("recovered.client.Alpha"),
            )

    def test_rejects_reserved_package(self):
        with self.assertRaises(RemapPlanError):
            build_remap_plan(
                _lineage(),
                _spec("java/lang/Alpha"),
            )

    def test_risk_scan_finds_package_resources(self):
        plan = build_remap_plan(
            _lineage(),
            _spec(),
        )
        report = remap_risk_scan(
            _index(),
            plan,
        )
        self.assertEqual(
            report["summary"][
                "package_resource_hit_count"
            ],
            1,
        )
        self.assertTrue(
            report["summary"][
                "manifest_requires_review"
            ]
        )


if __name__ == "__main__":
    unittest.main()

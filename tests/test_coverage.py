import unittest

from spk_recovery.coverage import build_coverage_report


def class_lineage():
    def cls(i, status):
        return {
            "logical_id": f"CLIENT_CLASS_{i:06d}",
            "semantic_name": None if status == "UNKNOWN" else f"Name{i}",
            "semantic_status": status,
            "semantic_confidence": 0.0 if status == "UNKNOWN" else 0.9,
            "lineage": [{
                "build_id": "v308",
                "internal_name": f"rs/{i}",
                "entry_path": f"rs/{i}.class",
                "entry_sha256": "b" * 64,
                "structural_sha256": "c" * 64,
                "relation": "BASELINE",
                "confidence": 1.0,
                "provenance": [],
            }],
            "semantic_provenance": [] if status == "UNKNOWN" else [{"source": "test"}],
        }
    return {
        "schema_version": 1,
        "namespace": "spawnpk-client",
        "id_format": "CLIENT_CLASS_%06d",
        "baseline_build_id": "v308",
        "builds": [{
            "build_id": "v308",
            "build_number": 308,
            "sha256": "a" * 64,
            "source_name": "client.jar",
            "authority": "EXACT_CURRENT_CLIENT",
        }],
        "classes": [cls(1, "ACCEPTED"), cls(2, "CANDIDATE"), cls(3, "UNKNOWN")],
        "unresolved": [],
    }


def member_lineage():
    def member(mid, owner, kind, status, name, desc):
        return {
            "member_id": mid,
            "owner_logical_id": owner,
            "kind": kind,
            "semantic_name": None if status == "UNKNOWN" else "Readable" + mid[-1],
            "semantic_status": status,
            "semantic_confidence": 0.0 if status == "UNKNOWN" else 0.9,
            "lineage": [{
                "build_id": "v308",
                "owner_internal_name": "rs/1",
                "name": name,
                "descriptor": desc,
                "access": 1,
                "relation": "BASELINE",
                "confidence": 1.0,
                "provenance": [],
            }],
            "semantic_provenance": [] if status == "UNKNOWN" else [{"source": "test"}],
        }
    return {
        "schema_version": 1,
        "kind": "member_lineage",
        "class_namespace": "spawnpk-client",
        "baseline_build_id": "v308",
        "source_sha256": "a" * 64,
        "members": [
            member("CLIENT_FIELD_000001", "CLIENT_CLASS_000001", "field", "ACCEPTED", "a", "I"),
            member("CLIENT_FIELD_000002", "CLIENT_CLASS_000001", "field", "UNKNOWN", "b", "I"),
            member("CLIENT_METHOD_000001", "CLIENT_CLASS_000001", "method", "CANDIDATE", "a", "()V"),
            member("CLIENT_METHOD_000002", "CLIENT_CLASS_000001", "method", "UNKNOWN", "b", "()V"),
        ],
        "unresolved": [],
    }


class CoverageTests(unittest.TestCase):
    def test_statuses_are_not_conflated(self):
        report = build_coverage_report(class_lineage(), member_lineage(), build_id="v308")
        self.assertEqual(report["summary"]["classes"]["accepted"], 1)
        self.assertEqual(report["summary"]["classes"]["candidate"], 1)
        self.assertEqual(report["summary"]["classes"]["unknown"], 1)
        self.assertEqual(report["summary"]["fields"]["accepted"], 1)
        self.assertEqual(report["summary"]["methods"]["candidate"], 1)
        self.assertEqual(report["overall"]["accepted"], 2)
        self.assertEqual(report["overall"]["candidate"], 2)
        self.assertEqual(report["overall"]["entities_total"], 7)


if __name__ == "__main__":
    unittest.main()

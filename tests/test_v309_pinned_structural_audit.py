from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import warnings
from zipfile import ZIP_DEFLATED, ZipFile

from spk_recovery.classfile import parse_class
import spk_recovery.v309_pinned_structural_audit as audit


def _u2(v):
    return struct.pack(">H", v)


def _u4(v):
    return struct.pack(">I", v)


def _utf8(v):
    raw = v.encode("utf-8")
    return b"\x01" + _u2(len(raw)) + raw


def _class(index):
    return b"\x07" + _u2(index)


def _minimal_class():
    cp = [_utf8("SyntheticPrivateClass"), _class(1),
          _utf8("java/lang/Object"), _class(3)]
    return (
        _u4(0xCAFEBABE) + _u2(0) + _u2(52)
        + _u2(5) + b"".join(cp)
        + _u2(0x21) + _u2(2) + _u2(4)
        + _u2(0) + _u2(0) + _u2(0) + _u2(0)
    )


def _record(data):
    return {
        "build_id": "v308",
        "entry_path": "SyntheticPrivateClass.class",
        "internal_name": "SyntheticPrivateClass",
        "entry_sha256": hashlib.sha256(data).hexdigest(),
        "structural_sha256": parse_class(data).structural_sha256(),
    }


class PinnedStructuralAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = _minimal_class()
        self.record = _record(self.raw)

    def _jar(self, name="old.jar", *, duplicate=False, extra=False):
        path = self.root / name
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(path, "w", ZIP_DEFLATED) as z:
                z.writestr("SyntheticPrivateClass.class", self.raw)
                if duplicate:
                    z.writestr("SyntheticPrivateClass.class", self.raw)
                if extra:
                    z.writestr("extra.txt", b"no code leaked")
        return path

    def test_exact_raw_and_structural_fingerprint_pass(self):
        path = self._jar()
        with patch.dict(audit._CLASS_COUNTS, {"v308": 1}):
            result = audit.audit_pinned_jar(
                path, "v308", [self.record], audit.sha256_file(path))
        self.assertEqual(result["pinned_records"], 1)
        self.assertEqual(result["exact_raw_entry_sha_matches"], 1)
        self.assertEqual(result["structural_hash_matches"], 1)
        self.assertEqual(result["structural_hash_drifts"], 0)

    def test_old_structural_fingerprint_drift_is_counted_never_promoted(self):
        path = self._jar()
        record = dict(self.record, structural_sha256="0" * 64)
        with patch.dict(audit._CLASS_COUNTS, {"v308": 1}):
            result = audit.audit_pinned_jar(
                path, "v308", [record], audit.sha256_file(path))
        self.assertEqual(result["structural_hash_matches"], 0)
        self.assertEqual(result["structural_hash_drifts"], 1)

    def test_wrong_exact_jar_and_class_raw_digest_both_fail_closed(self):
        path = self._jar()
        with patch.dict(audit._CLASS_COUNTS, {"v308": 1}):
            with self.assertRaisesRegex(audit.V309PinnedStructuralAuditError, "private exact JAR"):
                audit.audit_pinned_jar(path, "v308", [self.record], "1" * 64)
            record = dict(self.record, entry_sha256="a" * 64)
            with self.assertRaisesRegex(audit.V309PinnedStructuralAuditError, "raw SHA"):
                audit.audit_pinned_jar(
                    path, "v308", [record], audit.sha256_file(path))

    def test_missing_class_and_duplicate_entry_rejected(self):
        path = self._jar()
        with patch.dict(audit._CLASS_COUNTS, {"v308": 1}):
            record = dict(self.record, entry_path="missing.class")
            with self.assertRaisesRegex(audit.V309PinnedStructuralAuditError, "missing pinned"):
                audit.audit_pinned_jar(path, "v308", [record], audit.sha256_file(path))
            duplicate = self._jar("dup.jar", duplicate=True)
            with self.assertRaisesRegex(audit.V309PinnedStructuralAuditError, "duplicate"):
                audit.audit_pinned_jar(
                    duplicate, "v308", [self.record], audit.sha256_file(duplicate))

    def test_extra_nonclass_file_cannot_change_verified_fingerprints(self):
        path = self._jar(extra=True)
        with patch.dict(audit._CLASS_COUNTS, {"v308": 1}):
            result = audit.audit_pinned_jar(
                path, "v308", [self.record], audit.sha256_file(path))
        self.assertEqual(result["complete_jar_class_entries"], 1)
        self.assertEqual(result["structural_hash_matches"], 1)

    def _dual(self, *, new_structural_hash=None):
        old = self._jar("old.jar")
        new = self._jar("new.jar")
        old_digest = audit.sha256_file(old)
        new_digest = audit.sha256_file(new)
        old_record = dict(self.record, build_id="v308")
        new_record = dict(self.record, build_id="v309")
        if new_structural_hash is not None:
            new_record["structural_sha256"] = new_structural_hash
        lineage = {
            "builds": [
                {"build_id": "v308", "sha256": old_digest},
                {"build_id": "v309", "sha256": new_digest},
            ],
            "classes": [
                {"logical_id": "CLIENT_CLASS_000001", "lineage": [
                    old_record, new_record
                ]},
            ],
        }
        frontier = {
            "kind": "v309_recovery_frontier",
            "state": "ACCEPTED_INCOMPLETE",
            "frontier": {"unresolved": 143,
                         "descriptor_identity_guard_rejected": 26},
            "exact_clients": {"v308_sha256": old_digest,
                              "v309_sha256": new_digest},
        }
        return old, new, frontier, lineage

    def test_dual_build_aggregate_no_canonical_mutation(self):
        old, new, frontier, lineage = self._dual()
        before = repr((frontier, lineage))
        with patch.dict(audit._CLASS_COUNTS, {"v308": 1, "v309": 1}):
            with patch.dict(audit._LINEAGE_COUNTS, {"v308": 1, "v309": 1}):
                with patch.object(audit, "validate_lineage"):
                    result = audit.build_v309_pinned_structural_audit(
                        frontier, lineage, old, new)
        self.assertEqual(result["summary"]["structural_hash_matches"], 2)
        self.assertEqual(result["summary"]["structural_hash_drifts"], 0)
        self.assertEqual(result["summary"]["canonical_unresolved_field_relationships"], 143)
        self.assertEqual(result["summary"]["canonical_class_identities_accepted"], 0)
        self.assertEqual(before, repr((frontier, lineage)))
        # Class-path names, literal bytes, actual entry hashes are not emitted.
        import json
        public = json.dumps(result)
        self.assertNotIn("SyntheticPrivateClass", public)
        self.assertNotIn(self.record["entry_sha256"], public)

    def test_dual_drift_state_is_explicit_veto_not_accepted(self):
        old, new, frontier, lineage = self._dual(new_structural_hash="f" * 64)
        with patch.dict(audit._CLASS_COUNTS, {"v308": 1, "v309": 1}):
            with patch.dict(audit._LINEAGE_COUNTS, {"v308": 1, "v309": 1}):
                with patch.object(audit, "validate_lineage"):
                    result = audit.build_v309_pinned_structural_audit(
                        frontier, lineage, old, new)
        self.assertEqual(result["state"], "STRUCTURAL_FINGERPRINT_DRIFT_REVIEW_VETO")
        self.assertEqual(result["summary"]["structural_hash_drifts"], 1)
        self.assertEqual(result["summary"]["canonical_member_identities_accepted"], 0)

    def test_canonical_lineage_count_drift_rejected(self):
        _, _, frontier, lineage = self._dual()
        with patch.object(audit, "validate_lineage"):
            with self.assertRaisesRegex(audit.V309PinnedStructuralAuditError, "count drift"):
                audit._pinned_class_records(lineage)

    def test_protected_frontier_drift_is_not_ignored(self):
        old, new, frontier, lineage = self._dual()
        frontier["frontier"]["unresolved"] = 142
        with self.assertRaisesRegex(audit.V309PinnedStructuralAuditError, "143/26"):
            audit.build_v309_pinned_structural_audit(
                frontier, lineage, old, new)


if __name__ == "__main__":
    unittest.main()

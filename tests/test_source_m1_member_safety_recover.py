from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from spk_recovery.source_m1_member_safety_recover import (
    EXPECTED_ACCEPTANCE_SHA256,
    EXPECTED_ACCEPTANCE_SIZE,
    EXPECTED_REASON,
    EXPECTED_REPORT_ID,
    EXPECTED_RISK_IDS,
    SourceM1MemberSafetyRecoveryError,
    build_historical_acceptance,
    historical_acceptance_bytes,
)


class SourceM1MemberSafetyRecoveryTests(unittest.TestCase):
    def exact_report_shape(self) -> dict:
        return {
            "schema_version": 1,
            "kind": "member_safety_report",
            "source_sha256": (
                "854f26ff9f134b0317572e7ac1688e6f"
                "40a231d5a4c66f8db5d655b7f45ce7c6"
            ),
            "report_id": EXPECTED_REPORT_ID,
            "members": [
                {"risk_id": risk_id}
                for risk_id in EXPECTED_RISK_IDS
            ],
        }

    def test_historical_recipe_reproduces_exact_archived_bytes(self):
        acceptance = build_historical_acceptance(
            self.exact_report_shape()
        )
        payload = historical_acceptance_bytes(acceptance)

        self.assertEqual(len(payload), EXPECTED_ACCEPTANCE_SIZE)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            EXPECTED_ACCEPTANCE_SHA256,
        )
        self.assertEqual(len(acceptance["allow"]), 10)
        self.assertEqual(
            [row["risk_id"] for row in acceptance["allow"]],
            EXPECTED_RISK_IDS,
        )
        self.assertEqual(
            {row["reason"] for row in acceptance["allow"]},
            {EXPECTED_REASON},
        )

    def test_risk_order_drift_is_refused_before_emission(self):
        report = self.exact_report_shape()
        report["members"][0], report["members"][1] = (
            report["members"][1],
            report["members"][0],
        )

        with self.assertRaisesRegex(
            SourceM1MemberSafetyRecoveryError,
            "risk ordering/identity",
        ):
            build_historical_acceptance(report)

    def test_unknown_report_id_is_never_auto_approved(self):
        report = self.exact_report_shape()
        report["report_id"] = "MEMRISKREVIEW_" + "0" * 20

        with self.assertRaisesRegex(
            SourceM1MemberSafetyRecoveryError,
            "historically reviewed",
        ):
            build_historical_acceptance(report)

    def test_reason_drift_breaks_historical_hash(self):
        acceptance = build_historical_acceptance(
            self.exact_report_shape()
        )
        changed = copy.deepcopy(acceptance)
        changed["allow"][0]["reason"] += " changed"

        with self.assertRaisesRegex(
            SourceM1MemberSafetyRecoveryError,
            "byte size|SHA-256",
        ):
            historical_acceptance_bytes(changed)

    def test_serialization_is_stable_json_with_final_newline(self):
        acceptance = build_historical_acceptance(
            self.exact_report_shape()
        )
        payload = historical_acceptance_bytes(acceptance)
        self.assertTrue(payload.endswith(b"\n"))
        parsed = json.loads(payload.decode("utf-8"))
        self.assertEqual(parsed, acceptance)


if __name__ == "__main__":
    unittest.main()

"""Source-only original-v311 scene method triage and trust-boundary checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

from spk_recovery.scene_member_frontier import (
    MemberFrontierError,
    analyze_original_scene,
    parse_javap_scene,
    sha256_file,
)


def mock_javap(*, grid_methods=42, mutation_methods=22, regular_methods=65):
    lines = ["public final class rs.V {"]
    for i in range(regular_methods):
        lines.extend([
            f"  public void a{i}();",
            "    descriptor: ()V",
            "    Code:",
            "       0: aload_0",
        ])
        if i < grid_methods:
            lines.extend([
                "       1: getfield      #203 // Field i:[[[Lrs/H;",
                "       4: aaload",
            ])
        if i < mutation_methods:
            lines.extend([
                "       5: aastore",
                "       6: putfield      #91 // Field rs/H.r:I",
            ])
        lines.append("       9: return")
    lines.extend([
        "  static {};",
        "    Code:",
        "       0: iconst_0",
        "       1: return",
        "}",
    ])
    return "\n".join(lines)


def jar_fixture(directory: Path):
    jar = directory / "original-fixture.jar"
    scene_bytes = b"synthetic-classfile-fixture-only"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr("rs/V.class", scene_bytes)
    authority = {
        "sha256": sha256_file(jar),
        "build": 311,
        "scene_role_candidate": {
            "scene_class_path": "rs/V.class",
            "scene_class_sha256": hashlib.sha256(scene_bytes).hexdigest(),
        },
    }
    return jar, authority


class SceneMemberFrontierTests(unittest.TestCase):
    def test_complete_method_frontier_and_non_promotion(self):
        report = parse_javap_scene(
            mock_javap(), original_sha="a" * 64, class_sha="b" * 64,
        )
        self.assertEqual(report["observed_class_methods"], 66)
        self.assertEqual(report["grid_referencing_methods"], 42)
        self.assertEqual(report["mutation_review_candidates"], 22)
        self.assertEqual(len(report["methods"]), 42)
        self.assertTrue(report["methods"][0]["possible_mutation_review"])
        self.assertFalse(report["methods"][41]["possible_mutation_review"])
        self.assertFalse(report["bounds_guard_correctness_proven"])
        self.assertFalse(report["cross_build_member_identity_proven"])
        self.assertFalse(report["gameplay_executed"])
        self.assertFalse(report["source_compiled"])
        self.assertNotIn("Code:", json.dumps(report))
        self.assertEqual(len(report["methods"][0]["opcode_sequence_sha256"]), 64)
        self.assertEqual(len(report["methods"][0]["signature_descriptor_sha256"]), 64)

    def test_method_witness_determinism(self):
        a = parse_javap_scene(
            mock_javap(), original_sha="a" * 64, class_sha="b" * 64,
        )
        b = parse_javap_scene(
            mock_javap(), original_sha="a" * 64, class_sha="b" * 64,
        )
        self.assertEqual(a, b)

    def test_refuse_wrong_class_header(self):
        with self.assertRaisesRegex(MemberFrontierError, "CLASS_HEADER_MISMATCH"):
            parse_javap_scene(
                mock_javap().replace("rs.V", "rs.W", 1),
                original_sha="a" * 64, class_sha="b" * 64,
            )

    def test_refuse_incomplete_disassembly(self):
        with self.assertRaisesRegex(MemberFrontierError, "EXPECTED_66_METHODS"):
            parse_javap_scene(
                mock_javap(regular_methods=64),
                original_sha="a" * 64, class_sha="b" * 64,
            )

    def test_refuse_changed_grid_method_census(self):
        with self.assertRaisesRegex(MemberFrontierError, "EXPECTED_42_GRID_METHODS"):
            parse_javap_scene(
                mock_javap(grid_methods=41),
                original_sha="a" * 64, class_sha="b" * 64,
            )

    def test_refuse_changed_mutation_worklist_count(self):
        with self.assertRaisesRegex(
            MemberFrontierError, "EXPECTED_22_MUTATION_REVIEW_CANDIDATES"
        ):
            parse_javap_scene(
                mock_javap(mutation_methods=21),
                original_sha="a" * 64, class_sha="b" * 64,
            )

    def test_exact_jar_authority_refuses_wrong_bytes_before_javap(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, authority = jar_fixture(Path(directory))
            authority["sha256"] = "f" * 64
            with mock.patch("spk_recovery.scene_member_frontier.subprocess.run") as run:
                with self.assertRaisesRegex(MemberFrontierError, "WRONG_ORIGINAL_JAR"):
                    analyze_original_scene(jar, authority)
                run.assert_not_called()

    def test_original_scene_class_sha_refusal_before_javap(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, authority = jar_fixture(Path(directory))
            authority["scene_role_candidate"]["scene_class_sha256"] = "f" * 64
            with mock.patch("spk_recovery.scene_member_frontier.subprocess.run") as run:
                with self.assertRaisesRegex(MemberFrontierError, "SCENE_CLASS_HASH_MISMATCH"):
                    analyze_original_scene(jar, authority)
                run.assert_not_called()

    def test_private_javap_is_argument_vector_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, authority = jar_fixture(Path(directory))
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=mock_javap(), stderr=""
            )
            with mock.patch(
                "spk_recovery.scene_member_frontier.subprocess.run",
                return_value=completed,
            ) as runner:
                report = analyze_original_scene(jar, authority)
            args, kw = runner.call_args
            self.assertEqual(args[0][:2], ["javap", "-classpath"])
            self.assertEqual(args[0][-4:], ["-c", "-p", "-s", "rs.V"])
            self.assertEqual(args[0][2], str(jar))
            self.assertEqual(kw["timeout"], 45)
            self.assertNotIn("shell", kw)
            self.assertFalse(report["cross_build_member_identity_proven"])

    def test_javap_error_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, authority = jar_fixture(Path(directory))
            bad = subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="error")
            with mock.patch(
                "spk_recovery.scene_member_frontier.subprocess.run",
                return_value=bad,
            ):
                with self.assertRaisesRegex(MemberFrontierError, "JAVAP_FAILED"):
                    analyze_original_scene(jar, authority)

    def test_missing_role_authority_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            jar, authority = jar_fixture(Path(directory))
            del authority["scene_role_candidate"]
            with self.assertRaisesRegex(MemberFrontierError, "ROLE_NOT_PINNED"):
                analyze_original_scene(jar, authority)


if __name__ == "__main__":
    unittest.main(verbosity=2)

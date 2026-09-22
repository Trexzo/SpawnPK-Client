from __future__ import annotations

import subprocess
import sys
import unittest


COMMANDS = [
    "index",
    "diff",
    "update-intake",
    "update-transfer-classes",
    "update-transfer-members",
    "update-finalize",
    "update-migrate",
    "lineage-seed",
    "lineage-validate",
    "member-lineage-seed",
    "member-lineage-validate",
    "member-promote-new",
    "semantic-resolve",
    "semantic-accept",
    "lineage-apply-candidates",
    "lineage-promote-new",
    "remap-plan",
    "remap-risk-scan",
    "member-remap-plan",
    "member-safety-validate",
    "member-safety-scan",
    "class-remap",
    "jar-remap",
    "verify-remap",
    "decompile",
]


class CliSurfaceTests(unittest.TestCase):
    def test_all_core_subcommands_have_help(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "spk_recovery.cli",
                        command,
                        "--help",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=(
                        f"{command} --help failed\n"
                        f"stdout:\n{proc.stdout}\n"
                        f"stderr:\n{proc.stderr}"
                    ),
                )


if __name__ == "__main__":
    unittest.main()

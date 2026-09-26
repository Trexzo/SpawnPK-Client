from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


class PyprojectIntegrityTests(unittest.TestCase):
    def test_pyproject_toml_parses_and_console_scripts_are_clean(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "pyproject.toml"
        raw = path.read_text(encoding="utf-8")

        document = tomllib.loads(raw)
        scripts = (
            document.get("project", {})
            .get("scripts", {})
        )

        self.assertIsInstance(scripts, dict)
        self.assertTrue(scripts)

        for name, target in scripts.items():
            self.assertIsInstance(name, str)
            self.assertIsInstance(target, str)
            self.assertNotIn(
                "\\n",
                target,
                f"{name}: literal \\n leaked into console script target",
            )
            self.assertIn(
                ":",
                target,
                f"{name}: console script must be module:function",
            )

    def test_r8r_console_scripts_are_registered_individually(self):
        root = Path(__file__).resolve().parents[1]
        document = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )
        scripts = document["project"]["scripts"]

        self.assertEqual(
            scripts["spk-namespace-collision-proof"],
            "spk_recovery.namespace_collision_proof_cli:main",
        )
        self.assertEqual(
            scripts["spk-namespace-remap-impact"],
            "spk_recovery.namespace_remap_impact_cli:main",
        )
        self.assertEqual(
            scripts["spk-namespace-remap-bundle"],
            "spk_recovery.namespace_remap_bundle_cli:main",
        )


if __name__ == "__main__":
    unittest.main()

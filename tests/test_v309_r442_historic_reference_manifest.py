"""R442 public-only historical manifest verifier regression suite.

All JSON inventories, files and subprocesses are invented; no recovered
private Java source/classes, game client, real history or journals are used.
"""
from __future__ import annotations

from hashlib import sha256
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r441.approved_full_inventory import inventory_digest
from tools.r442 import verify_prior_r421_manifest as r442

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/r425/owner_only_run_r425.ps1"
VERIFY = ROOT / "tools/r442/verify_prior_r421_manifest.py"


class R442HistoricalReference(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="R442-Invented-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / "old-reviewed-R421.json"
        self.source = {
            r442.SOURCE_PATH: r425.PINNED_R421_STORE_SHA,
            "rs/InventedUnrelated.java": "a"*64,
        }
        self.classes = {
            r442.CLASS_PATH: r425.PINNED_R421_STORE_CLASS,
            "rs/InventedUnrelated.class": "b"*64,
        }
        self.data = {
            "schema": r442.SCHEMA,
            "source_inventory": self.source,
            "class_inventory": self.classes,
            "dependency_sha256": {
                "R239_filtered.jar": "c"*64,
                "R218.jar": "d"*64,
            },
            "archive_id": "R421-Reviewed-Archive-2026",
        }
        self.p1 = patch.object(r425, "BASELINE_SOURCE_COUNT", 2)
        self.p2 = patch.object(r425, "BASELINE_CLASS_COUNT", 2)
        self.p1.start()
        self.p2.start()
        self.addCleanup(self.p2.stop)
        self.addCleanup(self.p1.stop)

    def write(self, data=None):
        obj = self.data if data is None else data
        self.file.write_text(json.dumps(obj, sort_keys=True) + "\n",
                             encoding="utf-8")
        return sha256(self.file.read_bytes()).hexdigest()

    def verify(self):
        return r442.read_approved_manifest(self.file, self.write())

    def test_01_valid_prior_reference_derives_exact_r441_hashes(self):
        receipt = self.verify()
        self.assertEqual(receipt["status"],
                         "R442_PRIOR_R421_REFERENCE_BYTES_VERIFIED")
        self.assertEqual(receipt["approved_source_inventory_sha256"],
                         inventory_digest(self.source, "java"))
        self.assertEqual(receipt["approved_class_inventory_sha256"],
                         inventory_digest(self.classes, "class"))
        self.assertEqual(receipt["approved_dependency_a_sha256"], "c"*64)
        self.assertEqual(receipt["approved_dependency_b_sha256"], "d"*64)
        self.assertEqual(receipt["baseline_java_sources"], 2)
        self.assertEqual(receipt["baseline_compiled_classes"], 2)
        self.assertFalse(receipt["reference_origin_independently_verified"])
        self.assertFalse(receipt["release_authorized"])

    def test_02_missing_or_malformed_out_of_band_sha_refused(self):
        self.write()
        for value in ("", "x"*64, "A"*64, "a"*63, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(r442.Refused,
                                            "R442_APPROVED_MANIFEST_SHA_REQUIRED"):
                    r442.read_approved_manifest(self.file, value)

    def test_03_wrong_trusted_sha_cannot_accept_current_manifest(self):
        self.write()
        with self.assertRaisesRegex(r442.Refused,
                                    "R442_APPROVED_MANIFEST_SHA_MISMATCH"):
            r442.read_approved_manifest(self.file, "0"*64)

    def test_04_any_other_java_source_changed_is_rejected_by_old_sha(self):
        old = self.write()
        self.data["source_inventory"]["rs/InventedUnrelated.java"] = "1"*64
        self.write()
        self.assertEqual(len(self.source), 2)
        with self.assertRaisesRegex(r442.Refused,
                                    "R442_APPROVED_MANIFEST_SHA_MISMATCH"):
            r442.read_approved_manifest(self.file, old)

    def test_05_whitespace_reformatting_also_requires_reapproval(self):
        original = self.write()
        self.file.write_text(json.dumps(self.data, indent=2), "utf-8")
        with self.assertRaisesRegex(r442.Refused,
                                    "R442_APPROVED_MANIFEST_SHA_MISMATCH"):
            r442.read_approved_manifest(self.file, original)

    def test_06_duplicate_json_keys_are_refused_even_with_matching_raw_sha(self):
        self.file.write_text(
            '{"schema":"one","schema":"two","source_inventory":{}}',
            "utf-8")
        digest = sha256(self.file.read_bytes()).hexdigest()
        with self.assertRaisesRegex(r442.Refused,
                                    "R442_DUPLICATE_MANIFEST_JSON_KEY"):
            r442.read_approved_manifest(self.file, digest)

    def test_07_wrong_schema_version_or_extra_fields_refused(self):
        for changed in (
            {**self.data, "schema": "wrong-version"},
            {**self.data, "private_source_data": "must not exist"},
            {k: v for k, v in self.data.items() if k != "archive_id"},
        ):
            digest = self.write(changed)
            with self.assertRaisesRegex(
                    r442.Refused, "SCHEMA_MISMATCH|VERSION_MISMATCH"):
                r442.read_approved_manifest(self.file, digest)

    def test_08_reject_unsafe_relative_paths_case_collisions_and_suffix(self):
        for name in ("../secret.java", "/absolute.java", "./file.java",
                     "rs\\bad.java", "rs//bad.java", "rs/bad.class",
                     "rs/./bad.java", "rs/a/../bad.java"):
            altered = {
                **self.data,
                "source_inventory": {
                    r442.SOURCE_PATH: r425.PINNED_R421_STORE_SHA,
                    name: "a"*64,
                },
            }
            with self.subTest(name=name):
                digest = self.write(altered)
                with self.assertRaisesRegex(r442.Refused,
                                            "INVALID_REFERENCE_RELATIVE_PATH"):
                    r442.read_approved_manifest(self.file, digest)
        collision = {
            **self.data,
            "source_inventory": {
                r442.SOURCE_PATH: r425.PINNED_R421_STORE_SHA,
                "rs/TEST.java": "a"*64,
                "rs/test.java": "b"*64,
            },
        }
        with patch.object(r425, "BASELINE_SOURCE_COUNT", 3):
            with self.assertRaisesRegex(r442.Refused,
                                        "R442_REFERENCE_CASE_COLLISION"):
                r442.read_approved_manifest(self.file, self.write(collision))

    def test_09_exact_pinned_store_java_and_class_required(self):
        changed_source = {
            **self.data,
            "source_inventory": {**self.source, r442.SOURCE_PATH: "f"*64},
        }
        changed_class = {
            **self.data,
            "class_inventory": {**self.classes, r442.CLASS_PATH: "e"*64},
        }
        for item, code in (
            (changed_source, "PINNED_R421_SOURCE"),
            (changed_class, "PINNED_R421_CLASS"),
        ):
            with self.subTest(code=code):
                with self.assertRaisesRegex(r442.Refused, code):
                    r442.read_approved_manifest(self.file, self.write(item))

    def test_10_wrong_counts_or_invalid_member_shas_refused(self):
        missing = {
            **self.data,
            "source_inventory": {r442.SOURCE_PATH: r425.PINNED_R421_STORE_SHA},
        }
        with self.assertRaisesRegex(r442.Refused,
                                    "R442_REFERENCE_JAVA_COUNT_MISMATCH"):
            r442.read_approved_manifest(self.file, self.write(missing))
        wrong_sha = {
            **self.data,
            "class_inventory": {**self.classes, "rs/InventedUnrelated.class": "ABC"},
        }
        with self.assertRaisesRegex(r442.Refused,
                                    "R442_INVALID_REFERENCE_FILE_SHA"):
            r442.read_approved_manifest(self.file, self.write(wrong_sha))

    def test_11_invalid_dependencies_and_archive_reference_refused(self):
        for altered, match in (
            ({**self.data, "dependency_sha256": {"x.jar":"e"*64}},
             "DEPENDENCY_REFERENCE_SET"),
            ({**self.data, "dependency_sha256": {
                "R239_filtered.jar":"c"*64, "R218.jar":"c"*64}},
             "IDENTICAL_DEPENDENCIES"),
            ({**self.data, "archive_id":" "}, "INVALID_ARCHIVE_REFERENCE_ID"),
        ):
            with self.subTest(match=match):
                with self.assertRaisesRegex(r442.Refused, match):
                    r442.read_approved_manifest(self.file, self.write(altered))

    def test_12_manifest_size_symlink_and_missing_file_rejected(self):
        with self.assertRaisesRegex(r442.Refused, "MANIFEST_MISSING"):
            r442.read_approved_manifest(self.file, "1"*64)
        self.file.write_bytes(b"a" * (r442.MAX_MANIFEST_BYTES+1))
        with self.assertRaisesRegex(r442.Refused, "MANIFEST_SIZE_REFUSED"):
            r442.read_approved_manifest(
                self.file, sha256(self.file.read_bytes()).hexdigest())
        target = self.root / "real.json"
        target.write_text("{}", "utf-8")
        symlink = self.root / "linked.json"
        try:
            symlink.symlink_to(target)
        except (OSError, NotImplementedError):
            return  # unavailable on some Windows hosts
        with self.assertRaisesRegex(r442.Refused, "MANIFEST_NOT_REGULAR"):
            r442.read_approved_manifest(
                symlink, sha256(target.read_bytes()).hexdigest())

    def test_13_cli_real_python_process_with_full_invented_1277_1394(self):
        # This is a large INVENTED manifest, not a decompiled client.
        sources = {r442.SOURCE_PATH: r425.PINNED_R421_STORE_SHA}
        classes = {r442.CLASS_PATH: r425.PINNED_R421_STORE_CLASS}
        sources.update({f"rs/invented/Synthetic{i:04d}.java": "a"*64
                        for i in range(1276)})
        classes.update({f"rs/invented/Synthetic{i:04d}.class": "b"*64
                        for i in range(1393)})
        model = {**self.data, "source_inventory": sources,
                 "class_inventory": classes}
        sha = self.write(model)
        before = self.file.read_bytes()
        proc = subprocess.run([
            sys.executable, "-B", str(VERIFY),
            "--manifest-path", str(self.file),
            "--approved-manifest-sha256", sha,
        ], capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        result = json.loads(proc.stdout)
        self.assertEqual(result["approved_source_inventory_sha256"],
                         inventory_digest(sources, "java"))
        self.assertEqual(result["approved_class_inventory_sha256"],
                         inventory_digest(classes, "class"))
        self.assertFalse(result["reference_origin_independently_verified"])
        self.assertFalse(result["release_authorized"])
        self.assertNotIn(str(self.root), proc.stdout)
        self.assertEqual(self.file.read_bytes(), before)

    def test_14_ps1_requires_approved_manifest_before_current_hash(self):
        script = SCRIPT.read_text("utf-8")
        for name in ("ApprovedR421ManifestPath",
                     "ApprovedR421ManifestSha256",
                     "R442_REFERENCE_BASELINE_REFUSED",
                     "verify_prior_r421_manifest.py",
                     "ConvertFrom-Json",
                     "R442_PRIOR_R421_REFERENCE_BYTES_VERIFIED"):
            self.assertIn(name, script)
        self.assertLess(script.index("& $PythonExe -B @referenceArgs"),
                        script.index("$observedAHash = (Get-FileHash"))
        self.assertLess(script.index("& $PythonExe -B @referenceArgs"),
                        script.index("& $PythonExe -B @preflightArgs"))
        self.assertLess(script.index("& $PythonExe -B @preflightArgs"),
                        script.index("& $PythonExe @arguments"))
        self.assertLess(script.index("& $PythonExe @arguments"),
                        script.index("& $PythonExe @secondArgs"))

    def test_15_manual_hash_parameters_cannot_override_prior_reference(self):
        script = SCRIPT.read_text("utf-8")
        self.assertIn("caller-provided SHA disagrees with approved manifest",script)
        self.assertIn("Set-Variable -Name $entry.Key -Value $entry.Value", script)
        self.assertIn("reference_origin_independently_verified -ne $false",script)
        self.assertIn("R425_RELEASE_GATE_REMAINS_CLOSED", script)
        self.assertIn("R432_RELEASE_GATE_REMAINS_CLOSED", script)

    def test_16_verifier_never_writes_a_self_approved_manifest(self):
        code = inspect.getsource(r442)
        self.assertNotIn("write_text(", code)
        self.assertNotIn("write_bytes(", code)
        self.assertNotIn("touch(", code)
        self.assertNotIn("unlink(", code)
        self.assertNotIn("subprocess.run(", code)
        self.assertNotIn("Get-FileHash", code)
        self.assertIn('reference_origin_independently_verified": False', code)


if __name__ == "__main__":
    unittest.main()

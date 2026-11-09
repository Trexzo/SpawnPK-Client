"""R371 public synthetic tests; no private Java, client process or network."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.verify_v309_r371_rename_preservation import (
    verify, Refused, sha, OWNERS, PREVIOUS, CURRENT)

class R371SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.before = {p: ("class Old" + str(i) + " {}\n").encode()
                       for i, p in enumerate(OWNERS)}
        self.before["rs/gui/loadouts/Other.java"] = b"class Other {}\n"
        self.after = {**self.before, **{p: ("class Safe" + str(i) + " {}\n").encode()
                                          for i, p in enumerate(OWNERS)}}
        self.witness = {
            "source_count": 3, "changed_paths": list(OWNERS),
            "previous_owner_sha256": {p: sha(self.before[p]) for p in OWNERS},
            "candidate_owner_sha256": {p: sha(self.after[p]) for p in OWNERS},
            "candidate_jar_sha256": "a" * 64,
            "private_source_release_approved": False,
            "original_game_runtime_tested": False,
            "multi_file_transaction_proven": False,
            "power_loss_durability_tested": False}
        self.write_pair()

    def write_pair(self):
        before = self.dir / "before.zip"
        after = self.dir / "after.zip"
        with ZipFile(before, "w") as z:
            for path, data in self.before.items():
                z.writestr("source/" + path, data)
            z.writestr(PREVIOUS, json.dumps({
                "source_count": len(self.before),
                "source_sha256": {k: sha(v) for k, v in self.before.items()}}))
        self.witness["previous_zip_sha256"] = sha(before.read_bytes())
        with ZipFile(after, "w") as z:
            for path, data in self.after.items():
                z.writestr("source/" + path, data)
            z.writestr(CURRENT, json.dumps({
                "source_count": len(self.after),
                "source_sha256": {k: sha(v) for k, v in self.after.items()},
                "changed_files": list(OWNERS),
                "previous_r370_source_zip_sha256": self.witness["previous_zip_sha256"],
                "same_source_built_jar_sha256": "a" * 64,
                "private_source_release_approved": False,
                "multi_file_transaction": "NOT_IMPLEMENTED",
                "power_loss_durability": "NOT_TESTED",
                "original_client_runtime": "NOT_TESTED"}))
        self.witness["candidate_zip_sha256"] = sha(after.read_bytes())

    def check(self):
        return verify(self.dir / "before.zip", self.dir / "after.zip",
                      self.witness, count=3)

    def test_positive_source_delta(self):
        result = self.check()
        self.assertEqual(result["status"], "R371_PRIVATE_SOURCE_DELTA_VERIFIED")
        self.assertEqual(result["java_sources"], 3)
        self.assertFalse(result["multi_file_transaction_proven"])

    def test_corrupted_previous_archive(self):
        (self.dir / "before.zip").write_bytes(b"fake")
        with self.assertRaises(Refused): self.check()

    def test_corrupted_candidate_archive(self):
        (self.dir / "after.zip").write_bytes(b"fake")
        with self.assertRaises(Refused): self.check()

    def test_extra_source_drift(self):
        self.after["rs/gui/loadouts/Other.java"] += b" // drift"
        self.write_pair()
        with self.assertRaisesRegex(Refused, "UNEXPECTED_SOURCE_DELTA"): self.check()

    def test_missing_owner(self):
        self.after.pop(OWNERS[0])
        self.write_pair()
        with self.assertRaises(Refused): self.check()

    def test_wrong_owner_digest(self):
        self.witness["candidate_owner_sha256"][OWNERS[0]] = "0" * 64
        with self.assertRaises(Refused): self.check()

    def test_wrong_jar_digest(self):
        self.witness["candidate_jar_sha256"] = "not-sha256"
        with self.assertRaisesRegex(Refused, "INVALID_WITNESS"): self.check()

    def test_private_release_claim(self):
        self.witness["private_source_release_approved"] = True
        with self.assertRaisesRegex(Refused, "INVALID_WITNESS"): self.check()

    def test_game_runtime_claim(self):
        self.witness["original_game_runtime_tested"] = True
        with self.assertRaisesRegex(Refused, "INVALID_WITNESS"): self.check()

    def test_transaction_claim(self):
        self.witness["multi_file_transaction_proven"] = True
        with self.assertRaisesRegex(Refused, "INVALID_WITNESS"): self.check()

    def test_durability_claim(self):
        self.witness["power_loss_durability_tested"] = True
        with self.assertRaisesRegex(Refused, "INVALID_WITNESS"): self.check()

    def test_unexpected_witness_key(self):
        self.witness["permit_live_client"] = True
        with self.assertRaisesRegex(Refused, "UNEXPECTED_WITNESS_SCHEMA"): self.check()

    def test_source_count_drift(self):
        self.witness["source_count"] = 4
        with self.assertRaisesRegex(Refused, "INVALID_WITNESS"): self.check()

    def test_wrong_changed_path_set(self):
        self.witness["changed_paths"] = list(OWNERS[:1])
        with self.assertRaisesRegex(Refused, "INVALID_WITNESS"): self.check()

    def test_symlinked_archive(self):
        link = self.dir / "redirect.zip"
        try: link.symlink_to(self.dir / "after.zip")
        except (OSError, NotImplementedError): self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(Refused, "INVALID_PRIVATE_ARCHIVE"):
            verify(self.dir / "before.zip", link, self.witness, count=3)

    def test_changed_candidate_manifest(self):
        p = self.dir / "after.zip"
        with ZipFile(p) as z: content = {n: z.read(n) for n in z.namelist()}
        manifest = json.loads(content[CURRENT])
        manifest["multi_file_transaction"] = "COMPLETE"
        content[CURRENT] = json.dumps(manifest).encode()
        with ZipFile(p, "w") as z:
            for n, data in content.items(): z.writestr(n, data)
        self.witness["candidate_zip_sha256"] = sha(p.read_bytes())
        with self.assertRaisesRegex(Refused, "OWNER_OR_RELEASE_GATE_MISMATCH"):
            self.check()

    def test_original_source_added(self):
        self.after["rs/gui/loadouts/Other.java"] = b"class Other {int changed;}"
        self.write_pair()
        with self.assertRaisesRegex(Refused, "UNEXPECTED_SOURCE_DELTA"): self.check()

if __name__ == "__main__":
    unittest.main(verbosity=2)

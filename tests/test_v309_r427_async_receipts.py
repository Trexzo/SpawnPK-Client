"""R427 independently authored Java11 async-delete receipt model tests.

This suite does NOT load, patch, launch, or execute any private SpawnPK source,
class, JAR, profile or real loot history. Java tests run with invented scratch
files and the actual Swing EDT on both Windows and Ubuntu.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "fixtures/r427/R427AsyncDeleteCoordinator.java"
HARNESS = ROOT / "fixtures/r427/R427AsyncDeleteHarness.java"


class R427ReceiptBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("java"):
            raise RuntimeError("JDK 11+ is required for R427")
        cls.class_dir = tempfile.TemporaryDirectory(prefix="r427-class-tree-")
        cls.compiled = Path(cls.class_dir.name)
        command = ["javac", "--release", "11", "-proc:none",
                   "-encoding", "UTF-8", "-d", str(cls.compiled),
                   str(MODEL), str(HARNESS)]
        p = subprocess.run(command, capture_output=True, text=True, timeout=45)
        if p.returncode:
            raise RuntimeError("R427_JAVA_COMPILE_FAILURE\n" + p.stderr[-2200:])

    @classmethod
    def tearDownClass(cls):
        cls.class_dir.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            prefix="R427-Synthetic-", dir=tempfile.gettempdir())
        self.addCleanup(self.tmp.cleanup)
        self.scratch = Path(self.tmp.name)

    def run_scenario(self, scenario: str) -> None:
        command = ["java", "-Xmx256m",
                   "-Djava.awt.headless=true",
                   "-Djava.io.tmpdir=" + tempfile.gettempdir(),
                   "-cp", str(self.compiled),
                   "rs.plugins.loottracker.R427AsyncDeleteHarness",
                   scenario, str(self.scratch)]
        p = subprocess.run(command, capture_output=True, text=True, timeout=35)
        self.assertEqual(p.returncode, 0,
                         "Scenario " + scenario + "\n" + p.stdout + "\n" + p.stderr)
        expected = "R427_" + scenario.upper().replace("-", "_") + "_PASS"
        self.assertIn(expected, p.stdout)
        m = re.search(r"assertions=(\d+)", p.stdout)
        self.assertIsNotNone(m, p.stdout)
        self.assertGreaterEqual(int(m.group(1)), 2)

    def test_01_confirmed_receipt_requires_durability_and_edt_apply(self):
        self.run_scenario("confirmed")

    def test_02_stable_ids_copied_and_unmodifiable(self):
        self.run_scenario("immutable")

    def test_03_second_delete_rejected_while_first_in_flight(self):
        self.run_scenario("single-flight")

    def test_04_definite_refusal_never_removes_ui_rows(self):
        self.run_scenario("refused")

    def test_05_uncertain_result_quarantines_and_prohibits_retry(self):
        self.run_scenario("uncertain")

    def test_06_post_write_exception_is_uncertain_and_quarantined(self):
        self.run_scenario("post-write-failure")

    def test_07_changed_panel_version_requires_reload_not_stale_remove(self):
        self.run_scenario("version-drift")

    def test_08_old_session_result_cannot_mutate_new_panel(self):
        self.run_scenario("stale-session")

    def test_09_invalidated_session_cannot_enqueue_delete(self):
        self.run_scenario("early-session")

    def test_10_shutdown_drains_commit_before_owner_release_without_edt_wait(self):
        self.run_scenario("close-drains")

    def test_11_no_request_shutdown_is_idempotent_and_off_edt(self):
        self.run_scenario("close-idempotent")

    def test_12_non_edt_requests_or_shutdown_refused(self):
        self.run_scenario("off-edt-refusal")

    def test_13_intent_shape_and_key_safety(self):
        self.run_scenario("validation")

    def test_14_real_temp_fsynced_receipt_before_confirmed_ui(self):
        self.run_scenario("synthetic-file")

    def test_15_no_genuine_private_client_dependencies(self):
        text = MODEL.read_text(encoding="utf-8")
        self.assertNotIn("import rs.", text)
        self.assertNotIn("RuneLite", text)
        self.assertNotIn("Class307", text)
        self.assertNotIn("LootHistoryStore", text)
        self.assertNotIn("client.jar", text)

    def test_16_only_one_serial_worker_not_unbounded_threads(self):
        text = MODEL.read_text(encoding="utf-8")
        self.assertIn("Executors.newSingleThreadExecutor(factory)", text)
        self.assertIn("pending.compareAndSet(false, true)", text)
        self.assertIn("io.shutdown();", text)
        self.assertNotIn("shutdownNow(", text)

    def test_17_no_blind_retry_or_optimistic_panel_removal(self):
        text = MODEL.read_text(encoding="utf-8")
        self.assertIn("case UNCERTAIN:", text)
        self.assertIn("quarantined.set(true)", text)
        self.assertIn("case CONFIRMED:", text)
        self.assertNotIn("Thread.sleep(", text)
        self.assertNotIn("Retry", text.replace("retry.", ""))

    def test_18_receipt_requires_current_ui_version(self):
        text = MODEL.read_text(encoding="utf-8")
        self.assertIn("view.version() == request.uiVersion", text)
        self.assertIn("view.confirmedButNeedsReload(request)", text)
        self.assertIn("session.accepts(request.sessionEpoch)", text)

    def test_19_close_does_not_release_os_lease_on_edt(self):
        text = MODEL.read_text(encoding="utf-8")
        self.assertIn("io.execute(() -> {", text)
        self.assertIn("store.closeOwner();", text)
        self.assertIn("CompletableFuture<Void> closeAsync()", text)
        self.assertIn("requireEdt();", text)

    def test_20_file_fixture_is_restricted_to_direct_temp_child(self):
        text = HARNESS.read_text(encoding="utf-8")
        self.assertIn('startsWith("R427-Synthetic-")', text)
        self.assertIn("root.getParent().equals(tmp)", text)
        self.assertIn("R427_REFUSED_NON_SYNTHETIC_ROOT", text)


if __name__ == "__main__":
    unittest.main()

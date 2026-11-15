"""R428 Java11 real Swing shutdown deadline / fault-injection acceptance.

Synthetic-only: independently authored coordinator and fake Store; no private
SpawnPK Java, game client, actual cache, player history, or JAR is used.
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


class R428BoundedShutdownAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac") or not shutil.which("java"):
            raise RuntimeError("Java JDK11+ required")
        cls.class_tree = tempfile.TemporaryDirectory(prefix="R428-Public-Class-")
        cls.compiled = Path(cls.class_tree.name)
        cmd = [
            "javac", "--release", "11", "-proc:none", "-encoding", "UTF-8",
            "-d", str(cls.compiled), str(MODEL), str(HARNESS)
        ]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
        if run.returncode != 0:
            raise RuntimeError("R428_JAVA11_COMPILATION_FAILED: " +
                               run.stderr[-2000:])

    @classmethod
    def tearDownClass(cls):
        cls.class_tree.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="R427-Synthetic-", dir=tempfile.gettempdir())
        self.addCleanup(self.temp.cleanup)

    def scenario(self, name: str):
        cmd = [
            "java", "-Xmx256m", "-Djava.awt.headless=true",
            "-Djava.io.tmpdir=" + tempfile.gettempdir(),
            "-cp", str(self.compiled),
            "rs.plugins.loottracker.R427AsyncDeleteHarness",
            name, self.temp.name
        ]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        self.assertEqual(
            run.returncode, 0,
            "R428_"+name+"\nSTDOUT:\n"+run.stdout+"\nSTDERR:\n"+run.stderr)
        expected = "R427_"+name.upper().replace("-", "_")+"_PASS"
        self.assertIn(expected, run.stdout)
        match = re.search(r"assertions=(\d+)", run.stdout)
        self.assertIsNotNone(match, run.stdout)
        self.assertGreaterEqual(int(match.group(1)), 2)

    def test_01_overdue_observation_never_forcibly_releases_owner(self):
        self.scenario("close-deadline")

    def test_02_immediately_available_release_receipt(self):
        self.scenario("close-observed")

    def test_03_owner_release_exception_never_confirms_release(self):
        self.scenario("close-exception")

    def test_04_owner_release_assertion_error_never_confirms_release(self):
        self.scenario("close-error")

    def test_05_disk_assertion_error_after_fake_write_quarantines(self):
        self.scenario("post-write-error")

    def test_06_invalid_or_missing_deadline_refused_before_shutdown(self):
        self.scenario("invalid-deadline")

    def test_07_deadline_is_a_status_not_a_cancellation(self):
        s=MODEL.read_text(encoding="utf-8")
        self.assertIn("UNCONFIRMED_AT_DEADLINE",s)
        self.assertIn("closeWithDeadline(long duration, TimeUnit unit)",s)
        section=s.split("closeWithDeadline(long duration, TimeUnit unit)")[1]
        section=section.split("\n    boolean isPending()",1)[0]
        self.assertNotIn("store.closeOwner()",section)
        self.assertNotIn("shutdownNow()",section)
        self.assertNotIn("Thread.interrupt()",section)
        self.assertNotIn("closeFuture.complete(null)",section)
        self.assertIn("CompletableFuture.delayedExecutor",section)
        self.assertIn("SwingUtilities.invokeLater",section)

    def test_08_owner_close_error_quarantines_and_reports_uncertainty(self):
        s=MODEL.read_text(encoding="utf-8")
        self.assertIn("catch (Throwable releaseError)",s)
        self.assertIn("closeFuture.completeExceptionally(releaseError)",s)
        self.assertIn("quarantined.set(true)",s)

    def test_09_commit_error_cannot_be_marked_confirmed(self):
        s=MODEL.read_text(encoding="utf-8")
        self.assertIn("catch (Throwable ambiguousDiskOutcome)",s)
        self.assertIn("outcome = Outcome.UNCERTAIN",s)
        self.assertIn("case UNCERTAIN:",s)

    def test_10_watcher_completion_is_on_real_swing_edt(self):
        s=MODEL.read_text(encoding="utf-8")
        segment=s.split("closeWithDeadline(long duration, TimeUnit unit)")[1]
        segment=segment.split("\n    boolean isPending()",1)[0]
        self.assertIn("Consumer<CloseObservation> onEdt", segment)
        self.assertIn("reportCloseObservationOnEdt(", segment)
        self.assertIn("SwingUtilities.invokeLater", segment)
        self.assertIn("if (result.complete(outcome))", segment)
        self.assertIn("observer.accept(outcome)", segment)

    def test_11_existing_r427_worker_still_non_daemon(self):
        s=MODEL.read_text(encoding="utf-8")
        self.assertIn("t.setDaemon(false)",s)
        self.assertNotIn("t.setDaemon(true)",s)

    def test_12_original_cleanup_and_real_history_unreferenced(self):
        s=MODEL.read_text(encoding="utf-8")
        self.assertNotIn("import rs.",s)
        self.assertNotIn("LootHistoryStore",s)
        self.assertNotIn("loot-history.json",s)
        self.assertNotIn("client.jar",s)


if __name__=="__main__":
    unittest.main()

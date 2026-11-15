"""R426 FULL mock source->R424 patch->javac->class diff->actual harness test.

This test runs the production R425 Python orchestration unmodified (except
test-local monkeypatched PRIVATE SHA/count constants for invented fixtures).
NO real/private SpawnPK code, class, history, JAR, or account data is used.
The test exists to catch orchestration defects before owner's isolated PC run.
"""
from __future__ import annotations

from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
import uuid
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

from tools.r424 import prepare_private_legacy_cleanup_patch as patcher
from tools.r425 import compile_and_accept_private_overlay as runner

ROOT = Path(__file__).resolve().parents[1]
STORE = runner.STORE
HELPER = ROOT / "tests/fixtures/r424/LootLegacyCleanupR424.java"
HARNESS = ROOT / "tests/fixtures/r425/R425ActualPrivateOverlayAcceptance.java"

# This is an INVENTED two-file mini-client, specifically not recovered source.
FAKE_STORE = """
package rs.plugins.loottracker;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;

final class LootHistoryStore {
    static final String FILE_NAME = "loot-history.json";
    enum R411StageState { CLEAR, UNSAFE }
    static final class TestLog {
        void warn(String text, Object data) { }
        void info(String text, Object data) { }
    }
    private static final TestLog log = new TestLog();
    private final File file;
    private volatile boolean owner;

    LootHistoryStore(String root) {
        this.file = new File(root, FILE_NAME);
    }

    boolean r421PrepareHistoryDirectoryForLease() {
        Path path = file.getParentFile().toPath();
        try {
            Files.createDirectory(path);
            return true;
        } catch (java.nio.file.FileAlreadyExistsException already) {
            return Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS) &&
                   !Files.isSymbolicLink(path);
        } catch (IOException failed) {
            return false;
        }
    }
    synchronized boolean r419ActivateOwner() {
        if (owner) return true;
        if (!file.getParentFile().isDirectory()) return false;
        owner = true;
        return true;
    }
    synchronized void r419CloseOwner() { owner = false; }
    R411StageState r411StageState() {
        for (String marker : new String[] {
            "loot-history.json.tmp", "loot-history.delete.intent",
            "loot-history.delete.intent.tmp", "loot-history.delete.ack",
            "loot-history.delete.ack.tmp"}) {
            if (Files.exists(file.getParentFile().toPath().resolve(marker),
                             LinkOption.NOFOLLOW_LINKS))
                return R411StageState.UNSAFE;
        }
        return R411StageState.CLEAR;
    }
    boolean r411RefuseUnresolvedStage(String reason) {
        return r411StageState() != R411StageState.CLEAR;
    }
    void deleteStale() {
        if (owner) r419DeleteStaleLeased();
    }

    private void r419DeleteStaleLeased()
    {
        if (r411RefuseUnresolvedStage("legacy cleanup"))
        {
            return;
        }
        File parent = file.getParentFile();
        if (parent == null || !parent.isDirectory())
        {
            return;
        }
        File parts = new File(parent, "loot-history");
        if (parts.exists())
        {
            if (deleteTree(parts))
            {
                log.info("old synthetic tree removed", parts);
            }
        }
        File seenKeys = new File(parent, "loot-keys-seen.txt");
        if (seenKeys.exists() && !seenKeys.delete())
        {
            log.warn("old synthetic keys delete refused", seenKeys);
        }
    }

    /**
     * Deletes a file or a directory and everything in it.
     *
     * @return true when all synthetic entries were removed
     */
    private static boolean deleteTree(File file)
    {
        File[] children = file.listFiles();
        if (children != null)
        {
            for (File child : children)
            {
                if (!deleteTree(child)) return false;
            }
        }
        try
        {
            Files.deleteIfExists(file.toPath());
            return true;
        }
        catch (IOException ignored)
        {
            return false;
        }
    }
}
"""

OTHER = """package rs.plugins.loottracker;
final class SyntheticUnrelated { static int value() { return 42; } }
"""


def sha(data: bytes) -> str:
    return sha256(data).hexdigest()


class R426FullSyntheticPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javac = shutil.which("javac")
        cls.java = shutil.which("java")
        if not cls.javac or not cls.java:
            raise RuntimeError("R426 requires JDK11+")
        if not HELPER.is_file() or not HARNESS.is_file():
            raise RuntimeError("public-only helper/harness missing")

    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="R426-Full-Mock-")
        self.addCleanup(self.workspace.cleanup)
        base = Path(self.workspace.name)
        isolated = (base / "SpawnPK-R386-Isolated-Acceptance" /
                    "R421-Private-NoFollow-Cache-Directory-Preflight")
        self.source = isolated / "Source-Candidate-R421" / "source"
        self.prior_classes = isolated / "R421-Compiled-Classes"
        path = self.source / STORE
        path.parent.mkdir(parents=True)
        path.write_bytes(FAKE_STORE.encode("utf-8"))
        (path.parent / "SyntheticUnrelated.java").write_text(OTHER, encoding="utf-8")
        self.prior_classes.mkdir()
        build = subprocess.run(
            [self.javac, "--release", "11", "-proc:none",
             "-d", str(self.prior_classes),
             str(path), str(path.parent/"SyntheticUnrelated.java")],
            capture_output=True, text=True, timeout=50)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.baseline_store = sha(path.read_bytes())
        self.baseline_class = runner.hash_file(
            self.prior_classes / runner.EXPECTED_CHANGED_EXISTING_CLASS)
        self.class_count = len(runner.sha_inventory(self.prior_classes, ".class"))
        self.assertEqual(len(list(self.source.rglob("*.java"))), 2)
        self.assertEqual(self.class_count, 4)

        deps = base / "safe-empty-jars"
        deps.mkdir()
        self.deps = []
        for n in ("R239_filtered.jar", "R218.jar"):
            p = deps / n
            with zipfile.ZipFile(p, "w") as archive:
                archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            self.deps.append(p)
        self.args = SimpleNamespace(
            prior_source_root=self.source,
            prior_classes_root=self.prior_classes,
            public_helper_source=HELPER,
            public_acceptance_source=HARNESS,
            dependency_a=self.deps[0], dependency_b=self.deps[1],
            dependency_a_sha256=runner.hash_file(self.deps[0]),
            dependency_b_sha256=runner.hash_file(self.deps[1]),
            javac=Path(self.javac),
            java=Path(self.java),
            fresh_temp_destination=Path(tempfile.gettempdir()) /
                ("R424-Private-Candidate-R425-FullMock-"+uuid.uuid4().hex),
        )
        self.addCleanup(self.cleanup_candidate)

    def cleanup_candidate(self):
        p = self.args.fresh_temp_destination
        if p.is_dir() and p.parent == Path(tempfile.gettempdir()):
            shutil.rmtree(p)

    def _fixture_pins(self):
        context = ExitStack()
        self.addCleanup(context.close)
        context.enter_context(
            patch.object(patcher, "PINNED_R421_STORE_SHA", self.baseline_store))
        context.enter_context(
            patch.object(patcher, "EXPECTED_SOURCE_COUNT", 2))
        context.enter_context(
            patch.object(runner, "PINNED_R421_STORE_SHA", self.baseline_store))
        context.enter_context(
            patch.object(runner, "PINNED_R421_STORE_CLASS", self.baseline_class))
        context.enter_context(
            patch.object(runner, "BASELINE_SOURCE_COUNT", 2))
        context.enter_context(
            patch.object(runner, "BASELINE_CLASS_COUNT", self.class_count))
        # This test patching is never reachable from the owner-only CLI.
        return context

    def test_01_entire_r425_pipeline_with_real_javac_and_mock_source(self):
        with self._fixture_pins():
            receipt = runner.run(self.args)
        self.assertEqual(receipt["status"],
                         "R425_PRIVATE_OVERLAY_COMPILE_AND_ACTUAL_STORE_PASS")
        self.assertGreaterEqual(
            receipt["actual_private_store"]["real_class_assertions"],39)
        self.assertFalse(receipt["legacy_deletion_enabled"])
        self.assertFalse(receipt["release_authorized"])
        self.assertEqual(receipt["source_scope"]["candidate_sources"],3)
        self.assertEqual(receipt["class_scope"]["candidate_classes"],9)
        self.assertEqual(len(receipt["class_scope"]["added_helper_classes"]),5)
        self.assertEqual(
            receipt["class_scope"]["modified_existing_classes"],
            ["rs/plugins/loottracker/LootHistoryStore.class"])
        self.assertEqual(
            sha((self.source / STORE).read_bytes()),self.baseline_store)
        self.assertEqual(
            runner.hash_file(
                self.prior_classes / runner.EXPECTED_CHANGED_EXISTING_CLASS),
            self.baseline_class)
        result = self.args.fresh_temp_destination / "R425-Final-Private-Acceptance-Receipt.json"
        self.assertTrue(result.is_file())
        self.assertEqual(json.loads(result.read_text())["status"],
                         receipt["status"])

    def test_02_tampered_dependency_after_snapshot_refused(self):
        with self._fixture_pins():
            runner.validate_inputs(self.args)
            original = runner.sha_inventory(self.source, ".java")
            classes = runner.sha_inventory(self.prior_classes, ".class")
            self.deps[0].write_bytes(b"tampered-synthetic-JAR")
            with self.assertRaisesRegex(
                    runner.Refused,"R426_DEPENDENCY_A_CHANGED_DURING_BUILD"):
                runner.verify_unchanged_build_inputs(
                    self.args, original, classes, original, self.source)

    def test_03_tampered_second_dependency_after_snapshot_refused(self):
        with self._fixture_pins():
            runner.validate_inputs(self.args)
            original = runner.sha_inventory(self.source, ".java")
            classes = runner.sha_inventory(self.prior_classes, ".class")
            self.deps[1].write_bytes(b"tampered-synthetic-other-JAR")
            with self.assertRaisesRegex(
                    runner.Refused,"R426_DEPENDENCY_B_CHANGED_DURING_BUILD"):
                runner.verify_unchanged_build_inputs(
                    self.args, original, classes, original, self.source)

    def test_04_tampered_parent_java_source_after_snapshot_refused(self):
        with self._fixture_pins():
            original = runner.sha_inventory(self.source, ".java")
            classes = runner.sha_inventory(self.prior_classes, ".class")
            (self.source/"rs/plugins/loottracker/SyntheticUnrelated.java").write_text(
                OTHER+"\n// synthetic concurrent edit")
            with self.assertRaisesRegex(
                    runner.Refused,"R426_PRIOR_SOURCE_CHANGED_DURING_BUILD"):
                runner.verify_unchanged_build_inputs(
                    self.args, original, classes, original, self.source)

    def test_05_tampered_candidate_java_source_after_snapshot_refused(self):
        with self._fixture_pins():
            original = runner.sha_inventory(self.source, ".java")
            classes = runner.sha_inventory(self.prior_classes, ".class")
            candidate = Path(self.workspace.name)/"fake-candidate"
            shutil.copytree(self.source, candidate)
            candidate_before = runner.sha_inventory(candidate, ".java")
            (candidate/STORE).write_bytes(b"fake changed source")
            with self.assertRaisesRegex(
                    runner.Refused,"R426_CANDIDATE_SOURCES_CHANGED_DURING_BUILD"):
                runner.verify_unchanged_build_inputs(
                    self.args, original, classes, candidate_before, candidate)

    def test_06_tampered_original_class_after_snapshot_refused(self):
        with self._fixture_pins():
            original = runner.sha_inventory(self.source, ".java")
            classes = runner.sha_inventory(self.prior_classes, ".class")
            p=self.prior_classes/"rs/plugins/loottracker/SyntheticUnrelated.class"
            p.write_bytes(b"not a compiled class")
            with self.assertRaisesRegex(
                    runner.Refused,"R426_PRIOR_CLASSES_CHANGED_DURING_BUILD"):
                runner.verify_unchanged_build_inputs(
                    self.args, original, classes, original, self.source)

    def test_07_helper_hash_refusal_retains_owner_input(self):
        with self._fixture_pins():
            self.args.dependency_a_sha256="0"*64
            with self.assertRaisesRegex(runner.Refused,"R425_DEPENDENCY_A_SHA_DRIFT"):
                runner.run(self.args)
        self.assertFalse(self.args.fresh_temp_destination.exists())
        self.assertEqual(sha((self.source/STORE).read_bytes()),self.baseline_store)

    def test_08_running_real_owner_cli_does_not_enable_mock_pin_mode(self):
        # Monkeypatching exists only within this test process; no switches
        # for mock baselines, source counts or release authorization are exposed.
        cli = (ROOT/"tools/r425/compile_and_accept_private_overlay.py").read_text()
        self.assertNotIn("--mock-pin",cli)
        self.assertNotIn("--skip-source-sha",cli)
        self.assertNotIn("--authorize-deploy",cli)
        self.assertNotIn("--skip-acceptance",cli)
        self.assertIn("PINNED_R421_STORE_CLASS",cli)


if __name__ == "__main__":
    unittest.main()

"""R394 synthetic static startup chain tests and headless Swing ordering fixture."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

TARGET = Path(__file__).resolve().parents[1] / "tools/r394/audit_pre_ui_dependency_chains.py"
spec = importlib.util.spec_from_file_location("r394_pre_ui", TARGET)
r394 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r394)


class R394StaticWitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.zip = self.dir / "synthetic-kit.zip"
        self.samples = {
            "bootstrap": """
                class Class255 {
                  public void method3355(){
                    x.loadPlugins(); x.startPlugins(); y.show();
                  }
                }
            """,
            "plugin_manager": """
                class PluginManager {
                  public void startPlugins(){
                    SwingUtilities.invokeAndWait(() -> {this.startPlugin(plugin);});
                  }
                  public boolean startPlugin(){
                    plugin.startUp();
                    return true;
                  }
                }
            """,
            "client_ui": """
                class ClientUI {
                  public void show(){ SwingUtilities.invokeLater(this::showFrame); }
                }
            """,
            "loadouts_plugin": """
                class LoadoutsPlugin {
                  protected void startUp(){ this.panel=new LoadoutsPanel(); }
                }
            """,
            "loadouts_panel": """
                class LoadoutsPanel {
                  public LoadoutsPanel(){
                    ImageLoader.start();
                    this.store = new LoadoutStore(this);
                    this.store.loadFolder("fixture",true);
                    this.store.writeFolderOrderSettings();
                    new File("fixture").delete();
                    new File("fixture").delete();
                  }
                }
            """,
            "image_loader": """
                class ImageLoader {
                  static ExecutorService field3284 = Executors.newFixedThreadPool(5);
                  static Object[] field3285;
                  public static void start(){
                     var1 = new LoadoutIconWorker();
                     field3284.submit(var1);
                  }
                }
            """,
            "icon_worker": """
                class LoadoutIconWorker {
                  public void run(){ }
                }
            """,
            "loadout_store": """
                class LoadoutStore {
                  public LoadoutList loadFolder(String name,boolean var2){
                    if (!var5.exists() && var2) { var4.delete(); }
                    return null;
                  }
                  public synchronized void writeFolderOrderSettings(){
                    this.writeFolderOrderSettingsWithLock(path,destination);
                  }
                  private void writeFolderOrderSettingsWithLock(Path path,Path destination){
                    Files.newBufferedWriter(path);
                    Files.move(path,destination);
                  }
                }
            """,
            "loot_plugin": """
                class LootTrackerPlugin {
                  protected void startUp(){
                     historyStore = new LootHistoryStore();
                     historyStore.deleteStale();
                     loadHistory();
                  }
                  private void loadHistory(){
                     SwingUtilities.invokeLater(() -> {
                        if (!loaded) historyStore.load();
                     });
                  }
                }
            """,
            "loot_history_store": """
                class LootHistoryStore {
                  private static final long MAX_HISTORY_BYTES = 64L * 1024L * 1024L;
                  void deleteStale(){ deleteTree(parts); seenKeys.delete(); }
                  private static boolean deleteTree(File file){
                      if (deleteTree(child)) { }
                      Files.deleteIfExists(file.toPath());
                      return true;
                  }
                  List<LootTrackerRecord> load(){
                     if (length > MAX_HISTORY_BYTES) return null;
                     Files.newInputStream(file.toPath());
                     GSON.a(reader,Document.class);
                     return null;
                  }
                }
            """,
        }
        self.pack()

    def sources(self):
        return {r394.PATHS[name]: r394._r393.mask_java(text)
                for name, text in self.samples.items()}

    def pack(self):
        with zipfile.ZipFile(self.zip, "w") as z:
            for name, text in self.samples.items():
                z.writestr(r394.PATHS[name], text)

    def digest(self):
        return hashlib.sha256(self.zip.read_bytes()).hexdigest()

    def report(self):
        return r394.report_from_sources(self.sources())

    def test_expected_witnesses_and_closed_gates(self):
        r = self.report()
        self.assertEqual(r["status"], "R394_STATIC_PRE_UI_EDT_IO_WITNESS")
        self.assertTrue(r["bootstrap_plugin_start_precedes_ui_show"])
        self.assertTrue(r["loot_history_file_read_and_json_parse_in_callback"])
        self.assertEqual(r["loot_history_read_max_bytes"], 67108864)
        self.assertEqual(r["loadouts_fixed_executor_workers"], 5)
        self.assertEqual(r["loadouts_panel_constructor_explicit_delete_invocations"], 2)
        self.assertEqual(r["source_references_to_executor_shutdown"], 0)
        for key in ("client_executed", "real_user_data_accessed", "launch_authorized",
                    "isolated_guest_verified", "runtime_freeze_root_cause_proven"):
            self.assertFalse(r[key])

    def test_bootstrap_reordered_refused(self):
        self.samples["bootstrap"] = self.samples["bootstrap"].replace(
            "x.loadPlugins(); x.startPlugins(); y.show();",
            "x.loadPlugins(); y.show(); x.startPlugins();"
        )
        with self.assertRaisesRegex(r394.Refused, "STARTUP_CHAIN_MISSING_OR_REORDERED"):
            self.report()

    def test_swing_invoke_and_wait_required(self):
        self.samples["plugin_manager"] = self.samples["plugin_manager"].replace(
            "SwingUtilities.invokeAndWait", "SwingUtilities.invokeLater")
        with self.assertRaisesRegex(r394.Refused, "STARTUP_CHAIN_MISSING_OR_REORDERED"):
            self.report()

    def test_startup_dispatch_required(self):
        self.samples["plugin_manager"] = self.samples["plugin_manager"].replace(
            "plugin.startUp();", "plugin.doNothing();")
        with self.assertRaisesRegex(r394.Refused, "PLUGIN_STARTUP_DISPATCH_NOT_FOUND"):
            self.report()

    def test_loot_history_edt_callback_required(self):
        self.samples["loot_plugin"] = self.samples["loot_plugin"].replace(
            "SwingUtilities.invokeLater", "SwingUtilities.invokeAndWait")
        with self.assertRaisesRegex(r394.Refused, "STARTUP_CHAIN_MISSING_OR_REORDERED"):
            self.report()

    def test_history_byte_limit_must_be_64_mib(self):
        self.samples["loot_history_store"] = self.samples["loot_history_store"].replace(
            "64L * 1024L * 1024L", "128L * 1024L * 1024L")
        with self.assertRaisesRegex(r394.Refused, "LOOT_HISTORY_BYTE_LIMIT_CHANGED"):
            self.report()

    def test_history_read_api_required(self):
        self.samples["loot_history_store"] = self.samples["loot_history_store"].replace(
            "Files.newInputStream(", "Files.notRead(")
        with self.assertRaisesRegex(r394.Refused, "LOOT_HISTORY_READ_NOT_FOUND"):
            self.report()

    def test_loot_recursive_cleanup_required(self):
        self.samples["loot_history_store"] = self.samples["loot_history_store"].replace(
            "Files.deleteIfExists(", "Files.nop(")
        with self.assertRaisesRegex(r394.Refused, "LOOT_CLEANUP_PATH_CHANGED"):
            self.report()

    def test_loadouts_plugin_panel_required(self):
        self.samples["loadouts_plugin"] = self.samples["loadouts_plugin"].replace(
            "new LoadoutsPanel(", "new UnrelatedPanel(")
        with self.assertRaisesRegex(r394.Refused, "LOADOUTS_PANEL_INIT_MISSING"):
            self.report()

    def test_loadouts_panel_ordering_required(self):
        self.samples["loadouts_panel"] = self.samples["loadouts_panel"].replace(
            "ImageLoader.start();", "ImageLoader.start(); this.store.writeFolderOrderSettings();")
        with self.assertRaisesRegex(r394.Refused, "STARTUP_CHAIN_MISSING_OR_REORDERED"):
            # The added first settings write makes the documented order fail.
            self.report()

    def test_loadouts_delete_required(self):
        self.samples["loadouts_panel"] = self.samples["loadouts_panel"].replace(
            '.delete();', '.noDelete();'
        )
        with self.assertRaisesRegex(r394.Refused, "LOADOUTS_CONSTRUCTOR_DELETE_PATH_MISSING"):
            self.report()

    def test_loadouts_legacy_condition_required(self):
        self.samples["loadout_store"] = self.samples["loadout_store"].replace(
            "!var5.exists() && var2", "var2")
        with self.assertRaisesRegex(r394.Refused, "LOADOUTS_LEGACY_DELETE_BRANCH_CHANGED"):
            self.report()

    def test_locked_order_write_delegation_required(self):
        self.samples["loadout_store"] = self.samples["loadout_store"].replace(
            "this.writeFolderOrderSettingsWithLock(path,destination);", "this.doNothing();")
        with self.assertRaisesRegex(r394.Refused, "LOADOUTS_ORDER_WRITE_DELEGATION_CHANGED"):
            self.report()

    def test_staged_order_move_required(self):
        self.samples["loadout_store"] = self.samples["loadout_store"].replace(
            "Files.move(path,destination)", "Files.nop(path,destination)")
        with self.assertRaisesRegex(r394.Refused, "LOADOUTS_ORDER_WRITE_PATH_CHANGED"):
            self.report()

    def test_five_worker_pool_required(self):
        self.samples["image_loader"] = self.samples["image_loader"].replace(
            "Executors.newFixedThreadPool(5)", "Executors.newFixedThreadPool(2)")
        with self.assertRaisesRegex(r394.Refused, "LOADOUTS_EXECUTOR_PATH_CHANGED"):
            self.report()

    def test_worker_body_must_be_empty(self):
        self.samples["icon_worker"] = self.samples["icon_worker"].replace(
            "void run(){ }", "void run(){ risky(); }")
        with self.assertRaisesRegex(r394.Refused, "ICON_WORKER_RUN_NO_LONGER_EMPTY"):
            self.report()

    def test_source_reference_to_shutdown_counted_not_proven(self):
        self.samples["image_loader"] += "\nclass Other { void x(){ field3284.shutdown(); } }\n"
        r = self.report()
        self.assertEqual(r["source_references_to_executor_shutdown"], 1)
        self.assertTrue(r["source_reference_search_is_not_lifecycle_proof"])

    def test_missing_private_source_anchor_refused(self):
        self.samples.pop("icon_worker")
        with self.assertRaisesRegex(r394.Refused, "REQUIRED_SOURCE_MISSING"):
            self.report()

    def test_method_parser_does_not_match_recursive_conditional_call(self):
        body = r394.method_body(
            r394._r393.mask_java(self.samples["loot_history_store"]), "deleteTree")
        self.assertIn("Files.deleteIfExists", body)

    def test_malformed_method_name_refused(self):
        with self.assertRaisesRegex(r394.Refused, "INVALID_METHOD_NAME"):
            r394.method_body("void f(){}", "../f")

    def test_no_source_body_content_in_report(self):
        report = json.dumps(self.report())
        self.assertNotIn("GSON.a(", report)
        self.assertNotIn("source/rs/", report)
        self.assertNotIn("privateKit", report)

    def test_cli_pin_drift_refused(self):
        args = ["--kit", str(self.zip), "--kit-sha256", "0"*64,
                "--expected-sources", str(len(self.samples))]
        self.assertEqual(r394.main(args), 2)

    def test_existing_report_never_overwritten(self):
        out = self.dir / "existing.json"
        out.write_text("KEEP", encoding="utf-8")
        args = ["--kit", str(self.zip), "--kit-sha256", self.digest(),
                "--expected-sources", str(len(self.samples)), "--out", str(out)]
        self.assertEqual(r394.main(args), 2)
        self.assertEqual(out.read_text(encoding="utf-8"), "KEEP")

    def test_positive_cli_synthetic_only(self):
        out = self.dir / "fresh.json"
        args = ["--kit", str(self.zip), "--kit-sha256", self.digest(),
                "--expected-sources", str(len(self.samples)), "--out", str(out)]
        self.assertEqual(r394.main(args), 0)
        report = json.loads(out.read_text("utf-8"))
        self.assertEqual(report["status"], "R394_STATIC_PRE_UI_EDT_IO_WITNESS")
        self.assertFalse(report["client_executed"])


class SyntheticSwingHeadlessOrdering(unittest.TestCase):
    def test_pre_ui_history_event_precedes_show_event(self):
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK21 not installed")
        fixture = r'''
import javax.swing.SwingUtilities;
import java.util.*;
import java.util.concurrent.*;
public final class R394EdtFixture {
    public static void main(String[] args) throws Exception {
        System.setProperty("java.awt.headless", "true");
        List<String> sequence = Collections.synchronizedList(new ArrayList<>());
        CountDownLatch done = new CountDownLatch(1);
        SwingUtilities.invokeAndWait(() -> {
            SwingUtilities.invokeLater(() -> sequence.add("history"));
        });
        SwingUtilities.invokeLater(() -> {
            sequence.add("show");
            done.countDown();
        });
        if (!done.await(3, TimeUnit.SECONDS)) throw new AssertionError("timeout");
        String result = String.join(",", sequence);
        System.out.println(result);
        if (!"history,show".equals(result)) throw new AssertionError(result);
        System.exit(0);
    }
}
'''
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = root / "R394EdtFixture.java"
            source.write_text(fixture, encoding="utf-8")
            compile_ = subprocess.run(
                [javac, "-d", scratch, str(source)], timeout=30,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(compile_.returncode, 0, compile_.stderr[:500])
            run = subprocess.run(
                [java, "-Djava.awt.headless=true", "-cp", scratch, "R394EdtFixture"],
                timeout=15, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr[:500])
            self.assertEqual(run.stdout.strip(), "history,show")


if __name__ == "__main__":
    unittest.main()

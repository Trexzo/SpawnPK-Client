"""R421 invented source-auditor negative controls, no private Java published."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from tools.r421.audit_private_directory_preflight import Refused, audit, check

OLD_STORE="class PreviousStore { void original() {} }"
OLD_PLUGIN="class PreviousPlugin { void original() {} }"
STORE = """
class InventedStore {
 LootHistoryStore() {
     this(r421CacheLocationWithoutCreation());
 }
 static String r421CacheLocationWithoutCreation() {
     String key = Configuration.field1268;
     if (key == null || !key.matches("[A-Za-z0-9_-]{1,80}"))
         throw new IllegalStateException();
     if (Configuration.field1256) {
         return "." + File.separator + "cache" + File.separator;
     }
     String home = System.getProperty("user.home");
     if (home == null) throw new IllegalStateException();
     return home + Configuration.isTestBuild;
 }
 boolean r421PrepareHistoryDirectoryForLease() {
     final File parentFile = file.getParentFile();
     Path directory = parentFile.toPath().toAbsolutePath().normalize();
     Path parent = directory.getParent();
     Path ancestor = parent;
     while (ancestor != null) {
         Files.readAttributes(ancestor,BasicFileAttributes.class,
             LinkOption.NOFOLLOW_LINKS);
         ancestor = ancestor.getParent();
     }
     BasicFileAttributes parentBefore = Files.readAttributes(parent,
         BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
     try {
         BasicFileAttributes leafBefore = Files.readAttributes(directory,
             BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
         BasicFileAttributes leafAfter = Files.readAttributes(directory,
             BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
     } catch (NoSuchFileException absent) {
         try {
             Files.createDirectory(directory);
         } catch (FileAlreadyExistsException collision) {
             return false;
         }
     } catch (IOException | SecurityException error) {
         return false;
     }
     BasicFileAttributes parentAfter = Files.readAttributes(parent,
         BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
     if (leafBefore.isOther() || leafAfter.isSymbolicLink())
         return false;
     return r421SameDirectoryIdentity(parentBefore,parentAfter);
 }
 static boolean r421SameDirectoryIdentity(BasicFileAttributes before,
             BasicFileAttributes after) {
     return before.isDirectory() && after.isDirectory() &&
         !before.isSymbolicLink() &&
         before.fileKey().equals(after.fileKey());
 }
}
"""
PLUGIN="""
class InventedPlugin {
 boolean r420AcquireRestoreLeaseWithBoundedRetry(
          LootHistoryStore restoreStore,long generation) {
     if (SwingUtilities.isEventDispatchThread()) return false;
     if (Thread.currentThread().isInterrupted()) return false;
     synchronized (r395HistoryGate) {
         if (generation != r395HistoryGeneration ||
             !r399AcceptingDrops || instance != this ||
             historyStore != restoreStore) return false;
     }
     if (!restoreStore.r421PrepareHistoryDirectoryForLease()) return false;
     final long[] retryDelayMillis = {0L,75L,150L,300L,450L};
     for (long delay : retryDelayMillis) {
         if (restoreStore.r419ActivateOwner()) return true;
     }
     return false;
 }
 void loadHistory() {
    new Thread(() -> {
        if (!r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation))
            return;
        restoreStore.deleteStale();
    });
 }
}
"""


class R421AuditNegatives(unittest.TestCase):
    def bad_store(self, old, new):
        candidate = STORE.replace(old,new)
        self.assertNotEqual(candidate, STORE)
        with self.assertRaises(Refused):
            check(candidate,PLUGIN,OLD_STORE,OLD_PLUGIN)

    def bad_plugin(self, old, new):
        candidate = PLUGIN.replace(old,new)
        self.assertNotEqual(candidate, PLUGIN)
        with self.assertRaises(Refused):
            check(STORE,candidate,OLD_STORE,OLD_PLUGIN)

    def test_01_valid_fabricated_shape(self):
        result = check(STORE,PLUGIN,OLD_STORE,OLD_PLUGIN)
        self.assertTrue(result["noncreating_store_constructor"])

    def test_02_old_cache_resolver_invoked_again(self):
        self.bad_store("this(r421CacheLocationWithoutCreation())",
                       "this(Class307.method121())")

    def test_03_mutating_resolver_not_used(self):
        self.bad_store("return home + Configuration.isTestBuild;",
                       "Class307.method121(); return home + Configuration.isTestBuild;")

    def test_04_forged_cache_identifier(self):
        self.bad_store('"[A-Za-z0-9_-]{1,80}"','".*"')

    def test_05_no_original_config_key(self):
        self.bad_store("Configuration.field1268","foreignValue")

    def test_06_null_home_falls_back_to_working_dir(self):
        self.bad_store("home == null","false")

    def test_07_no_parent_directory_check(self):
        self.bad_store("while (ancestor != null)","while (false)")

    def test_08_nofollow_removed(self):
        self.bad_store("LinkOption.NOFOLLOW_LINKS","LinkOption.FOLLOW_LINKS")

    def test_09_recursive_mkdir_substituted(self):
        self.bad_store("Files.createDirectory(directory)",
                       "Files.createDirectories(directory)")

    def test_10_unexpected_directory_delete(self):
        self.bad_store("Files.createDirectory(directory)",
                       "Files.delete(directory); Files.createDirectory(directory)")

    def test_11_no_collision_handler(self):
        self.bad_store("FileAlreadyExistsException collision",
                       "RuntimeException collision")

    def test_12_no_symlink rejection(self):
        self.bad_store("leafAfter.isSymbolicLink()",
                       "false")

    def test_13_identity_check_removed(self):
        self.bad_store("before.fileKey().equals(after.fileKey())",
                       "true")

    def test_14_security_exception_not_refused(self):
        self.bad_store("IOException | SecurityException","IOException")

    def test_15_create_before_parent_check(self):
        self.bad_store("final File parentFile = file.getParentFile();",
                       "Files.createDirectory(directory);"
                       "final File parentFile = file.getParentFile();")

    def test_16_prepare_invoked_before_session_gate(self):
        self.bad_plugin("if (SwingUtilities.isEventDispatchThread())",
                        "restoreStore.r421PrepareHistoryDirectoryForLease();"
                        "if (SwingUtilities.isEventDispatchThread())")

    def test_17_prepare_called_twice(self):
        self.bad_plugin("if (!restoreStore.r421PrepareHistoryDirectoryForLease())",
                        "restoreStore.r421PrepareHistoryDirectoryForLease();"
                        "if (!restoreStore.r421PrepareHistoryDirectoryForLease())")

    def test_18_preflight_not_on_background_helper(self):
        self.bad_plugin("if (!restoreStore.r421PrepareHistoryDirectoryForLease())",
                        "if (true)")

    def test_19_no_edt_guard(self):
        self.bad_plugin("SwingUtilities.isEventDispatchThread()","false")

    def test_20_missing_epoch_check(self):
        self.bad_plugin("generation != r395HistoryGeneration","false")

    def test_21_direct_preflight_on_restore(self):
        self.bad_plugin("if (!r420AcquireRestoreLeaseWithBoundedRetry",
                        "restoreStore.r421PrepareHistoryDirectoryForLease();"
                        "if (!r420AcquireRestoreLeaseWithBoundedRetry")

    def test_22_missing_lease_acquisition(self):
        self.bad_plugin("restoreStore.r419ActivateOwner()", "true")

    def test_23_no_permanent_backoff(self):
        self.bad_plugin("final long[] retryDelayMillis","final int[] wrongDelayList")

    def test_24_prior_already_contains_preparation(self):
        with self.assertRaises(Refused):
            check(STORE,PLUGIN,
                  OLD_STORE+"r421PrepareHistoryDirectoryForLease()",
                  OLD_PLUGIN)

    def test_25_source_inventory_pin_refuses_extra_changes(self):
        with tempfile.TemporaryDirectory(prefix="r421-audit-trees-") as tmp:
            root=Path(tmp)
            dirs=[root/name for name in ("prior-src","new-src","prior-classes","new-classes")]
            for d in dirs:d.mkdir()
            store="rs/plugins/loottracker/LootHistoryStore.java"
            plugin="rs/plugins/loottracker/LootTrackerPlugin.java"
            storeclass=store[:-5]+".class"
            pluginclass=plugin[:-5]+".class"
            def put(base,relative,value):
                p=base/relative
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(value)
            put(dirs[0],store,OLD_STORE);put(dirs[1],store,STORE)
            put(dirs[0],plugin,OLD_PLUGIN);put(dirs[1],plugin,PLUGIN)
            put(dirs[2],storeclass,"old");put(dirs[3],storeclass,"new")
            put(dirs[2],pluginclass,"old");put(dirs[3],pluginclass,"new")
            pins={k:sha256((source/name).read_bytes()).hexdigest()
                  for k,source,name in [
                      ("prior-store",dirs[0],store),("new-store",dirs[1],store),
                      ("prior-plugin",dirs[0],plugin),("new-plugin",dirs[1],plugin)]}
            self.assertEqual(audit(*dirs,pins,source_count=2,class_count=2)["modified_sources"],2)
            put(dirs[1],"Unrelated.java","extra")
            with self.assertRaises(Refused):
                audit(*dirs,pins,source_count=2,class_count=2)


if __name__=="__main__":
    unittest.main()

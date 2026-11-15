"""Invented private-source facsimile for exact R424 source transformation.

Does not read/compile any recovered game Java. The real private tool refuses
sources not matching the pinned R421 SHA and writes fresh TEMP-only outputs.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.r424.prepare_private_legacy_cleanup_patch import (
    Refused, PINNED_PUBLIC_HELPER_SHA, PINNED_R421_STORE_SHA,
    patch_source_text,
)

ROOT=Path(__file__).resolve().parents[1]
PATCH=ROOT/'tools/r424/prepare_private_legacy_cleanup_patch.py'
HELPER=ROOT/'tests/fixtures/r424/LootLegacyCleanupR424.java'
HARNESS=ROOT/'tests/fixtures/r424/R424LegacyCleanupHarness.java'

FAKE_PRIOR='''package rs.plugins.loottracker;
import java.io.File;
import java.nio.file.Files;
import java.io.IOException;
class LootHistoryStore {
   enum R411StageState { CLEAR, UNSAFE }
   private final File file;
   private static final TestLog log = new TestLog();
   static class TestLog {
      void warn(String text, Object data) { System.out.println("WARN"); }
      void info(String text, Object data) { System.out.println("INFO"); }
   }
   LootHistoryStore(File root) { this.file = new File(root, "loot-history.json"); }
   boolean r411RefuseUnresolvedStage(String reason) { return false; }
   R411StageState r411StageState() { return R411StageState.CLEAR; }
   void deleteStale() { r419DeleteStaleLeased(); }
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
            System.out.println("old cleanup");
         }
      }
      File seenKeys = new File(parent, "loot-keys-seen.txt");
      if (seenKeys.exists() && !seenKeys.delete())
      {
         System.out.println("unable to delete seen keys");
      }
   }

   /**
    * Deletes a file or a directory and everything in it.
    *
    * @return true if nothing is left behind
    */
   private static boolean deleteTree(File file)
   {
      File[] children = file.listFiles();
      if (children != null)
      {
         boolean clean = true;
         for (File child : children)
         {
            clean &= deleteTree(child);
         }
         if (!clean)
         {
            return false;
         }
      }
      try
      {
         Files.deleteIfExists(file.toPath());
         return true;
      }
      catch (IOException e)
      {
         return false;
      }
   }

   void preservedUnrelatedMethod() { System.out.println("preserved"); }
}
'''

FAKE_ACCEPTANCE='''package rs.plugins.loottracker;
import java.nio.file.*;
import java.io.File;
public final class R424PatchedStoreAcceptance {
  public static void main(String[] args) throws Exception {
    Path root=Paths.get(args[0]);
    Path old=root.resolve("loot-history");
    Files.createDirectories(old);
    Path record=old.resolve("some-legacy-entry.bin");
    Files.write(record,new byte[]{1,2,3});
    Path keys=root.resolve("loot-keys-seen.txt");
    Files.write(keys,new byte[]{4});
    LootHistoryStore test=new LootHistoryStore(root.toFile());
    test.deleteStale();
    if(!Files.exists(old) || !Files.exists(record) || !Files.exists(keys))
      throw new AssertionError("R424_PRIVATE_OVERLAY_MUST_NOT_DELETE");
    System.out.println("R424_SYNTHETIC_PRIVATE_PATCH_DRY_RUN_PASS");
  }
}
'''

class R424PatchGate(unittest.TestCase):
    def expected(self,text=FAKE_PRIOR):
        return sha256(text.encode('utf-8')).hexdigest()

    def patch(self,text=FAKE_PRIOR):
        return patch_source_text(text,self.expected(text))

    def fail_mutation(self,original,new):
        modified=FAKE_PRIOR.replace(original,new)
        self.assertNotEqual(modified,FAKE_PRIOR)
        with self.assertRaises(Refused): self.patch(modified)

    def test_01_valid_fake_source_transformed(self):
        s=self.patch()
        self.assertIn('LootLegacyCleanupR424.run(',s)
        self.assertNotIn('private static boolean deleteTree',s)

    def test_02_unrelated_method_unchanged(self):
        s=self.patch()
        self.assertIn('void preservedUnrelatedMethod() { System.out.println("preserved"); }',s)

    def test_03_dry_run_is_hardcoded(self):
        s=self.patch()
        self.assertIn('false); // R424:',s)
        self.assertNotIn('true); // R424:',s)

    def test_04_old_recursive_deletion_removed(self):
        s=self.patch()
        self.assertNotIn('deleteTree(parts)',s)
        self.assertNotIn('deleteTree(child)',s)
        self.assertNotIn('seenKeys.delete()',s)

    def test_05_old_obsolete_javadoc_removed(self):
        s=self.patch()
        self.assertNotIn('Deletes a file or a directory and everything in it.',s)

    def test_06_wrong_source_pin_refused(self):
        with self.assertRaises(Refused): patch_source_text(FAKE_PRIOR,'0'*64)

    def test_07_malformed_source_pin_refused(self):
        with self.assertRaises(Refused): patch_source_text(FAKE_PRIOR,'bad')

    def test_08_repeated_patch_refused(self):
        s=self.patch()
        with self.assertRaises(Refused): patch_source_text(s,self.expected(s))

    def test_09_stage_guard_removed_refused(self):
        self.fail_mutation('r411RefuseUnresolvedStage("legacy cleanup")','false')

    def test_10_old_delete_call_removed_refused(self):
        self.fail_mutation('deleteTree(parts)','true')

    def test_11_old_seen_keys_delete_removed_refused(self):
        self.fail_mutation('seenKeys.delete()','true')

    def test_12_old_listfiles_removed_refused(self):
        self.fail_mutation('file.listFiles()','new File[0]')

    def test_13_old_recursion_changed_refused(self):
        self.fail_mutation('deleteTree(child)','false')

    def test_14_old_file_delete_changed_refused(self):
        self.fail_mutation('Files.deleteIfExists(file.toPath())','noop()')

    def test_15_extra_old_tree_caller_refused(self):
        self.fail_mutation('void preservedUnrelatedMethod() {',
                           'void preservedUnrelatedMethod() { deleteTree(file);')

    def test_16_duplicate_old_method_refused(self):
        self.fail_mutation('void preservedUnrelatedMethod()',
                           'private static boolean deleteTree(File extra) { return false; }\n'
                           'void preservedUnrelatedMethod()')

    def test_17_obsolete_javadoc_change_refused(self):
        self.fail_mutation('Deletes a file or a directory and everything in it.',
                           'Undocumented old recursive method.')

    def test_18_unbalanced_unrelated_method_rejected_by_compiler(self):
        damaged=FAKE_PRIOR.replace('void preservedUnrelatedMethod() {',
                                  'void preservedUnrelatedMethod() { {')
        patched=self.patch(damaged)
        with tempfile.TemporaryDirectory(prefix='r424-compiler-negative-') as d:
            p=Path(d)/'LootHistoryStore.java'
            p.write_text(patched,encoding='utf8')
            compiled=subprocess.run(['javac','--release','11','-d',d,
                                     str(HELPER),str(p)],
                                    capture_output=True,text=True,timeout=40)
            self.assertNotEqual(compiled.returncode,0)

    def test_19_public_helper_exact_pin(self):
        self.assertEqual(sha256(HELPER.read_bytes()).hexdigest(),
                         PINNED_PUBLIC_HELPER_SHA)

    def test_20_private_pin_is_unchanged_r421(self):
        self.assertEqual(PINNED_R421_STORE_SHA,
                         '0369e9b55e194ecfebfd754d15f66e6de84067634f16799a3c57c435b0616b29')

    def test_21_public_helper_java11_compiles(self):
        with tempfile.TemporaryDirectory(prefix='r424-compile-') as d:
            r=subprocess.run(['javac','--release','11','-d',d,str(HELPER)],
                capture_output=True,text=True,timeout=40)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_22_patched_fabricated_store_java11_compiles(self):
        with tempfile.TemporaryDirectory(prefix='r424-compile-') as d:
            root=Path(d); src=root/'LootHistoryStore.java'
            src.write_text(self.patch(),encoding='utf8')
            r=subprocess.run(['javac','--release','11','-d',d,str(HELPER),str(src)],
                capture_output=True,text=True,timeout=50)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_23_compiled_fake_patch_startup_is_nondestructive(self):
        with tempfile.TemporaryDirectory(prefix='r424-compiled-') as d:
            root=Path(d); src=root/'LootHistoryStore.java'
            src.write_text(self.patch(),encoding='utf8')
            harness=root/'R424PatchedStoreAcceptance.java'
            harness.write_text(FAKE_ACCEPTANCE,encoding='utf8')
            r=subprocess.run(['javac','--release','11','-d',d,str(HELPER),str(src),str(harness)],
                capture_output=True,text=True,timeout=50)
            self.assertEqual(r.returncode,0,r.stderr)
            fixture=root/'R424-Synthetic-Store'; fixture.mkdir()
            p=subprocess.run(['java','-Djava.awt.headless=true','-cp',d,
                'rs.plugins.loottracker.R424PatchedStoreAcceptance',str(fixture)],
                capture_output=True,text=True,timeout=25)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('R424_SYNTHETIC_PRIVATE_PATCH_DRY_RUN_PASS',p.stdout)

    def test_24_real_pinned_cli_refuses_fabricated_tree(self):
        with tempfile.TemporaryDirectory(prefix='r424-fakecli-') as d:
            root=Path(d); src=root/'source';(src/'rs/plugins/loottracker').mkdir(parents=True)
            (src/'rs/plugins/loottracker/LootHistoryStore.java').write_text(FAKE_PRIOR)
            dest=Path(tempfile.gettempdir())/('R424-Private-Candidate-TestNoCreate')
            if dest.exists(): self.skipTest('reserved temp basename already exists')
            p=subprocess.run([sys.executable,str(PATCH),'--owner-private-source-root',str(src),
                '--public-helper-source',str(HELPER),'--fresh-temp-destination',str(dest)],
                capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,2,p.stderr)
            self.assertFalse(dest.exists())
            self.assertIn('R424_PREPARATION_REFUSED',p.stdout)


    def test_25_crlf_original_newlines_preserved(self):
        crlf=FAKE_PRIOR.replace('\\n','\\r\\n')
        patched=patch_source_text(crlf,sha256(crlf.encode('utf-8')).hexdigest())
        self.assertIn('\\r\\n',patched)
        self.assertEqual(patched.count('\\n'),patched.count('\\r\\n'))
        self.assertIn('false); // R424:',patched)

    def test_26_output_source_uses_bytes_not_platform_text_newline(self):
        source=PATCH.read_text('utf8')
        self.assertIn('new_store.write_bytes(patch.encode("utf-8"))',source)

if __name__=='__main__': unittest.main()

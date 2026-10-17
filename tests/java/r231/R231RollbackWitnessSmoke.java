package rs.cache.updater.assets;

import java.io.IOException;
import java.lang.reflect.Method;
import java.nio.file.*;

/** Synthetic original-independent recovery test; Java 11, no game classes. */
public final class R231RollbackWitnessSmoke {
   private static int checked = 0;
   static void ok(boolean v, String m) { if (!v) throw new AssertionError(m); checked++; }
   static void witness(Path w, Path original) throws Exception {
      Method m = CacheUpdateTransaction.class.getDeclaredMethod(
         "writeRollbackWitness", Path.class, Path.class);
      m.setAccessible(true);
      m.invoke(null, w, original);
   }
   static Path work(Path root, String phase) throws IOException {
      Path w = Files.createTempDirectory(root.getParent(), ".spk-cache-update-");
      Files.writeString(w.resolve(".transaction"),
         "SPK-CACHE-TRANSACTION-V1\n" + root + "\n" + phase + "\n");
      return w;
   }
   public static void main(String[] args) throws Exception {
      Path p = Files.createTempDirectory("r231-recovery-");
      Path root = p.resolve("assets");
      Path w = work(root, "ROLLBACK_PREPARED");
      Path old = Files.createDirectory(w.resolve("previous"));
      Files.writeString(old.resolve("file"), "ORIGINAL");
      witness(w, old);
      Files.move(old, root);
      Files.writeString(root.resolve("file"), "REPLACED");
      try {
         CacheUpdateTransaction.recover(root.toFile());
         throw new AssertionError("Untrusted replacement treated as restored cache");
      } catch (IOException expected) {
         ok(expected.getMessage().contains("persisted original backup witness"),
            "Unexpected rejection: " + expected.getMessage());
      }
      ok(Files.readString(root.resolve("file")).equals("REPLACED"),
         "Conflict recovery deleted unrelated live data");
      ok(Files.exists(w.resolve(".transaction")), "Rollback journal was destroyed");
      ok(Files.exists(w.resolve(".rollback-witness")), "Fingerprint evidence was destroyed");
      Files.writeString(root.resolve("file"), "ORIGINAL");
      CacheUpdateTransaction.recover(root.toFile());
      ok(Files.readString(root.resolve("file")).equals("ORIGINAL"),
         "Valid restoration failed");
      ok(!Files.exists(w), "Recovered transaction was not cleaned");

      Path legacy = work(root, "ROLLBACK_PREPARED");
      CacheUpdateTransaction.recover(root.toFile());
      ok(!Files.exists(legacy), "Old-format journal compatibility failed");

      Path complete = work(root, "ROLLBACK_RESTORED");
      Path backup = Files.createDirectory(complete.resolve("previous"));
      Files.writeString(backup.resolve("file"), "ORIGINAL");
      witness(complete, backup);
      Files.delete(backup.resolve("file")); Files.delete(backup);
      Files.writeString(root.resolve("file"), "CHANGED!");
      try {
         CacheUpdateTransaction.recover(root.toFile());
         throw new AssertionError("Completed rollback accepted altered live root");
      } catch (IOException expected) {
         ok(expected.getMessage().contains("persisted original backup witness"),
            "Unexpected completed-rollback rejection");
      }
      ok(Files.exists(complete.resolve(".rollback-witness")),
         "Completed rollback discarded witness before verification");
      System.out.println("R231_PUBLIC_ROLLBACK_WITNESS_PASS checks=" + checked);
   }
}

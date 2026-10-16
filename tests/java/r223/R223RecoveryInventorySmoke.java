package rs.cache.updater.assets;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.stream.Stream;

/** JDK11-only, no private game classes: test inventory rejection before mutation. */
public final class R223RecoveryInventorySmoke {
   private static class Halt extends Error {}
   private static void check(boolean v, String message) {
      if (!v) throw new AssertionError(message);
   }
   private static void mustReject(RunnableIO action, String needle) throws Exception {
      try {
         action.run();
         throw new AssertionError("Missing rejection: " + needle);
      } catch (IOException failure) {
         check(failure.getMessage().contains(needle), "Wrong failure: " + failure);
      }
   }
   @FunctionalInterface interface RunnableIO { void run() throws Exception; }
   static void rm(Path p) throws IOException {
      if (!Files.exists(p, LinkOption.NOFOLLOW_LINKS)) return;
      Files.walkFileTree(p, new SimpleFileVisitor<Path>() {
         @Override public FileVisitResult visitFile(Path file, BasicFileAttributes a) throws IOException {
            Files.delete(file); return FileVisitResult.CONTINUE;
         }
         @Override public FileVisitResult postVisitDirectory(Path dir, IOException e) throws IOException {
            if (e != null) throw e;
            Files.delete(dir); return FileVisitResult.CONTINUE;
         }
      });
   }
   static String journal(Path root, String phase) {
      return "SPK-CACHE-TRANSACTION-V1\n" + root.toAbsolutePath().normalize() + "\n" + phase + "\n";
   }
   static boolean extract(String dir, java.io.File archive) throws IOException {
      Files.writeString(Path.of(dir, "cache.dat"), "new");
      return true;
   }
   static java.io.File download(java.io.File archive) throws IOException {
      Files.writeString(archive.toPath(), "archive");
      return archive;
   }
   public static void main(String[] args) throws Exception {
      Path temp = Files.createTempDirectory("r223-public-");
      try {
         Path a = temp.resolve("alpha");
         Path b = temp.resolve("beta");
         Files.createDirectories(a);
         Files.createDirectories(b);
         Files.writeString(a.resolve("cache.dat"), "original");
         Files.writeString(b.resolve("cache.dat"), "other");
         try {
            CacheUpdateTransaction.install(a.toFile(),
               R223RecoveryInventorySmoke::download, R223RecoveryInventorySmoke::extract,
               () -> { throw new Halt(); });
            throw new AssertionError("Expected simulated crash");
         } catch (Halt ignored) {}
         Path owned;
         try (Stream<Path> entries = Files.list(temp)) {
            owned = entries.filter(p -> p.getFileName().toString().startsWith(".spk-cache-update-")
               && Files.exists(p.resolve("previous"))).findFirst().orElseThrow();
         }
         Path duplicate = Files.createDirectory(temp.resolve(owned.getFileName() + "-copy"));
         Files.createDirectory(duplicate.resolve("previous"));
         Files.writeString(duplicate.resolve("previous/cache.dat"), "duplicate-backup");
         Files.writeString(duplicate.resolve(".transaction"), journal(a, "OLD_MOVED"));
         mustReject(() -> CacheUpdateTransaction.recover(a.toFile()), "Multiple pending transactions");
         check(!Files.exists(a), "Ambiguous recovery modified live cache");
         check(Files.readString(owned.resolve("previous/cache.dat")).equals("original"), "Original backup deleted");
         check(Files.readString(duplicate.resolve("previous/cache.dat")).equals("duplicate-backup"),
            "Duplicate backup deleted");
         mustReject(() -> CacheUpdateTransaction.install(a.toFile(),
            R223RecoveryInventorySmoke::download, R223RecoveryInventorySmoke::extract),
            "Multiple pending transactions");
         CacheUpdateTransaction.recover(b.toFile());
         check(Files.readString(b.resolve("cache.dat")).equals("other"), "Foreign cache modified");
         rm(duplicate);
         CacheUpdateTransaction.recover(a.toFile());
         check(Files.readString(a.resolve("cache.dat")).equals("original"), "Recovery did not restore cache");
         Path spoof = Files.createDirectory(temp.resolve(owned.getFileName() + "-spoof"));
         Files.writeString(spoof.resolve(".transaction"), journal(b, "PREPARING"));
         mustReject(() -> CacheUpdateTransaction.recover(a.toFile()), "owner does not match");
         check(Files.readString(a.resolve("cache.dat")).equals("original"), "Spoof affected root");
         rm(spoof);
         Path noMarker = Files.createDirectory(temp.resolve(owned.getFileName() + "-unmarked"));
         Files.createDirectory(noMarker.resolve("staged"));
         Files.writeString(noMarker.resolve("staged/cache.dat"), "keep");
         mustReject(() -> CacheUpdateTransaction.recover(a.toFile()), "Unidentified cache recovery data");
         check(Files.readString(noMarker.resolve("staged/cache.dat")).equals("keep"), "Discarded orphan data");
         rm(noMarker);
         check(CacheUpdateTransaction.install(a.toFile(),
            R223RecoveryInventorySmoke::download, R223RecoveryInventorySmoke::extract),
            "Normal update failed after manual ambiguity resolution");
         check(Files.readString(a.resolve("cache.dat")).equals("new"), "Normal update content mismatch");
         System.out.println("R223_PUBLIC_INVENTORY_PASS duplicate, foreign, spoof, orphan, rollback, install");
      } finally { rm(temp); }
   }
}

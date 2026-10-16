package rs.cache.updater.assets;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Original-independent test of root-scoped workspace recovery. */
public final class R222RootIsolationSmoke {
   private static final class Crash extends Error { }
   private static void check(boolean state, String message) {
      if (!state) throw new AssertionError(message);
   }
   private static java.io.File download(java.io.File archive) throws IOException {
      Files.writeString(archive.toPath(), "test"); return archive;
   }
   private static boolean extract(String target, java.io.File archive) throws IOException {
      Files.writeString(Path.of(target, "cache.dat"), "replacement"); return true;
   }
   public static void main(String[] args) throws Exception {
      Path parent = Files.createTempDirectory("r222-public-");
      Path a = parent.resolve("cache-a"), b = parent.resolve("cache-b");
      Files.createDirectories(a); Files.createDirectories(b);
      Files.writeString(a.resolve("cache.dat"), "original-a");
      Files.writeString(b.resolve("cache.dat"), "original-b");

      // An unknown recovery journal belongs to a different scoped cache.
      Path foreign = Files.createDirectory(parent.resolve(
         ".spk-cache-update-aaaaaaaaaaaaaaaaaaaaaaaa-foreign"));
      Files.createDirectory(foreign.resolve("previous"));
      Files.writeString(foreign.resolve("previous/value"), "untouched");
      Files.writeString(foreign.resolve(".transaction"), "invalid");
      CacheUpdateTransaction.recover(a.toFile());
      check(Files.readString(foreign.resolve("previous/value")).equals("untouched"),
         "A foreign journal was touched");

      // Simulate abrupt failure precisely after the original cache rename.
      try {
         CacheUpdateTransaction.install(a.toFile(),
            R222RootIsolationSmoke::download, R222RootIsolationSmoke::extract,
            () -> { throw new Crash(); });
         throw new AssertionError("Crash hook was ignored");
      } catch (Crash intended) { }
      check(!Files.exists(a), "Expected old directory to be temporarily absent");
      CacheUpdateTransaction.recover(b.toFile());
      check(Files.readString(b.resolve("cache.dat")).equals("original-b"),
         "Recovering unrelated cache touched its data");
      CacheUpdateTransaction.recover(a.toFile());
      check(Files.readString(a.resolve("cache.dat")).equals("original-a"),
         "Interrupted cache rollback failed");

      // Both isolated caches remain updatable, without changing the foreign journal.
      check(CacheUpdateTransaction.install(a.toFile(),
         R222RootIsolationSmoke::download, R222RootIsolationSmoke::extract),
         "Cache A installation rejected");
      check(CacheUpdateTransaction.install(b.toFile(),
         R222RootIsolationSmoke::download, R222RootIsolationSmoke::extract),
         "Cache B installation rejected");
      check(Files.readString(a.resolve("cache.dat")).equals("replacement") &&
         Files.readString(b.resolve("cache.dat")).equals("replacement"),
         "Independent installs did not complete");
      check(Files.readString(foreign.resolve("previous/value")).equals("untouched"),
         "Unowned recovery backup was deleted");
      System.out.println("R222_PUBLIC_ROOT_ISOLATION_PASS");
   }
}

package rs.cache.updater.assets;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** Original-independent Java11 test: full ancestry collision, not only leaf. */
public final class R230AncestorCollisionSmoke {
   private static int checks;
   private static void check(boolean ok, String why) {
      if (!ok) throw new AssertionError(why);
      checks++;
   }
   private static void reject(Path path) throws Exception {
      try {
         CacheUpdateTransaction.verifyCaseFoldCollision(path, true);
         throw new AssertionError("Unsafe folded ancestor accepted: " + path);
      } catch (IOException expected) {
         check(expected.getMessage().contains("collision"), "Unexpected failure: " + expected);
      }
   }
   public static void main(String[] args) throws Exception {
      Path temp = Files.createTempDirectory("r230-ancestor-");
      Path first = Files.createDirectories(temp.resolve("Parent/inner/cache"));
      CacheUpdateTransaction.verifyCaseFoldCollision(first, true);
      checks++;
      CacheUpdateTransaction.verifyCaseFoldCollision(first, false);
      checks++;
      if (!Files.exists(temp.resolve("parent"))) {
         Path second = Files.createDirectories(temp.resolve("parent/inner/cache"));
         check(!Files.isSameFile(first, second), "Case-sensitive fixture shares inode");
         reject(first);
         reject(second);
         reject(temp.resolve("Parent/inner/future-cache"));
         CacheUpdateTransaction.verifyCaseFoldCollision(first, false);
         checks++;
      } else {
         Path alias = Path.of(first.toString().toUpperCase(Locale.ROOT));
         check(Files.isSameFile(first, alias), "Windows alias did not resolve");
         CacheUpdateTransaction.verifyCaseFoldCollision(alias, true);
         checks++;
      }
      Path nested = Files.createDirectories(temp.resolve("stable/Upper/cache"));
      if (!Files.exists(temp.resolve("stable/upper"))) {
         Files.createDirectory(temp.resolve("stable/upper"));
         reject(nested);
         reject(temp.resolve("stable/Upper/uncreated"));
      } else {
         CacheUpdateTransaction.verifyCaseFoldCollision(nested, true);
         checks++;
      }
      Path leaf = Files.createDirectories(temp.resolve("final/Cache"));
      if (!Files.exists(temp.resolve("final/cache"))) {
         Files.createDirectory(temp.resolve("final/cache"));
         reject(leaf);
      } else {
         CacheUpdateTransaction.verifyCaseFoldCollision(leaf, true);
         checks++;
      }
      System.out.println("R230_FULL_ANCESTRY_COLLISION_PASS checks=" + checks);
   }
}

package rs.cache.updater.assets;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;

/** JDK-only tests of the exact helper. Private original CacheUpdater is tested separately. */
public final class R220PublicTransactionSmoke {
   private static void check(boolean value, String message) {
      if (!value) throw new AssertionError(message);
   }
   private static void clean(Path parent) throws IOException {
      try (Stream<Path> children = Files.list(parent)) {
         check(children.noneMatch(p -> p.getFileName().toString().startsWith(".spk-cache-update-")),
            "Recovery staging directory leaked");
      }
   }
   public static void main(String[] args) throws Exception {
      Path parent = Files.createTempDirectory("r220-public-");
      Path live = parent.resolve("live");
      Files.createDirectories(live.resolve("sprites"));
      Files.writeString(live.resolve("cache.dat"), "old");
      Files.writeString(live.resolve("sprites/icon"), "preserve");
      check(!CacheUpdateTransaction.install(live.toFile(), destination -> null,
         (dir,archive) -> true), "Null download accepted");
      check(Files.readString(live.resolve("cache.dat")).equals("old"), "Download failure lost cache");
      clean(parent);
      try {
         CacheUpdateTransaction.install(live.toFile(), destination -> {
            Files.writeString(destination.toPath(), "archive"); return destination;
         }, (dir,archive) -> {
            Files.writeString(Path.of(dir).resolve("cache.dat"), "new"); return true;
         }, () -> { throw new IOException("intentional fault at swap boundary"); });
         throw new AssertionError("Injected rename failure accepted");
      } catch (IOException expected) { }
      check(Files.readString(live.resolve("cache.dat")).equals("old"), "Rollback failed");
      clean(parent);
      check(CacheUpdateTransaction.install(live.toFile(), destination -> {
            Files.writeString(destination.toPath(), "archive"); return destination;
         }, (dir,archive) -> {
            Files.writeString(Path.of(dir).resolve("cache.dat"), "new"); return true;
         }), "Normal update failed");
      check(Files.readString(live.resolve("cache.dat")).equals("new"), "New cache not installed");
      check(Files.readString(live.resolve("sprites/icon")).equals("preserve"), "Sprite data lost");
      clean(parent);
      System.out.println("R220_PUBLIC_TRANSACTION_PASS");
   }
}

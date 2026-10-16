package rs.cache.updater.assets;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import java.util.stream.Stream;

/** JDK11-only replay of a rollback interrupted between restore and cleanup. */
public final class R224RollbackReplaySmoke {
   private static int checks;
   private static void check(boolean v, String message) {
      if (!v) throw new AssertionError(message);
      checks++;
   }
   private static void remove(Path p) throws IOException {
      if (!Files.exists(p, LinkOption.NOFOLLOW_LINKS)) return;
      Files.walkFileTree(p, new SimpleFileVisitor<Path>() {
         @Override public FileVisitResult visitFile(Path f, BasicFileAttributes a) throws IOException {
            Files.delete(f); return FileVisitResult.CONTINUE;
         }
         @Override public FileVisitResult postVisitDirectory(Path d, IOException e) throws IOException {
            if (e != null) throw e;
            Files.delete(d); return FileVisitResult.CONTINUE;
         }
      });
   }
   private static Path workspace(Path cache, String suffix) throws Exception {
      byte[] digest = MessageDigest.getInstance("SHA-256").digest(
         cache.toAbsolutePath().normalize().toString().getBytes(StandardCharsets.UTF_8));
      StringBuilder id = new StringBuilder();
      for (int i = 0; i < 12; i++) id.append(String.format("%02x", digest[i] & 255));
      return Files.createDirectory(cache.getParent().resolve(
         ".spk-cache-update-" + id + "-" + suffix));
   }
   private static void phase(Path w, Path root, String status) throws IOException {
      Files.writeString(w.resolve(".transaction"), "SPK-CACHE-TRANSACTION-V1\n" +
         root.toAbsolutePath().normalize() + "\n" + status + "\n");
   }
   private static void noWork(Path parent) throws Exception {
      try (Stream<Path> paths = Files.list(parent)) {
         check(paths.noneMatch(p -> p.getFileName().toString().startsWith(".spk-cache-update-")),
            "Completed recovery left journal");
      }
   }
   public static void main(String[] args) throws Exception {
      Path parent = Files.createTempDirectory("r224-public-rollback-");
      try {
         Path root = Files.createDirectory(parent.resolve("assets"));
         Files.writeString(root.resolve("existing"), "ORIGINAL");
         Path w = workspace(root, "restored-before-journal");
         phase(w,root,"ROLLBACK_PREPARED");
         Files.createDirectory(w.resolve("interrupted-new"));
         Files.writeString(w.resolve("interrupted-new/existing"), "NEW");
         CacheUpdateTransaction.recover(root.toFile());
         check(Files.readString(root.resolve("existing")).equals("ORIGINAL"),
            "A replay deleted the previously restored original");
         noWork(parent);

         w = workspace(root, "journal-written-before-cleanup");
         phase(w,root,"ROLLBACK_RESTORED");
         CacheUpdateTransaction.recover(root.toFile());
         check(Files.readString(root.resolve("existing")).equals("ORIGINAL"),
            "Completed rollback replay mutated cache");
         noWork(parent);

         Files.delete(root.resolve("existing")); Files.delete(root);
         w = workspace(root, "after-quarantine");
         Files.createDirectory(w.resolve("previous"));
         Files.writeString(w.resolve("previous/existing"), "ORIGINAL");
         Files.createDirectory(w.resolve("interrupted-new"));
         phase(w,root,"ROLLBACK_PREPARED");
         CacheUpdateTransaction.recover(root.toFile());
         check(Files.readString(root.resolve("existing")).equals("ORIGINAL"),
            "Crash after quarantine did not restore backup");
         noWork(parent);

         Files.delete(root.resolve("existing")); Files.delete(root);
         w = workspace(root, "no-original");
         Files.createDirectory(root);
         Files.writeString(root.resolve("existing"), "UNCOMMITTED");
         phase(w,root,"ROLLBACK_EMPTY");
         CacheUpdateTransaction.recover(root.toFile());
         check(!Files.exists(root), "No-original rollback retained incomplete installation");
         noWork(parent);

         w = workspace(root, "no-original-replay");
         Files.createDirectory(w.resolve("interrupted-new"));
         phase(w,root,"ROLLBACK_EMPTY");
         CacheUpdateTransaction.recover(root.toFile());
         check(!Files.exists(root), "No-original replay recreated deleted cache");
         noWork(parent);

         Files.createDirectory(root);
         Files.writeString(root.resolve("existing"), "ORIGINAL");
         try {
            CacheUpdateTransaction.install(root.toFile(), f -> {
               Files.writeString(f.toPath(), "PARTIAL");
               throw new IOException("simulated ENOSPC");
            }, (dir,zip) -> true);
            throw new AssertionError("Partial download succeeded");
         } catch (IOException e) { check(e.getMessage().contains("ENOSPC"), "Wrong error"); }
         check(Files.readString(root.resolve("existing")).equals("ORIGINAL"),
            "Partial download altered installed cache");
         noWork(parent);
         try {
            CacheUpdateTransaction.install(root.toFile(), f -> {
               Files.writeString(f.toPath(), "ARCHIVE"); return f;
            }, (dir,zip) -> {
               Files.writeString(Path.of(dir,"existing"),"PARTIAL");
               throw new IOException("simulated ENOSPC");
            });
            throw new AssertionError("Partial extraction succeeded");
         } catch (IOException e) { check(e.getMessage().contains("ENOSPC"), "Wrong error"); }
         check(Files.readString(root.resolve("existing")).equals("ORIGINAL"),
            "Partial extraction altered installed cache");
         noWork(parent);
         System.out.println("R224_PUBLIC_ROLLBACK_REPLAY_PASS checks=" + checks);
      } finally { remove(parent); }
   }
}

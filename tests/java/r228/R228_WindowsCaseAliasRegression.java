package rs.cache.updater.assets;

import java.io.*;
import java.nio.file.*;
import java.util.Locale;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import java.util.stream.Stream;

/** Real JVM child-process tests of Windows case-insensitive cache root identity. */
public final class R228_WindowsCaseAliasRegression {
   private static int assertions;
   private static void check(boolean x, String message) {
      if (!x) throw new AssertionError(message);
      assertions++;
   }
   private static File download(File target) throws IOException {
      Files.writeString(target.toPath(), "synthetic archive");
      return target;
   }
   private static boolean extract(String stage, File archive) throws IOException {
      Files.writeString(Path.of(stage, "updated.dat"), "new-cache");
      return true;
   }
   private static Process child(String mode, Path root) throws IOException {
      String java = Path.of(System.getProperty("java.home"), "bin",
         File.separatorChar == '\\' ? "java.exe" : "java").toString();
      return new ProcessBuilder(java, "-cp", System.getProperty("java.class.path"),
         R228_WindowsCaseAliasRegression.class.getName(), mode, root.toString())
         .redirectError(ProcessBuilder.Redirect.INHERIT).start();
   }
   public static void main(String[] args) throws Exception {
      if (args.length == 2) {
         Path root = Path.of(args[1]);
         switch (args[0]) {
            case "hold":
               CacheUpdateTransaction.install(root.toFile(),
                  R228_WindowsCaseAliasRegression::download,
                  R228_WindowsCaseAliasRegression::extract, () -> {
                     System.out.write('L'); System.out.flush();
                     try { Thread.sleep(4500); }
                     catch (InterruptedException e) { Thread.currentThread().interrupt();
                        throw new IOException("Child lock holder interrupted", e); }
                  });
               return;
            case "crash":
               CacheUpdateTransaction.install(root.toFile(),
                  R228_WindowsCaseAliasRegression::download,
                  R228_WindowsCaseAliasRegression::extract, () -> {
                     System.out.write('H'); System.out.flush();
                     Runtime.getRuntime().halt(17);
                  });
               return;
            default: throw new AssertionError("unexpected child mode");
         }
      }
      // R229: on a case-sensitive filesystem two physical root directories
      // may differ only by capitalization. Never assign them one Windows lock.
      Path fixture = Files.createTempDirectory("r229-distinct-roots-");
      Path upper = Files.createDirectory(fixture.resolve("Cache"));
      Path lower = fixture.resolve("cache");
      if (!Files.exists(lower)) {
         Files.createDirectory(lower);
      }
      if (!Files.isSameFile(upper, lower)) {
         try {
            CacheUpdateTransaction.verifyCaseFoldCollision(upper, true);
            throw new AssertionError("R229 accepted separate cache roots with one lock identity");
         } catch (IOException expected) {
            if (!expected.getMessage().contains("identity collision")) throw expected;
         }
      } else {
         CacheUpdateTransaction.verifyCaseFoldCollision(upper, true);
      }
      System.out.println("R229_CASE_COLLISION_PRECHECK_PASS");
      if (File.separatorChar != '\\') {
         System.out.println("R228_WINDOWS_ALIAS_NOT_APPLICABLE; Java11 test compiled");
         return;
      }
      Path parent = Files.createTempDirectory("r228-casealias-");
      Path root = Files.createDirectory(parent.resolve("assetCache"));
      Files.writeString(root.resolve("original.dat"), "ORIGINAL");
      Path aliased = Path.of(root.toString().toUpperCase(Locale.ROOT));
      check(Files.isSameFile(root, aliased), "Test platform does not resolve casing aliases");
      Process holding = child("hold", root);
      try {
         int ready = holding.getInputStream().read();
         check(ready == 'L', "Failed to establish second-process lock holder");
         try {
            CacheUpdateTransaction.recover(aliased.toFile());
            throw new AssertionError("Cache alias bypassed the active writer's file lock");
         } catch (IOException expected) {
            check(expected.getMessage().contains("Another client"),
               "Unexpected concurrent cache failure: " + expected);
         }
      } finally {
         if (!holding.waitFor(9, java.util.concurrent.TimeUnit.SECONDS)) {
            holding.destroyForcibly(); holding.waitFor();
         }
      }
      check(holding.exitValue() == 0, "Lock holder's installation did not finish");
      check(Files.readString(root.resolve("updated.dat")).equals("new-cache"),
         "Valid source instance lost cache during lock conflict");
      Files.writeString(root.resolve("original.dat"), "NEW-ORIGINAL");
      Process stopped = child("crash", root);
      check(stopped.getInputStream().read() == 'H', "Child did not reach rename boundary");
      check(stopped.waitFor(8, java.util.concurrent.TimeUnit.SECONDS), "Crash child never exited");
      check(stopped.exitValue() == 17, "Crash child did not terminate at exact hook");
      check(!Files.exists(root), "Expected cache root moved aside during interrupted transaction");
      CacheUpdateTransaction.recover(aliased.toFile());
      check(Files.readString(root.resolve("original.dat")).equals("NEW-ORIGINAL"),
         "Cased-root recovery failed to restore original cache");
      check(Files.readString(root.resolve("updated.dat")).equals("new-cache"),
         "Recovery deleted the previous cache's updated file");
      // Simulate a journal/workspace created by pre-R228 with a mixed-case
      // path digest. A restart under a different spelling must still recover it.
      Process legacyStop = child("crash", root);
      check(legacyStop.getInputStream().read() == 'H', "Legacy test child did not reach rename");
      check(legacyStop.waitFor(8, java.util.concurrent.TimeUnit.SECONDS), "Legacy child hung");
      check(legacyStop.exitValue() == 17, "Legacy child not abruptly terminated");
      Path owned;
      try (Stream<Path> paths = Files.list(parent)) {
         owned = paths.filter(x -> x.getFileName().toString().startsWith(".spk-cache-update-"))
            .findFirst().orElseThrow();
      }
      byte[] exactDigest = MessageDigest.getInstance("SHA-256")
         .digest(root.toString().getBytes(StandardCharsets.UTF_8));
      StringBuilder hex = new StringBuilder();
      for (int i = 0; i < 12; i++) hex.append(String.format("%02x", exactDigest[i] & 255));
      Path oldStyle = parent.resolve(".spk-cache-update-" + hex + "-legacy-casing");
      check(!owned.equals(oldStyle), "Legacy namespace unexpectedly identical");
      Files.move(owned, oldStyle);
      CacheUpdateTransaction.recover(aliased.toFile());
      check(Files.readString(root.resolve("original.dat")).equals("NEW-ORIGINAL"),
         "Legacy cased journal was not discovered/restored");
      check(!Files.exists(oldStyle), "Legacy transaction not cleaned after recovery");
      System.out.println("R228_WINDOWS_CASE_ALIAS_PASS checks=" + assertions);
   }
}

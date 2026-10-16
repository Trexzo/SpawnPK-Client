package rs.cache.updater.assets;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;

/** Zero-network, exact-production-helper crash/restart and inter-process locking test. */
public final class R221_CrashAndLockRegression {
   private static int cases;
   static class SimulatedCrash extends Error {
      SimulatedCrash(String phase) { super("simulated JVM crash after " + phase); }
   }
   private static void check(boolean value, String why) { if (!value) throw new AssertionError(why); }
   private static void initial(Path root) throws IOException {
      Files.createDirectories(root.resolve("sprites"));
      Files.createDirectories(root.resolve("configs"));
      Files.writeString(root.resolve("cache.dat"), "old");
      Files.writeString(root.resolve("sprites/icon"), "sprites-preserved");
      Files.writeString(root.resolve("configs/view"), "configs-preserved");
      Files.writeString(root.resolve("versions.dat"), "version-preserved");
   }
   private static File downloaded(File file) throws IOException {
      Files.writeString(file.toPath(), "fake-offline-archive"); return file;
   }
   private static boolean extracted(String directory, File archive) throws IOException {
      Files.writeString(Path.of(directory, "cache.dat"), "new"); return true;
   }
   private static void oldIsIntact(Path root) throws IOException {
      check(Files.readString(root.resolve("cache.dat")).equals("old"), "old cache not restored");
      check(Files.readString(root.resolve("sprites/icon")).equals("sprites-preserved"), "sprite missing");
      check(Files.readString(root.resolve("configs/view")).equals("configs-preserved"), "config missing");
      check(Files.readString(root.resolve("versions.dat")).equals("version-preserved"), "version missing");
   }
   private static void noJournal(Path parent) throws IOException {
      try (Stream<Path> paths = Files.list(parent)) {
         check(paths.noneMatch(p -> p.getFileName().toString().startsWith(".spk-cache-update-")),
            "staging/journal residue remains");
      }
   }
   private static void crashBackup(Path root) throws IOException {
      try {
         CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
            R221_CrashAndLockRegression::extracted,
            () -> { throw new SimulatedCrash("backup move"); });
         throw new AssertionError("Expected backup-stage JVM crash");
      } catch (SimulatedCrash expected) { }
      check(!Files.exists(root), "backup crash unexpectedly preserved live directory");
      CacheUpdateTransaction.recover(root.toFile());
      oldIsIntact(root); noJournal(root.getParent()); cases++;
   }
   private static void crashPromotion(Path root) throws IOException {
      try {
         CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
            R221_CrashAndLockRegression::extracted,
            () -> { }, () -> { throw new SimulatedCrash("promotion move"); });
         throw new AssertionError("Expected post-promotion JVM crash");
      } catch (SimulatedCrash expected) { }
      check(Files.readString(root.resolve("cache.dat")).equals("new"), "promotion crash not triggered");
      CacheUpdateTransaction.recover(root.toFile());
      oldIsIntact(root); noJournal(root.getParent()); cases++;
   }
   private static void failedPromotion(Path root) throws IOException {
      try {
         CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
            R221_CrashAndLockRegression::extracted,
            () -> { throw new IOException("injected fault"); });
         throw new AssertionError("Expected rollback exception");
      } catch (IOException expected) { }
      oldIsIntact(root); noJournal(root.getParent()); cases++;
   }
   private static void simultaneousThreads(Path root) throws Exception {
      java.util.concurrent.CountDownLatch entered = new java.util.concurrent.CountDownLatch(1);
      java.util.concurrent.CountDownLatch release = new java.util.concurrent.CountDownLatch(1);
      java.util.concurrent.atomic.AtomicReference<Throwable> workerError = new java.util.concurrent.atomic.AtomicReference<>();
      Thread worker = new Thread(() -> {
         try {
            CacheUpdateTransaction.install(root.toFile(), destination -> {
               entered.countDown();
               try { release.await(); } catch (InterruptedException e) { Thread.currentThread().interrupt(); throw new IOException(e); }
               return null;
            }, (dir,zip) -> true);
         } catch (Throwable error) { workerError.set(error); }
      }, "r221-stalled-transfer");
      worker.start();
      try {
         check(entered.await(5, java.util.concurrent.TimeUnit.SECONDS), "lock-holder thread did not start");
         try {
            CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
               R221_CrashAndLockRegression::extracted);
            throw new AssertionError("Simultaneous Java threads overlapped cache update");
         } catch (IOException expected) {
            check(expected.getMessage().contains("Another client"), "Unexpected concurrent error: " + expected);
         }
      } finally {
         release.countDown(); worker.join(5000);
      }
      check(!worker.isAlive() && workerError.get() == null, "lock-holder failed " + workerError.get());
      oldIsIntact(root); noJournal(root.getParent()); cases++;
   }
   private static String javaExecutable() {
      return System.getProperty("java.home") + File.separator + "bin" + File.separator
         + (System.getProperty("os.name").toLowerCase().contains("win") ? "java.exe" : "java");
   }
   private static void secondProcess(Path root) throws Exception {
      Process child = new ProcessBuilder(javaExecutable(),
         "-cp", System.getProperty("java.class.path"), R221_CrashAndLockRegression.class.getName(),
         "hold", root.toString()).redirectErrorStream(true).start();
      try {
         int ready = child.getInputStream().read();
         check(ready == 'L', "child failed to acquire lock; first output byte=" + ready);
         try {
            CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
               R221_CrashAndLockRegression::extracted);
            throw new AssertionError("Second process entered protected cache");
         } catch (IOException expected) {
            check(expected.getMessage().contains("Another client"), "Unexpected subprocess lock error");
         }
         child.getOutputStream().write(1);
         child.getOutputStream().flush();
         check(child.waitFor(10, java.util.concurrent.TimeUnit.SECONDS) && child.exitValue() == 0,
            "Lock-holder subprocess failed");
      } finally {
         if (child.isAlive()) child.destroyForcibly();
      }
      oldIsIntact(root); noJournal(root.getParent()); cases++;
   }
   private static void hold(Path root) throws IOException {
      CacheUpdateTransaction.install(root.toFile(), dest -> {
         System.out.write('L'); System.out.flush();
         System.in.read();
         return null;
      }, (dir,zip) -> true);
   }
   private static void hardKill(Path root, String phase) throws Exception {
      Process child = new ProcessBuilder(javaExecutable(), "-cp", System.getProperty("java.class.path"),
         R221_CrashAndLockRegression.class.getName(), "halt", root.toString(), phase)
         .redirectErrorStream(true).start();
      try {
         check(child.waitFor(12, java.util.concurrent.TimeUnit.SECONDS), "Hard-kill child hung");
         check(child.exitValue() == 71, "Hard-kill child unexpectedly exited " + child.exitValue());
         CacheUpdateTransaction.recover(root.toFile());
         oldIsIntact(root); noJournal(root.getParent()); cases++;
      } finally {
         if (child.isAlive()) child.destroyForcibly();
      }
   }
   private static void halt(Path root, String phase) throws Exception {
      if (phase.equals("after-backup")) {
         CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
            R221_CrashAndLockRegression::extracted,
            () -> { Runtime.getRuntime().halt(71); });
      } else if (phase.equals("after-promotion")) {
         CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
            R221_CrashAndLockRegression::extracted,
            () -> { }, () -> { Runtime.getRuntime().halt(71); });
      } else { throw new IllegalArgumentException(phase); }
      throw new AssertionError("Hard-kill hook not invoked");
   }
   private static void noOriginal(Path parent) throws IOException {
      Path root = parent.resolve("fresh-cache");
      try {
         CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
            R221_CrashAndLockRegression::extracted, () -> { },
            () -> { throw new SimulatedCrash("initial installation"); });
         throw new AssertionError("New root crash not detected");
      } catch (SimulatedCrash expected) { }
      CacheUpdateTransaction.recover(root.toFile());
      check(!Files.exists(root), "Previously absent cache not restored to absence");
      noJournal(parent); cases++;
      check(CacheUpdateTransaction.install(root.toFile(), R221_CrashAndLockRegression::downloaded,
         R221_CrashAndLockRegression::extracted), "Fresh install failed");
      check(Files.readString(root.resolve("cache.dat")).equals("new"), "Fresh root wrong");
      noJournal(parent); cases++;
   }
   private static void unknownBackupMustNotBeDeleted(Path parent) throws IOException {
      Path work = Files.createDirectory(parent.resolve(".spk-cache-update-legacy"));
      Files.createDirectory(work.resolve("previous"));
      Files.writeString(work.resolve("previous/precious.dat"), "old");
      try {
         CacheUpdateTransaction.recover(parent.resolve("cache").toFile());
         throw new AssertionError("Unknown legacy backup silently discarded");
      } catch (IOException expected) {
         check(Files.readString(work.resolve("previous/precious.dat")).equals("old"), "Legacy backup changed");
      }
      cases++;
   }
   public static void main(String[] args) throws Exception {
      if (args.length > 0 && args[0].equals("hold")) { hold(Path.of(args[1])); return; }
      if (args.length > 0 && args[0].equals("halt")) { halt(Path.of(args[1]), args[2]); return; }
      Path parent = Files.createTempDirectory("r221-cache-crash-lock-");
      Path cache = parent.resolve("cache");
      initial(cache);
      crashBackup(cache);
      crashPromotion(cache);
      hardKill(cache, "after-backup");
      hardKill(cache, "after-promotion");
      failedPromotion(cache);
      simultaneousThreads(cache);
      secondProcess(cache);
      noOriginal(parent);
      unknownBackupMustNotBeDeleted(parent);
      System.out.println("R221_CRASH_LOCK_RECOVERY_PASS cases=" + cases);
   }
}

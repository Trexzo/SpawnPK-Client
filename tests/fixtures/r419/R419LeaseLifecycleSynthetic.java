import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * R419 invented Java 11 lifecycle model, not recovered-client source.
 * Uses R418's real FileChannel.tryLock model against TEMP test directories.
 * No player-history files are read, parsed, written, renamed or removed.
 */
public final class R419LeaseLifecycleSynthetic {
   static final class Controller {
      private final Path directory;
      private long epoch;
      private boolean accepting;
      private R418SingleWriterModel.Lease lease;
      private final AtomicInteger modeledCommits = new AtomicInteger();
      private Thread closeWorker;

      Controller(Path directory) { this.directory = directory; }

      synchronized long start() {
         epoch++;
         accepting = true;
         return epoch;
      }

      boolean activate(long expectedEpoch) throws IOException {
         // Always acquire outside the state monitor (and never on EDT).
         R418SingleWriterModel.Lease candidate = R418SingleWriterModel.acquire(directory);
         if (candidate == null) return false;
         synchronized (this) {
            if (!accepting || expectedEpoch != epoch || lease != null) {
               candidate.close();
               return false;
            }
            lease = candidate;
            return true;
         }
      }

      synchronized boolean emit(long expectedEpoch) {
         if (!accepting || epoch != expectedEpoch || lease == null)
            return false;
         final R418SingleWriterModel.Lease admitted = lease;
         final UUID token = admitted.session();
         return admitted.apply(token, modeledCommits::incrementAndGet);
      }

      synchronized boolean restore(long expectedEpoch) {
         if (!accepting || epoch != expectedEpoch || lease == null)
            return false;
         return lease.permit(lease.session());
      }

      void stop() {
         final R418SingleWriterModel.Lease prior;
         synchronized (this) {
            epoch++;
            accepting = false;
            prior = lease;
            lease = null;
         }
         if (prior == null) return;
         closeWorker = new Thread(() -> {
            try { prior.close(); }
            catch (IOException ignored) { /* Synthetic fail-closed mode. */ }
         }, "R419-Synthetic-Lease-Reaper");
         closeWorker.setDaemon(true);
         closeWorker.start();
      }

      void awaitRelease() throws InterruptedException {
         Thread t = closeWorker;
         if (t != null) t.join(5000);
         if (t != null && t.isAlive())
            throw new AssertionError("lease-close-must-not-hang");
      }

      synchronized int commits() { return modeledCommits.get(); }
   }

   static void check(boolean condition, String reason) {
      if (!condition) throw new AssertionError(reason);
   }

   static int run(Path directory) throws Exception {
      int passed = 0;
      Controller a = new Controller(directory);
      final long s1 = a.start();
      check(s1 > 0, "epoch-positive"); passed++;
      check(a.activate(s1), "first-worker-admitted"); passed++;
      check(a.restore(s1), "first-restore-admitted"); passed++;
      check(a.emit(s1), "first-commit"); passed++;
      check(a.commits() == 1, "first-commit-count"); passed++;
      check(!a.emit(s1 + 1), "future-epoch-denied"); passed++;
      check(!a.emit(s1 - 1), "old-epoch-denied"); passed++;
      check(!a.activate(s1), "duplicate-acquisition-denied"); passed++;
      Controller b = new Controller(directory);
      final long sb = b.start();
      check(!b.activate(sb), "competing-owner-denied"); passed++;
      check(b.commits() == 0, "competitor-never-wrote"); passed++;
      a.stop();
      check(!a.emit(s1), "old-callback-after-stop-denied"); passed++;
      check(!a.restore(s1), "old-restore-after-stop-denied"); passed++;
      a.awaitRelease();
      check(Files.isRegularFile(directory.resolve(R418SingleWriterModel.LOCK_NAME),
                               LinkOption.NOFOLLOW_LINKS),
            "release-kept-lock-path"); passed++;
      check(b.activate(sb), "competitor-after-release-admitted"); passed++;
      check(b.emit(sb), "new-owner-action-admitted"); passed++;
      check(a.commits() == 1, "old-owner-not-resurrected"); passed++;
      b.stop(); b.awaitRelease();
      final long s2 = a.start();
      check(s2 != s1, "session-rotated"); passed++;
      check(a.activate(s2), "restart-reacquired"); passed++;
      check(!a.emit(s1), "retired-generation-rejected"); passed++;
      check(a.emit(s2), "new-generation-admitted"); passed++;
      check(a.commits() == 2, "no-duplicate-old-commit"); passed++;
      a.stop(); a.awaitRelease();
      check(!a.emit(s2), "stopped-generation-stays-dead"); passed++;

      // A delayed activation from a retired session MUST NOT publish
      // the acquired OS lock into the new session's ownership field.
      Controller c = new Controller(directory);
      final long old = c.start();
      c.stop();
      final long now = c.start();
      check(!c.activate(old), "stale-startup-worker-refused"); passed++;
      check(c.activate(now), "current-startup-worker-admitted"); passed++;
      c.stop(); c.awaitRelease();

      check(!Files.exists(directory.resolve("loot-history.json")),
            "no-synthetic-history-created"); passed++;
      check(!Files.exists(directory.resolve("loot-history.delete.intent")),
            "no-marker-created"); passed++;
      return passed;
   }

   public static void main(String[] args) throws Exception {
      if (args.length != 2 || !"selftest".equals(args[0]))
         throw new IllegalArgumentException("selftest <fabricated TEMP directory>");
      Path directory = Paths.get(args[1]);
      System.out.println("R419_SYNTHETIC_LIFECYCLE_PASS assertions=" + run(directory));
   }
}

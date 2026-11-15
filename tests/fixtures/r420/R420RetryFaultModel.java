import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import javax.swing.SwingUtilities;

/**
 * R420 Java 11 TEMP-only fault model using actual R418 cooperative OS FileLock.
 * Synthetic session, no game, no recovered code, no loot history read/write.
 */
public final class R420RetryFaultModel {
    static final long[] RETRY_DELAY_MS = {0L, 75L, 150L, 300L, 450L};

    static final class Session {
        long epoch;
        boolean active;
        R418SingleWriterModel.Lease owner;

        synchronized long start() {
            epoch++;
            active = true;
            return epoch;
        }

        synchronized void invalidate() {
            active = false;
            epoch++;
        }

        synchronized boolean valid(long captured) {
            return active && epoch == captured;
        }

        synchronized void close() throws IOException {
            invalidate();
            if (owner != null) {
                owner.close();
                owner = null;
            }
        }
    }

    static final class Outcome {
        final String status;
        final int attempts;
        final boolean interruptedPreserved;
        Outcome(String status, int attempts, boolean interruptedPreserved) {
            this.status = status;
            this.attempts = attempts;
            this.interruptedPreserved = interruptedPreserved;
        }
        public String toString() { return status + " attempts=" + attempts; }
    }

    /** Worker-only. No history gate held during sleep or nonblocking OS tryLock. */
    static Outcome retry(Path directory, Session state, long expected) {
        if (SwingUtilities.isEventDispatchThread())
            return new Outcome("EDT_REFUSED", 0, false);
        int attempts = 0;
        for (long delay : RETRY_DELAY_MS) {
            if (delay > 0) {
                try {
                    Thread.sleep(delay);
                } catch (InterruptedException canceled) {
                    Thread.currentThread().interrupt();
                    return new Outcome("INTERRUPTED", attempts,
                                       Thread.currentThread().isInterrupted());
                }
            }
            if (Thread.currentThread().isInterrupted())
                return new Outcome("INTERRUPTED", attempts, true);
            synchronized (state) {
                if (!state.valid(expected))
                    return new Outcome("STALE", attempts, false);
            }
            attempts++;
            R418SingleWriterModel.Lease lease = R418SingleWriterModel.acquire(directory);
            if (lease == null) continue;
            synchronized (state) {
                if (!state.valid(expected) || state.owner != null) {
                    try { lease.close(); }
                    catch (IOException error) { throw new IllegalStateException(error); }
                    return new Outcome("STALE", attempts, false);
                }
                state.owner = lease;
                return new Outcome("ACQUIRED", attempts, false);
            }
        }
        return new Outcome("BUSY", attempts, false);
    }

    static void require(boolean truth, String message) {
        if (!truth) throw new AssertionError(message);
    }

    static void print(Outcome outcome) { System.out.println(outcome); }

    static void stalledWriteClose(Path directory) throws Exception {
        R418SingleWriterModel.Lease owner = R418SingleWriterModel.acquire(directory);
        require(owner != null, "must-acquire");
        UUID session = owner.session();
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch releaseAction = new CountDownLatch(1);
        CountDownLatch released = new CountDownLatch(1);
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread writer = new Thread(() -> {
            try {
                require(owner.apply(session, () -> {
                    entered.countDown();
                    try {
                        if (!releaseAction.await(5, TimeUnit.SECONDS))
                            throw new AssertionError("writer-blocked-too-long");
                    } catch (InterruptedException canceled) {
                        Thread.currentThread().interrupt();
                        throw new AssertionError(canceled);
                    }
                }), "action-was-not-admitted");
            } catch (Throwable error) {
                failure.set(error);
            }
        }, "R420-Blocked-Synthetic-Write");
        writer.setDaemon(true);
        writer.start();
        require(entered.await(2, TimeUnit.SECONDS), "writer-did-not-enter");

        Thread closer = new Thread(() -> {
            try { owner.close(); } catch (Throwable error) { failure.set(error); }
            finally { released.countDown(); }
        }, "R420-Reaper");
        closer.setDaemon(true);
        closer.start();
        // The simulated UI thread schedules the close and returns without
        // synchronously waiting for an in-flight write to complete.
        require(!released.await(80, TimeUnit.MILLISECONDS),
                "should-not-release-while-action-is-active");
        releaseAction.countDown();
        require(released.await(2, TimeUnit.SECONDS), "close-did-not-complete");
        writer.join(1500);
        require(!writer.isAlive(), "writer-still-running");
        require(failure.get() == null, "blocked-write-failure: " + failure.get());
        require(!owner.permit(session), "old-session-survived-close");
        R418SingleWriterModel.Lease next = R418SingleWriterModel.acquire(directory);
        require(next != null, "next-process-lock-not-reacquirable");
        next.close();
        require(!Files.exists(directory.resolve("loot-history.json")),
                "should-not-generate-player-history");
        System.out.println("HELD_WRITE_RELEASE_SAFE");
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2)
            throw new IllegalArgumentException("<probe|retry|busy|invalidate|interrupt|edt|held-write|fresh> <TEMP dir>");
        String mode = args[0];
        Path directory = Paths.get(args[1]);
        if ("held-write".equals(mode)) {
            stalledWriteClose(directory);
            return;
        }
        Session state = new Session();
        long gen = state.start();
        if ("invalidate".equals(mode) || "interrupt".equals(mode)) {
            CountDownLatch started = new CountDownLatch(1);
            AtomicReference<Outcome> result = new AtomicReference<>();
            Thread worker = new Thread(() -> {
                started.countDown();
                result.set(retry(directory, state, gen));
            }, "R420-Synthetic-Worker");
            worker.start();
            require(started.await(2, TimeUnit.SECONDS), "worker-never-started");
            Thread.sleep(125L);
            if ("interrupt".equals(mode)) worker.interrupt();
            else state.invalidate();
            worker.join(4000);
            require(!worker.isAlive(), "canceled-worker-stuck");
            print(result.get());
            state.close();
            return;
        }
        if ("edt".equals(mode)) {
            AtomicReference<Outcome> result = new AtomicReference<>();
            SwingUtilities.invokeAndWait(() -> result.set(retry(directory, state, gen)));
            print(result.get());
            state.close();
            return;
        }
        Outcome result = retry(directory, state, gen);
        print(result);
        state.close();
    }
}

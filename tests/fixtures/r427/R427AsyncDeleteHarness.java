package rs.plugins.loottracker;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.BooleanSupplier;
import javax.swing.SwingUtilities;

/** Public-only synthetic harness. Never opens/executes a private client. */
public final class R427AsyncDeleteHarness {
    private static final long WAIT_SECONDS = 7;
    private static int passed;

    private static void check(boolean ok, String label) {
        if (!ok) throw new AssertionError("R427_FAILURE_" + label);
        passed++;
    }

    private static <T> T edt(Callable<T> action) throws Exception {
        FutureTask<T> task = new FutureTask<>(action);
        SwingUtilities.invokeAndWait(task);
        try {
            return task.get(WAIT_SECONDS, TimeUnit.SECONDS);
        } catch (ExecutionException wrapped) {
            // FutureTask wraps a deliberate EDT-side invalid-input
            // exception. Preserve the original type for negative tests.
            Throwable cause = wrapped.getCause();
            if (cause instanceof RuntimeException) throw (RuntimeException) cause;
            if (cause instanceof Error) throw (Error) cause;
            if (cause instanceof Exception) throw (Exception) cause;
            throw wrapped;
        }
    }

    private static final class TestSession implements R427AsyncDeleteCoordinator.Session {
        final AtomicLong epoch = new AtomicLong(44);
        final AtomicBoolean active = new AtomicBoolean(true);
        @Override public long currentEpoch() { return epoch.get(); }
        @Override public boolean accepts(long generation) {
            return active.get() && epoch.get() == generation;
        }
        void invalidate() { epoch.incrementAndGet(); active.set(false); }
    }

    private static final class TestStore implements R427AsyncDeleteCoordinator.Store {
        final CountDownLatch entered = new CountDownLatch(1);
        final CountDownLatch release = new CountDownLatch(1);
        final AtomicInteger calls = new AtomicInteger();
        final AtomicBoolean ownerReleased = new AtomicBoolean();
        final AtomicBoolean releaseOnEdt = new AtomicBoolean();
        final AtomicBoolean commitOnEdt = new AtomicBoolean();
        final AtomicBoolean commitOnDaemon = new AtomicBoolean();
        final AtomicBoolean durable = new AtomicBoolean();
        final AtomicBoolean commitInProgress = new AtomicBoolean();
        volatile boolean block;
        volatile boolean recheckAdmission = true;
        volatile boolean throwAfterWrite;
        volatile boolean throwErrorAfterWrite;
        volatile boolean failCloseWithError;
        volatile boolean failCloseWithException;
        volatile R427AsyncDeleteCoordinator.Outcome next =
            R427AsyncDeleteCoordinator.Outcome.CONFIRMED;
        volatile List<String> lastKeys = Collections.emptyList();
        volatile Path testFile;

        @Override public R427AsyncDeleteCoordinator.Outcome commit(
                R427AsyncDeleteCoordinator.Request request,
                BooleanSupplier admission) throws Exception {
            commitOnEdt.set(SwingUtilities.isEventDispatchThread());
            commitOnDaemon.set(Thread.currentThread().isDaemon());
            if (!admission.getAsBoolean()) {
                return R427AsyncDeleteCoordinator.Outcome.REFUSED;
            }
            calls.incrementAndGet();
            commitInProgress.set(true);
            try {
                lastKeys = request.keys;
                entered.countDown();
                if (block && !release.await(WAIT_SECONDS, TimeUnit.SECONDS)) {
                    throw new IOException("synthetic-gate-timeout");
                }
                if (recheckAdmission && !admission.getAsBoolean()) {
                    return R427AsyncDeleteCoordinator.Outcome.REFUSED;
                }
                if (testFile != null) {
                    // Synthetic filesystem receipt, never production history.
                    try (FileChannel ch = FileChannel.open(testFile,
                            StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                        ByteBuffer bytes = ByteBuffer.wrap(
                            "fabricated-durable-deletion-receipt".getBytes(
                                StandardCharsets.US_ASCII));
                        while (bytes.hasRemaining()) ch.write(bytes);
                        ch.force(true);
                    }
                    durable.set(true);
                } else if (next == R427AsyncDeleteCoordinator.Outcome.CONFIRMED) {
                    durable.set(true);
                }
                if (throwAfterWrite) {
                    throw new IOException("synthetic-ambiguous-post-write-crash");
                }
                if (throwErrorAfterWrite) {
                    throw new AssertionError("synthetic-post-write-assertion-error");
                }
                return next;
            } finally {
                commitInProgress.set(false);
            }
        }

        @Override public void closeOwner() {
            releaseOnEdt.set(SwingUtilities.isEventDispatchThread());
            if (commitInProgress.get()) {
                throw new AssertionError("release-overtook-durable-commit");
            }
            if (failCloseWithError) {
                throw new AssertionError("synthetic-owner-release-error");
            }
            if (failCloseWithException) {
                throw new IllegalStateException("synthetic-owner-release-exception");
            }
            ownerReleased.set(true);
        }
    }

    private static final class TestView implements R427AsyncDeleteCoordinator.View {
        final AtomicLong currentVersion = new AtomicLong(4);
        final AtomicInteger applied = new AtomicInteger();
        final AtomicInteger reload = new AtomicInteger();
        final AtomicInteger refused = new AtomicInteger();
        final AtomicInteger uncertain = new AtomicInteger();
        final AtomicInteger closed = new AtomicInteger();
        final AtomicBoolean wrongThread = new AtomicBoolean();
        final AtomicBoolean appliedBeforeDurable = new AtomicBoolean();
        final CountDownLatch result = new CountDownLatch(1);
        final CountDownLatch released = new CountDownLatch(1);
        final TestStore store;
        volatile R427AsyncDeleteCoordinator.Request lastRequest;
        volatile Throwable closeFailure;

        TestView(TestStore store) { this.store = store; }
        void checkThread() {
            if (!SwingUtilities.isEventDispatchThread()) wrongThread.set(true);
        }
        @Override public long version() { checkThread(); return currentVersion.get(); }
        @Override public void applyConfirmed(R427AsyncDeleteCoordinator.Request request) {
            checkThread();
            if (!store.durable.get()) appliedBeforeDurable.set(true);
            lastRequest = request;
            applied.incrementAndGet();
            result.countDown();
        }
        @Override public void confirmedButNeedsReload(
                R427AsyncDeleteCoordinator.Request request) {
            checkThread(); lastRequest = request; reload.incrementAndGet();
            result.countDown();
        }
        @Override public void refused(R427AsyncDeleteCoordinator.Request request) {
            checkThread(); refused.incrementAndGet(); result.countDown();
        }
        @Override public void uncertainAndQuarantine(
                R427AsyncDeleteCoordinator.Request request) {
            checkThread(); uncertain.incrementAndGet(); result.countDown();
        }
        @Override public void ownerClosed(Throwable error) {
            checkThread(); closeFailure = error;
            closed.incrementAndGet(); released.countDown();
        }
    }

    private static final class Fixture {
        final TestStore store = new TestStore();
        final TestSession session = new TestSession();
        final TestView view = new TestView(store);
        final R427AsyncDeleteCoordinator coordinator =
            new R427AsyncDeleteCoordinator(session, store, view);

        boolean submit(R427AsyncDeleteCoordinator.Kind kind, String... keys)
                throws Exception {
            return edt(() -> coordinator.submit(kind, Arrays.asList(keys)));
        }
        void awaitCommit() throws Exception {
            check(store.entered.await(WAIT_SECONDS, TimeUnit.SECONDS), "worker-started");
        }
        void awaitResult() throws Exception {
            check(view.result.await(WAIT_SECONDS, TimeUnit.SECONDS), "edt-delivered");
        }
        void shutdown() throws Exception {
            CompletableFuture<Void> done = edt(coordinator::closeAsync);
            done.get(WAIT_SECONDS, TimeUnit.SECONDS);
            check(view.released.await(WAIT_SECONDS, TimeUnit.SECONDS), "closed-event");
        }
    }

    static void successfulReceipt() throws Exception {
        Fixture f = new Fixture();
        f.store.block = true;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitCommit();
        check(f.view.applied.get() == 0, "no-optimistic-ui");
        check(f.coordinator.isPending(), "single-flight-active");
        f.store.release.countDown();
        f.awaitResult();
        check(f.view.applied.get() == 1, "one-confirmed-ui-update");
        check(!f.view.appliedBeforeDurable.get(), "durable-before-apply");
        check(!f.store.commitOnEdt.get(), "commit-not-edt");
        check(!f.store.commitOnDaemon.get(), "accepted-commit-non-daemon");
        check(!f.view.wrongThread.get(), "callbacks-on-edt");
        f.shutdown();
        check(f.store.ownerReleased.get(), "owner-released");
        check(!f.store.releaseOnEdt.get(), "owner-close-not-edt");
    }

    static void edtRemainsResponsive() throws Exception {
        Fixture f = new Fixture();
        f.store.block = true;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitCommit();
        // The disk worker remains deliberately stalled here, yet Swing's
        // real Event Dispatch Thread must still dispatch an input callback.
        boolean tick = edt(() -> SwingUtilities.isEventDispatchThread());
        check(tick, "edt-served-during-blocking-disk-operation");
        check(f.view.applied.get() == 0, "no-premature-panel-mutation");
        f.store.release.countDown();
        f.awaitResult();
        f.shutdown();
    }

    static void immutableStableIds() throws Exception {
        Fixture f = new Fixture();
        f.store.block = true;
        List<String> editable = new ArrayList<>(Arrays.asList("id-7", "id-9", "id-7"));
        check(edt(() -> f.coordinator.submit(
            R427AsyncDeleteCoordinator.Kind.RECORD_IDS, editable)), "accepted");
        editable.set(0, "mutated-id");
        editable.add("post-capture");
        f.awaitCommit();
        check(f.store.lastKeys.equals(Arrays.asList("id-7", "id-9")),
            "deduped-stable-id-snapshot");
        boolean immutable = false;
        try { f.store.lastKeys.add("should-fail"); }
        catch (UnsupportedOperationException expected) { immutable = true; }
        check(immutable, "immutable-request");
        f.store.release.countDown();
        f.awaitResult();
        f.shutdown();
    }

    static void rejectConcurrent() throws Exception {
        Fixture f = new Fixture();
        f.store.block = true;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.SOURCE_KEY, "dragon"),
            "first-accepted");
        f.awaitCommit();
        check(!f.submit(R427AsyncDeleteCoordinator.Kind.SOURCE_KEY, "demon"),
            "second-blocked-while-first-busy");
        f.store.release.countDown();
        f.awaitResult();
        check(f.store.calls.get() == 1, "one-worker-commit");
        f.shutdown();
    }

    static void refusedDoesNotChangeUi() throws Exception {
        Fixture f = new Fixture();
        f.store.next = R427AsyncDeleteCoordinator.Outcome.REFUSED;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.TYPE_KEY, "rare"), "accepted");
        f.awaitResult();
        check(f.view.applied.get() == 0 && f.view.refused.get() == 1,
            "refusal-no-panel-edit");
        check(!f.coordinator.isQuarantined(), "definite-refusal-not-uncertain");
        f.shutdown();
    }

    static void uncertainQuarantines() throws Exception {
        Fixture f = new Fixture();
        f.store.next = R427AsyncDeleteCoordinator.Outcome.UNCERTAIN;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitResult();
        check(f.coordinator.isQuarantined(), "quarantined");
        check(f.view.applied.get() == 0 && f.view.uncertain.get() == 1,
              "uncertain-no-panel-edit");
        check(!f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "no-blind-retry");
        check(f.store.calls.get() == 1, "exactly-one-attempt");
        f.shutdown();
    }

    static void thrownAfterWriteIsUncertain() throws Exception {
        Fixture f = new Fixture();
        f.store.throwAfterWrite = true;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitResult();
        check(f.store.durable.get(), "fake-write-happened");
        check(f.view.applied.get() == 0, "no-unverified-ui-remove");
        check(f.coordinator.isQuarantined(), "post-write-throw-quarantined");
        f.shutdown();
    }

    static void changedUiVersionRequiresReload() throws Exception {
        Fixture f = new Fixture();
        f.store.block = true;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.RECORD_IDS, "id-77"),
            "accepted");
        f.awaitCommit();
        edt(() -> { f.view.currentVersion.incrementAndGet(); return null; });
        f.store.release.countDown();
        f.awaitResult();
        check(f.view.applied.get() == 0, "stale-row-does-not-apply");
        check(f.view.reload.get() == 1, "reload-required");
        f.shutdown();
    }

    static void sessionRolloverRejectsCallback() throws Exception {
        Fixture f = new Fixture();
        f.store.block = true;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitCommit();
        f.session.invalidate();
        f.store.release.countDown();
        // A stale callback must not call the View, even if it executes later.
        edt(() -> null);
        check(!f.session.active.get(), "session-invalid");
        f.shutdown();
        edt(() -> null);
        check(f.view.applied.get() == 0 && f.view.reload.get() == 0 &&
              f.view.refused.get() == 0, "stale-session-view-untouched");
    }

    static void earlySessionRejection() throws Exception {
        Fixture f = new Fixture();
        f.session.invalidate();
        check(!f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL),
              "rejected-before-enqueue");
        check(f.store.calls.get() == 0, "no-worker-commit");
        f.shutdown();
    }

    static void closeDrainsCommit() throws Exception {
        Fixture f = new Fixture();
        f.store.block = true;
        f.store.recheckAdmission = false; // Synthetic in-flight durable write.
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitCommit();
        CompletableFuture<Void> close = edt(f.coordinator::closeAsync);
        check(f.coordinator.isClosed(), "closed-immediately");
        check(!close.isDone(), "close-does-not-overtake-commit");
        check(!f.store.ownerReleased.get(), "owner-still-held");
        check(!f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL),
              "closed-rejects-new-request");
        f.store.release.countDown();
        close.get(WAIT_SECONDS, TimeUnit.SECONDS);
        check(f.view.released.await(WAIT_SECONDS, TimeUnit.SECONDS), "release-event");
        edt(() -> null);
        check(f.store.ownerReleased.get(), "owner-released-after-commit");
        check(f.view.applied.get() == 0, "shutdown-no-stale-ui-apply");
        check(!f.store.releaseOnEdt.get(), "release-off-edt");
    }

    static void closeWithoutRequest() throws Exception {
        Fixture f = new Fixture();
        f.shutdown();
        check(f.store.ownerReleased.get(), "no-request-owner-release");
        check(!f.coordinator.isPending(), "never-busy");
        check(!f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL),
            "closed-does-not-accept");
        CompletableFuture<Void> again = edt(f.coordinator::closeAsync);
        check(again.isDone(), "idempotent-close-future");
        check(f.view.closed.get() == 1, "single-close-event");
    }

    static void rejectNonEdt() throws Exception {
        Fixture f = new Fixture();
        boolean rejectedSubmit = false;
        try { f.coordinator.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL,
                                   Collections.emptyList()); }
        catch (IllegalStateException expected) { rejectedSubmit = true; }
        check(rejectedSubmit, "background-request-refused");
        boolean rejectedClose = false;
        try { f.coordinator.closeAsync(); }
        catch (IllegalStateException expected) { rejectedClose = true; }
        check(rejectedClose, "background-close-refused");
        f.shutdown();
    }

    static void validation() throws Exception {
        Fixture f = new Fixture();
        for (String invalid : new String[]{"", "bad ", " bad"}) {
            boolean rejected = false;
            try { f.submit(R427AsyncDeleteCoordinator.Kind.RECORD_IDS, invalid); }
            catch (IllegalArgumentException expected) { rejected = true; }
            check(rejected, "invalid-key-refused");
        }
        boolean rejectedEmpty = false;
        try { f.submit(R427AsyncDeleteCoordinator.Kind.RECORD_IDS); }
        catch (IllegalArgumentException expected) { rejectedEmpty = true; }
        check(rejectedEmpty, "empty-records-refused");
        boolean rejectedClearKey = false;
        try { f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL, "bad"); }
        catch (IllegalArgumentException expected) { rejectedClearKey = true; }
        check(rejectedClearKey, "clear-has-no-selector");
        boolean rejectedSourceCount = false;
        try { f.submit(R427AsyncDeleteCoordinator.Kind.SOURCE_KEY, "a", "b"); }
        catch (IllegalArgumentException expected) { rejectedSourceCount = true; }
        check(rejectedSourceCount, "source-requires-single-key");
        check(!f.coordinator.isPending(), "bad-requests-never-queued");
        f.shutdown();
    }

    static void realSyntheticFileReceipt(Path scratch) throws Exception {
        Fixture f = new Fixture();
        Path file = scratch.resolve("R427-fabricated-durable-receipt.bin");
        if (Files.exists(file, LinkOption.NOFOLLOW_LINKS)) {
            throw new IllegalArgumentException("R427_EXISTING_SYNTHETIC_OUTPUT");
        }
        f.store.block = true;
        f.store.testFile = file;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitCommit();
        check(!Files.exists(file, LinkOption.NOFOLLOW_LINKS),
              "no-file-before-worker-unblocked");
        f.store.release.countDown();
        f.awaitResult();
        check(Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS),
              "durable-fake-file-exists");
        check(Files.readAllBytes(file).length > 0, "fake-receipt-has-bytes");
        check(f.view.applied.get() == 1 && !f.view.appliedBeforeDurable.get(),
              "ui-after-fsynced-fake-receipt");
        f.shutdown();
    }

    /** A deadline reports overdue progress but cannot release held I/O. */
    static void closeDeadlineKeepsOwner() throws Exception {
        Fixture f = new Fixture();
        f.store.block = true;
        f.store.recheckAdmission = false;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitCommit();

        AtomicBoolean observationOffEdt = new AtomicBoolean();
        AtomicInteger observationCount = new AtomicInteger();
        CountDownLatch observationDelivered = new CountDownLatch(1);
        CompletableFuture<R427AsyncDeleteCoordinator.CloseObservation> observation =
            edt(() -> f.coordinator.closeWithDeadline(
                75, TimeUnit.MILLISECONDS, status -> {
                    if (!SwingUtilities.isEventDispatchThread())
                        observationOffEdt.set(true);
                    observationCount.incrementAndGet();
                    observationDelivered.countDown();
                }));
        check(observation.get(WAIT_SECONDS, TimeUnit.SECONDS) ==
            R427AsyncDeleteCoordinator.CloseObservation.UNCONFIRMED_AT_DEADLINE,
            "overdue-only-reported");
        check(observationDelivered.await(WAIT_SECONDS, TimeUnit.SECONDS),
              "callback-delivered-explicitly");
        check(!observationOffEdt.get(), "observation-completed-on-edt");
        check(observationCount.get() == 1, "single-observer-result");
        check(!f.store.ownerReleased.get(), "watchdog-never-releases-lock");
        check(f.store.commitInProgress.get(), "worker-still-holds-commit");
        check(f.coordinator.isClosed(), "new-work-rejected");
        check(!f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL),
              "deadline-cannot-reopen");
        check(edt(() -> SwingUtilities.isEventDispatchThread()),
              "edt-responsive-after-deadline");

        f.store.release.countDown();
        CompletableFuture<Void> finalClose = edt(f.coordinator::closeAsync);
        finalClose.get(WAIT_SECONDS, TimeUnit.SECONDS);
        check(f.view.released.await(WAIT_SECONDS, TimeUnit.SECONDS),
              "eventual-owner-release");
        check(f.store.ownerReleased.get(), "owner-finally-released");
        check(f.view.closed.get() == 1, "single-release-event");
        check(observationCount.get() == 1, "late-release-does-not-repeat-observer");
        check(f.view.applied.get() == 0, "no-stale-ui-apply-after-close");
        CompletableFuture<R427AsyncDeleteCoordinator.CloseObservation> late =
            edt(() -> f.coordinator.closeWithDeadline(3, TimeUnit.SECONDS));
        check(late.get(WAIT_SECONDS, TimeUnit.SECONDS) ==
              R427AsyncDeleteCoordinator.CloseObservation.RELEASE_CONFIRMED,
              "subsequent-observation-reports-real-release");
    }

    static void immediateCloseObserved() throws Exception {
        Fixture f = new Fixture();
        CompletableFuture<R427AsyncDeleteCoordinator.CloseObservation> future =
            edt(() -> f.coordinator.closeWithDeadline(3, TimeUnit.SECONDS));
        check(future.get(WAIT_SECONDS, TimeUnit.SECONDS) ==
              R427AsyncDeleteCoordinator.CloseObservation.RELEASE_CONFIRMED,
              "clean-owner-release-confirmed");
        check(f.view.released.await(WAIT_SECONDS, TimeUnit.SECONDS),
              "close-event-delivered");
        check(f.store.ownerReleased.get(), "owner-released");
        check(f.view.closeFailure == null, "no-close-error");
    }

    static void failingOwnerRelease(boolean asError) throws Exception {
        Fixture f = new Fixture();
        f.store.failCloseWithError = asError;
        f.store.failCloseWithException = !asError;
        CompletableFuture<R427AsyncDeleteCoordinator.CloseObservation> status =
            edt(() -> f.coordinator.closeWithDeadline(3, TimeUnit.SECONDS));
        check(status.get(WAIT_SECONDS, TimeUnit.SECONDS) ==
              R427AsyncDeleteCoordinator.CloseObservation.RELEASE_UNCERTAIN,
              "release-failure-not-confirmed");
        check(f.view.released.await(WAIT_SECONDS, TimeUnit.SECONDS),
              "failure-notification-arrived");
        check(f.view.closeFailure != null,
              "original-release-error-preserved");
        check(f.coordinator.isQuarantined(), "release-failure-quarantines");
        check(!f.store.ownerReleased.get(), "owner-not-claimed-released");
        check(!f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL),
              "failed-shutdown-disallows-new-request");
        CompletableFuture<Void> close = edt(f.coordinator::closeAsync);
        check(close.isCompletedExceptionally(), "real-close-future-not-successful");
    }

    static void postWriteAssertionErrorIsUncertain() throws Exception {
        Fixture f = new Fixture();
        f.store.throwErrorAfterWrite = true;
        check(f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL), "accepted");
        f.awaitResult();
        check(f.store.durable.get(), "synthetic-write-completed-before-error");
        check(f.coordinator.isQuarantined(), "error-after-write-quarantined");
        check(f.view.uncertain.get() == 1, "error-receipt-uncertain");
        check(f.view.applied.get() == 0, "no-optimistic-delete-on-error");
        check(!f.submit(R427AsyncDeleteCoordinator.Kind.CLEAR_ALL),
              "error-refuses-blind-retry");
        f.shutdown();
    }

    static void invalidCloseDeadlines() throws Exception {
        Fixture f = new Fixture();
        boolean zeroRefused = false;
        try {
            edt(() -> f.coordinator.closeWithDeadline(0, TimeUnit.MILLISECONDS));
        } catch (IllegalArgumentException correct) {
            zeroRefused = true;
        }
        check(zeroRefused, "nonpositive-deadline-rejected");
        boolean unitRefused = false;
        try {
            edt(() -> f.coordinator.closeWithDeadline(10, null));
        } catch (IllegalArgumentException correct) {
            unitRefused = true;
        }
        check(unitRefused, "null-timeunit-rejected");
        check(!f.coordinator.isClosed(), "invalid-deadline-does-not-close");
        f.shutdown();
    }

    private static void run(String scenario, Path scratch) throws Exception {
        switch (scenario) {
            case "confirmed": successfulReceipt(); break;
            case "immutable": immutableStableIds(); break;
            case "edt-responsive": edtRemainsResponsive(); break;
            case "single-flight": rejectConcurrent(); break;
            case "refused": refusedDoesNotChangeUi(); break;
            case "uncertain": uncertainQuarantines(); break;
            case "post-write-failure": thrownAfterWriteIsUncertain(); break;
            case "version-drift": changedUiVersionRequiresReload(); break;
            case "stale-session": sessionRolloverRejectsCallback(); break;
            case "early-session": earlySessionRejection(); break;
            case "close-drains": closeDrainsCommit(); break;
            case "close-idempotent": closeWithoutRequest(); break;
            case "off-edt-refusal": rejectNonEdt(); break;
            case "validation": validation(); break;
            case "synthetic-file": realSyntheticFileReceipt(scratch); break;
            case "close-deadline": closeDeadlineKeepsOwner(); break;
            case "close-observed": immediateCloseObserved(); break;
            case "close-exception": failingOwnerRelease(false); break;
            case "close-error": failingOwnerRelease(true); break;
            case "post-write-error": postWriteAssertionErrorIsUncertain(); break;
            case "invalid-deadline": invalidCloseDeadlines(); break;
            default: throw new IllegalArgumentException("R427_UNKNOWN_SCENARIO");
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2)
            throw new IllegalArgumentException("<scenario> <R427-Synthetic-TEMP-root>");
        Path root = Paths.get(args[1]).toAbsolutePath().normalize();
        Path tmp = Paths.get(System.getProperty("java.io.tmpdir"))
            .toAbsolutePath().normalize();
        if (!root.getParent().equals(tmp) || root.getFileName() == null ||
            !root.getFileName().toString().startsWith("R427-Synthetic-") ||
            !Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS) ||
            Files.isSymbolicLink(root))
            throw new IllegalArgumentException("R427_REFUSED_NON_SYNTHETIC_ROOT");
        run(args[0], root);
        System.out.println("R427_"+args[0].toUpperCase().replace('-', '_')+
                           "_PASS assertions="+passed);
    }
}

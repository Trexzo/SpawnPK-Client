package rs.plugins.loottracker;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import java.util.concurrent.Callable;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.FutureTask;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import javax.swing.SwingUtilities;

/** R431 PUBLIC fabricated Store + REAL Swing EDT/worker acceptance harness. */
public final class R431JournalBoundAsyncHarness {
    static int assertions;
    static final long WAIT = 8;
    static void yes(boolean condition, String label) {
        if (!condition) throw new AssertionError("R431_" + label);
        assertions++;
    }

    static <T> T edt(Callable<T> action) throws Exception {
        FutureTask<T> task = new FutureTask<>(action);
        SwingUtilities.invokeAndWait(task);
        return task.get(WAIT, TimeUnit.SECONDS);
    }

    static void beforeHistory(Path root) throws Exception {
        if (!Files.exists(root.resolve(R431SyntheticJournalStore.HISTORY),
                          LinkOption.NOFOLLOW_LINKS))
            Files.write(root.resolve(R431SyntheticJournalStore.HISTORY),
                R431SyntheticJournalStore.BEFORE,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
    }

    static final class Session implements R427AsyncDeleteCoordinator.Session {
        final AtomicLong epoch = new AtomicLong(101);
        final AtomicBoolean active = new AtomicBoolean(true);
        public long currentEpoch() { return epoch.get(); }
        public boolean accepts(long generation) {
            return active.get() && generation == epoch.get();
        }
        void invalidate() { active.set(false); epoch.incrementAndGet(); }
    }

    static final class View implements R427AsyncDeleteCoordinator.View {
        final CountDownLatch callback = new CountDownLatch(1);
        final CountDownLatch close = new CountDownLatch(1);
        final AtomicInteger applied = new AtomicInteger();
        final AtomicInteger uncertain = new AtomicInteger();
        final AtomicInteger refused = new AtomicInteger();
        final AtomicInteger reloaded = new AtomicInteger();
        final AtomicBoolean offEdt = new AtomicBoolean();
        volatile Throwable closeFailure;
        volatile long version = 1;
        void checkEdt() {
            if (!SwingUtilities.isEventDispatchThread()) offEdt.set(true);
        }
        public long version() { checkEdt(); return version; }
        public void applyConfirmed(R427AsyncDeleteCoordinator.Request request) {
            checkEdt(); applied.incrementAndGet(); callback.countDown();
        }
        public void confirmedButNeedsReload(R427AsyncDeleteCoordinator.Request request) {
            checkEdt(); reloaded.incrementAndGet(); callback.countDown();
        }
        public void refused(R427AsyncDeleteCoordinator.Request request) {
            checkEdt(); refused.incrementAndGet(); callback.countDown();
        }
        public void uncertainAndQuarantine(
                R427AsyncDeleteCoordinator.Request request) {
            checkEdt(); uncertain.incrementAndGet(); callback.countDown();
        }
        public void ownerClosed(Throwable error) {
            checkEdt(); closeFailure = error; close.countDown();
        }
    }

    static final class Fixture {
        final Session session = new Session();
        final View view = new View();
        final R431SyntheticJournalStore store;
        final R427AsyncDeleteCoordinator control;
        Fixture(Path root, R431SyntheticJournalStore.Hook hook)
                throws Exception {
            store = new R431SyntheticJournalStore(root, hook);
            control = new R427AsyncDeleteCoordinator(session, store, view);
        }
        boolean submit() throws Exception {
            return edt(() -> control.submit(
                R427AsyncDeleteCoordinator.Kind.RECORD_IDS,
                Arrays.asList("synthetic-22")));
        }
        boolean submitWrongKind() throws Exception {
            return edt(() -> control.submit(
                R427AsyncDeleteCoordinator.Kind.CLEAR_ALL,
                java.util.Collections.emptyList()));
        }
        void receipt() throws Exception {
            yes(view.callback.await(WAIT, TimeUnit.SECONDS), "EDT_RECEIPT_MISSING");
        }
        void shutdown() throws Exception {
            CompletableFuture<Void> done = edt(control::closeAsync);
            done.get(WAIT, TimeUnit.SECONDS);
            yes(view.close.await(WAIT, TimeUnit.SECONDS),
                "OWNER_CLOSED_EVENT_MISSING");
            yes(view.closeFailure == null, "OWNER_RELEASE_FAILED");
            yes(store.isReleased(), "OWNER_NOT_RELEASED");
            yes(!store.wasCloseOnEdt(), "OWNER_RELEASED_ON_EDT");
        }
        void noOptimisticUI() {
            yes(view.applied.get() == 0, "UNACKNOWLEDGED_DELETE_APPLIED");
            yes(view.reloaded.get() == 0, "UNACKNOWLEDGED_DELETE_RELOADED");
            yes(!view.offEdt.get(), "VIEW_CALLBACK_OFF_EDT");
        }
    }

    static void oneShotAndRestart(Path root, boolean already) throws Exception {
        if (!already) beforeHistory(root);
        Fixture f = new Fixture(root, null);
        try {
            yes(f.submit(), "INITIAL_SUBMISSION_REFUSED");
            f.receipt();
            f.noOptimisticUI();
            if (already) {
                yes(f.view.refused.get() == 1, "PERSISTENT_FENCE_NOT_REFUSED");
                yes(!f.store.wasCommitAttempted(), "DUPLICATE_COMMIT_STARTED");
                yes(!f.store.hasPersistentChange(), "DUPLICATE_WRITE_ATTEMPTED");
            } else {
                yes(f.store.hasCommittedSyntheticHistory(),
                    "SYNTHETIC_ATOMIC_REPLACE_NOT_COMPLETED");
                yes(f.store.hasPersistentChange(), "SYNTHETIC_INTENT_NOT_ATTEMPTED");
                yes(f.view.uncertain.get() == 1,
                    "UNACKNOWLEDGED_REPLACE_NOT_QUARANTINED");
                yes(f.control.isQuarantined(), "COORDINATOR_NOT_QUARANTINED");
                yes(!f.submit(), "SECOND_REQUEST_NOT_FENCED");
                yes(Files.isRegularFile(root.resolve(R431SyntheticJournalStore.INTENT),
                                        LinkOption.NOFOLLOW_LINKS),
                    "IMMUTABLE_INTENT_NOT_RETAINED");
            }
        } finally {
            f.shutdown();
        }
    }

    static void midCommitCloseDrains(Path root) throws Exception {
        beforeHistory(root);
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch proceed = new CountDownLatch(1);
        Fixture f = new Fixture(root, phase -> {
            if ("BEFORE_ATOMIC_REPLACE".equals(phase)) {
                entered.countDown();
                if (!proceed.await(WAIT, TimeUnit.SECONDS))
                    throw new IOException("R431_SYNTHETIC_HELD_WORKER");
            }
        });
        try {
            yes(f.submit(), "SUBMIT");
            yes(entered.await(WAIT, TimeUnit.SECONDS),
                "WORKER_NEVER_REACHED_INTENT_PUBLISHED");
            CompletableFuture<R427AsyncDeleteCoordinator.CloseObservation> observation =
                edt(() -> f.control.closeWithDeadline(60, TimeUnit.MILLISECONDS));
            yes(observation.get(WAIT, TimeUnit.SECONDS) ==
                R427AsyncDeleteCoordinator.CloseObservation.UNCONFIRMED_AT_DEADLINE,
                "WRITER_CLOSE_NOT_OBSERVED_OVERDUE");
            yes(!f.store.isReleased(), "LEASE_RELEASED_DURING_INFLIGHT_WRITE");
            yes(!f.submit(), "SHUTDOWN_ACCEPTED_NEW_WRITE");
            yes(edt(() -> SwingUtilities.isEventDispatchThread()),
                "EDT_STALLED_DURING_DISK_OPERATION");
        } finally {
            proceed.countDown();
            f.shutdown();
        }
        f.noOptimisticUI();
        yes(!f.store.hasCommittedSyntheticHistory(),
            "CANCELLED_AFTER_INTENT_SHOULD_NOT_REPLACE");
        yes(Files.isRegularFile(root.resolve(R431SyntheticJournalStore.INTENT),
                                LinkOption.NOFOLLOW_LINKS), "INTENT_MISSING_AFTER_SHUTDOWN");
        yes(Files.isRegularFile(root.resolve(R431SyntheticJournalStore.STAGE),
                                LinkOption.NOFOLLOW_LINKS), "STAGE_EVIDENCE_LOST");
    }

    static void failAfter(Path root, String location) throws Exception {
        beforeHistory(root);
        Fixture f = new Fixture(root, stage -> {
            if (stage.equals(location))
                throw new IOException("R431_SYNTHETIC_FAULT_"+location);
        });
        try {
            yes(f.submit(), "FAULT_SUBMITTED");
            f.receipt();
            yes(f.view.uncertain.get() == 1, "FAULT_NOT_QUARANTINED");
            yes(f.control.isQuarantined(), "FAULT_ALLOWED_BLIND_RETRY");
            f.noOptimisticUI();
            yes(f.store.hasPersistentChange(), "FAULT_DID_NOT_ENTER_PERSISTENCE");
        } finally {
            f.shutdown();
        }
        yes(Files.exists(root.resolve(R431SyntheticJournalStore.STAGE),
                         LinkOption.NOFOLLOW_LINKS) ||
            Files.exists(root.resolve(R431SyntheticJournalStore.INTENT),
                         LinkOption.NOFOLLOW_LINKS), "FAULT_ARTIFACTS_UNEXPECTEDLY_GONE");
    }

    static void cancelBeforePersistence(Path root) throws Exception {
        beforeHistory(root);
        Fixture f = new Fixture(root, stage -> {
            if ("BEFORE_PERSISTENCE".equals(stage)) f.session.invalidate();
        });
        try {
            yes(f.submit(), "CANCEL_SUBMITTED");
            // Callback is suppressed after invalidation: ensure worker drained
            // using close rather than waiting for an obsolete panel receipt.
        } finally {
            f.shutdown();
        }
        yes(!f.store.hasPersistentChange(), "STALE_SESSION_WROTE_HISTORY_STAGE");
        yes(!Files.exists(root.resolve(R431SyntheticJournalStore.STAGE),
                          LinkOption.NOFOLLOW_LINKS), "STAGE_CREATED_AFTER_INVALIDATION");
        yes(!Files.exists(root.resolve(R431SyntheticJournalStore.INTENT),
                          LinkOption.NOFOLLOW_LINKS), "INTENT_CREATED_AFTER_INVALIDATION");
        f.noOptimisticUI();
    }

    static void refuseEvidence(Path root) throws Exception {
        beforeHistory(root);
        Path orphan = root.resolve(R431SyntheticJournalStore.ACK);
        Files.write(orphan, new byte[]{9,9,9}, StandardOpenOption.CREATE_NEW);
        Fixture f = new Fixture(root, null);
        try {
            yes(f.submit(), "ACK_SUBMITTED");
            f.receipt();
            yes(f.view.refused.get() == 1, "EXISTING_ACK_NOT_REFUSED");
            yes(!f.store.wasCommitAttempted(), "ACK_DID_NOT_FENCE_COMMIT");
            yes(!f.store.hasPersistentChange(), "ACK_ALLOWED_STAGE");
            yes(java.util.Arrays.equals(Files.readAllBytes(orphan),
                                         new byte[]{9,9,9}), "FOREIGN_ACK_WAS_ALTERED");
            f.noOptimisticUI();
        } finally { f.shutdown(); }
    }

    static void refuseUnsupportedIntent(Path root) throws Exception {
        beforeHistory(root);
        Fixture f = new Fixture(root, null);
        try {
            yes(f.submitWrongKind(), "OTHER_KIND_SUBMITTED");
            f.receipt();
            yes(f.view.refused.get() == 1, "UNSUPPORTED_KIND_NOT_REFUSED");
            yes(!f.store.wasCommitAttempted(), "OTHER_KIND_WRITER_STARTED");
            yes(!f.store.hasPersistentChange(), "OTHER_KIND_WROTE_DISK");
        } finally { f.shutdown(); }
    }

    static void refuseExistingSymlink(Path root) throws Exception {
        beforeHistory(root);
        Path external = root.resolve("synthetic-external-preserve.txt");
        Files.write(external, new byte[]{1,2,3}, StandardOpenOption.CREATE_NEW);
        Path marker = root.resolve(R431SyntheticJournalStore.INTENT);
        try {
            Files.createSymbolicLink(marker, external);
        } catch (UnsupportedOperationException | IOException | SecurityException unavailable) {
            System.out.println("R431_OPTIONAL_SYMLINK_UNAVAILABLE");
            return;
        }
        Fixture f = new Fixture(root, null);
        try {
            yes(f.submit(), "SYMLINK_SUBMITTED");
            f.receipt();
            yes(f.view.refused.get() == 1, "SYMLINK_INTENT_NOT_FENCED");
            yes(java.util.Arrays.equals(Files.readAllBytes(external),
                                         new byte[]{1,2,3}), "SYMLINK_TARGET_MODIFIED");
            yes(!f.store.hasPersistentChange(), "SYMLINK_ALLOWED_WRITE");
        } finally { f.shutdown(); }
    }

    static void liveOwnerHold(Path root) throws Exception {
        R431SyntheticJournalStore store = new R431SyntheticJournalStore(root, null);
        try {
            System.out.println("R431_SYNTHETIC_OWNER_LOCK_HELD");
            System.out.flush();
            System.in.read();
        } finally {
            store.closeOwner();
        }
    }

    static void probeCompetingOwner(Path root) throws Exception {
        boolean refused = false;
        try {
            R431SyntheticJournalStore other =
                new R431SyntheticJournalStore(root, null);
            other.closeOwner();
        } catch (IOException locked) {
            refused = true;
        }
        yes(refused, "COMPETING_PROCESS_NOT_REFUSED");
    }

    static void verifyNoRealData(Path root) throws Exception {
        yes(R431SyntheticJournalStore.isolated(root).equals(root),
            "ROOT_WAS_NOT_SYNTHETIC");
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2)
            throw new IllegalArgumentException("R431_MODE_AND_SYNTHETIC_ROOT_REQUIRED");
        Path root = Paths.get(args[1]).toAbsolutePath().normalize();
        verifyNoRealData(root);
        String mode = args[0];
        switch (mode) {
            case "commit": oneShotAndRestart(root, false); break;
            case "restart": oneShotAndRestart(root, true); break;
            case "close-drains": midCommitCloseDrains(root); break;
            case "fault-after-stage": failAfter(root, "AFTER_HISTORY_STAGE_FORCE"); break;
            case "fault-after-intent-temp": failAfter(root, "AFTER_INTENT_TEMP_FORCE"); break;
            case "fault-after-publish": failAfter(root, "AFTER_INTENT_PUBLISHED"); break;
            case "fault-after-replace": failAfter(root, "AFTER_ATOMIC_REPLACE"); break;
            case "cancel-before": cancelBeforePersistence(root); break;
            case "refuse-ack": refuseEvidence(root); break;
            case "refuse-kind": refuseUnsupportedIntent(root); break;
            case "refuse-symlink": refuseExistingSymlink(root); break;
            case "hold-owner": liveOwnerHold(root); break;
            case "probe-owner": probeCompetingOwner(root); break;
            default: throw new IllegalArgumentException("R431_UNRECOGNIZED_MODE");
        }
        System.out.println("R431_"+mode.toUpperCase().replace('-', '_')+
            "_PASS assertions="+assertions);
    }
}

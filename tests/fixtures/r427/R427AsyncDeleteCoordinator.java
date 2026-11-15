package rs.plugins.loottracker;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.BooleanSupplier;
import javax.swing.SwingUtilities;

/**
 * R427 independent PUBLIC Java 11 prototype for non-blocking history deletion
 * receipts. NOT recovered/private client source and NOT integrated into v312.
 *
 * Design contract:
 * - One request in flight; immutable stable keys, never Swing row positions.
 * - Only the owner Store adapter performs history I/O, exclusively on worker.
 * - Store must check admission while holding the existing R419 owner/epoch
 *   gate at the durable commit boundary; caller does not implement journaling.
 * - UI changes only after a CONFIRMED durable receipt and version/session match.
 * - Ambiguous outcome quarantines further requests; NO blind retry.
 * - Closing drains any in-flight I/O before releasing owner on the same
 *   worker, without waiting on Swing's EDT.
 * - Safe release/fencing of R415-R417 deletion intent/ack must be implemented
 *   and separately proven in the future real Store adapter before deployment.
 */
final class R427AsyncDeleteCoordinator {
    static final int MAX_BATCH_KEYS = 4096;

    enum Kind { CLEAR_ALL, RECORD_IDS, SOURCE_KEY, TYPE_KEY }
    enum Outcome { CONFIRMED, REFUSED, UNCERTAIN }

    /** A deadline is a progress observation, NEVER permission to drop a lock. */
    enum CloseObservation {
        RELEASE_CONFIRMED, RELEASE_UNCERTAIN, UNCONFIRMED_AT_DEADLINE
    }

    static final class Request {
        final Kind kind;
        final List<String> keys;
        final long sessionEpoch;
        final long uiVersion;

        Request(Kind kind, Collection<String> source, long sessionEpoch,
                long uiVersion) {
            this.kind = Objects.requireNonNull(kind, "kind");
            Objects.requireNonNull(source, "source");
            Set<String> stable = new LinkedHashSet<>();
            if (source.size() > MAX_BATCH_KEYS) {
                throw new IllegalArgumentException("R427_BATCH_TOO_LARGE");
            }
            for (String key : source) {
                if (key == null || key.isEmpty() || key.length() > 256 ||
                    !key.equals(key.trim())) {
                    throw new IllegalArgumentException("R427_INVALID_STABLE_KEY");
                }
                stable.add(key);
            }
            if ((kind == Kind.CLEAR_ALL && !stable.isEmpty()) ||
                (kind == Kind.RECORD_IDS && stable.isEmpty()) ||
                ((kind == Kind.SOURCE_KEY || kind == Kind.TYPE_KEY) &&
                 stable.size() != 1)) {
                throw new IllegalArgumentException("R427_INVALID_INTENT_SHAPE");
            }
            this.keys = Collections.unmodifiableList(new ArrayList<>(stable));
            this.sessionEpoch = sessionEpoch;
            this.uiVersion = uiVersion;
        }
    }

    interface Session {
        /** Thread-safe; capture a monotonically increasing unique owner epoch. */
        long currentEpoch();

        /** Thread-safe: verify the original owner session is still live. */
        boolean accepts(long epoch);
    }

    interface Store {
        /**
         * Synchronous, off-EDT operation. The adapter must:
         * 1) refuse unowned/unsafe journal state and stale session,
         * 2) hold the OS owner lease throughout the durable transaction,
         * 3) test admission again UNDER its history gate at commit boundary,
         * 4) return CONFIRMED only for fully durable, acknowledged removal,
         * 5) return UNCERTAIN for errors where a write may have occurred.
         *
         * This public coordinator does not implement any of these guarantees.
         * It never retries or assumes a thrown exception means no disk write.
         */
        Outcome commit(Request request, BooleanSupplier admission) throws Exception;

        /** Blocking release: called only after all accepted I/O has drained. */
        void closeOwner() throws Exception;
    }

    interface View {
        /** Called on EDT only. Must include *all* panel edits in this version. */
        long version();
        void applyConfirmed(Request request);
        void confirmedButNeedsReload(Request request);
        void refused(Request request);
        void uncertainAndQuarantine(Request request);
        void ownerClosed(Throwable releaseError);
    }

    private final Session session;
    private final Store store;
    private final View view;
    private final ExecutorService io;
    private final AtomicBoolean closed = new AtomicBoolean();
    private final AtomicBoolean pending = new AtomicBoolean();
    private final AtomicBoolean quarantined = new AtomicBoolean();
    private final CompletableFuture<Void> closeFuture = new CompletableFuture<>();

    R427AsyncDeleteCoordinator(Session session, Store store, View view) {
        this.session = Objects.requireNonNull(session, "session");
        this.store = Objects.requireNonNull(store, "store");
        this.view = Objects.requireNonNull(view, "view");
        ThreadFactory factory = operation -> {
            Thread t = new Thread(operation, "SpawnPK-R427-DeleteReceipt");
            // A daemon can disappear when the JVM exits while an accepted
            // durable transaction is in flight. Keep this managed worker
            // non-daemon and require the closeAsync drain to finish; this
            // trades crash-exit latency for graceful-shutdown durability.
            t.setDaemon(false);
            return t;
        };
        this.io = Executors.newSingleThreadExecutor(factory);
    }

    boolean submit(Kind kind, Collection<String> stableKeys) {
        requireEdt();
        if (closed.get() || quarantined.get() || pending.get()) {
            return false;
        }
        final long epoch = session.currentEpoch();
        if (!session.accepts(epoch)) {
            return false;
        }
        // Capture the version and stable IDs while still on EDT.
        final Request request = new Request(
            kind, stableKeys, epoch, view.version());
        if (!pending.compareAndSet(false, true)) {
            return false;
        }
        try {
            io.execute(() -> execute(request));
            return true;
        } catch (RejectedExecutionException unavailable) {
            pending.set(false);
            return false;
        }
    }

    private boolean admitted(Request request) {
        return !closed.get() &&
               !Thread.currentThread().isInterrupted() &&
               session.accepts(request.sessionEpoch);
    }

    private void execute(Request request) {
        Outcome outcome;
        try {
            if (!admitted(request)) {
                outcome = Outcome.REFUSED;
            } else {
                outcome = store.commit(request, () -> admitted(request));
                if (outcome == null) {
                    outcome = Outcome.UNCERTAIN;
                }
            }
        } catch (Throwable ambiguousDiskOutcome) {
            // A thrown exception *or Error* cannot prove a durable write
            // failed. Keep the original session quarantined; do not retry.
            // A fatal VM failure can still terminate the process; this is
            // only best-effort containment in a live synthetic JVM.
            outcome = Outcome.UNCERTAIN;
        }
        if (outcome == Outcome.UNCERTAIN) {
            quarantined.set(true);
        }
        final Outcome finalOutcome = outcome;
        SwingUtilities.invokeLater(() -> deliver(request, finalOutcome));
    }

    private void deliver(Request request, Outcome outcome) {
        requireEdt();
        try {
            // A successful old-session disk transaction may have completed
            // before shutdown. Its receipt must never touch a new panel.
            if (closed.get() || !session.accepts(request.sessionEpoch)) {
                return;
            }
            switch (outcome) {
                case CONFIRMED:
                    if (view.version() == request.uiVersion) {
                        view.applyConfirmed(request);
                    } else {
                        view.confirmedButNeedsReload(request);
                    }
                    break;
                case REFUSED:
                    view.refused(request);
                    break;
                case UNCERTAIN:
                    view.uncertainAndQuarantine(request);
                    break;
                default:
                    throw new IllegalStateException("Unexpected receipt outcome");
            }
        } finally {
            pending.set(false);
        }
    }

    /** EDT-only; never joins the I/O thread or releases an OS lock on EDT. */
    CompletableFuture<Void> closeAsync() {
        requireEdt();
        if (!closed.compareAndSet(false, true)) {
            return closeFuture;
        }
        try {
            io.execute(() -> {
                Throwable failure = null;
                try {
                    // Single worker executes this AFTER the accepted commit.
                    store.closeOwner();
                    closeFuture.complete(null);
                } catch (Throwable releaseError) {
                    // No exception category proves that the OS lock was
                    // actually released. Report unknown rather than success.
                    quarantined.set(true);
                    failure = releaseError;
                    closeFuture.completeExceptionally(releaseError);
                } finally {
                    final Throwable receipt = failure;
                    SwingUtilities.invokeLater(() -> view.ownerClosed(receipt));
                }
            });
            io.shutdown(); // drain; never shutdownNow/cancel an in-flight write.
        } catch (RejectedExecutionException unavailable) {
            // Abnormal executor failure: do NOT claim owner was released.
            closeFuture.completeExceptionally(unavailable);
        }
        return closeFuture;
    }

    /**
     * EDT-only, nonblocking bounded *observation* of graceful owner release.
     * An overdue writer remains owned/unknown; this never interrupts the
     * durable commit, deletes a marker, or releases the owner out-of-order.
     * The original closeFuture may still complete later and ownerClosed()
     * still reports that final result on the EDT.
     */
    CompletableFuture<CloseObservation> closeWithDeadline(long duration, TimeUnit unit) {
        requireEdt();
        if (duration <= 0 || unit == null) {
            throw new IllegalArgumentException("R428_INVALID_CLOSE_DEADLINE");
        }
        final CompletableFuture<Void> completion = closeAsync();
        final CompletableFuture<CloseObservation> observation = new CompletableFuture<>();
        completion.whenComplete((ignored, failure) ->
            SwingUtilities.invokeLater(() -> observation.complete(
                failure == null ? CloseObservation.RELEASE_CONFIRMED :
                                  CloseObservation.RELEASE_UNCERTAIN)));
        // The timer reports incomplete progress, it is NOT a cancellation.
        // Complete the observation on EDT so its completion callbacks cannot
        // accidentally change Swing state from a timer or I/O thread.
        CompletableFuture.delayedExecutor(duration, unit).execute(() ->
            SwingUtilities.invokeLater(() ->
                observation.complete(CloseObservation.UNCONFIRMED_AT_DEADLINE)));
        return observation;
    }

    boolean isPending() {
        return pending.get();
    }

    boolean isQuarantined() {
        return quarantined.get();
    }

    boolean isClosed() {
        return closed.get();
    }

    private static void requireEdt() {
        if (!SwingUtilities.isEventDispatchThread()) {
            throw new IllegalStateException("R427_UI_CALL_MUST_BE_ON_EDT");
        }
    }
}

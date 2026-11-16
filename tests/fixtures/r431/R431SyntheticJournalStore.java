package rs.plugins.loottracker;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.Collections;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.BooleanSupplier;
import javax.swing.SwingUtilities;

/**
 * R431 independently authored, PUBLIC synthetic adapter of the R415
 * confirmed-delete *research* ordering, bound to the R427 async controller.
 *
 * This is NOT original private LootHistoryStore code or a replacement for
 * R410/R411/R415-R417/R419. It refuses production paths and never supports
 * more than one invented RECORD_IDS("synthetic-22") transaction.
 *
 * The R415 confirmed-delete path persists a v1 intent and leaves all future
 * writes fenced. R416 passive schema verification and R417 ack fences do NOT
 * constitute durable restart adoption. Thus this adapter ALWAYS reports
 * UNCERTAIN after the first persistent side effect, even if an atomic move
 * succeeds, and it never provides a CONFIRMED UI deletion receipt.
 */
final class R431SyntheticJournalStore implements R427AsyncDeleteCoordinator.Store {
    static final String HISTORY = "loot-history.json";
    static final String STAGE = HISTORY + ".tmp";
    static final String INTENT = "loot-history.delete.intent";
    static final String INTENT_TMP = INTENT + ".tmp";
    static final String ACK = "loot-history.delete.ack";
    static final String ACK_TMP = ACK + ".tmp";
    static final String OWNER = "R431-Synthetic-Owner.lock";
    static final byte[] BEFORE = (
        "{\"version\":1,\"records\":[{\"title\":\"synthetic\",\"subtitle\":\"\","
        + "\"type\":\"OTHER\",\"kills\":0,\"timestamp\":1,\"items\":[]}]}"
    ).getBytes(java.nio.charset.StandardCharsets.UTF_8);
    static final byte[] AFTER =
        "{\"version\":1,\"records\":[]}"
        .getBytes(java.nio.charset.StandardCharsets.UTF_8);

    interface Hook {
        void reached(String stage) throws Exception;
    }

    private final Path root;
    private final FileChannel channel;
    private final FileLock lease;
    private final Hook hook;
    private final AtomicBoolean released = new AtomicBoolean();
    private volatile boolean operationStarted;
    private volatile boolean attemptedPersistentChange;
    private volatile boolean committedHistory;
    private volatile boolean busy;
    private volatile boolean ownerCloseOnEdt;
    private volatile boolean workOnEdt;

    static Path isolated(Path supplied) throws Exception {
        Path p = supplied.toAbsolutePath().normalize();
        Path tmp = Paths.get(System.getProperty("java.io.tmpdir"))
            .toAbsolutePath().normalize();
        if (p.getParent() == null || !p.getParent().equals(tmp) ||
            p.getFileName() == null ||
            !p.getFileName().toString().startsWith("R431-Synthetic-"))
            throw new IOException("R431_REFUSED_NON_SYNTHETIC_TEMP");
        for (Path ancestor = p; ancestor != null; ancestor = ancestor.getParent()) {
            BasicFileAttributes a = Files.readAttributes(
                ancestor, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            if (!a.isDirectory() || a.isSymbolicLink() || a.isOther())
                throw new IOException("R431_UNSAFE_ANCESTOR");
        }
        return p;
    }

    private static boolean present(Path p) throws IOException {
        try {
            Files.readAttributes(p, BasicFileAttributes.class,
                LinkOption.NOFOLLOW_LINKS);
            return true;
        } catch (NoSuchFileException absent) {
            return false;
        }
    }

    private static boolean ordinaryFile(Path p) throws IOException {
        BasicFileAttributes a = Files.readAttributes(
            p, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        return a.isRegularFile() && !a.isSymbolicLink() && !a.isOther()
            && a.size() > 0 && a.size() <= 1024 * 1024;
    }

    private static byte[] bounded(Path p) throws IOException {
        if (!ordinaryFile(p))
            throw new IOException("R431_UNSAFE_OR_OVERSIZED_FILE");
        try (FileChannel c = FileChannel.open(p, StandardOpenOption.READ,
                                            LinkOption.NOFOLLOW_LINKS)) {
            long size = c.size();
            if (size <= 0 || size > 1024 * 1024)
                throw new IOException("R431_UNSAFE_HISTORY_SIZE");
            ByteBuffer buffer = ByteBuffer.allocate((int)size);
            while (buffer.hasRemaining()) {
                if (c.read(buffer) <= 0)
                    throw new IOException("R431_HISTORY_READ_INCOMPLETE");
            }
            return buffer.array();
        }
    }

    private static void forceNew(Path file, byte[] data) throws IOException {
        try (FileChannel c = FileChannel.open(file,
                 StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE,
                 LinkOption.NOFOLLOW_LINKS)) {
            ByteBuffer b = ByteBuffer.wrap(data);
            while (b.hasRemaining()) {
                if (c.write(b) <= 0)
                    throw new IOException("R431_FAILED_STAGED_WRITE");
            }
            c.force(true);
        }
    }

    private static String sha(byte[] data) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(data);
            StringBuilder text = new StringBuilder(64);
            for (byte b : digest) {
                text.append(Character.forDigit((b >>> 4) & 15, 16));
                text.append(Character.forDigit(b & 15, 16));
            }
            return text.toString();
        } catch (Exception cannotHash) {
            throw new IllegalStateException(cannotHash);
        }
    }

    R431SyntheticJournalStore(Path scratch, Hook hook) throws Exception {
        root = isolated(scratch);
        this.hook = hook == null ? ignored -> { } : hook;
        Path lock = root.resolve(OWNER);
        FileChannel c;
        if (present(lock)) {
            if (!ordinaryFile(lock))
                throw new IOException("R431_UNSAFE_LOCK_FILE");
            c = FileChannel.open(lock, StandardOpenOption.READ,
                 StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
        } else {
            c = FileChannel.open(lock, StandardOpenOption.CREATE_NEW,
                 StandardOpenOption.READ, StandardOpenOption.WRITE,
                 LinkOption.NOFOLLOW_LINKS);
            c.write(ByteBuffer.wrap(new byte[]{1}));
            c.force(true);
        }
        FileLock held = null;
        try {
            held = c.tryLock();
            if (held == null)
                throw new IOException("R431_OWNER_ALREADY_LOCKED");
        } catch (OverlappingFileLockException overlap) {
            c.close();
            throw new IOException("R431_OWNER_ALREADY_LOCKED", overlap);
        } catch (Exception error) {
            c.close();
            throw error;
        }
        channel = c;
        lease = held;
    }

    private boolean noOutstandingEvidence() throws Exception {
        for (String name : new String[]{
            STAGE, INTENT, INTENT_TMP, ACK, ACK_TMP,
            "R429-synthetic-intent.ledger",
        }) {
            if (present(root.resolve(name)))
                return false;
        }
        return true;
    }

    @Override
    public synchronized R427AsyncDeleteCoordinator.Outcome commit(
            R427AsyncDeleteCoordinator.Request request,
            BooleanSupplier admission) throws Exception {
        workOnEdt = SwingUtilities.isEventDispatchThread();
        if (workOnEdt)
            throw new IllegalStateException("R431_DISK_WRITE_ON_EDT");
        if (released.get() || !lease.isValid() || !admission.getAsBoolean())
            return R427AsyncDeleteCoordinator.Outcome.REFUSED;
        if (request.kind != R427AsyncDeleteCoordinator.Kind.RECORD_IDS ||
            !request.keys.equals(Collections.singletonList("synthetic-22")))
            return R427AsyncDeleteCoordinator.Outcome.REFUSED;
        if (!noOutstandingEvidence())
            return R427AsyncDeleteCoordinator.Outcome.REFUSED;

        byte[] original;
        try {
            original = bounded(root.resolve(HISTORY));
        } catch (IOException unsafeInput) {
            return R427AsyncDeleteCoordinator.Outcome.REFUSED;
        }
        if (!java.util.Arrays.equals(original, BEFORE))
            return R427AsyncDeleteCoordinator.Outcome.REFUSED;
        if (!admission.getAsBoolean())
            return R427AsyncDeleteCoordinator.Outcome.REFUSED;

        operationStarted = true;
        busy = true;
        try {
            hook.reached("BEFORE_PERSISTENCE");
            if (!admission.getAsBoolean())
                return R427AsyncDeleteCoordinator.Outcome.REFUSED;
            // R415 synthetic sequence: forced staged image, forced v1
            // intent.tmp, no-clobber hard-link publication, strict atomic
            // stage-to-history replace, preserve final intent forever.
            // A CREATE_NEW/force failure can occur after creating or
            // partially writing the stage. Mark ambiguity BEFORE attempting
            // this first persistent operation, not only after it succeeds.
            attemptedPersistentChange = true;
            forceNew(root.resolve(STAGE), AFTER);
            hook.reached("AFTER_HISTORY_STAGE_FORCE");
            String oldHash = sha(original);
            String newHash = sha(AFTER);
            if (oldHash.equals(newHash) ||
                !java.util.Arrays.equals(bounded(root.resolve(HISTORY)), BEFORE) ||
                !java.util.Arrays.equals(bounded(root.resolve(STAGE)), AFTER)) {
                return R427AsyncDeleteCoordinator.Outcome.UNCERTAIN;
            }
            String marker = "v=1\nserial=1\nnonce=" + UUID.randomUUID().toString()
                + "\nbefore=" + oldHash + "\nafter=" + newHash + "\n";
            forceNew(root.resolve(INTENT_TMP),
                     marker.getBytes(java.nio.charset.StandardCharsets.US_ASCII));
            hook.reached("AFTER_INTENT_TEMP_FORCE");
            // Cancellation after persistent side effects must not be
            // interpreted as a definite noncommit. Preserve all evidence.
            if (!admission.getAsBoolean())
                return R427AsyncDeleteCoordinator.Outcome.UNCERTAIN;
            if (!java.util.Arrays.equals(bounded(root.resolve(HISTORY)), BEFORE) ||
                !java.util.Arrays.equals(bounded(root.resolve(STAGE)), AFTER))
                return R427AsyncDeleteCoordinator.Outcome.UNCERTAIN;
            Files.createLink(root.resolve(INTENT), root.resolve(INTENT_TMP));
            hook.reached("AFTER_INTENT_PUBLISHED");
            // Only remove the exact owned temp alias, never the final marker.
            Files.delete(root.resolve(INTENT_TMP));
            hook.reached("BEFORE_ATOMIC_REPLACE");
            // Even a closed session cannot prove cancellation safe AFTER
            // publication: the final R415 intent remains for restart review.
            if (!admission.getAsBoolean())
                return R427AsyncDeleteCoordinator.Outcome.UNCERTAIN;
            Files.move(root.resolve(STAGE), root.resolve(HISTORY),
                       StandardCopyOption.ATOMIC_MOVE,
                       StandardCopyOption.REPLACE_EXISTING);
            hook.reached("AFTER_ATOMIC_REPLACE");
            if (!java.util.Arrays.equals(bounded(root.resolve(HISTORY)), AFTER) ||
                !ordinaryFile(root.resolve(INTENT)))
                return R427AsyncDeleteCoordinator.Outcome.UNCERTAIN;
            committedHistory = true;
            // Even apparently successful R415 synthetic commit is *not*
            // proof of a durable, adopted acknowledgment. No R427 CONFIRMED.
            return R427AsyncDeleteCoordinator.Outcome.UNCERTAIN;
        } catch (Exception ambiguous) {
            return attemptedPersistentChange
                ? R427AsyncDeleteCoordinator.Outcome.UNCERTAIN
                : R427AsyncDeleteCoordinator.Outcome.REFUSED;
        } finally {
            busy = false;
        }
    }

    @Override
    public synchronized void closeOwner() throws Exception {
        ownerCloseOnEdt = SwingUtilities.isEventDispatchThread();
        if (ownerCloseOnEdt)
            throw new IllegalStateException("R431_CLOSE_ON_EDT");
        if (busy)
            throw new IllegalStateException("R431_RELEASE_OVERRAN_COMMIT");
        if (!released.get()) {
            // Do not claim successful release before both operations
            // actually complete. An exception means ownership is UNKNOWN
            // even if closing the channel may have released the OS lock.
            lease.release();
            channel.close();
            released.set(true);
        }
    }

    boolean isReleased() { return released.get(); }
    boolean wasCommitAttempted() { return operationStarted; }
    boolean hasPersistentChange() { return attemptedPersistentChange; }
    boolean hasCommittedSyntheticHistory() { return committedHistory; }
    boolean wasCommitOnEdt() { return workOnEdt; }
    boolean wasCloseOnEdt() { return ownerCloseOnEdt; }
}

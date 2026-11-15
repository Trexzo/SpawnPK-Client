import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.FileVisitOption;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.FileTime;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import javax.swing.SwingUtilities;

/**
 * R423 independently written PUBLIC synthetic model. NOT recovered private source.
 * This is a cooperative local filesystem safety aid, not protection from an
 * attacker replacing ancestor path components between NOFOLLOW checks.
 * The model refuses ambiguous input and never alters canonical history.
 */
public final class R423NoFollowLegacyCleanup {
    static final String LEGACY_TREE = "loot-history";
    static final String LEGACY_KEYS = "loot-keys-seen.txt";
    static final String LOCK_PATH = "loot-history.writer.lock";
    static final String CANONICAL_HISTORY = "loot-history.json";
    static final String[] JOURNAL_EVIDENCE = {
        "loot-history.json.tmp", "loot-history.delete.intent",
        "loot-history.delete.intent.tmp", "loot-history.delete.ack",
        "loot-history.delete.ack.tmp"
    };
    private static final int MAX_ENTRIES = 4096;
    private static final int MAX_DEPTH = 16;
    private static final long MAX_FILE_SIZE = 64L * 1024L * 1024L;

    enum State { CLEANED, NOTHING, READY, REFUSED, INTERRUPTED, PARTIAL }

    static final class Result {
        final State state;
        final int planned;
        final int deleted;
        Result(State state, int planned, int deleted) {
            this.state = state;
            this.planned = planned;
            this.deleted = deleted;
        }
        @Override public String toString() {
            return state + " planned=" + planned + " deleted=" + deleted;
        }
    }

    interface BeforeDelete {
        void before(Path path, int deletionNumber) throws IOException, InterruptedException;
    }

    static final class Lease implements AutoCloseable {
        private final FileChannel channel;
        private final FileLock lock;
        private final Path root;
        private boolean closed;

        private Lease(FileChannel channel, FileLock lock, Path root) {
            this.channel = channel;
            this.lock = lock;
            this.root = root;
        }
        synchronized boolean owns(Path directory) {
            return !closed && lock.isValid() && root.equals(directory);
        }
        synchronized Result withinOwner(Path directory, boolean dryRun, BeforeDelete hook) {
            // Check cancellation before querying native lock/toolkit state.
            if (Thread.currentThread().isInterrupted())
                return new Result(State.INTERRUPTED, 0, 0);
            if (!owns(directory)) return new Result(State.REFUSED, 0, 0);
            return cleanupUnderLease(directory, dryRun, hook);
        }
        @Override public synchronized void close() throws IOException {
            if (closed) return;
            closed = true;
            try { lock.release(); }
            finally { channel.close(); }
        }
    }

    private static BasicFileAttributes attrs(Path path) throws IOException {
        return Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
    }
    /** Do not treat inaccessible paths as absent. Only ENOENT means absent. */
    private static boolean presentNoFollow(Path path) throws IOException {
        try {
            attrs(path);
            return true;
        } catch (NoSuchFileException absent) {
            return false;
        }
    }
    private static boolean normalDirectory(Path path) throws IOException {
        BasicFileAttributes a = attrs(path);
        return a.isDirectory() && !a.isSymbolicLink() && !a.isOther();
    }
    private static boolean safeAncestors(Path root) throws IOException {
        for (Path current = root; current != null; current = current.getParent()) {
            if (!normalDirectory(current)) return false;
        }
        return true;
    }

    /** The intended synthetic root must be one existing direct child of TEMP. */
    private static Path syntheticRoot(String value) throws IOException {
        Path root = Paths.get(value).toAbsolutePath().normalize();
        Path temp = Paths.get(System.getProperty("java.io.tmpdir"))
            .toAbsolutePath().normalize();
        if (!temp.equals(root.getParent()) || root.getFileName() == null ||
            !root.getFileName().toString().startsWith("R423-Synthetic-") ||
            !safeAncestors(root))
            throw new IllegalArgumentException("R423_REFUSED_NON_SYNTHETIC_ROOT");
        return root;
    }

    static Lease tryOwner(Path root) {
        try {
            if (!safeAncestors(root)) return null;
            Path lockPath = root.resolve(LOCK_PATH);
            try {
                BasicFileAttributes existing = attrs(lockPath);
                if (!existing.isRegularFile() || existing.isSymbolicLink()) return null;
            } catch (NoSuchFileException missing) {
                // A persistent lock filename does not prove a live owner.
            }
            Set<OpenOption> options = new HashSet<>();
            options.add(StandardOpenOption.CREATE);
            options.add(StandardOpenOption.WRITE);
            options.add(LinkOption.NOFOLLOW_LINKS);
            FileChannel channel = FileChannel.open(lockPath, options);
            FileLock lock = null;
            boolean transferred = false;
            try {
                try { lock = channel.tryLock(); }
                catch (OverlappingFileLockException busySameProcess) { return null; }
                if (lock == null || !lock.isValid()) return null;
                Lease lease = new Lease(channel, lock, root);
                transferred = true;
                return lease;
            } finally {
                if (!transferred) {
                    if (lock != null && lock.isValid()) lock.release();
                    channel.close();
                }
            }
        } catch (IOException | SecurityException denied) {
            return null;
        }
    }

    private static final class Entry {
        final Path path;
        final boolean directory;
        final Object key;
        final long size;
        final FileTime modified;
        Entry(Path path, BasicFileAttributes a) {
            this.path = path;
            this.directory = a.isDirectory();
            this.key = a.fileKey();
            this.size = a.size();
            this.modified = a.lastModifiedTime();
        }
        boolean stillMatches() {
            try {
                BasicFileAttributes now = attrs(path);
                if (now.isSymbolicLink() || now.isOther() ||
                    directory != now.isDirectory() ||
                    (!directory && !now.isRegularFile())) return false;
                if (key != null) return key.equals(now.fileKey());
                // After deleting children, a directory's size/mtime naturally
                // changes (and Windows may report null fileKey). Do not
                // compare these mutable fields on a directory. NOFOLLOW
                // and type still apply; hostile path swaps remain unsolved.
                if (directory) return now.isDirectory();
                return size == now.size() && modified.equals(now.lastModifiedTime());
            } catch (IOException | SecurityException e) {
                return false;
            }
        }
    }

    private static boolean journalsClear(Path root) {
        try {
            for (String name : JOURNAL_EVIDENCE) {
                if (presentNoFollow(root.resolve(name))) return false;
            }
            return true;
        } catch (IOException | SecurityException ambiguous) {
            return false;
        }
    }

    private static List<Entry> preflight(Path root) throws IOException {
        if (!safeAncestors(root)) throw new IOException("unsafe-root-or-ancestor");
        for (String marker : JOURNAL_EVIDENCE) {
            if (presentNoFollow(root.resolve(marker)))
                throw new IOException("unresolved-journal-evidence");
        }
        Path legacy = root.resolve(LEGACY_TREE);
        Path keys = root.resolve(LEGACY_KEYS);
        List<Entry> plan = new ArrayList<>();
        if (presentNoFollow(legacy)) {
            BasicFileAttributes top = attrs(legacy);
            if (!top.isDirectory() || top.isSymbolicLink() || top.isOther())
                throw new IOException("legacy-root-not-a-real-directory");
            Files.walkFileTree(legacy, EnumSet.noneOf(FileVisitOption.class),
                MAX_DEPTH, new SimpleFileVisitor<Path>() {
                private void append(Path file, BasicFileAttributes a) throws IOException {
                    if (!file.toAbsolutePath().normalize().startsWith(legacy) ||
                        a.isSymbolicLink() || a.isOther() ||
                        (!a.isRegularFile() && !a.isDirectory()) ||
                        (!a.isDirectory() && a.size() > MAX_FILE_SIZE))
                        throw new IOException("unsupported-legacy-entry");
                    if (plan.size() >= MAX_ENTRIES)
                        throw new IOException("legacy-entry-limit-exceeded");
                    plan.add(new Entry(file, a));
                }
                @Override public FileVisitResult preVisitDirectory(
                        Path directory, BasicFileAttributes a) throws IOException {
                    if (!directory.equals(legacy) &&
                        (!a.isDirectory() || a.isOther() || a.isSymbolicLink()))
                        throw new IOException("unsupported-subdirectory");
                    return FileVisitResult.CONTINUE;
                }
                @Override public FileVisitResult visitFile(Path file, BasicFileAttributes a)
                        throws IOException {
                    // A directory reported as a file at maxDepth contains
                    // unexplored descendants, so refuse before any deletion.
                    if (a.isDirectory())
                        throw new IOException("legacy-max-depth-exceeded");
                    append(file, a);
                    return FileVisitResult.CONTINUE;
                }
                @Override public FileVisitResult postVisitDirectory(Path directory,
                        IOException error) throws IOException {
                    if (error != null) throw error;
                    append(directory, attrs(directory));
                    return FileVisitResult.CONTINUE;
                }
                @Override public FileVisitResult visitFileFailed(Path file,
                        IOException error) throws IOException {
                    throw error;
                }
            });
        }
        if (presentNoFollow(keys)) {
            BasicFileAttributes a = attrs(keys);
            if (!a.isRegularFile() || a.isSymbolicLink() || a.isOther() ||
                a.size() > MAX_FILE_SIZE)
                throw new IOException("legacy-key-path-not-a-regular-file");
            if (plan.size() >= MAX_ENTRIES)
                throw new IOException("legacy-entry-limit-exceeded");
            plan.add(new Entry(keys, a));
        }
        return plan;
    }

    private static Result cleanupUnderLease(Path root, boolean dryRun,
                                            BeforeDelete hook) {
        if (Thread.currentThread().isInterrupted())
            return new Result(State.INTERRUPTED, 0, 0);
        if (SwingUtilities.isEventDispatchThread())
            return new Result(State.REFUSED, 0, 0);
        if (Thread.currentThread().isInterrupted())
            return new Result(State.INTERRUPTED, 0, 0);
        final List<Entry> plan;
        try { plan = preflight(root); }
        catch (IOException | SecurityException unsafe) {
            return new Result(State.REFUSED, 0, 0);
        }
        if (plan.isEmpty()) return new Result(State.NOTHING, 0, 0);
        if (dryRun) return new Result(State.READY, plan.size(), 0);
        int deleted = 0;
        for (Entry entry : plan) {
            if (Thread.currentThread().isInterrupted())
                return new Result(State.INTERRUPTED, plan.size(), deleted);
            try {
                if (hook != null) hook.before(entry.path, deleted);
            } catch (InterruptedException canceled) {
                Thread.currentThread().interrupt();
                return new Result(State.INTERRUPTED, plan.size(), deleted);
            } catch (IOException fault) {
                return new Result(State.PARTIAL, plan.size(), deleted);
            }
            // Recheck journal state and all path ancestors after any
            // injected filesystem fault and before the next deletion.
            if (!journalsClear(root))
                return new Result(State.PARTIAL, plan.size(), deleted);
            try {
                if (!safeAncestors(entry.path.getParent()))
                    return new Result(State.PARTIAL, plan.size(), deleted);
            } catch (IOException | SecurityException unsafeAncestor) {
                return new Result(State.PARTIAL, plan.size(), deleted);
            }
            if (!entry.stillMatches())
                return new Result(State.PARTIAL, plan.size(), deleted);
            try {
                Files.delete(entry.path);
            } catch (IOException | SecurityException failure) {
                return new Result(State.PARTIAL, plan.size(), deleted);
            }
            deleted++;
        }
        return new Result(State.CLEANED, plan.size(), deleted);
    }

    private static Result attempt(Path root, String mode) throws IOException {
        if ("no-owner".equals(mode)) return new Result(State.REFUSED, 0, 0);
        Lease owner = tryOwner(root);
        if (owner == null) return new Result(State.REFUSED, 0, 0);
        try {
            if ("hold".equals(mode)) {
                System.out.println("ACQUIRED");
                System.out.flush();
                System.in.read();
                return new Result(State.NOTHING, 0, 0);
            }
            if ("crash".equals(mode)) {
                System.out.println("ACQUIRED");
                System.out.flush();
                Runtime.getRuntime().halt(77);
            }
            if ("interrupt".equals(mode)) Thread.currentThread().interrupt();
            boolean dryRun = "dry-run".equals(mode);
            BeforeDelete hook = null;
            if ("fault-before-first".equals(mode))
                hook = (path, number) -> { throw new IOException("synthetic-fault"); };
            if ("fault-after-one".equals(mode))
                hook = (path, number) -> {
                    if (number == 1) throw new IOException("synthetic-fault");
                };
            if ("cancel-after-one".equals(mode))
                hook = (path, number) -> {
                    if (number == 1) throw new InterruptedException("synthetic-stop");
                };
            if ("journal-after-scan".equals(mode))
                hook = (path, number) -> {
                    if (number == 0) Files.write(
                        root.resolve("loot-history.delete.intent"),
                        "fabricated-late-marker".getBytes(
                            java.nio.charset.StandardCharsets.US_ASCII),
                        StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
                };
            if ("replace-first-with-symlink".equals(mode))
                hook = (path, number) -> {
                    if (number == 0) {
                        Files.delete(path);
                        Files.createSymbolicLink(path, root.resolve("sentinel.txt"));
                    }
                };
            return owner.withinOwner(root, dryRun, hook);
        } finally { owner.close(); }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException(
            "<clean|dry-run|fault-before-first|fault-after-one|cancel-after-one|interrupt|no-owner|hold|crash> <R423-Synthetic-TEMP-directory>");
        Path root = syntheticRoot(args[1]);
        Result result = attempt(root, args[0]);
        System.out.println(result);
    }
}

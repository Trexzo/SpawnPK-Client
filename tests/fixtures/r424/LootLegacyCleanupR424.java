package rs.plugins.loottracker;

import java.io.IOException;
import java.nio.file.FileVisitOption;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.FileTime;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.function.BooleanSupplier;
import javax.swing.SwingUtilities;

/**
 * R424 independently authored, Java 11-compatible legacy-path cleanup helper.
 * No recovered client code is included. R424 integration uses preflight ONLY:
 * the private plugin caller hardcodes commit=false until separately accepted.
 *
 * Not an anchored/openat defense against a hostile filesystem actor moving
 * ancestor paths between nofollow checks; non-cooperative writers remain unsafe.
 */
final class LootLegacyCleanupR424 {
    static final int MAX_ENTRIES = 4096;
    static final int MAX_DEPTH = 16;
    static final long MAX_FILE_BYTES = 64L * 1024L * 1024L;
    private static final String RETIRED_TREE = "loot-history";
    private static final String RETIRED_KEYS = "loot-keys-seen.txt";
    private static final String[] PENDING_EVIDENCE = {
        "loot-history.json.tmp", "loot-history.delete.intent",
        "loot-history.delete.intent.tmp", "loot-history.delete.ack",
        "loot-history.delete.ack.tmp"
    };

    enum Status { NOT_PRESENT, SCANNED, CLEANED, REFUSED, INTERRUPTED, PARTIAL }

    static final class Receipt {
        final Status status;
        final int planned;
        final int deleted;

        Receipt(Status status, int planned, int deleted) {
            this.status = status;
            this.planned = planned;
            this.deleted = deleted;
        }

        @Override public String toString() {
            return status + " planned=" + planned + " deleted=" + deleted;
        }
    }

    private static final class Entry {
        final Path path;
        final Object key;
        final boolean directory;
        final long size;
        final FileTime modified;

        Entry(Path path, BasicFileAttributes attrs) {
            this.path = path;
            this.key = attrs.fileKey();
            this.directory = attrs.isDirectory();
            this.size = attrs.size();
            this.modified = attrs.lastModifiedTime();
        }

        boolean matchesNow() {
            try {
                BasicFileAttributes now = read(path);
                if (now.isSymbolicLink() || now.isOther() ||
                    directory != now.isDirectory() ||
                    (!directory && !now.isRegularFile())) return false;
                if (key != null && !key.equals(now.fileKey())) return false;
                // Directory size/mtime legitimately changes as children go;
                // with null fileKey this check is only fail-closed on type.
                if (!directory && (size != now.size() ||
                    !modified.equals(now.lastModifiedTime()))) return false;
                return true;
            } catch (IOException | SecurityException error) {
                return false;
            }
        }
    }

    private LootLegacyCleanupR424() { }

    private static BasicFileAttributes read(Path p) throws IOException {
        return Files.readAttributes(p, BasicFileAttributes.class,
                                    LinkOption.NOFOLLOW_LINKS);
    }

    private static boolean existsNoFollow(Path p) throws IOException {
        try {
            read(p);
            return true;
        } catch (NoSuchFileException missing) {
            return false;
        }
    }

    private static boolean safeAncestors(Path p) throws IOException {
        for (Path current = p; current != null; current = current.getParent()) {
            BasicFileAttributes attrs = read(current);
            if (!attrs.isDirectory() || attrs.isSymbolicLink() || attrs.isOther())
                return false;
        }
        return true;
    }

    private static boolean evidenceAbsent(Path root) {
        try {
            for (String marker : PENDING_EVIDENCE)
                if (existsNoFollow(root.resolve(marker))) return false;
            return true;
        } catch (IOException | SecurityException uncertain) {
            return false;
        }
    }

    private static boolean allowed(BooleanSupplier admission) {
        try { return admission != null && admission.getAsBoolean(); }
        catch (RuntimeException error) { return false; }
    }

    private static List<Entry> completePlan(Path root) throws IOException {
        if (!safeAncestors(root)) throw new IOException("Unsafe legacy parent directory");
        if (!evidenceAbsent(root)) throw new IOException("Unresolved journal evidence");

        Path legacy = root.resolve(RETIRED_TREE);
        Path keys = root.resolve(RETIRED_KEYS);
        List<Entry> entries = new ArrayList<>();
        if (existsNoFollow(legacy)) {
            BasicFileAttributes top = read(legacy);
            if (!top.isDirectory() || top.isSymbolicLink() || top.isOther())
                throw new IOException("Unsafe legacy tree root");
            Files.walkFileTree(legacy, EnumSet.noneOf(FileVisitOption.class),
                MAX_DEPTH, new SimpleFileVisitor<Path>() {
                private void add(Path path, BasicFileAttributes a) throws IOException {
                    if (!path.toAbsolutePath().normalize().startsWith(legacy) ||
                        a.isSymbolicLink() || a.isOther() ||
                        (!a.isDirectory() && !a.isRegularFile()) ||
                        (!a.isDirectory() && a.size() > MAX_FILE_BYTES) ||
                        entries.size() >= MAX_ENTRIES)
                        throw new IOException("Legacy entry unsupported or too numerous");
                    entries.add(new Entry(path, a));
                }

                @Override public FileVisitResult preVisitDirectory(
                        Path dir, BasicFileAttributes a) throws IOException {
                    if (!a.isDirectory() || a.isSymbolicLink() || a.isOther())
                        throw new IOException("Unsafe directory entry");
                    if (Thread.currentThread().isInterrupted())
                        throw new IOException("Interrupted during preflight");
                    return FileVisitResult.CONTINUE;
                }

                @Override public FileVisitResult visitFile(
                        Path path, BasicFileAttributes a) throws IOException {
                    // At maxDepth a directory arrives here, not preVisitDirectory.
                    if (a.isDirectory()) throw new IOException("Legacy depth cap exceeded");
                    add(path, a);
                    return FileVisitResult.CONTINUE;
                }

                @Override public FileVisitResult postVisitDirectory(
                        Path dir, IOException error) throws IOException {
                    if (error != null) throw error;
                    add(dir, read(dir));
                    return FileVisitResult.CONTINUE;
                }

                @Override public FileVisitResult visitFileFailed(
                        Path file, IOException error) throws IOException {
                    throw error;
                }
            });
        }
        if (existsNoFollow(keys)) {
            BasicFileAttributes k = read(keys);
            if (!k.isRegularFile() || k.isSymbolicLink() || k.isOther() ||
                k.size() > MAX_FILE_BYTES || entries.size() >= MAX_ENTRIES)
                throw new IOException("Unsafe retired seen-keys file");
            entries.add(new Entry(keys, k));
        }
        return entries;
    }

    /**
     * Runs complete no-follow preflight first. No cleanup is performed unless
     * commit is true; R424 private integration is pinned to commit=false.
     * Caller must already hold the persistent OS writer lease. The supplied
     * admission callback must independently confirm current session and
     * journal state, and is rechecked before each individual deletion.
     */
    static Receipt run(Path parent, BooleanSupplier admission, boolean commit) {
        if (Thread.currentThread().isInterrupted())
            return new Receipt(Status.INTERRUPTED, 0, 0);
        if (SwingUtilities.isEventDispatchThread())
            return new Receipt(Status.REFUSED, 0, 0);
        if (Thread.currentThread().isInterrupted())
            return new Receipt(Status.INTERRUPTED, 0, 0);
        if (parent == null || !allowed(admission))
            return new Receipt(Status.REFUSED, 0, 0);

        final Path root = parent.toAbsolutePath().normalize();
        final List<Entry> plan;
        try {
            plan = completePlan(root);
        } catch (IOException | SecurityException failure) {
            return new Receipt(Thread.currentThread().isInterrupted()
                ? Status.INTERRUPTED : Status.REFUSED, 0, 0);
        }
        if (!allowed(admission) || !evidenceAbsent(root))
            return new Receipt(Status.REFUSED, plan.size(), 0);
        if (Thread.currentThread().isInterrupted())
            return new Receipt(Status.INTERRUPTED, plan.size(), 0);
        if (plan.isEmpty()) return new Receipt(Status.NOT_PRESENT, 0, 0);
        if (!commit) return new Receipt(Status.SCANNED, plan.size(), 0);

        int deleted = 0;
        for (Entry entry : plan) {
            if (Thread.currentThread().isInterrupted())
                return new Receipt(Status.INTERRUPTED, plan.size(), deleted);
            if (!allowed(admission) || !evidenceAbsent(root))
                return new Receipt(Status.PARTIAL, plan.size(), deleted);
            try {
                if (!safeAncestors(entry.path.getParent()) ||
                    !entry.matchesNow())
                    return new Receipt(Status.PARTIAL, plan.size(), deleted);
                Files.delete(entry.path);
            } catch (IOException | SecurityException error) {
                return new Receipt(Status.PARTIAL, plan.size(), deleted);
            }
            deleted++;
        }
        return new Receipt(Status.CLEANED, plan.size(), deleted);
    }
}

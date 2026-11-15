package rs.plugins.loottracker;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Invented PUBLIC stub for testing the R422 harness itself in CI.
 *
 * This is NOT derived from the actual recovered private implementation and
 * MUST NOT be packaged or mistaken for production LootHistoryStore source.
 * It models only the interface exercised by R422ActualStoreAcceptance.
 */
final class LootHistoryStore {
    static final String FILE_NAME = "loot-history.json";
    private final Path root;
    private final Path history;
    private volatile Lease owner;

    enum R411StageState { CLEAR, ORPHAN, UNSAFE }

    LootHistoryStore(String directory) {
        this.root = Paths.get(directory);
        this.history = root.resolve(FILE_NAME);
    }

    boolean r421PrepareHistoryDirectoryForLease() {
        Path directory = root.toAbsolutePath().normalize();
        Path parent = directory.getParent();
        if (parent == null || directory.getFileName() == null) return false;
        try {
            for (Path ancestor = parent; ancestor != null;
                 ancestor = ancestor.getParent()) {
                BasicFileAttributes attrs = Files.readAttributes(
                    ancestor, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                if (!attrs.isDirectory() || attrs.isSymbolicLink() || attrs.isOther())
                    return false;
            }
            BasicFileAttributes parentBefore = Files.readAttributes(
                parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            try {
                BasicFileAttributes leafBefore = Files.readAttributes(
                    directory, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                if (!leafBefore.isDirectory() || leafBefore.isSymbolicLink())
                    return false;
                BasicFileAttributes leafAfter = Files.readAttributes(
                    directory, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                BasicFileAttributes parentAfter = Files.readAttributes(
                    parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                return sameIdentity(leafBefore, leafAfter) &&
                       sameIdentity(parentBefore, parentAfter);
            } catch (NoSuchFileException missing) {
                Files.createDirectory(directory);
                BasicFileAttributes leaf = Files.readAttributes(
                    directory, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                BasicFileAttributes parentAfter = Files.readAttributes(
                    parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                return leaf.isDirectory() && !leaf.isSymbolicLink() &&
                       sameIdentity(parentBefore, parentAfter);
            }
        } catch (IOException | SecurityException error) {
            return false;
        }
    }

    private static boolean sameIdentity(BasicFileAttributes before,
                                        BasicFileAttributes after) {
        return before.isDirectory() && after.isDirectory() &&
               !before.isSymbolicLink() && !after.isSymbolicLink() &&
               (before.fileKey() == null || before.fileKey().equals(after.fileKey()));
    }

    private static final class Lease {
        final FileChannel channel;
        final FileLock fileLock;
        final UUID token = UUID.randomUUID();
        boolean released;

        Lease(FileChannel channel, FileLock lock) {
            this.channel = channel;
            this.fileLock = lock;
        }

        synchronized boolean live() {
            return !released && fileLock.isValid();
        }

        synchronized boolean withOwner(Runnable action) {
            if (!live() || action == null) return false;
            action.run();
            return true;
        }

        synchronized void close() throws IOException {
            if (released) return;
            released = true;
            try { fileLock.release(); }
            finally { channel.close(); }
        }
    }

    synchronized boolean r419ActivateOwner() {
        if (owner != null) return owner.live();
        try {
            Path directory = root.toAbsolutePath().normalize();
            BasicFileAttributes attrs = Files.readAttributes(
                directory, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            if (!attrs.isDirectory()) return false;
            Path lockPath = directory.resolve("loot-history.writer.lock");
            try {
                BasicFileAttributes existing = Files.readAttributes(
                    lockPath, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                if (!existing.isRegularFile()) return false;
            } catch (NoSuchFileException missing) {
                // Old file existence is not proof of ownership.
            }
            Set<OpenOption> options = new HashSet<>();
            options.add(StandardOpenOption.WRITE);
            options.add(StandardOpenOption.CREATE);
            options.add(LinkOption.NOFOLLOW_LINKS);
            FileChannel channel = FileChannel.open(lockPath, options);
            FileLock lock = null;
            boolean handedOff = false;
            try {
                try {
                    lock = channel.tryLock();
                } catch (OverlappingFileLockException sameJvm) {
                    return false;
                }
                if (lock == null || !lock.isValid()) return false;
                owner = new Lease(channel, lock);
                handedOff = true;
                return true;
            } finally {
                if (!handedOff) {
                    if (lock != null && lock.isValid()) lock.release();
                    channel.close();
                }
            }
        } catch (IOException | SecurityException error) {
            return false;
        }
    }

    synchronized void r419CloseOwner() {
        Lease prior = owner;
        owner = null;
        if (prior == null) return;
        try { prior.close(); }
        catch (IOException unexpected) { throw new IllegalStateException(unexpected); }
    }

    private boolean r419WithOwner(Runnable action) {
        Lease local = owner;
        return local != null && local.withOwner(action);
    }

    R411StageState r411StageState() {
        Lease local = owner;
        if (local == null || !local.live()) return R411StageState.UNSAFE;
        for (String name : new String[]{
                "loot-history.delete.intent", "loot-history.delete.intent.tmp",
                "loot-history.delete.ack", "loot-history.delete.ack.tmp"}) {
            if (Files.exists(root.resolve(name), LinkOption.NOFOLLOW_LINKS))
                return R411StageState.UNSAFE;
        }
        if (Files.exists(root.resolve("loot-history.json.tmp"),
                         LinkOption.NOFOLLOW_LINKS))
            return R411StageState.ORPHAN;
        return R411StageState.CLEAR;
    }

    List<LootTrackerRecord> loadForMerge() {
        List<List<LootTrackerRecord>> receipt = new ArrayList<>(1);
        if (!r419WithOwner(() -> {
            if (r411StageState() != R411StageState.CLEAR) {
                receipt.add(null);
            } else {
                receipt.add(new ArrayList<>());
            }
        })) return null;
        return receipt.get(0);
    }

    boolean saveWithReceipt(Collection<LootTrackerRecord> records) {
        boolean[] result = new boolean[1];
        if (!r419WithOwner(() -> {
            if (records == null || r411StageState() != R411StageState.CLEAR)
                return;
            Path temp = root.resolve("loot-history.json.tmp");
            try {
                Files.write(temp,
                    "{\"version\":1,\"records\":[]}".getBytes(StandardCharsets.UTF_8),
                    StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
                Files.move(temp, history, StandardCopyOption.ATOMIC_MOVE,
                           StandardCopyOption.REPLACE_EXISTING);
                result[0] = true;
            } catch (IOException refused) {
                // Never overwrite an unresolved staging path.
            }
        })) return false;
        return result[0];
    }

    boolean clearWithReceipt() {
        boolean[] result = new boolean[1];
        if (!r419WithOwner(() -> {
            if (r411StageState() != R411StageState.CLEAR) return;
            try {
                Files.deleteIfExists(history);
                result[0] = true;
            } catch (IOException refused) {
                // Keep canonical evidence when deletion fails.
            }
        })) return false;
        return result[0];
    }
}

/** Invented placeholder only; the acceptance harness writes empty records. */
final class LootTrackerRecord { }

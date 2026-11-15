import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * R418 invented Java 11 cooperative writer-lock/session model.
 * No client imports or real loot history. Never authorizes any writes.
 * Only cooperating holders of the SAME lock inode are excluded.
 */
public final class R418SingleWriterModel {
    static final String LOCK_NAME = "synthetic-loot-history.writer.lock";

    public static final class Lease implements AutoCloseable {
        private final FileChannel channel;
        private final FileLock lock;
        private final UUID session;
        private boolean closed;
        private final AtomicInteger actions = new AtomicInteger();

        private Lease(FileChannel channel, FileLock lock) {
            this.channel = channel;
            this.lock = lock;
            this.session = UUID.randomUUID();
        }

        public synchronized UUID session() { return session; }

        public synchronized boolean permit(UUID captured) {
            return !closed && lock.isValid() && session.equals(captured);
        }

        public synchronized boolean apply(UUID captured, Runnable action) {
            if (action == null || !permit(captured)) return false;
            action.run();
            actions.incrementAndGet();
            return true;
        }

        public synchronized int actions() { return actions.get(); }

        @Override public synchronized void close() throws IOException {
            if (closed) return;
            closed = true;
            try { lock.release(); } finally { channel.close(); }
        }
    }

    /** Never delete the lock pathname. File existence is NOT lock ownership. */
    static Lease acquire(Path directory) {
        if (directory == null || !Files.isDirectory(directory, LinkOption.NOFOLLOW_LINKS))
            return null;
        Path path = directory.resolve(LOCK_NAME);
        try {
            try {
                BasicFileAttributes attrs = Files.readAttributes(
                    path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                if (!attrs.isRegularFile()) return null;
            } catch (java.nio.file.NoSuchFileException absent) {
                // An unlocked, persistent pathname is not a stale owner.
            }
            Set<OpenOption> options = new HashSet<>();
            options.add(StandardOpenOption.CREATE);
            options.add(StandardOpenOption.WRITE);
            options.add(LinkOption.NOFOLLOW_LINKS);
            FileChannel channel = FileChannel.open(path, options);
            FileLock lock = null;
            boolean transferred = false;
            try {
                try { lock = channel.tryLock(); }
                catch (OverlappingFileLockException ownProcessConflict) { return null; }
                if (lock == null || !lock.isValid()) return null;
                Lease lease = new Lease(channel, lock);
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

    static void check(boolean condition, String reason) {
        if (!condition) throw new AssertionError(reason);
    }

    static int selfTest(Path root) throws Exception {
        int cases = 0;
        Lease first = acquire(root);
        check(first != null, "initial-acquire"); cases++;
        UUID token = first.session();
        check(first.permit(token), "own-token"); cases++;
        check(!first.permit(UUID.randomUUID()), "wrong-token"); cases++;
        check(first.apply(token, () -> { }), "admitted-action"); cases++;
        check(first.actions() == 1, "once"); cases++;
        check(!first.apply(UUID.randomUUID(), () -> { throw new AssertionError(); }),
              "rejected-action"); cases++;
        check(first.actions() == 1, "rejected-did-not-run"); cases++;
        check(acquire(root) == null, "overlap-same-process"); cases++;
        CountDownLatch both = new CountDownLatch(1);
        AtomicInteger admitted = new AtomicInteger();
        Thread raced = new Thread(() -> {
            try { both.await(); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }
            if (acquire(root) != null) admitted.incrementAndGet();
        });
        raced.start(); both.countDown(); raced.join();
        check(admitted.get() == 0, "concurrent-same-process-denied"); cases++;
        Path lockPath = root.resolve(LOCK_NAME);
        check(Files.isRegularFile(lockPath, LinkOption.NOFOLLOW_LINKS), "persistent-path"); cases++;
        first.close();
        check(!first.permit(token), "revoked-after-close"); cases++;
        first.close(); cases++;
        check(Files.exists(lockPath), "release-does-not-unlink"); cases++;
        Lease next = acquire(root);
        check(next != null, "reacquire-after-release"); cases++;
        check(!next.permit(token), "stale-session-denied-after-reacquire"); cases++;
        check(next.permit(next.session()), "new-session-admitted"); cases++;
        next.close();
        check(!next.apply(next.session(), () -> { throw new AssertionError(); }),
              "no-actions-postclose"); cases++;
        check(Files.isRegularFile(lockPath, LinkOption.NOFOLLOW_LINKS),
              "unlocked-file-still-present"); cases++;
        return cases;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2)
            throw new IllegalArgumentException("<selftest|hold|try|crash> <TEMP directory>");
        Path root = Paths.get(args[1]);
        if ("selftest".equals(args[0])) {
            System.out.println("R418_SYNTHETIC_JAVA_SELFTEST_PASS cases=" + selfTest(root));
            return;
        }
        Lease lease = acquire(root);
        if (lease == null) {
            System.out.println("REFUSED"); System.out.flush(); return;
        }
        System.out.println("ACQUIRED " + lease.session()); System.out.flush();
        if ("crash".equals(args[0])) Runtime.getRuntime().halt(77);
        if ("hold".equals(args[0])) System.in.read();
        else if (!"try".equals(args[0])) throw new IllegalArgumentException("invalid command");
        lease.close();
        System.out.println("RELEASED"); System.out.flush();
    }
}

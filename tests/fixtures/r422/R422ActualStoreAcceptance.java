package rs.plugins.loottracker;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/**
 * R422 OPTIONAL owner-private compiled-class acceptance.
 *
 * This file is public-safe: it contains NO recovered private source/class bytes
 * and must be compiled on the owner's isolated machine against the exact
 * owner-private R421 compiled classes, NEVER included in a release JAR.
 *
 * Only accepts explicitly designated, synthetic TEMP roots beginning with
 * "R422-Synthetic-". It does not instantiate a game client, authenticate,
 * use a live history path, or read player data.
 */
public final class R422ActualStoreAcceptance {
    private static int passed;

    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError("R422_FAIL_" + label);
        passed++;
    }

    private static Path safeRoot(String arg) throws IOException {
        Path root = Paths.get(arg).toAbsolutePath().normalize();
        Path temp = Paths.get(System.getProperty("java.io.tmpdir"))
                         .toAbsolutePath().normalize();
        // An absent final leaf is valid for the one-level directory-creation
        // test, but the direct parent must already be a real directory.
        // The actual R421 store performs its own full ancestor preflight.
        boolean exists = Files.exists(root, LinkOption.NOFOLLOW_LINKS);
        boolean safeLeaf = exists
            ? Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS) &&
              !Files.isSymbolicLink(root)
            : root.getParent() != null &&
              Files.isDirectory(root.getParent(), LinkOption.NOFOLLOW_LINKS) &&
              !Files.isSymbolicLink(root.getParent());
        if (!root.startsWith(temp) || root.equals(temp) ||
            root.getFileName() == null ||
            !root.getFileName().toString().startsWith("R422-Synthetic-") ||
            !safeLeaf)
            throw new IllegalArgumentException("R422_REFUSE_NON_SYNTHETIC_TEMP_ROOT");
        return root;
    }

    private static Path unused(Path root, String name) {
        Path path = root.resolve(name);
        if (Files.exists(path, LinkOption.NOFOLLOW_LINKS) ||
            Files.isSymbolicLink(path))
            throw new IllegalArgumentException("R422_REFUSE_EXISTING_FIXTURE_" + name);
        return path;
    }

    private static byte[] sha(byte[] bytes) throws Exception {
        return MessageDigest.getInstance("SHA-256").digest(bytes);
    }

    private static LootHistoryStore store(Path root) {
        return new LootHistoryStore(root.toString());
    }

    private static void freshAndLock(Path root) throws Exception {
        Path dir = unused(root, "fresh-and-lock");
        LootHistoryStore a = store(dir);
        check(!Files.exists(dir, LinkOption.NOFOLLOW_LINKS), "preflight-does-not-precreate");
        check(a.loadForMerge() == null, "read-requires-owner");
        check(!a.saveWithReceipt(Collections.emptyList()), "save-requires-owner");
        check(!a.clearWithReceipt(), "clear-requires-owner");
        check(!Files.exists(dir, LinkOption.NOFOLLOW_LINKS),
              "unleased-operations-never-make-directory");
        check(a.r421PrepareHistoryDirectoryForLease(), "create-one-leaf");
        check(Files.isDirectory(dir, LinkOption.NOFOLLOW_LINKS), "leaf-created");
        check(a.r421PrepareHistoryDirectoryForLease(), "idempotent-existing-leaf");
        check(a.r419ActivateOwner(), "acquire-os-owner");
        check(a.r419ActivateOwner(), "same-owner-idempotent");
        check(a.r411StageState() == LootHistoryStore.R411StageState.CLEAR,
              "clear-stage-after-owner");
        List<LootTrackerRecord> unloaded = a.loadForMerge();
        check(unloaded != null && unloaded.isEmpty(), "fresh-read-empty");
        check(a.saveWithReceipt(Collections.emptyList()), "forced-empty-history-save");
        Path history = dir.resolve(LootHistoryStore.FILE_NAME);
        check(Files.isRegularFile(history, LinkOption.NOFOLLOW_LINKS),
              "saved-history-is-regular");
        byte[] historical = Files.readAllBytes(history);
        check(historical.length > 0, "historical-image-nonempty");
        List<LootTrackerRecord> reloaded = a.loadForMerge();
        check(reloaded != null && reloaded.isEmpty(), "roundtrip-read-empty");

        LootHistoryStore b = store(dir);
        check(!b.r419ActivateOwner(), "second-owner-rejected");
        check(!b.saveWithReceipt(Collections.emptyList()), "nonowner-write-refused");
        check(b.loadForMerge() == null, "nonowner-read-refused");
        check(!b.clearWithReceipt(), "nonowner-clear-refused");
        check(Arrays.equals(historical, Files.readAllBytes(history)),
              "second-owner-never-mutates-history");

        a.r419CloseOwner();
        check(a.loadForMerge() == null, "released-owner-cannot-read");
        check(!a.clearWithReceipt(), "released-owner-cannot-delete");
        check(b.r419ActivateOwner(), "different-owner-acquires-after-release");
        check(b.loadForMerge() != null, "new-owner-reads");
        check(b.clearWithReceipt(), "new-owner-clear-receipt");
        check(!Files.exists(history, LinkOption.NOFOLLOW_LINKS),
              "clear-deleted-only-canonical-history");
        b.r419CloseOwner();
        check(Files.isRegularFile(dir.resolve("loot-history.writer.lock"),
                                  LinkOption.NOFOLLOW_LINKS),
              "lock-path-preserved-after-release");
    }

    private static void unresolved(Path root, String name,
                                   String fixtureName) throws Exception {
        Path dir = unused(root, fixtureName);
        LootHistoryStore store = store(dir);
        check(store.r421PrepareHistoryDirectoryForLease(),
              fixtureName + "-create");
        Path marker = dir.resolve(name);
        byte[] bytes = ("fabricated-" + fixtureName).getBytes(StandardCharsets.US_ASCII);
        Files.write(marker, bytes, StandardOpenOption.CREATE_NEW);
        check(store.r419ActivateOwner(), fixtureName + "-owner");
        check(store.r411StageState() == LootHistoryStore.R411StageState.UNSAFE ||
              store.r411StageState() == LootHistoryStore.R411StageState.ORPHAN,
              fixtureName + "-stage-block");
        check(store.loadForMerge() == null, fixtureName + "-read-block");
        check(!store.saveWithReceipt(Collections.emptyList()),
              fixtureName + "-save-block");
        check(!store.clearWithReceipt(), fixtureName + "-clear-block");
        check(Arrays.equals(bytes, Files.readAllBytes(marker)),
              fixtureName + "-marker-untouched");
        check(!Files.exists(dir.resolve(LootHistoryStore.FILE_NAME),
                             LinkOption.NOFOLLOW_LINKS),
              fixtureName + "-no-history-created");
        store.r419CloseOwner();
    }

    private static void invalidPaths(Path root) throws Exception {
        Path absent = unused(root, "parent-missing").resolve("child");
        LootHistoryStore s = store(absent);
        check(!s.r421PrepareHistoryDirectoryForLease(), "missing-parent-rejected");
        check(!Files.exists(absent.getParent()), "missing-parent-not-created");

        Path occupied = unused(root, "occupied");
        byte[] keep = "synthetic-keep-file".getBytes(StandardCharsets.US_ASCII);
        Files.write(occupied, keep, StandardOpenOption.CREATE_NEW);
        s = store(occupied);
        check(!s.r421PrepareHistoryDirectoryForLease(), "regular-file-leaf-refused");
        check(Arrays.equals(keep, Files.readAllBytes(occupied)),
              "regular-file-unchanged");

        Path target = unused(root, "symlink-target");
        Files.createDirectory(target);
        Path link = root.resolve("symlink-leaf");
        try {
            Files.createSymbolicLink(link, target);
            check(!store(link).r421PrepareHistoryDirectoryForLease(),
                  "symlink-leaf-refused");
            check(Files.isDirectory(target), "symlink-target-unchanged");
        } catch (UnsupportedOperationException | IOException | SecurityException notAllowed) {
            System.out.println("R422_OPTIONAL_SYMLINK_UNAVAILABLE");
        }
    }

    private static void heldActionRelease(Path root) throws Exception {
        Path dir = unused(root, "held-operation");
        LootHistoryStore s = store(dir);
        check(s.r421PrepareHistoryDirectoryForLease(), "held-dir-prepared");
        check(s.r419ActivateOwner(), "held-owner");
        // Obtain same actual store's lease via package-private API tests only:
        // a second lock against the same path must fail while the owner lives.
        CountDownLatch entered = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        CountDownLatch closed = new CountDownLatch(1);
        AtomicReference<Throwable> failure = new AtomicReference<>();

        java.lang.reflect.Method method =
            LootHistoryStore.class.getDeclaredMethod("r419WithOwner", Runnable.class);
        method.setAccessible(true);
        Thread action = new Thread(() -> {
            try {
                Boolean result = (Boolean) method.invoke(s, (Runnable) () -> {
                    entered.countDown();
                    try {
                        if (!release.await(5, TimeUnit.SECONDS))
                            throw new AssertionError("blocked-action-timeout");
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        throw new AssertionError(e);
                    }
                });
                if (!result) throw new AssertionError("action-refused");
            } catch (Throwable e) { failure.compareAndSet(null, e); }
        }, "R422-Synthetic-Store-Action");
        action.setDaemon(true);
        action.start();
        check(entered.await(2, TimeUnit.SECONDS), "action-entered");

        Thread closer = new Thread(() -> {
            try { s.r419CloseOwner(); }
            catch (Throwable e) { failure.compareAndSet(null, e); }
            finally { closed.countDown(); }
        }, "R422-Synthetic-Store-Close");
        closer.setDaemon(true);
        closer.start();
        check(!closed.await(70, TimeUnit.MILLISECONDS),
              "close-waits-for-inflight-action");
        release.countDown();
        check(closed.await(2, TimeUnit.SECONDS), "close-eventually-finished");
        action.join(1600L);
        check(!action.isAlive(), "original-action-finished");
        check(failure.get() == null, "held-operation-no-error");
        check(!s.saveWithReceipt(Collections.emptyList()),
              "closed-owner-write-refused");
        LootHistoryStore b = store(dir);
        check(b.r419ActivateOwner(), "new-owner-after-held-action");
        b.r419CloseOwner();
    }

    private static void selftest(Path root) throws Exception {
        freshAndLock(root);
        unresolved(root, "loot-history.json.tmp", "unresolved-history-stage");
        unresolved(root, "loot-history.delete.intent", "unresolved-intent");
        unresolved(root, "loot-history.delete.ack", "unresolved-ack");
        unresolved(root, "loot-history.delete.ack.tmp", "unresolved-ack-stage");
        invalidPaths(root);
        heldActionRelease(root);
        System.out.println("R422_ACTUAL_PRIVATE_STORE_PASS assertions=" + passed);
    }

    private static void externalOwner(Path root, String mode) throws Exception {
        LootHistoryStore s = store(root);
        if (!s.r421PrepareHistoryDirectoryForLease()) {
            System.out.println("REFUSED_PREPARE");
            return;
        }
        if (!s.r419ActivateOwner()) {
            System.out.println("REFUSED_OWNER");
            return;
        }
        System.out.println("ACQUIRED");
        System.out.flush();
        if ("crash".equals(mode)) Runtime.getRuntime().halt(77);
        if ("hold".equals(mode)) System.in.read();
        s.r419CloseOwner();
        System.out.println("RELEASED");
        System.out.flush();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2)
            throw new IllegalArgumentException(
                "<selftest|try|hold|crash> <R422-Synthetic-TEMP-root>");
        Path root = safeRoot(args[1]);
        if ("selftest".equals(args[0])) selftest(root);
        else if ("try".equals(args[0]) || "hold".equals(args[0]) ||
                 "crash".equals(args[0])) externalOwner(root, args[0]);
        else throw new IllegalArgumentException("unsupported-test-mode");
    }
}

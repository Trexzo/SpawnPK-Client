package rs.plugins.loottracker;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;

/**
 * Owner-only acceptance of EXACT rebuilt private R425 class bytes.
 *
 * Public harness, not recovered source. Executes only the isolated compiled
 * LootHistoryStore in fabricated R425-Synthetic-* TEMP directories.
 *
 * This does not construct the game client, plugin UI, or visit live history.
 */
public final class R425ActualPrivateOverlayAcceptance {
    private static int assertions;

    static void require(boolean yes, String name) {
        if (!yes) throw new AssertionError("R425_FAIL_" + name);
        assertions++;
    }

    static Path newLeaf(Path root, String name) {
        Path p = root.resolve(name);
        if (Files.exists(p, LinkOption.NOFOLLOW_LINKS) || Files.isSymbolicLink(p))
            throw new IllegalArgumentException("R425_UNEXPECTED_PREEXISTING_FIXTURE");
        return p;
    }

    static void put(Path path, byte[] content) throws Exception {
        Files.write(path, content, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
    }

    static LootHistoryStore owned(Path path) throws Exception {
        LootHistoryStore store = new LootHistoryStore(path.toString());
        require(store.r421PrepareHistoryDirectoryForLease(), "prepared-" + path.getFileName());
        require(store.r419ActivateOwner(), "owned-" + path.getFileName());
        return store;
    }

    static void dryRunPreservesLegacy(Path root) throws Exception {
        Path dir = newLeaf(root, "preserve-legacy");
        LootHistoryStore store = owned(dir);
        try {
            Path retired = dir.resolve("loot-history");
            Files.createDirectory(retired);
            Path nested = retired.resolve("nested");
            Files.createDirectory(nested);
            byte[] value = "fabricated-private-store-record".getBytes(StandardCharsets.US_ASCII);
            Path item = nested.resolve("record.dat");
            put(item, value);
            byte[] keys = "fabricated-seen-key".getBytes(StandardCharsets.US_ASCII);
            Path seen = dir.resolve("loot-keys-seen.txt");
            put(seen, keys);
            byte[] canonical = "{\"version\":1,\"records\":[]}".getBytes(StandardCharsets.US_ASCII);
            Path history = dir.resolve(LootHistoryStore.FILE_NAME);
            put(history, canonical);
            // The actual patched store startup path must NEVER delete.
            store.deleteStale();
            require(Files.isDirectory(retired, LinkOption.NOFOLLOW_LINKS), "retired-tree-remains");
            require(Files.isDirectory(nested, LinkOption.NOFOLLOW_LINKS), "nested-tree-remains");
            require(Arrays.equals(value, Files.readAllBytes(item)), "legacy-record-remains");
            require(Arrays.equals(keys, Files.readAllBytes(seen)), "seen-keys-remain");
            require(Arrays.equals(canonical, Files.readAllBytes(history)), "canonical-remains");
            store.deleteStale();
            require(Arrays.equals(value, Files.readAllBytes(item)), "second-startup-no-delete");
            require(Arrays.equals(keys, Files.readAllBytes(seen)), "second-startup-keys-remain");
        } finally {
            store.r419CloseOwner();
        }
    }

    static void ownerIsRequired(Path root) throws Exception {
        Path dir = newLeaf(root, "owner-required");
        LootHistoryStore store = new LootHistoryStore(dir.toString());
        require(store.r421PrepareHistoryDirectoryForLease(), "owner-directory-prepared");
        Files.createDirectory(dir.resolve("loot-history"));
        put(dir.resolve("loot-keys-seen.txt"), new byte[]{14});
        store.deleteStale();
        require(Files.isDirectory(dir.resolve("loot-history")), "unowned-tree-preserved");
        require(Files.isRegularFile(dir.resolve("loot-keys-seen.txt")), "unowned-keys-preserved");
        require(store.r419ActivateOwner(), "owner-acquired-after-inert-preflight");
        store.r419CloseOwner();
        store.deleteStale();
        require(Files.isDirectory(dir.resolve("loot-history")), "released-owner-no-delete");
    }

    static void unresolvedMarkersBlock(Path root) throws Exception {
        String[] markers = {
            "loot-history.json.tmp",
            "loot-history.delete.intent",
            "loot-history.delete.intent.tmp",
            "loot-history.delete.ack",
            "loot-history.delete.ack.tmp"
        };
        for (int i = 0; i < markers.length; i++) {
            Path dir = newLeaf(root, "pending-" + i);
            LootHistoryStore store = owned(dir);
            try {
                Path retired = dir.resolve("loot-history");
                Files.createDirectory(retired);
                Path seen = dir.resolve("loot-keys-seen.txt");
                put(seen, new byte[]{1});
                Path marker = dir.resolve(markers[i]);
                byte[] receipt = ("fabricated-" + markers[i])
                    .getBytes(StandardCharsets.US_ASCII);
                put(marker, receipt);
                store.deleteStale();
                require(Files.isDirectory(retired), "marker-legacy-preserved-" + i);
                require(Files.isRegularFile(seen), "marker-keys-preserved-" + i);
                require(Arrays.equals(receipt, Files.readAllBytes(marker)),
                        "marker-contents-preserved-" + i);
            } finally {
                store.r419CloseOwner();
            }
        }
    }

    static void symlinkRefusal(Path root) throws Exception {
        Path dir = newLeaf(root, "symlink-legacy");
        LootHistoryStore store = owned(dir);
        try {
            Path outside = newLeaf(root, "outside-retired-tree");
            Files.createDirectory(outside);
            Path sentinel = outside.resolve("outside.txt");
            put(sentinel, "never-delete".getBytes(StandardCharsets.US_ASCII));
            Path retired = dir.resolve("loot-history");
            Files.createDirectory(retired);
            try {
                Files.createSymbolicLink(retired.resolve("external"), outside);
                store.deleteStale();
                require(Files.exists(retired.resolve("external"), LinkOption.NOFOLLOW_LINKS),
                        "symlink-not-deleted");
                require(Arrays.equals("never-delete".getBytes(StandardCharsets.US_ASCII),
                        Files.readAllBytes(sentinel)), "outside-file-not-deleted");
            } catch (UnsupportedOperationException | java.io.IOException |
                     SecurityException unavailable) {
                System.out.println("R425_OPTIONAL_SYMLINK_UNAVAILABLE");
            }
        } finally {
            store.r419CloseOwner();
        }
    }

    public static void main(String[] argv) throws Exception {
        if (argv.length != 1)
            throw new IllegalArgumentException("R425_SYNTHETIC_TEMP_ROOT_REQUIRED");
        Path root = Paths.get(argv[0]).toAbsolutePath().normalize();
        Path temp = Paths.get(System.getProperty("java.io.tmpdir"))
            .toAbsolutePath().normalize();
        if (root.getParent() == null || !root.getParent().equals(temp) ||
            root.getFileName() == null ||
            !root.getFileName().toString().startsWith("R425-Synthetic-") ||
            !Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS) ||
            Files.isSymbolicLink(root))
            throw new IllegalArgumentException("R425_UNSAFE_SYNTHETIC_ROOT");
        dryRunPreservesLegacy(root);
        ownerIsRequired(root);
        unresolvedMarkersBlock(root);
        symlinkRefusal(root);
        System.out.println("R425_ACTUAL_PATCHED_PRIVATE_STORE_PASS assertions=" + assertions);
    }
}

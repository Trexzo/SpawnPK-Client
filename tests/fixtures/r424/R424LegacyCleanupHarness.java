package rs.plugins.loottracker;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import javax.swing.SwingUtilities;

/** Public-only original helper acceptance; fake TEMP data only. */
public final class R424LegacyCleanupHarness {
    private static int asserts;
    static void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
        asserts++;
    }
    static void write(Path p, String value) throws Exception {
        Files.createDirectories(p.getParent());
        Files.write(p, value.getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
    }
    static Path newPath(Path root, String n) {return root.resolve(n);}
    static void test(Path root) throws Exception {
        Path legacy = root.resolve("loot-history");
        Path history = root.resolve("loot-history.json");
        write(legacy.resolve("nested/item.dat"), "synthetic");
        write(root.resolve("loot-keys-seen.txt"), "synthetic-key");
        write(history, "synthetic-canonical");
        LootLegacyCleanupR424.Receipt dry = LootLegacyCleanupR424.run(root, () -> true, false);
        check(dry.status == LootLegacyCleanupR424.Status.SCANNED, "dry-status");
        check(dry.planned == 4, "dry-plan-count");
        check(dry.deleted == 0, "dry-no-deletion");
        check(Files.exists(legacy.resolve("nested/item.dat")), "dry-leaves-tree");
        check(Files.exists(root.resolve("loot-keys-seen.txt")), "dry-leaves-keys");
        check(Files.exists(history), "dry-leaves-history");
        LootLegacyCleanupR424.Receipt refused = LootLegacyCleanupR424.run(root, () -> false, true);
        check(refused.status == LootLegacyCleanupR424.Status.REFUSED, "admission-refuses");
        check(Files.exists(legacy), "admission-no-delete");
        LootLegacyCleanupR424.Receipt committed = LootLegacyCleanupR424.run(root, () -> true, true);
        check(committed.status == LootLegacyCleanupR424.Status.CLEANED, "synthetic-commit");
        check(committed.deleted == 4, "commit-count");
        check(!Files.exists(legacy), "tree-removed");
        check(!Files.exists(root.resolve("loot-keys-seen.txt")), "keys-removed");
        check(Files.exists(history), "canonical-preserved");
        LootLegacyCleanupR424.Receipt none = LootLegacyCleanupR424.run(root, () -> true, false);
        check(none.status == LootLegacyCleanupR424.Status.NOT_PRESENT, "empty-state");

        Path bad = root.resolve("unsafe-legacy");
        Files.createDirectory(bad);
        Path outside = root.resolve("keep.txt");
        write(outside, "DO NOT DELETE");
        try {
            Files.createSymbolicLink(bad.resolve("loot-history"), outside);
            LootLegacyCleanupR424.Receipt s = LootLegacyCleanupR424.run(bad, () -> true, true);
            check(s.status == LootLegacyCleanupR424.Status.REFUSED, "symlink-tree-refused");
            check(Files.exists(outside), "outside-preserved");
        } catch (UnsupportedOperationException | java.io.IOException | SecurityException e) {
            System.out.println("R424_OPTIONAL_SYMLINK_UNAVAILABLE");
        }
        Path pending = root.resolve("pending");
        Files.createDirectory(pending);
        write(pending.resolve("loot-history.delete.ack"), "synthetic-evidence");
        write(pending.resolve("loot-keys-seen.txt"), "synthetic-key");
        LootLegacyCleanupR424.Receipt blocked = LootLegacyCleanupR424.run(pending, () -> true, true);
        check(blocked.status == LootLegacyCleanupR424.Status.REFUSED, "unresolved-marker-refused");
        check(Files.exists(pending.resolve("loot-keys-seen.txt")), "marker-does-not-delete");
        check(Files.exists(pending.resolve("loot-history.delete.ack")), "marker-preserved");
        Path invalid = root.resolve("not-a-dir");
        write(invalid, "synthetic");
        check(LootLegacyCleanupR424.run(invalid, () -> true, false).status == LootLegacyCleanupR424.Status.REFUSED,
            "invalid-parent-refused");
        Thread.currentThread().interrupt();
        LootLegacyCleanupR424.Receipt interrupted = LootLegacyCleanupR424.run(root, () -> true, true);
        check(interrupted.status == LootLegacyCleanupR424.Status.INTERRUPTED, "interrupt-first");
        Thread.interrupted();
        final LootLegacyCleanupR424.Receipt[] edt = new LootLegacyCleanupR424.Receipt[1];
        SwingUtilities.invokeAndWait(() -> edt[0] = LootLegacyCleanupR424.run(root, () -> true, true));
        check(edt[0].status == LootLegacyCleanupR424.Status.REFUSED, "edt-refused");
        System.out.println("R424_PUBLIC_HELPER_PASS assertions="+asserts);
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=1) throw new IllegalArgumentException("exact scratch path required");
        Path root=Paths.get(args[0]).toAbsolutePath().normalize();
        Path tmp=Paths.get(System.getProperty("java.io.tmpdir")).toAbsolutePath().normalize();
        if(!root.getParent().equals(tmp) || root.getFileName()==null ||
           !root.getFileName().toString().startsWith("R424-Synthetic-") ||
           !Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS) || Files.isSymbolicLink(root))
           throw new IllegalArgumentException("R424_REFUSED_NON_SYNTHETIC_TEMP_ROOT");
        test(root);
    }
}

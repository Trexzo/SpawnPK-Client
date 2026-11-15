package rs.plugins.loottracker;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import java.util.zip.CRC32;

/**
 * R429 PUBLIC, independently authored Java 11 synthetic-only durable-intent
 * research model. NOT recovered SpawnPK source and NEVER a runtime patch.
 *
 * All operations are fenced to R429-Synthetic-* directly beneath Java TEMP.
 * A committed intent is retained across JVM restarts and is never silently
 * cleared after a simulated success, an exception, or a crash.
 *
 * This is an extra research ledger and is NOT a substitute for R415-R417
 * deletion intent/ack, an R419 lifetime owner lease, directory fsync,
 * hostile path-swap defense or power-cut durability verification.
 */
public final class R429SyntheticRestartFence {
    static final String FILE = "R429-synthetic-intent.ledger";
    static final int SLOT = 128;
    static final int BYTES = SLOT * 2;
    static final long MAGIC = 0x523432394c454447L;
    static final int VERSION = 1;
    static final String[] OLD_EVIDENCE = {
        "loot-history.json.tmp",
        "loot-history.delete.intent",
        "loot-history.delete.intent.tmp",
        "loot-history.delete.ack",
        "loot-history.delete.ack.tmp"
    };
    enum Phase { EMPTY, PENDING, CONFIRMED }
    static final class Record {
        final long sequence;
        final Phase phase;
        final UUID operation;

        Record(long sequence, Phase phase, UUID operation) {
            this.sequence = sequence;
            this.phase = phase;
            this.operation = operation;
        }
    }
    private static final class Read {
        final Record record;
        final int active;
        Read(Record record, int active) {
            this.record = record;
            this.active = active;
        }
    }
    private static final class Refused extends Exception {
        Refused(String reason) { super(reason); }
    }

    private R429SyntheticRestartFence() {}

    private static BasicFileAttributes attributes(Path p) throws IOException {
        return Files.readAttributes(p, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
    }

    private static void realDirectoryAncestors(Path p) throws Exception {
        for (Path ancestor = p; ancestor != null; ancestor = ancestor.getParent()) {
            BasicFileAttributes a = attributes(ancestor);
            if (!a.isDirectory() || a.isSymbolicLink() || a.isOther())
                throw new Refused("R429_UNSAFE_ANCESTOR");
        }
    }

    private static Path syntheticRoot(String userInput) throws Exception {
        Path root = Paths.get(userInput).toAbsolutePath().normalize();
        Path temp = Paths.get(System.getProperty("java.io.tmpdir")).toAbsolutePath().normalize();
        if (root.getParent() == null || !root.getParent().equals(temp) ||
            root.getFileName() == null ||
            !root.getFileName().toString().startsWith("R429-Synthetic-"))
            throw new Refused("R429_ROOT_NOT_DIRECT_SYNTHETIC_TEMP");
        realDirectoryAncestors(root);
        return root;
    }

    private static boolean isPresentNoFollow(Path p) throws IOException {
        try {
            attributes(p);
            return true;
        } catch (NoSuchFileException absent) {
            return false;
        }
    }

    private static void requireNoForeignJournalEvidence(Path root)
            throws Exception {
        for (String name : OLD_EVIDENCE) {
            if (isPresentNoFollow(root.resolve(name)))
                throw new Refused("R429_UNRESOLVED_EXISTING_DELETE_EVIDENCE");
        }
    }

    private static byte[] bytes(Record record) {
        byte[] data = new byte[SLOT];
        ByteBuffer b = ByteBuffer.wrap(data);
        b.putLong(MAGIC);
        b.putInt(VERSION);
        b.putInt(record.phase.ordinal());
        b.putLong(record.sequence);
        b.putLong(record.operation.getMostSignificantBits());
        b.putLong(record.operation.getLeastSignificantBits());
        CRC32 crc = new CRC32();
        crc.update(data, 0, 40);
        b.putInt((int) crc.getValue());
        return data;
    }

    private static boolean zero(byte[] data) {
        for (byte b : data) if (b != 0) return false;
        return true;
    }

    private static Record decode(byte[] data) throws Exception {
        if (zero(data)) return null;
        if (data.length != SLOT) throw new Refused("R429_INVALID_SLOT_SIZE");
        ByteBuffer b = ByteBuffer.wrap(data);
        long magic = b.getLong();
        int version = b.getInt();
        int type = b.getInt();
        long sequence = b.getLong();
        long high = b.getLong();
        long low = b.getLong();
        int storedCrc = b.getInt();
        CRC32 crc = new CRC32();
        crc.update(data, 0, 40);
        if (magic != MAGIC || version != VERSION || type < 0 ||
            type >= Phase.values().length || sequence < 1 ||
            storedCrc != (int) crc.getValue())
            throw new Refused("R429_CORRUPT_OR_UNKNOWN_SLOT");
        for (int i = 44; i < SLOT; i++) {
            if (data[i] != 0)
                throw new Refused("R429_UNEXPECTED_TRAILING_BYTES");
        }
        return new Record(sequence, Phase.values()[type], new UUID(high, low));
    }

    private static byte[] readExactly(FileChannel channel, int position)
            throws Exception {
        byte[] data = new byte[SLOT];
        ByteBuffer b = ByteBuffer.wrap(data);
        long start = position;
        while (b.hasRemaining()) {
            int n = channel.read(b, start + b.position());
            if (n < 0) throw new Refused("R429_TRUNCATED_LEDGER");
            if (n == 0) throw new Refused("R429_INCOMPLETE_SLOT_READ");
        }
        return data;
    }

    private static Read readCurrent(FileChannel channel) throws Exception {
        if (channel.size() != BYTES)
            throw new Refused("R429_LEDGER_UNEXPECTED_SIZE");
        Record first = decode(readExactly(channel, 0));
        Record second = decode(readExactly(channel, SLOT));
        if (first == null && second == null)
            throw new Refused("R429_NO_VALID_RECORD");
        if (first != null && second != null && first.sequence == second.sequence)
            throw new Refused("R429_DUPLICATE_SEQUENCE");
        if (first != null && (second == null || first.sequence > second.sequence))
            return new Read(first, 0);
        return new Read(second, 1);
    }

    private static void writeSlot(FileChannel channel, int index, Record r)
            throws Exception {
        ByteBuffer b = ByteBuffer.wrap(bytes(r));
        long offset = (long) index * SLOT;
        while (b.hasRemaining()) {
            int n = channel.write(b, offset + b.position());
            if (n <= 0) throw new Refused("R429_FAILED_SLOT_WRITE");
        }
        channel.force(true);
        Record observed = decode(readExactly(channel, (int) offset));
        if (observed == null || observed.sequence != r.sequence ||
            observed.phase != r.phase || !observed.operation.equals(r.operation))
            throw new Refused("R429_WRITE_VERIFICATION_FAILED");
    }

    private static void assertRegularLedger(Path ledger) throws Exception {
        BasicFileAttributes a = attributes(ledger);
        if (!a.isRegularFile() || a.isSymbolicLink() || a.isOther())
            throw new Refused("R429_LEDGER_NOT_REGULAR_NOFOLLOW");
    }

    private static FileChannel openExisting(Path ledger) throws Exception {
        assertRegularLedger(ledger);
        Set<OpenOption> options = new HashSet<>();
        options.add(StandardOpenOption.READ);
        options.add(StandardOpenOption.WRITE);
        options.add(LinkOption.NOFOLLOW_LINKS);
        return FileChannel.open(ledger, options);
    }

    private static FileLock exclusive(FileChannel channel) throws Exception {
        try {
            FileLock lock = channel.tryLock();
            if (lock == null) throw new Refused("R429_BUSY_LOCK");
            return lock;
        } catch (OverlappingFileLockException sameJvm) {
            throw new Refused("R429_BUSY_SAME_JVM");
        }
    }

    private static String inspect(Path root) throws Exception {
        requireNoForeignJournalEvidence(root);
        try (FileChannel c = openExisting(root.resolve(FILE));
             FileLock locked = exclusive(c)) {
            Read latest = readCurrent(c);
            return label(latest.record);
        }
    }

    private static String initialize(Path root) throws Exception {
        requireNoForeignJournalEvidence(root);
        Set<OpenOption> options = new HashSet<>();
        options.add(StandardOpenOption.CREATE_NEW);
        options.add(StandardOpenOption.READ);
        options.add(StandardOpenOption.WRITE);
        options.add(LinkOption.NOFOLLOW_LINKS);
        try (FileChannel c = FileChannel.open(root.resolve(FILE), options);
             FileLock locked = exclusive(c)) {
            ByteBuffer blank = ByteBuffer.wrap(new byte[BYTES]);
            while (blank.hasRemaining()) {
                if (c.write(blank) <= 0)
                    throw new Refused("R429_LEDGER_ALLOCATION_FAILED");
            }
            writeSlot(c, 0, new Record(1, Phase.EMPTY, new UUID(0, 0)));
            Read verified = readCurrent(c);
            if (verified.record.phase != Phase.EMPTY)
                throw new Refused("R429_INIT_NOT_VERIFIED");
            return "R429_INITIALIZED " + label(verified.record);
        }
    }

    private static String begin(Path root, UUID id, boolean crash)
            throws Exception {
        requireNoForeignJournalEvidence(root);
        try (FileChannel c = openExisting(root.resolve(FILE));
             FileLock locked = exclusive(c)) {
            Read before = readCurrent(c);
            if (before.record.phase != Phase.EMPTY)
                throw new Refused("R429_PERSISTED_UNRESOLVED_EVIDENCE");
            if (id.equals(new UUID(0, 0)))
                throw new Refused("R429_INVALID_OPERATION_ID");
            Record pending = new Record(
                before.record.sequence + 1, Phase.PENDING, id);
            writeSlot(c, 1 - before.active, pending);
            if (crash) {
                System.out.println("R429_SYNTHETIC_INTENT_FORCED_BEFORE_CRASH");
                System.out.flush();
                Runtime.getRuntime().halt(77);
            }
            return "R429_INTENT_RECORDED " + label(pending);
        }
    }

    /**
     * Synthetic only. An external store would require a proven durable
     * acknowledged transaction under its R419 writer gate. Even with this
     * simulated proof, the marker is retained and restart stays fenced.
     * No automatic clear/reset/reuse API is provided.
     */
    private static String simulateProof(Path root, UUID id) throws Exception {
        requireNoForeignJournalEvidence(root);
        try (FileChannel c = openExisting(root.resolve(FILE));
             FileLock locked = exclusive(c)) {
            Read latest = readCurrent(c);
            if (latest.record.phase != Phase.PENDING ||
                !latest.record.operation.equals(id))
                throw new Refused("R429_PROOF_NOT_MATCHING_PENDING_INTENT");
            Record sealed = new Record(
                latest.record.sequence + 1, Phase.CONFIRMED, id);
            writeSlot(c, 1 - latest.active, sealed);
            return "R429_SIMULATED_PROOF_RETAINED " + label(sealed);
        }
    }

    private static String label(Record r) {
        return "R429_STATE=" + r.phase + " SEQ=" + r.sequence +
               " OP=" + r.operation;
    }

    private static void hold(Path root) throws Exception {
        requireNoForeignJournalEvidence(root);
        try (FileChannel c = openExisting(root.resolve(FILE));
             FileLock locked = exclusive(c)) {
            readCurrent(c);
            System.out.println("R429_SYNTHETIC_LOCK_HELD");
            System.out.flush();
            System.in.read();
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 2 || args.length > 3)
            throw new IllegalArgumentException(
                "<init|status|begin|crash|seal|hold> <R429-Synthetic-TEMP> [uuid]");
        try {
            Path root = syntheticRoot(args[1]);
            String mode = args[0];
            String result;
            if ("init".equals(mode) && args.length == 2) result = initialize(root);
            else if ("status".equals(mode) && args.length == 2) result = inspect(root);
            else if ("hold".equals(mode) && args.length == 2) {
                hold(root);
                result = "R429_SYNTHETIC_LOCK_RELEASED";
            } else if (("begin".equals(mode) || "crash".equals(mode) ||
                        "seal".equals(mode)) && args.length == 3) {
                UUID id = UUID.fromString(args[2]);
                result = "seal".equals(mode) ? simulateProof(root, id) :
                    begin(root, id, "crash".equals(mode));
            } else throw new Refused("R429_UNKNOWN_MODE_OR_ARGUMENTS");
            System.out.println(result);
        } catch (Refused | IOException | SecurityException e) {
            String reason = e instanceof Refused ? e.getMessage() :
                "R429_IO_OR_PERMISSION_UNCERTAIN";
            System.out.println("R429_REFUSED " + reason);
            System.exit(2);
        }
    }
}

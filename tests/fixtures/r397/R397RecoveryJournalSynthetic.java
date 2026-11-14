import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.zip.CRC32;

/**
 * R397 standalone crash-recovery protocol experiment. This is invented
 * synthetic data, NOT SpawnPK source, not a client module, not approved for
 * live use, and does not prove OS power-loss durability or multi-writer safety.
 *
 * A future integration would need persistent event IDs AND a snapshot
 * lastApplied watermark. Merely appending drops to a separate file would
 * double-count them after a crash between a snapshot save and journal erase.
 */
public final class R397RecoveryJournalSynthetic {
    static final int FRAME_MAGIC = 0x52333937;
    static final int SNAP_MAGIC = 0x53333937;
    static final int MAX_PAYLOAD = 64 * 1024;
    static final int MAX_JOURNAL = 2 * 1024 * 1024;
    static int passed;

    static final class Drop {
        final long id;
        final String value;
        Drop(long id, String value) { this.id = id; this.value = value; }
    }
    static final class Snapshot {
        final long watermark;
        final List<Drop> records;
        Snapshot(long watermark, List<Drop> records) {
            this.watermark = watermark;
            this.records = records;
        }
    }
    static void check(boolean ok, String msg) {
        if (!ok) throw new AssertionError(msg);
    }

    static final class Journal {
        final Path home, frames, main;
        int snapshotWrites;
        boolean failCommitBeforeMove;

        Journal(Path home) throws Exception {
            this.home = home;
            if (!Files.isDirectory(home, LinkOption.NOFOLLOW_LINKS)
                    || Files.isSymbolicLink(home)) {
                throw new IOException("UNSAFE_JOURNAL_DIRECTORY");
            }
            frames = home.resolve("recovery.frames");
            main = home.resolve("history.snapshot");
        }
        void ensureSafe(Path p) throws IOException {
            if (Files.isSymbolicLink(p)) throw new IOException("REFUSE_SYMLINK");
        }
        static int crc(byte[] bytes) {
            CRC32 c = new CRC32();
            c.update(bytes);
            return (int)c.getValue();
        }
        static byte[] encodeFrame(long id, String value) throws Exception {
            byte[] payload = value.getBytes(StandardCharsets.UTF_8);
            if (payload.length < 1 || payload.length > MAX_PAYLOAD) {
                throw new IOException("PAYLOAD_LIMIT");
            }
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            DataOutputStream d = new DataOutputStream(output);
            d.writeInt(FRAME_MAGIC);
            d.writeLong(id);
            d.writeInt(payload.length);
            d.write(payload);
            d.flush();
            byte[] core = output.toByteArray();
            d.writeInt(crc(core));
            d.flush();
            return output.toByteArray();
        }
        long append(String value) throws Exception {
            List<Drop> existing = scan();
            Snapshot old = readSnapshot();
            long last = old.watermark;
            if (!existing.isEmpty()) last = Math.max(last, existing.get(existing.size()-1).id);
            if (last == Long.MAX_VALUE) throw new IOException("ID_EXHAUSTED");
            long id = last + 1;
            byte[] frame = encodeFrame(id, value);
            ensureSafe(frames);
            long oldSize = Files.exists(frames, LinkOption.NOFOLLOW_LINKS)
                    ? Files.size(frames) : 0;
            if (oldSize + frame.length > MAX_JOURNAL) throw new IOException("JOURNAL_FULL");
            // Force the frame to stable storage as far as Java/OS promises.
            // Directory metadata and hardware power-loss durability are unproven.
            try (FileChannel fc = FileChannel.open(frames,
                    StandardOpenOption.WRITE, StandardOpenOption.CREATE, StandardOpenOption.APPEND)) {
                ByteBuffer data = ByteBuffer.wrap(frame);
                while (data.hasRemaining()) fc.write(data);
                fc.force(true);
            }
            return id;
        }
        List<Drop> scan() throws Exception {
            ensureSafe(frames);
            if (!Files.exists(frames, LinkOption.NOFOLLOW_LINKS)) {
                return new ArrayList<Drop>();
            }
            if (Files.size(frames) > MAX_JOURNAL) throw new IOException("JOURNAL_LIMIT");
            byte[] data = Files.readAllBytes(frames);
            List<Drop> result = new ArrayList<Drop>();
            int offset = 0;
            long previous = 0;
            while (offset < data.length) {
                if (data.length - offset < 20) throw new IOException("TRUNCATED_FRAME");
                DataInputStream in = new DataInputStream(new ByteArrayInputStream(
                        data, offset, data.length-offset));
                int magic = in.readInt();
                long id = in.readLong();
                int size = in.readInt();
                if (magic != FRAME_MAGIC || size < 1 || size > MAX_PAYLOAD) {
                    throw new IOException("BAD_FRAME");
                }
                long frameLength = 4L+8L+4L+size+4L;
                if (frameLength > data.length-offset) throw new IOException("TRUNCATED_FRAME");
                byte[] payload = new byte[size];
                in.readFully(payload);
                int declaredCrc = in.readInt();
                byte[] core = Arrays.copyOfRange(data, offset, offset+16+size);
                if (declaredCrc != crc(core)) throw new IOException("FRAME_CRC_MISMATCH");
                if (id <= previous) throw new IOException("FRAME_SEQUENCE_DRIFT");
                result.add(new Drop(id, new String(payload, StandardCharsets.UTF_8)));
                previous = id;
                offset += (int)frameLength;
            }
            return result;
        }
        Snapshot readSnapshot() throws Exception {
            ensureSafe(main);
            if (!Files.exists(main, LinkOption.NOFOLLOW_LINKS)) {
                return new Snapshot(0, new ArrayList<Drop>());
            }
            byte[] raw = Files.readAllBytes(main);
            if (raw.length < 20 || raw.length > MAX_JOURNAL) throw new IOException("SNAPSHOT_LIMIT");
            int claimed = ByteBuffer.wrap(raw, raw.length-4, 4).getInt();
            if (claimed != crc(Arrays.copyOf(raw, raw.length-4))) {
                throw new IOException("SNAPSHOT_CRC_MISMATCH");
            }
            DataInputStream input = new DataInputStream(
                    new ByteArrayInputStream(raw, 0, raw.length-4));
            if (input.readInt() != SNAP_MAGIC) throw new IOException("INVALID_SNAPSHOT");
            long watermark = input.readLong();
            int count = input.readInt();
            if (count < 0 || count > 20000) throw new IOException("SNAPSHOT_RECORD_LIMIT");
            List<Drop> out = new ArrayList<Drop>();
            long last = 0;
            for (int i=0;i<count;i++) {
                long id = input.readLong();
                int len = input.readInt();
                if (len < 1 || len > MAX_PAYLOAD) throw new IOException("SNAPSHOT_PAYLOAD_LIMIT");
                byte[] bytes = new byte[len];
                input.readFully(bytes);
                if (id <= last || id > watermark) throw new IOException("SNAPSHOT_ORDER_DRIFT");
                last = id;
                out.add(new Drop(id, new String(bytes,StandardCharsets.UTF_8)));
            }
            if (input.available()!=0) throw new IOException("SNAPSHOT_TRAILING_BYTES");
            return new Snapshot(watermark,out);
        }
        List<Drop> recovered() throws Exception {
            Snapshot snapshot = readSnapshot();
            List<Drop> all = new ArrayList<Drop>(snapshot.records);
            for (Drop entry : scan()) {
                if (entry.id > snapshot.watermark) all.add(entry);
            }
            return all;
        }
        static byte[] snapshotBytes(List<Drop> records) throws Exception {
            ByteArrayOutputStream stream = new ByteArrayOutputStream();
            DataOutputStream out = new DataOutputStream(stream);
            out.writeInt(SNAP_MAGIC);
            out.writeLong(records.isEmpty()?0:records.get(records.size()-1).id);
            out.writeInt(records.size());
            long last = 0;
            for (Drop event : records) {
                if (event.id <= last) throw new IOException("NONMONOTONIC_SNAPSHOT");
                last = event.id;
                byte[] payload = event.value.getBytes(StandardCharsets.UTF_8);
                if (payload.length==0 || payload.length>MAX_PAYLOAD)
                    throw new IOException("SNAPSHOT_BAD_PAYLOAD");
                out.writeLong(event.id);
                out.writeInt(payload.length);
                out.write(payload);
            }
            out.flush();
            byte[] beforeCrc = stream.toByteArray();
            out.writeInt(crc(beforeCrc));
            out.flush();
            return stream.toByteArray();
        }
        boolean commit() throws Exception {
            // Fail-closed: do not truncate the journal and don't overwrite an
            // unreadable snapshot or malformed journal.
            List<Drop> all = recovered();
            Snapshot old = readSnapshot();
            if (all.size() == old.records.size()) return false; // no-op
            if (failCommitBeforeMove) throw new IOException("INJECTED_COMMIT_FAILURE");
            byte[] data = snapshotBytes(all);
            Path staging = Files.createTempFile(home,"r397-stage-", ".tmp");
            try {
                try(FileChannel fc=FileChannel.open(staging,StandardOpenOption.WRITE,
                         StandardOpenOption.TRUNCATE_EXISTING)) {
                    ByteBuffer b = ByteBuffer.wrap(data);
                    while (b.hasRemaining()) fc.write(b);
                    fc.force(true);
                }
                Files.move(staging,main,
                        StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
                snapshotWrites++;
            } finally {
                // Deletes only this function's fresh synthetic staging file.
                Files.deleteIfExists(staging);
            }
            // Journal is intentionally retained. Replays filter IDs already
            // in the snapshot. Reclaiming space safely needs another design.
            return true;
        }
    }

    static Path scratch() throws Exception {
        return Files.createTempDirectory("r397-journal-synthetic-");
    }
    static void run(String name, Scenario scenario) throws Exception {
        Path root=scratch();
        try {
            scenario.execute(root);
            passed++;
        } finally {
            // Synthetic temp paths only; don't touch user or SpawnPK data.
            try (java.util.stream.Stream<Path> paths=Files.walk(root)) {
                paths.sorted(Collections.reverseOrder()).forEach(p -> {
                    try { Files.deleteIfExists(p); } catch(IOException e) { throw new RuntimeException(e); }
                });
            }
        }
    }
    interface Scenario { void execute(Path root) throws Exception; }
    static void same(List<Drop> drops,String... expected) {
        List<String> values = new ArrayList<String>();
        for(Drop x:drops) values.add(x.value);
        check(values.equals(Arrays.asList(expected)),"records="+values);
    }
    public static void main(String[] args) throws Exception {
        run("replay after abrupt stop", root -> {
            Journal a=new Journal(root);
            a.append("new-drop");
            same(new Journal(root).recovered(),"new-drop");
        });
        run("exactly once after commit before journal cleanup", root -> {
            Journal a=new Journal(root);
            a.append("drop-A");a.commit();
            same(new Journal(root).recovered(),"drop-A");
            check(!new Journal(root).commit(),"replayed old journal into duplicate snapshot");
        });
        run("two indistinguishable drops retain distinct IDs", root -> {
            Journal a=new Journal(root);
            long x=a.append("same");long y=a.append("same");
            check(x!=y,"IDs collided");
            a.commit();
            same(new Journal(root).recovered(),"same","same");
        });
        run("dirty tail after committed watermark", root -> {
            Journal a=new Journal(root);
            a.append("old");a.commit();
            a.append("new");
            same(new Journal(root).recovered(),"old","new");
            a.commit();
            same(new Journal(root).recovered(),"old","new");
        });
        run("unchanged state does not rewrite original", root -> {
            Journal a=new Journal(root);
            check(!a.commit(),"empty snapshot unnecessarily rewritten");
            a.append("x");check(a.commit(),"first commit missing");
            int count=a.snapshotWrites;
            check(!a.commit() && a.snapshotWrites==count,"clean commit rewrote snapshot");
        });
        run("save failure keeps journal and old snapshot", root -> {
            Journal a=new Journal(root);
            a.append("kept");a.commit();
            a.append("not-yet-merged");
            a.failCommitBeforeMove=true;
            try {a.commit();throw new AssertionError("expected failure");}
            catch(IOException expected){}
            same(new Journal(root).recovered(),"kept","not-yet-merged");
        });
        run("truncated journal tail is refused", root -> {
            Journal a=new Journal(root);a.append("okay");
            try(FileChannel fc=FileChannel.open(a.frames,StandardOpenOption.APPEND)) {
                fc.write(ByteBuffer.wrap(new byte[]{1,2,3}));
                fc.force(true);
            }
            try {a.recovered();throw new AssertionError("truncated tail accepted");}
            catch(IOException expected){}
        });
        run("bit flip is refused", root -> {
            Journal a=new Journal(root);a.append("okay");
            try(FileChannel fc=FileChannel.open(a.frames,StandardOpenOption.WRITE)) {
                fc.write(ByteBuffer.wrap(new byte[]{(byte)0xef}),16);
                fc.force(true);
            }
            try {a.recovered();throw new AssertionError("bad CRC accepted");}
            catch(IOException expected){}
        });
        run("corrupted snapshot cannot be silently overwritten", root -> {
            Journal a=new Journal(root);a.append("saved");a.commit();
            try(FileChannel fc=FileChannel.open(a.main,StandardOpenOption.WRITE)) {
                fc.write(ByteBuffer.wrap(new byte[]{(byte)0xff}),0);
                fc.force(true);
            }
            try { a.append("extra"); throw new AssertionError("corrupt snapshot accepted"); }
            catch(IOException expected) { /* primary history remains byte-for-byte untouched */ }
            check(Files.exists(a.frames) && Files.exists(a.main), "files unexpectedly removed");
        });
        run("oversized payload refused before writing", root -> {
            Journal a=new Journal(root);
            char[] chars = new char[MAX_PAYLOAD+1];Arrays.fill(chars,'a');
            try {a.append(new String(chars));throw new AssertionError("oversized accepted");}
            catch(IOException expected){}
            check(!Files.exists(a.frames),"oversized append created journal");
        });
        run("symlink refused", root -> {
            Journal a=new Journal(root);
            Path victim=root.resolve("elsewhere");
            Files.write(victim,new byte[]{1,2,3});
            try {
                Files.createSymbolicLink(a.frames,victim);
            } catch(UnsupportedOperationException | java.nio.file.FileSystemException denied) {
                return; // privilege/security environment disallows symlinks
            }
            try {a.append("x");throw new AssertionError("symlink followed");}
            catch(IOException expected){}
            check(Files.size(victim)==3,"symlink target changed");
        });
        System.out.println("R397_JOURNAL_SYNTHETIC_PASS "+passed+" scenarios");
    }
}

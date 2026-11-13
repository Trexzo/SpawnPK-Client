import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.file.*;
import java.util.Comparator;
import java.util.Set;

/** Public scratch-only provider probe: no private client source, cache or network. */
public final class WindowsContractPortabilityProbe {
    private static int checks;
    private static void yes(boolean condition, String label) {
        checks++;
        if (!condition) throw new AssertionError(label);
    }
    public static void main(String[] args) throws Exception {
        Path scratch=Files.createTempDirectory("r382-provider-probe-");
        try {
            Path real=Files.createFile(scratch.resolve("real-stage.tmp"));
            Files.writeString(real,"test-only");
            Path name=Path.of("rs","gui","loadouts","LoadoutStore.java");
            yes(name.getNameCount()==4,"PATH_SEGMENTS");
            yes(name.iterator().next().toString().equals("rs"),"PATH_FIRST_SEGMENT");
            yes(name.toString().contains("LoadoutStore.java"),"PATH_LAST_SEGMENT");
            yes(Files.isRegularFile(real,LinkOption.NOFOLLOW_LINKS),"REAL_FILE");
            Path lock=Files.createFile(scratch.resolve("scratch.lock"));
            try(FileChannel channel=FileChannel.open(lock,StandardOpenOption.WRITE);
                FileLock held=channel.tryLock()) {
                yes(held!=null && held.isValid(),"LOCK_ACQUIRED");
                yes(Files.exists(lock,LinkOption.NOFOLLOW_LINKS),"LOCK_PATH_EXISTS");
            }
            yes(Files.readString(real).equals("test-only"),"STAGED_BYTES_UNCHANGED");
            Path link=scratch.resolve("stage-link.tmp");
            boolean symlinkSupported=false;
            try {
                Files.createSymbolicLink(link,real);
                symlinkSupported=true;
                yes(Files.isSymbolicLink(link),"SYMLINK_NOFOLLOW");
            } catch (UnsupportedOperationException | SecurityException | FileSystemException e) {
                if (!(System.getProperty("os.name").toLowerCase().contains("windows") ||
                      e instanceof UnsupportedOperationException)) throw e;
                System.out.println("R382_SYMLINK_PRIVILEGE_OR_PROVIDER_SKIP");
            }
            if(symlinkSupported) yes(Files.exists(link,LinkOption.NOFOLLOW_LINKS),"LINK_PRESERVED");
            yes(Files.readString(real).equals("test-only"),"SCRATCH_CONTENT_UNCHANGED");
            System.out.println("R382_PUBLIC_PROVIDER_PROBE_PASS checks="+checks+" symlink="+(symlinkSupported?"tested":"skipped"));
        } finally {
            try(var walk=Files.walk(scratch)) {
                for(Path p:walk.sorted(Comparator.reverseOrder()).toList()) Files.deleteIfExists(p);
            }
        }
    }
}

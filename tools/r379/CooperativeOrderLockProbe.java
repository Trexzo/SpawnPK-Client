import java.io.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Generic scratch-only JDK probe. A lock result is NOT process ownership evidence. */
public final class CooperativeOrderLockProbe {
  private static int checks;
  private static void ok(boolean good, String message) {
    checks++;
    if (!good) throw new AssertionError(message);
  }
  private static String probe(Path path) {
    try {
      BasicFileAttributes attrs = Files.readAttributes(path,
          BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
      if (!attrs.isRegularFile()) return "UNSAFE_NO_PROBE";
    } catch (NoSuchFileException absent) {
      return "ABSENT_NO_PROBE";
    } catch (IOException | SecurityException denied) {
      return "METADATA_UNAVAILABLE";
    }
    try (FileChannel channel = FileChannel.open(path,
        StandardOpenOption.READ, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)) {
      try (FileLock acquired = channel.tryLock()) {
        return acquired == null ? "BUSY_AT_OBSERVATION" : "FREE_AT_OBSERVATION";
      } catch (OverlappingFileLockException overlap) {
        return "BUSY_AT_OBSERVATION";
      }
    } catch (IOException | UnsupportedOperationException | SecurityException denied) {
      return "PROBE_UNAVAILABLE";
    }
  }
  public static void main(String[] args) throws Exception {
    if (args.length == 2 && args[0].equals("hold")) {
      try (FileChannel channel = FileChannel.open(Path.of(args[1]),
               StandardOpenOption.READ, StandardOpenOption.WRITE);
           FileLock held = channel.lock()) {
        System.out.println("LOCK_HELD"); System.out.flush();
        while (System.in.read() != -1) { }
      }
      return;
    }
    Path dir = Files.createTempDirectory("r379-generic-lock-probe-");
    Path lock = dir.resolve(".loadout_order_lock.lck");
    Process other = null;
    try {
      ok(probe(lock).equals("ABSENT_NO_PROBE"), "ABSENT_LOCK");
      ok(!Files.exists(lock), "NO_IMPLICIT_CREATION");
      Files.writeString(lock, "unchanged");
      String first = probe(lock);
      if (first.equals("PROBE_UNAVAILABLE")) {
        System.out.println("R379_PROVIDER_PROBE_UNAVAILABLE_NO_OWNERSHIP_CLAIM");
      } else {
        ok(first.equals("FREE_AT_OBSERVATION"), "FREE_IDLE_LOCK");
        try (FileChannel channel = FileChannel.open(lock,
                 StandardOpenOption.READ, StandardOpenOption.WRITE);
             FileLock held = channel.lock()) {
          ok(probe(lock).equals("BUSY_AT_OBSERVATION"), "SAME_JVM_BUSY");
          ok(held.isValid(), "DO_NOT_STEAL_LOCK");
        }
        ok(probe(lock).equals("FREE_AT_OBSERVATION"), "SAME_JVM_RELEASE");
        String java = Path.of(System.getProperty("java.home"), "bin", "java").toString();
        other = new ProcessBuilder(java, "-cp", System.getProperty("java.class.path"),
            "CooperativeOrderLockProbe", "hold", lock.toString())
            .redirectErrorStream(true).start();
        String greeting = new BufferedReader(new InputStreamReader(other.getInputStream())).readLine();
        ok("LOCK_HELD".equals(greeting), "SECOND_JVM_READY");
        ok(probe(lock).equals("BUSY_AT_OBSERVATION"), "SECOND_JVM_BUSY");
        other.getOutputStream().close();
        if (!other.waitFor(10, TimeUnit.SECONDS)) throw new AssertionError("HOLDER_TIMEOUT");
        other = null;
        ok(probe(lock).equals("FREE_AT_OBSERVATION"), "SECOND_JVM_RELEASE");
      }
      ok(Files.readString(lock).equals("unchanged"), "NO_PAYLOAD_WRITE");
      Files.delete(lock);
      Files.createDirectory(lock);
      ok(probe(lock).equals("UNSAFE_NO_PROBE"), "DIRECTORY_UNSAFE");
      Files.delete(lock);
      try {
        Files.createSymbolicLink(lock, dir);
        ok(probe(lock).equals("UNSAFE_NO_PROBE"), "SYMLINK_UNSAFE");
      } catch (UnsupportedOperationException | SecurityException | FileSystemException unsupported) {
        System.out.println("R379_SYMLINK_TEST_NOT_SUPPORTED");
      }
      System.out.println("R379_GENERIC_LOCK_PROBE_PASS checks=" + checks
          + " (no deletion, no ownership claim)");
    } finally {
      if (other != null) other.destroyForcibly();
      try (var all = Files.walk(dir)) {
        for (Path p : all.sorted(Comparator.reverseOrder()).toArray(Path[]::new))
          Files.deleteIfExists(p);
      }
    }
  }
}

import java.nio.file.*;
import java.nio.channels.*;
import java.nio.file.attribute.*;
import java.util.*;
/** Generic scratch-only Java 11+ provider probe. No game or owner files. */
public final class PassiveLockMetadataProbe {
  private static String passive(Path file) {
    try {
      BasicFileAttributes a=Files.readAttributes(file,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
      return a.isRegularFile()?"PRESENT_HELD_UNKNOWN":"UNSAFE_HELD_UNKNOWN";
    } catch(NoSuchFileException absent) {return "ABSENT_HELD_UNKNOWN";}
    catch(Exception unavailable) {return "UNAVAILABLE_HELD_UNKNOWN";}
  }
  public static void main(String[] args) throws Exception {
    Path dir=Files.createTempDirectory("r378-public-probe-");
    Path file=dir.resolve(".loadout_order_lock.lck");
    try {
      if(!passive(file).equals("ABSENT_HELD_UNKNOWN"))throw new AssertionError("ABSENT");
      if(Files.exists(file))throw new AssertionError("PASSIVE_CREATED_FILE");
      Files.writeString(file,"");
      String idle=passive(file);
      if(!idle.equals("PRESENT_HELD_UNKNOWN"))throw new AssertionError("PRESENT");
      try(FileChannel c=FileChannel.open(file,StandardOpenOption.READ,StandardOpenOption.WRITE);
          FileLock held=c.lock()) {
        if(!passive(file).equals(idle)||!held.isValid())throw new AssertionError("HELD_MISCLASSIFIED");
      }
      if(!passive(file).equals(idle))throw new AssertionError("RELEASE_MISCLASSIFIED");
      System.out.println("R378_PASSIVE_PROBE_PASS lock_path_presence_is_not_ownership_proof");
    } finally {Files.deleteIfExists(file); Files.deleteIfExists(dir);}
  }
}

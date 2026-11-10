import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;
/** Pure JDK filesystem probe. No game code, no user files. */
public final class StagingAgeMetadataProbe {
  private static int count=0;
  private static void ok(boolean value,String reason) {
    count++;if(!value)throw new AssertionError(reason);
  }
  private static String age(Path p,long now) throws Exception {
    BasicFileAttributes a=Files.readAttributes(p,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
    if(!a.isRegularFile())return "UNSAFE";
    long modified=a.lastModifiedTime().toMillis();
    if(modified<0 || modified>now)return "CLOCK_UNKNOWN";
    long elapsed=now-modified;
    return elapsed<86400000L?"UNDER_24H":elapsed<604800000L?"OVER_24H":"OVER_7D";
  }
  public static void main(String[] args)throws Exception {
    Path root=Files.createTempDirectory("r377-metadata-probe-");
    long now=1_800_000_000_000L;
    try {
      Path young=root.resolve("young.tmp"),old=root.resolve("old.tmp"),future=root.resolve("future.tmp");
      Files.writeString(young,"keep");Files.writeString(old,"keep");Files.writeString(future,"keep");
      Files.setLastModifiedTime(young,FileTime.fromMillis(now-60000));
      Files.setLastModifiedTime(old,FileTime.fromMillis(now-8*86400000L));
      Files.setLastModifiedTime(future,FileTime.fromMillis(now+60000));
      ok(age(young,now).equals("UNDER_24H"),"young");
      ok(age(old,now).equals("OVER_7D"),"old");
      ok(age(future,now).equals("CLOCK_UNKNOWN"),"future");
      ok(Files.readString(old).equals("keep"),"no modification");
      Path symlink=root.resolve("link.tmp");
      try {
        Files.createSymbolicLink(symlink,young.getFileName());
        ok(age(symlink,now).equals("UNSAFE"),"nofollow symlink");
      }catch(UnsupportedOperationException|SecurityException|java.io.IOException unsupported) {
        System.out.println("R377_SYMLINK_PROBE_UNSUPPORTED");
      }
      ok(Files.exists(old),"old stage retained");
      System.out.println("R377_PUBLIC_METADATA_PROBE_PASS checks="+count+
         " os="+System.getProperty("os.name"));
    } finally {
      try(var walk=Files.walk(root)) {
        for(Path entry:walk.sorted(Comparator.reverseOrder()).toArray(Path[]::new))Files.deleteIfExists(entry);
      }
    }
  }
}

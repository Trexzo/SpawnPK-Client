import java.io.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
/** Scratch-only, generic JDK probe. Reports lock contention, NEVER identifies an owner. */
public final class CooperativeFolderLockProbe {
  private static int checks=0;
  private static void ok(boolean b,String s) {checks++;if(!b)throw new AssertionError(s);}
  private static String probe(Path p) {
    try {
      BasicFileAttributes a=Files.readAttributes(p,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
      if(!a.isRegularFile())return "UNSAFE_NO_PROBE";
    }catch(NoSuchFileException no){return "ABSENT_NO_PROBE";}
    catch(IOException|SecurityException denied){return "METADATA_UNAVAILABLE";}
    try(FileChannel ch=FileChannel.open(p,StandardOpenOption.READ,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)) {
      try(FileLock lock=ch.tryLock()) {return lock==null?"BUSY_AT_OBSERVATION":"FREE_AT_OBSERVATION";}
      catch(OverlappingFileLockException overlap){return "BUSY_AT_OBSERVATION";}
    }catch(IOException|UnsupportedOperationException|SecurityException denied){return "PROBE_UNAVAILABLE";}
  }
  // Generic filename contract only. Does not use any recovered Java code.
  private static Path correlatedLockPath(Path directory,String stageName) {
    String prefix=".loadout-stage-",suffix=".pending";
    if(!stageName.startsWith(prefix)||!stageName.endsWith(suffix))return null;
    String body=stageName.substring(prefix.length(),stageName.length()-suffix.length());
    if(body.length()<=33||body.charAt(32)!='-'||
       !body.substring(0,32).matches("[0-9a-f]{32}")||
       !body.substring(33).matches("[A-Za-z0-9]+"))return null;
    return directory.resolve(".loadout_lock-"+body.substring(0,32)+".lck");
  }
  public static void main(String[] args)throws Exception {
    if(args.length==2 && args[0].equals("hold")) {
      Path p=Path.of(args[1]);
      try(FileChannel c=FileChannel.open(p,StandardOpenOption.READ,StandardOpenOption.WRITE);
          FileLock lock=c.lock()) {
        System.out.println("LOCK_HELD");System.out.flush();
        while(System.in.read()!=-1){}
      }
      return;
    }
    Path folder=Files.createTempDirectory("r380-generic-folder-lock-");
    Path lock=folder.resolve(".loadout_lock-0123456789abcdef0123456789abcdef.lck");
    Process other=null;
    try {
      String stage=".loadout-stage-0123456789abcdef0123456789abcdef-123456.pending";
      ok(lock.equals(correlatedLockPath(folder,stage)),"CORRELATED_STAGE_LOCK");
      ok(correlatedLockPath(folder,".loadout-stage-legacy.pending")==null,"LEGACY_UNKNOWN");
      ok(correlatedLockPath(folder,".loadout-stage-0123456789abcdef0123456789abcdef-bad_name.pending")==null,"MALFORMED_UNKNOWN");
      ok(correlatedLockPath(folder,".loadout_order_stage-random.pending")==null,"ORDER_NOT_FOLDER");
      ok(probe(lock).equals("ABSENT_NO_PROBE"),"ABSENT");
      ok(!Files.exists(lock),"NO_CREATE");
      Files.writeString(lock,"unchanged");
      String free=probe(lock);
      // Some Windows providers prohibit this advisory exclusive open; report it
      // rather than falsely claiming ownership or failed cross-platform runtime.
      if(!free.equals("FREE_AT_OBSERVATION")) {
        if(!free.equals("PROBE_UNAVAILABLE"))throw new AssertionError("UNEXPECTED_PROVIDER="+free);
        System.out.println("R380_PROVIDER_PROBE_UNAVAILABLE_NO_OWNERSHIP_CLAIM");
      } else {
        ok(free.equals("FREE_AT_OBSERVATION"),"FREE_LOCK");
        try(FileChannel c=FileChannel.open(lock,StandardOpenOption.READ,StandardOpenOption.WRITE);
            FileLock held=c.lock()) {
          ok(probe(lock).equals("BUSY_AT_OBSERVATION"),"SAME_PROCESS_LOCK");
          ok(held.isValid(),"DO_NOT_STEAL");
        }
        ok(probe(lock).equals("FREE_AT_OBSERVATION"),"RELEASED");
        String java=Path.of(System.getProperty("java.home"),"bin","java").toString();
        other=new ProcessBuilder(java,"-cp",System.getProperty("java.class.path"),
            "CooperativeFolderLockProbe","hold",lock.toString()).redirectErrorStream(true).start();
        String msg=new BufferedReader(new InputStreamReader(other.getInputStream())).readLine();
        ok("LOCK_HELD".equals(msg),"SECOND_PROCESS_READY");
        ok(probe(lock).equals("BUSY_AT_OBSERVATION"),"SECOND_PROCESS_CONTENTION");
        other.getOutputStream().close();
        if(!other.waitFor(10,TimeUnit.SECONDS))throw new AssertionError("SECOND_PROCESS_EXIT_TIMEOUT");
        other=null;
        ok(probe(lock).equals("FREE_AT_OBSERVATION"),"SECOND_PROCESS_RELEASE");
      }
      ok(Files.readString(lock).equals("unchanged"),"NO_WRITE");
      Files.delete(lock);Files.createDirectory(lock);
      ok(probe(lock).equals("UNSAFE_NO_PROBE"),"DIRECTORY_REFUSED");
      Files.delete(lock);
      try {
        Files.createSymbolicLink(lock,folder);
        ok(probe(lock).equals("UNSAFE_NO_PROBE"),"SYMLINK_REFUSED");
      } catch(UnsupportedOperationException|SecurityException|FileSystemException unavailable) {
        System.out.println("R380_SYMLINK_TEST_NOT_SUPPORTED");
      }
      System.out.println("R380_GENERIC_LOCK_PROBE_PASS checks="+checks+" (no stage deletion, no process identification)");
    } finally {
      if(other!=null)other.destroyForcibly();
      try(var all=Files.walk(folder)){for(Path p:all.sorted(Comparator.reverseOrder()).toArray(Path[]::new))Files.deleteIfExists(p);}
    }
  }
}

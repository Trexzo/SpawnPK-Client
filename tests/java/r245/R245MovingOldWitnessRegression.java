package rs.cache.updater.assets;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.attribute.BasicFileAttributes;
import java.lang.reflect.Method;
import java.security.MessageDigest;
import java.io.IOException;
import java.util.*;

/** R245: a witnessed MOVING_OLD journal with previous/ missing must prove its still-live root. */
public final class R245MovingOldWitnessRegression {
  private static int checks;
  private static void ok(boolean x, String msg) { if(!x) throw new AssertionError(msg); checks++; }
  private static String digest(String s)throws Exception {
    byte[] bytes=MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8));
    StringBuilder b=new StringBuilder();for(int i=0;i<12;i++)b.append(String.format("%02x",bytes[i]&255));return b.toString();
  }
  private static String fingerprint(Path path)throws Exception {
    Method m=CacheUpdateTransaction.class.getDeclaredMethod("snapshotFingerprint",Path.class);
    m.setAccessible(true);return (String)m.invoke(null,path);
  }
  private static void rm(Path p)throws IOException {
    if(!Files.exists(p,LinkOption.NOFOLLOW_LINKS))return;
    Files.walkFileTree(p,new SimpleFileVisitor<Path>() {
      @Override public FileVisitResult visitFile(Path f,BasicFileAttributes a)throws IOException {Files.delete(f);return FileVisitResult.CONTINUE;}
      @Override public FileVisitResult postVisitDirectory(Path d,IOException e)throws IOException {if(e!=null)throw e; Files.delete(d);return FileVisitResult.CONTINUE;}
    });
  }
  private static void scenario(String version,String alteration,boolean refuse)throws Exception {
    Path parent=Files.createTempDirectory("r245-moving-old-");
    try {
      Path root=Files.createDirectory(parent.resolve("cache"));
      Path oldFile=root.resolve("original.dat");Files.writeString(oldFile,"OLD_BYTES_AA");
      String oldFingerprint=fingerprint(root);
      Path work=Files.createDirectory(parent.resolve(".spk-cache-update-"+digest(root.toString())+"-r245"));
      Path stage=Files.createDirectory(work.resolve("staged"));Files.writeString(stage.resolve("new.dat"),"NEW_BYTES");
      String stagedFingerprint=fingerprint(stage);
      Files.writeString(work.resolve(".transaction"),"SPK-CACHE-TRANSACTION-"+version+"\n"+root+"\nMOVING_OLD\n");
      if(!version.equals("V1")) {
        Files.writeString(work.resolve(".install-witness"),"SPK-CACHE-INSTALL-WITNESS-V1\n"+
          (alteration.equals("false-origin")?"NO_ORIGINAL":"HAD_ORIGINAL")+"\n"+stagedFingerprint+"\n");
      }
      if(version.equals("V3") && !alteration.equals("missing-witness")) {
        String proof=alteration.equals("bad-witness")?"0".repeat(64):oldFingerprint;
        Files.writeString(work.resolve(".rollback-witness"),"SPK-CACHE-ROLLBACK-WITNESS-V1\n"+proof+"\n");
      }
      if(alteration.equals("changed")) {
        Files.writeString(oldFile,"NEW_BYTES_AA");
        ok(Files.size(oldFile)==12,"Preserved size for mutation test");
      }
      if(alteration.equals("new-file")) Files.writeString(root.resolve("foreign.dat"),"FOREIGN");
      if(alteration.equals("missing-root")) rm(root);
      boolean refused=false;
      try { CacheUpdateTransaction.recover(root.toFile()); }
      catch(IOException x){ refused=true; ok(x.getMessage()!=null,"Missing error message"); }
      ok(refused==refuse,"Unexpected recovery response: "+version+" "+alteration+" refused="+refused);
      if(refuse) {
        ok(Files.exists(work.resolve(".transaction")),"Journal lost: "+alteration);
        ok(Files.exists(stage.resolve("new.dat")),"Unique staged update lost: "+alteration);
        ok(Files.exists(root,LinkOption.NOFOLLOW_LINKS)==!alteration.equals("missing-root"),"Original altered by recovery");
      } else {
        ok(!Files.exists(work),"Safe legacy/verified recovery failed to clean");
        ok(Files.exists(root.resolve("original.dat")),"Safe recovery lost original");
      }
    }finally{rm(parent);}
  }
  public static void main(String[] args)throws Exception {
    scenario("V3","changed",true);
    scenario("V3","new-file",true);
    scenario("V3","missing-witness",true);
    scenario("V3","bad-witness",true);
    scenario("V3","false-origin",true);
    scenario("V3","missing-root",true);
    scenario("V3","normal",false);
    scenario("V2","normal",false);
    scenario("V1","normal",false);
    System.out.println("R245_MOVING_OLD_ORIGINAL_WITNESS_PASS checks="+checks);
  }
}

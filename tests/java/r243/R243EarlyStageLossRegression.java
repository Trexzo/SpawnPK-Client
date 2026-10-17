package rs.cache.updater.assets;

import java.io.IOException;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.lang.reflect.Method;

/** Crash replay must never erase the last staged copy of an original cache. */
public final class R243EarlyStageLossRegression {
  private static int checks;
  private static void yes(boolean c, String m) { if (!c) throw new AssertionError(m); checks++; }
  private static void rm(Path p) throws IOException {
    if (!Files.exists(p, LinkOption.NOFOLLOW_LINKS)) return;
    Files.walkFileTree(p,new SimpleFileVisitor<Path>() {
      @Override public FileVisitResult visitFile(Path f,BasicFileAttributes a)throws IOException {
        Files.delete(f); return FileVisitResult.CONTINUE;
      }
      @Override public FileVisitResult postVisitDirectory(Path d,IOException e)throws IOException {
        if(e!=null)throw e; Files.delete(d); return FileVisitResult.CONTINUE;
      }
    });
  }
  private static Path newWork(Path root)throws Exception {
    byte[] b=MessageDigest.getInstance("SHA-256").digest(root.toString().getBytes(StandardCharsets.UTF_8));
    StringBuilder d=new StringBuilder(".spk-cache-update-");
    for(int i=0;i<12;i++)d.append(String.format("%02x",b[i]&255));
    return Files.createDirectory(root.getParent().resolve(d+"-r243"));
  }
  private static String hash(Path stage)throws Exception {
    Method m=CacheUpdateTransaction.class.getDeclaredMethod("snapshotFingerprint",Path.class);
    m.setAccessible(true);return (String)m.invoke(null,stage);
  }
  private static void journal(Path w,Path root,String version,String phase,String origin,String digest)throws IOException {
    Files.writeString(w.resolve(".transaction"),version+"\n"+root+"\n"+phase+"\n");
    if(origin!=null)Files.writeString(w.resolve(".install-witness"),
      "SPK-CACHE-INSTALL-WITNESS-V1\n"+origin+"\n"+digest+"\n");
  }
  private static void mustPreserve(String version,String phase)throws Exception {
    Path parent=Files.createTempDirectory("r243-original-lost-");
    try {
      Path root=parent.resolve("cache"),w=newWork(root),stage=Files.createDirectory(w.resolve("staged"));
      Files.writeString(stage.resolve("sole-copy.dat"),"ORIGINAL_CACHE_BYTES");
      journal(w,root,version,phase,phase.equals("PREPARING")?null:"HAD_ORIGINAL",hash(stage));
      try {
        CacheUpdateTransaction.recover(root.toFile());
        throw new AssertionError("Recovery removed last staged original: "+version+" "+phase);
      } catch(IOException expected) {
        yes(expected.getMessage().contains("cache")||expected.getMessage().contains("original")||
          expected.getMessage().contains("PREPARING"),"Unexpected recovery error "+expected);
      }
      yes(Files.readString(stage.resolve("sole-copy.dat")).equals("ORIGINAL_CACHE_BYTES"),"Staged copy changed");
      yes(Files.exists(w.resolve(".transaction")),"Journal erased");
      yes(!Files.exists(root),"Unexpected replacement root");
    } finally { rm(parent); }
  }
  private static void emptyPreparing()throws Exception {
    Path p=Files.createTempDirectory("r243-empty-");
    try {
      Path root=p.resolve("cache"),w=newWork(root);
      Files.createDirectory(w.resolve("staged"));
      journal(w,root,"SPK-CACHE-TRANSACTION-V3","PREPARING",null,null);
      CacheUpdateTransaction.recover(root.toFile());
      yes(!Files.exists(w),"Empty first-install PREPARING retained");
    } finally { rm(p); }
  }
  private static void genuineFirstInstall()throws Exception {
    Path p=Files.createTempDirectory("r243-first-");
    try {
      Path root=p.resolve("cache"),w=newWork(root),stage=Files.createDirectory(w.resolve("staged"));
      Files.writeString(stage.resolve("new.dat"),"NEW");
      journal(w,root,"SPK-CACHE-TRANSACTION-V3","STAGED","NO_ORIGINAL",hash(stage));
      CacheUpdateTransaction.recover(root.toFile());
      yes(!Files.exists(w),"NO_ORIGINAL staged journal not cleaned");
    } finally { rm(p); }
  }
  private static void existingOriginal()throws Exception {
    Path p=Files.createTempDirectory("r243-existing-");
    try {
      Path root=Files.createDirectory(p.resolve("cache"));
      Files.writeString(root.resolve("old.dat"),"OLD");
      Path w=newWork(root),stage=Files.createDirectory(w.resolve("staged"));
      Files.writeString(stage.resolve("new.dat"),"NEW");
      journal(w,root,"SPK-CACHE-TRANSACTION-V3","STAGED","HAD_ORIGINAL",hash(stage));
      CacheUpdateTransaction.recover(root.toFile());
      yes(Files.readString(root.resolve("old.dat")).equals("OLD"),"Live original mutated");
      yes(!Files.exists(w),"Verified rollback left staged workspace");
    } finally { rm(p); }
  }
  public static void main(String[] args)throws Exception {
    mustPreserve("SPK-CACHE-TRANSACTION-V3","PREPARING");
    mustPreserve("SPK-CACHE-TRANSACTION-V1","PREPARING");
    mustPreserve("SPK-CACHE-TRANSACTION-V3","STAGED");
    mustPreserve("SPK-CACHE-TRANSACTION-V2","STAGED");
    emptyPreparing();genuineFirstInstall();existingOriginal();
    System.out.println("R243_EARLY_STAGE_ORIGINAL_LOSS_PASS checks="+checks);
  }
}

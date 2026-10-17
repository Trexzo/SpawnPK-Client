package rs.cache.updater.assets;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.*;

/** Conservative recovery when PREPARING has no durable install witness yet. */
public final class R244PreparingStageOwnershipRegression {
  private static int checks;
  private static void check(boolean v, String why) { if (!v) throw new AssertionError(why); checks++; }
  private static String digest(String value) throws Exception {
    byte[] h=MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
    StringBuilder b=new StringBuilder(); for(int i=0;i<12;i++)b.append(String.format("%02x",h[i]&255)); return b.toString();
  }
  private static void wipe(Path p)throws IOException {
    if(!Files.exists(p, LinkOption.NOFOLLOW_LINKS)) return;
    Files.walkFileTree(p, new SimpleFileVisitor<Path>() {
      public FileVisitResult visitFile(Path f, BasicFileAttributes a)throws IOException {Files.delete(f);return FileVisitResult.CONTINUE;}
      public FileVisitResult postVisitDirectory(Path d, IOException e)throws IOException {if(e!=null)throw e;Files.delete(d);return FileVisitResult.CONTINUE;}
    });
  }
  private static void probe(String scenario, boolean expectRefusal) throws Exception {
    Path parent=Files.createTempDirectory("r244-preparing-"),root=Files.createDirectory(parent.resolve("assets"));
    try {
      Files.createDirectories(root.resolve("nested"));
      Files.writeString(root.resolve("original.dat"),"BASE-ORIGINAL",StandardCharsets.UTF_8);
      Files.writeString(root.resolve("nested/keep.dat"),"BASE-NESTED",StandardCharsets.UTF_8);
      Path work=Files.createDirectory(parent.resolve(".spk-cache-update-"+digest(root.toString())+"-r244"));
      Path stage=Files.createDirectory(work.resolve("staged"));
      Path stageFile=stage.resolve("original.dat");
      if (!scenario.equals("empty")) Files.writeString(stageFile,"BASE-ORIGINAL");
      if(scenario.equals("rewritten")) {
        Files.writeString(stageFile,"FAKE-ORIGINAL");
        check(Files.size(stageFile)==Files.size(root.resolve("original.dat")),"Fixture length changed");
        Files.setLastModifiedTime(stageFile,Files.getLastModifiedTime(root.resolve("original.dat")));
      }
      if(scenario.equals("new-file")) Files.writeString(stage.resolve("unowned.dat"),"NONOWNER");
      if(scenario.equals("new-directory")) Files.createDirectory(stage.resolve("new-tree"));
      if(scenario.equals("changed-root")) Files.writeString(root.resolve("original.dat"),"NEW-ORIGINAL!");
      if(scenario.equals("nested-subset")) {
        Files.createDirectory(stage.resolve("nested"));
        Files.writeString(stage.resolve("nested/keep.dat"),"BASE-NESTED");
      }
      Files.writeString(work.resolve(".transaction"),"SPK-CACHE-TRANSACTION-V3\n"+root+"\nPREPARING\n");
      boolean refused=false;
      try {CacheUpdateTransaction.recover(root.toFile());}
      catch(IOException e){ refused=true;check(e.getMessage().contains("PREPARING")||e.getMessage().contains("stage"),"Wrong refusal: "+e);}
      check(refused==expectRefusal,scenario+" should "+(expectRefusal?"preserve":"clean")+" PREPARING stage");
      check(Files.readString(root.resolve("nested/keep.dat")).equals("BASE-NESTED"),"Original unaffected");
      if(expectRefusal) {
        check(Files.exists(work.resolve("staged")),"Staged evidence lost");
        check(Files.exists(work.resolve(".transaction")),"Journal evidence lost");
      } else check(!Files.exists(work),"Safe stage not cleaned");
    }finally{wipe(parent);}
  }
  public static void main(String[] args)throws Exception {
    probe("rewritten",true);
    probe("new-file",true);
    probe("new-directory",true);
    probe("changed-root",true);
    probe("copy-subset",false);
    probe("nested-subset",false);
    probe("empty",false);
    System.out.println("R244_PREPARING_STAGE_OWNERSHIP_PASS checks="+checks);
  }
}

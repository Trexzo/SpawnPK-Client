package rs.cache.updater.assets;
import java.io.*;
import java.nio.file.*;
public final class R225CacheTest {
 public static void main(String[] args) throws Exception {
  Path p=Files.createTempDirectory("r225-ci-"), root=Files.createDirectory(p.resolve("live"));
  Path file=root.resolve("data");
  Files.writeString(file,"ORIGINAL");
  try {
   CacheUpdateTransaction.install(root.toFile(),archive->{
    Files.writeString(archive.toPath(),"test");
    Files.writeString(file,"MODIFIED");
    return archive;
   },(dir,archive)->true);
   throw new AssertionError("Expected update refusal");
  } catch(IOException expected) {
   if(!expected.getMessage().contains("Active cache changed"))throw expected;
  }
  if(!Files.readString(file).equals("MODIFIED"))throw new AssertionError("Unexpected content");
  System.out.println("R225_PUBLIC_CACHE_TEST_PASS");
 }
}

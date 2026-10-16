import java.io.File;
import java.io.IOException;
import java.nio.file.*;
import java.util.zip.ZipEntry;
import rs.cache.updater.SafeZipPath;

/** JDK-only regression for the new helper, not the private game. */
public class SafeZipPathSelfTest {
   private static void reject(File root, String entry) throws Exception {
      try {
         SafeZipPath.resolveUnderRoot(root, new ZipEntry(entry));
         throw new AssertionError("Allowed unsafe entry " + entry);
      } catch (IOException expected) {
         // Rejection is intended.
      }
   }
   public static void main(String[] args) throws Exception {
      Path temp = Files.createTempDirectory("r217-public-");
      Path root = Files.createDirectory(temp.resolve("asset-root"));
      for (String name : new String[] {
         "../outside.txt", "nested/../../escape", "nested\\..\\..\\escape",
         "/absolute", "C:/Windows/win.ini", "\\\\server\\share\\file", "file:ads",
         ".", "./", "nested/..", "nested\\.."
      }) {
         reject(root.toFile(), name);
      }
      File safe = SafeZipPath.resolveUnderRoot(root.toFile(), new ZipEntry("nested/subdir/asset.dat"));
      if (!safe.getCanonicalFile().equals(root.resolve("nested/subdir/asset.dat").toFile().getCanonicalFile())) {
         throw new AssertionError("Normal entry did not resolve correctly");
      }
      File windows = SafeZipPath.resolveUnderRoot(root.toFile(), new ZipEntry("nested\\subdir\\asset.dat"));
      if (!windows.equals(safe)) {
         throw new AssertionError("Windows-style path not normalized");
      }
      Path outside = Files.createDirectory(temp.resolve("outside"));
      try {
         Files.createSymbolicLink(root.resolve("link"), outside);
         reject(root.toFile(), "link/escape.txt");
      } catch (UnsupportedOperationException | FileSystemException | SecurityException e) {
         System.out.println("Symlink test unsupported: " + e.getClass().getSimpleName());
      }
      System.out.println("PASS: R217 JDK-only ZIP target path regression");
   }
}

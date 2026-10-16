package rs.cache.updater;

import java.io.File;
import java.io.IOException;
import java.util.zip.ZipEntry;

/** Ensures a ZIP entry cannot escape the chosen asset extraction directory. */
public final class SafeZipPath {
   private SafeZipPath() { }

   public static File resolveUnderRoot(File root, ZipEntry entry) throws IOException {
      if (root == null || entry == null) {
         throw new IOException("Missing ZIP extraction root or entry");
      }
      String name = entry.getName();
      if (name == null || name.isEmpty() || name.indexOf('\0') >= 0) {
         throw new IOException("Invalid ZIP entry name");
      }
      // ZIPs use '/', but reject Windows-style traversal on all operating systems.
      name = name.replace('\\', '/');
      if (name.startsWith("/") || name.indexOf(':') >= 0) {
         throw new IOException("Absolute or device ZIP entry path rejected: " + name);
      }
      for (String segment : name.split("/", -1)) {
         if (segment.equals("..")) {
            throw new IOException("Parent traversal ZIP entry rejected: " + name);
         }
      }
      File base = root.getCanonicalFile();
      File resolved = new File(base, name.replace('/', File.separatorChar)).getCanonicalFile();
      if (resolved.equals(base) || !resolved.toPath().startsWith(base.toPath())) {
         throw new IOException("ZIP entry outside extraction directory: " + name);
      }
      return resolved;
   }
}

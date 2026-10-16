package rs.cache.download;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

/**
 * Standalone client asset transfer mechanism. Does not depend on any game class.
 * The file returned by this method has passed HTTP status/length checks and was
 * staged in the destination directory before replacing an existing file.
 */
public final class SafeDownloadTransfer {
   public static final int CONNECT_TIMEOUT_MS = 15000;
   public static final int READ_TIMEOUT_MS = 30000;
   private static final int BUFFER_SIZE = 16384;

   private SafeDownloadTransfer() { }

   public interface ProgressListener {
      void onStart(long expectedBytes);
      void onBytes(long totalBytes);
   }

   public static File transfer(URL url, File targetFile, ProgressListener progress)
      throws IOException {
      if (url == null || targetFile == null) throw new IOException("Missing download URL or target");
      URLConnection connection = null;
      Path temporary = null;
      try {
         File parent = targetFile.getAbsoluteFile().getParentFile();
         if (parent == null) throw new IOException("No download destination parent");
         if (!parent.isDirectory() && !parent.mkdirs()) {
            throw new IOException("Cannot create download destination: " + parent);
         }
         connection = url.openConnection();
         connection.setUseCaches(false);
         connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
         connection.setReadTimeout(READ_TIMEOUT_MS);
         if (connection instanceof HttpURLConnection) {
            int status = ((HttpURLConnection)connection).getResponseCode();
            if (status < 200 || status >= 300) {
               throw new IOException("HTTP " + status + " fetching " + url);
            }
         }
         long expected = connection.getContentLengthLong();
         if (progress != null) progress.onStart(expected);
         temporary = Files.createTempFile(parent.toPath(), "spk-download-", ".part");
         long count = 0L;
         try (InputStream input = new BufferedInputStream(connection.getInputStream(), BUFFER_SIZE);
              OutputStream output = Files.newOutputStream(temporary)) {
            byte[] buffer = new byte[BUFFER_SIZE];
            int read;
            while ((read = input.read(buffer)) != -1) {
               if (read == 0) continue;
               output.write(buffer, 0, read);
               count += read;
               if (progress != null) progress.onBytes(count);
            }
         }
         if (expected >= 0L && count != expected) {
            throw new IOException("Incomplete download: expected " + expected + " bytes but received " + count);
         }
         try {
            Files.move(temporary, targetFile.toPath(),
               StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
         } catch (java.nio.file.AtomicMoveNotSupportedException unsupported) {
            Files.move(temporary, targetFile.toPath(), StandardCopyOption.REPLACE_EXISTING);
         }
         temporary = null;
         return targetFile;
      } finally {
         if (temporary != null) Files.deleteIfExists(temporary);
         if (connection instanceof HttpURLConnection) ((HttpURLConnection)connection).disconnect();
      }
   }
}

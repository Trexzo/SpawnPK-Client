package rs.cache.updater.assets;

import java.io.File;
import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.StandardCopyOption;
import java.nio.file.attribute.BasicFileAttributes;

/**
 * Original-independent, Java 11 cache installation transaction.
 * The active cache is neither deleted nor modified until the download and
 * extraction have both succeeded in a separate sibling directory.
 */
public final class CacheUpdateTransaction {
   private CacheUpdateTransaction() { }

   @FunctionalInterface
   public interface Downloader {
      File download(File archiveDestination) throws IOException;
   }

   @FunctionalInterface
   public interface Extractor {
      boolean extract(String extractionDirectory, File archive) throws IOException;
   }

   @FunctionalInterface
   interface SwitchHook {
      void afterBackup() throws IOException;
   }

   public static boolean install(File cacheRoot, Downloader downloader, Extractor extractor)
         throws IOException {
      return install(cacheRoot, downloader, extractor, () -> { });
   }

   /** Package-private test seam for forced failure BETWEEN the two moves. */
   static synchronized boolean install(File cacheRoot, Downloader downloader,
         Extractor extractor, SwitchHook hook) throws IOException {
      if (cacheRoot == null || downloader == null || extractor == null || hook == null) {
         throw new IOException("Missing cache update input");
      }
      Path original = cacheRoot.toPath().toAbsolutePath().normalize();
      Path parent = original.getParent();
      if (parent == null || original.getFileName() == null || !Files.isDirectory(parent)) {
         throw new IOException("Unsafe cache root: " + original);
      }
      if (Files.exists(original, LinkOption.NOFOLLOW_LINKS)) {
         BasicFileAttributes attributes = Files.readAttributes(original,
            BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
         if (!attributes.isDirectory() || attributes.isSymbolicLink() || attributes.isOther()) {
            throw new IOException("Refusing non-directory or linked cache root: " + original);
         }
      }
      Path work = Files.createTempDirectory(parent, ".spk-cache-update-");
      Path staged = work.resolve("staged");
      Path previous = work.resolve("previous");
      Path archive = work.resolve("cache.zip");
      boolean keepRecovery = false;
      try {
         Files.createDirectory(staged);
         if (Files.exists(original, LinkOption.NOFOLLOW_LINKS)) {
            copyTreeNoLinks(original, staged);
         }
         File downloaded = downloader.download(archive.toFile());
         if (downloaded == null || !downloaded.toPath().toAbsolutePath().normalize().equals(archive)
               || !Files.isRegularFile(archive, LinkOption.NOFOLLOW_LINKS)) {
            return false;
         }
         if (!extractor.extract(staged.toString(), archive.toFile())) {
            return false;
         }
         Files.deleteIfExists(archive);
         boolean movedExisting = false;
         try {
            if (Files.exists(original, LinkOption.NOFOLLOW_LINKS)) {
               moveDirectory(original, previous);
               movedExisting = true;
            }
            hook.afterBackup();
            moveDirectory(staged, original);
         } catch (IOException | RuntimeException failure) {
            if (movedExisting) {
               try {
                  if (!Files.exists(original, LinkOption.NOFOLLOW_LINKS)) {
                     moveDirectory(previous, original);
                  } else {
                     keepRecovery = true;
                  }
               } catch (IOException rollbackError) {
                  keepRecovery = true;
                  failure.addSuppressed(rollbackError);
               }
            }
            throw failure;
         }
         return true;
      } finally {
         if (!keepRecovery) {
            try {
               deleteTreeNoLinks(work);
            } catch (IOException cleanupFailure) {
               // A completed update must not be rolled back because an old-file
               // backup is locked; retain residue for manual investigation.
               System.err.println("Cache update cleanup incomplete, inspect: " + work
                  + " (" + cleanupFailure + ")");
            }
         } else {
            System.err.println("Cache update could not restore original; recovery files retained at: " + work);
         }
      }
   }

   private static void moveDirectory(Path source, Path target) throws IOException {
      try {
         Files.move(source, target, StandardCopyOption.ATOMIC_MOVE);
      } catch (AtomicMoveNotSupportedException unavailable) {
         Files.move(source, target);
      }
   }

   private static void copyTreeNoLinks(Path root, Path destination) throws IOException {
      Files.walkFileTree(root, new SimpleFileVisitor<Path>() {
         @Override public FileVisitResult preVisitDirectory(Path directory, BasicFileAttributes attrs)
               throws IOException {
            if (!attrs.isDirectory() || attrs.isSymbolicLink() || attrs.isOther()) {
               throw new IOException("Unsafe cache directory entry: " + directory);
            }
            Files.createDirectories(destination.resolve(root.relativize(directory)));
            return FileVisitResult.CONTINUE;
         }
         @Override public FileVisitResult visitFile(Path source, BasicFileAttributes attrs)
               throws IOException {
            if (!attrs.isRegularFile() || attrs.isSymbolicLink() || attrs.isOther()) {
               throw new IOException("Unsafe cache file type: " + source);
            }
            Files.copy(source, destination.resolve(root.relativize(source)),
               StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.COPY_ATTRIBUTES);
            return FileVisitResult.CONTINUE;
         }
      });
   }

   private static void deleteTreeNoLinks(Path root) throws IOException {
      if (!Files.exists(root, LinkOption.NOFOLLOW_LINKS)) return;
      Files.walkFileTree(root, new SimpleFileVisitor<Path>() {
         @Override public FileVisitResult visitFile(Path file, BasicFileAttributes attrs)
               throws IOException {
            Files.delete(file);
            return FileVisitResult.CONTINUE;
         }
         @Override public FileVisitResult postVisitDirectory(Path directory, IOException error)
               throws IOException {
            if (error != null) throw error;
            Files.delete(directory);
            return FileVisitResult.CONTINUE;
         }
      });
   }
}

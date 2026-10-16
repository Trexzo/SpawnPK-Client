package rs.cache.updater.assets;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.DirectoryStream;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.OpenOption;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.List;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Conservative, restart-recoverable cache update with an inter-process file lock.
 * Source-only Java 11 implementation: no original game bytecode or helper stubs.
 * This is NOT a guarantee of power-loss durability across all filesystems.
 */
public final class CacheUpdateTransaction {
   private static final String WORK_PREFIX = ".spk-cache-update-";
   private static final String MARKER = ".transaction";
   private static final String MAGIC = "SPK-CACHE-TRANSACTION-V1";
   private static final LinkOption NOFOLLOW = LinkOption.NOFOLLOW_LINKS;

   private CacheUpdateTransaction() { }

   @FunctionalInterface public interface Downloader {
      File download(File archiveDestination) throws IOException;
   }
   @FunctionalInterface public interface Extractor {
      boolean extract(String extractionDirectory, File archive) throws IOException;
   }
   @FunctionalInterface interface SwitchHook {
      void onSwitch() throws IOException;
   }

   public static boolean install(File cacheRoot, Downloader downloader, Extractor extractor)
         throws IOException {
      return install(cacheRoot, downloader, extractor, () -> { }, () -> { });
   }

   // Compatibility with R220's fault-injection interface.
   static boolean install(File cacheRoot, Downloader downloader, Extractor extractor,
         SwitchHook afterBackup) throws IOException {
      return install(cacheRoot, downloader, extractor, afterBackup, () -> { });
   }

   /** Integration hook only for synthetic crash and rollback regression. */
   static boolean install(File cacheRoot, Downloader downloader, Extractor extractor,
         SwitchHook afterBackup, SwitchHook afterPromotion) throws IOException {
      if (cacheRoot == null || downloader == null || extractor == null ||
            afterBackup == null || afterPromotion == null) {
         throw new IOException("Missing cache update input");
      }
      Path root = checkedRoot(cacheRoot);
      try (Guard guard = lock(root)) {
         recoverUnderLock(root);
         return doInstall(root, downloader, extractor, afterBackup, afterPromotion);
      }
   }

   /** Recover only this exact cache root, while holding the same cross-process lock. */
   public static void recover(File cacheRoot) throws IOException {
      Path root = checkedRoot(cacheRoot);
      try (Guard guard = lock(root)) {
         recoverUnderLock(root);
      }
   }

   private static Path checkedRoot(File rootFile) throws IOException {
      Path root = rootFile.toPath().toAbsolutePath().normalize();
      Path parent = root.getParent();
      if (parent == null || root.getFileName() == null ||
            !Files.isDirectory(parent, NOFOLLOW) || Files.isSymbolicLink(parent)) {
         throw new IOException("Unsafe cache parent: " + root);
      }
      // A linked ancestor (including a Windows junction/reparse directory)
      // can redirect the supposedly fixed cache parent to another filesystem.
      Path ancestor = root.getRoot();
      if (ancestor == null) throw new IOException("Cache root must be absolute");
      for (Path segment : ancestor.relativize(parent)) {
         ancestor = ancestor.resolve(segment);
         if (!Files.exists(ancestor, NOFOLLOW)) {
            throw new IOException("Cache ancestor disappeared: " + ancestor);
         }
         BasicFileAttributes attrs = Files.readAttributes(ancestor,
            BasicFileAttributes.class, NOFOLLOW);
         if (!attrs.isDirectory() || attrs.isSymbolicLink() || attrs.isOther()) {
            throw new IOException("Unsafe cache ancestor: " + ancestor);
         }
      }
      if (Files.exists(root, NOFOLLOW)) {
         requirePlainDirectory(root);
      }
      return root;
   }

   private static final class Guard implements AutoCloseable {
      private final FileChannel channel;
      private final FileLock lock;
      Guard(FileChannel channel, FileLock lock) {
         this.channel = channel; this.lock = lock;
      }
      @Override public void close() throws IOException {
         try { lock.release(); } finally { channel.close(); }
      }
   }

   private static Guard lock(Path root) throws IOException {
      Path lockFile = root.getParent().resolve(".spk-cache-lock-" + digest(root.toString()) + ".lck");
      if (Files.exists(lockFile, NOFOLLOW) &&
            (!Files.isRegularFile(lockFile, NOFOLLOW) || Files.isSymbolicLink(lockFile))) {
         throw new IOException("Unsafe cache lock path: " + lockFile);
      }
      FileChannel channel = FileChannel.open(lockFile, StandardOpenOption.CREATE,
         StandardOpenOption.WRITE, NOFOLLOW);
      try {
         FileLock acquired;
         try {
            acquired = channel.tryLock();
         } catch (OverlappingFileLockException busy) {
            throw new IOException("Another client is updating this cache: " + root, busy);
         }
         if (acquired == null) {
            throw new IOException("Another client is updating this cache: " + root);
         }
         // The lock file is intentionally persistent: deleting it would create
         // a second inode and could let a competing process bypass the lock.
         return new Guard(channel, acquired);
      } catch (IOException | RuntimeException failure) {
         try { channel.close(); } catch (IOException closeError) { failure.addSuppressed(closeError); }
         throw failure;
      }
   }

   /** Each cache root owns its recovery workspace; unrelated cache journals stay isolated. */
   private static String scopedWorkPrefix(Path root) throws IOException {
      return WORK_PREFIX + digest(root.toString()) + "-";
   }

   private static boolean isScopedWorkspace(String name) {
      return name.matches("\\.spk-cache-update-[0-9a-f]{24}-.*");
   }

   private static String digest(String value) throws IOException {
      try {
         byte[] hash = MessageDigest.getInstance("SHA-256")
            .digest(value.getBytes(StandardCharsets.UTF_8));
         StringBuilder out = new StringBuilder();
         for (int i = 0; i < 12; i++) out.append(String.format("%02x", hash[i] & 0xff));
         return out.toString();
      } catch (NoSuchAlgorithmException impossible) {
         throw new IOException("SHA-256 unavailable", impossible);
      }
   }

   private static boolean doInstall(Path root, Downloader downloader, Extractor extractor,
         SwitchHook afterBackup, SwitchHook afterPromotion) throws IOException {
      Path work = Files.createTempDirectory(root.getParent(), scopedWorkPrefix(root));
      Path stage = work.resolve("staged");
      Path old = work.resolve("previous");
      Path archive = work.resolve("cache.zip");
      boolean completed = false;
      boolean recovered = false;
      try {
         writeState(work, root, "PREPARING");
         Files.createDirectory(stage);
         boolean hadOriginal = Files.exists(root, NOFOLLOW);
         if (hadOriginal) copyTreeNoLinks(root, stage);
         File downloaded = downloader.download(archive.toFile());
         if (downloaded == null || !downloaded.toPath().toAbsolutePath().normalize().equals(archive)
               || !Files.isRegularFile(archive, NOFOLLOW)) {
            completed = true; return false;
         }
         if (!extractor.extract(stage.toString(), archive.toFile())) {
            completed = true; return false;
         }
         Files.deleteIfExists(archive);
         writeState(work, root, "STAGED");
         if (hadOriginal) {
            writeState(work, root, "MOVING_OLD");
            moveDirectory(root, old);
            writeState(work, root, "OLD_MOVED");
         }
         afterBackup.onSwitch();
         writeState(work, root, "PROMOTING");
         moveDirectory(stage, root);
         afterPromotion.onSwitch();
         writeState(work, root, "PROMOTED");
         completed = true;
         return true;
      } catch (IOException | RuntimeException failure) {
         try {
            recoverSingle(root, work);
            recovered = true;
         } catch (IOException recoveryError) {
            failure.addSuppressed(recoveryError);
         }
         throw failure;
      } finally {
         // Uncaught Errors simulate sudden JVM/process death in tests. Do not
         // remove the backup or journal; the next invocation will recover it.
         if (completed || recovered) {
            try { deleteTreeNoLinks(work); }
            catch (IOException cleanupError) {
               System.err.println("Cache staging cleanup incomplete: " + work + ": " + cleanupError);
            }
         }
      }
   }

   private static void recoverUnderLock(Path root) throws IOException {
      // Read and verify the ENTIRE root-specific inventory before modifying
      // the live cache or any backup. DirectoryStream iteration has no stable
      // order, so recovering the first of two journals can destroy evidence.
      List<Path> owned = new ArrayList<>();
      String expectedPrefix = scopedWorkPrefix(root);
      try (DirectoryStream<Path> candidates = Files.newDirectoryStream(root.getParent(), WORK_PREFIX + "*")) {
         for (Path work : candidates) {
            String workspaceName = work.getFileName().toString();
            // Never even open another root's scoped journal or backup.
            if (isScopedWorkspace(workspaceName) &&
                  !workspaceName.startsWith(expectedPrefix)) continue;
            boolean expectedScoped = workspaceName.startsWith(expectedPrefix);
            if (!Files.isDirectory(work, NOFOLLOW) || Files.isSymbolicLink(work)) {
               throw new IOException("Unsafe cache recovery directory: " + work);
            }
            Path marker = work.resolve(MARKER);
            if (!Files.exists(marker, NOFOLLOW)) {
               // In a root-owned workspace, even an unmarked staged cache may
               // represent a partially initialized update. Never silently
               // discard it. Legacy unmarked backups are equally ambiguous.
               if (Files.exists(work.resolve("previous"), NOFOLLOW) ||
                     (expectedScoped && Files.exists(work.resolve("staged"), NOFOLLOW))) {
                  throw new IOException("Unidentified cache recovery data; manual inspection required: " + work);
               }
               continue;
            }
            String[] journal = readState(work);
            if (!journal[1].equals(root.toString())) {
               if (expectedScoped) {
                  throw new IOException("Scoped journal owner does not match cache root: " + work);
               }
               continue;
            }
            owned.add(work);
         }
      }
      if (owned.size() > 1) {
         throw new IOException("Multiple pending transactions for the same cache root; " +
            "preserving all backups for manual recovery: " + root);
      }
      if (!owned.isEmpty()) recoverSingle(root, owned.get(0));
   }

   private static void recoverSingle(Path root, Path work) throws IOException {
      String[] entry = readState(work);
      if (!entry[1].equals(root.toString())) {
         throw new IOException("Cache recovery marker points to another root: " + work);
      }
      String phase = entry[2];
      Path old = work.resolve("previous");
      Path stage = work.resolve("staged");
      Path abandoned = work.resolve("interrupted-new");
      boolean oldExists = Files.exists(old, NOFOLLOW);
      boolean activeExists = Files.exists(root, NOFOLLOW);
      boolean stageExists = Files.exists(stage, NOFOLLOW);
      if (oldExists) requirePlainDirectory(old);
      if (activeExists) requirePlainDirectory(root);
      if (stageExists) requirePlainDirectory(stage);
      if (Files.exists(abandoned, NOFOLLOW)) {
         throw new IOException("Recovery has an unresolved interrupted-new directory: " + work);
      }
      if (oldExists) {
         if (phase.equals("PROMOTED") && activeExists) {
            // The journal says installation completed; old is safe to release.
            deleteTreeNoLinks(work);
            return;
         }
         if (activeExists) {
            if (!phase.equals("PROMOTING") || stageExists) {
               throw new IOException("Ambiguous cache recovery; old and active present: " + work);
            }
            // New cache may have been promoted just before a crash; quarantine
            // it temporarily before putting the original back.
            moveDirectory(root, abandoned);
         }
         try {
            moveDirectory(old, root);
         } catch (IOException restoreFailed) {
            throw new IOException("Rollback failed; original preserved at " + old, restoreFailed);
         }
         deleteTreeNoLinks(work);
         return;
      }
      if (activeExists) {
         if (phase.equals("PROMOTED")) {
            deleteTreeNoLinks(work);
            return;
         }
         if (phase.equals("PROMOTING") && !stageExists) {
            // Previously missing cache: uncommitted promotion is quarantined,
            // restoring the prior state (no active cache).
            moveDirectory(root, abandoned);
            deleteTreeNoLinks(work);
            return;
         }
         if ((stageExists || phase.equals("PREPARING")) && (phase.equals("PREPARING") || phase.equals("STAGED") ||
               phase.equals("MOVING_OLD"))) {
            // Old root was never moved, so discard the staged candidate.
            deleteTreeNoLinks(work);
            return;
         }
         throw new IOException("Ambiguous cache root without a verified backup: " + work);
      }
      if ((stageExists || phase.equals("PREPARING")) && (phase.equals("PREPARING") || phase.equals("STAGED") ||
            phase.equals("PROMOTING"))) {
         deleteTreeNoLinks(work);
         return;
      }
      throw new IOException("No active cache or backup; refusing recovery cleanup: " + work);
   }

   private static String[] readState(Path work) throws IOException {
      Path marker = work.resolve(MARKER);
      if (!Files.isRegularFile(marker, NOFOLLOW) || Files.size(marker) > 8192) {
         throw new IOException("Invalid cache recovery marker: " + marker);
      }
      String[] lines = Files.readString(marker, StandardCharsets.UTF_8).split("\\n", -1);
      if (lines.length != 4 || !lines[0].equals(MAGIC) ||
            lines[1].isEmpty() || !lines[3].isEmpty() ||
            !(lines[2].equals("PREPARING") || lines[2].equals("STAGED") ||
               lines[2].equals("MOVING_OLD") || lines[2].equals("OLD_MOVED") ||
               lines[2].equals("PROMOTING") || lines[2].equals("PROMOTED"))) {
         throw new IOException("Malformed cache recovery marker: " + marker);
      }
      return lines;
   }

   private static void writeState(Path work, Path root, String phase) throws IOException {
      Path temporary = Files.createTempFile(work, ".journal-", ".tmp");
      try {
         byte[] bytes = (MAGIC + "\n" + root + "\n" + phase + "\n")
            .getBytes(StandardCharsets.UTF_8);
         try (FileChannel channel = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) channel.write(buffer);
            channel.force(true);
         }
         try {
            Files.move(temporary, work.resolve(MARKER), StandardCopyOption.REPLACE_EXISTING,
               StandardCopyOption.ATOMIC_MOVE);
         } catch (AtomicMoveNotSupportedException notAtomic) {
            Files.move(temporary, work.resolve(MARKER), StandardCopyOption.REPLACE_EXISTING);
         }
      } finally {
         Files.deleteIfExists(temporary);
      }
   }

   private static void requirePlainDirectory(Path directory) throws IOException {
      BasicFileAttributes attrs = Files.readAttributes(directory, BasicFileAttributes.class, NOFOLLOW);
      if (!attrs.isDirectory() || attrs.isSymbolicLink() || attrs.isOther()) {
         throw new IOException("Refusing linked or non-directory cache path: " + directory);
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
      if (!Files.exists(root, NOFOLLOW)) return;
      Files.walkFileTree(root, new SimpleFileVisitor<Path>() {
         @Override public FileVisitResult visitFile(Path file, BasicFileAttributes attrs)
               throws IOException {
            Files.delete(file); return FileVisitResult.CONTINUE;
         }
         @Override public FileVisitResult postVisitDirectory(Path directory, IOException error)
               throws IOException {
            if (error != null) throw error;
            Files.delete(directory); return FileVisitResult.CONTINUE;
         }
      });
   }
}

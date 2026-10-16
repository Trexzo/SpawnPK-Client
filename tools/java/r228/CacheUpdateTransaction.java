package rs.cache.updater.assets;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
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
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.Arrays;
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
      Path lockFile = root.getParent().resolve(".spk-cache-lock-" + digest(rootIdentity(root)) + ".lck");
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
      return WORK_PREFIX + digest(rootIdentity(root)) + "-";
   }

   private static boolean isScopedWorkspace(String name) {
      return name.matches("\\.spk-cache-update-[0-9a-f]{24}-.*");
   }

   /**
    * Windows path lookups are case-insensitive on the supported standard
    * filesystem layout. File names used for lock/workspace identity therefore
    * MUST NOT depend on caller-provided path capitalization. The original
    * normalized Path still points to the same physical data and the journal
    * keeps its full path for evidence/rollback.
    *
    * This does not normalize 8.3 aliases or third-party filesystem semantics.
    */
   private static String rootIdentity(Path root) {
      String text = root.toAbsolutePath().normalize().toString();
      return File.separatorChar == '\\' ? text.toLowerCase(Locale.ROOT) : text;
   }

   private static boolean sameRoot(String journalRoot, Path expectedRoot) {
      if (File.separatorChar == '\\') {
         return journalRoot.toLowerCase(Locale.ROOT).equals(rootIdentity(expectedRoot));
      }
      return journalRoot.equals(expectedRoot.toString());
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
         Map<String, byte[]> initial = null;
         if (hadOriginal) {
            // Take a content fingerprint of the active files, not timestamps.
            // The later copy and promotion checks detect non-cooperating writers
            // that run while the archive is downloaded and extracted.
            // Cheap size preflight comes before expensive content hashing so
            // very large sparse files fail without a long read.
            verifyStagingHeadroom(root);
            initial = snapshotTreeNoLinks(root);
            copyTreeNoLinks(root, stage);
            requireSameSnapshot(initial, snapshotTreeNoLinks(stage),
               "Cache changed while creating staging copy");
            requireSameSnapshot(initial, snapshotTreeNoLinks(root),
               "Active cache changed while staging was copied");
         }
         File downloaded = downloader.download(archive.toFile());
         if (downloaded == null || !downloaded.toPath().toAbsolutePath().normalize().equals(archive)
               || !Files.isRegularFile(archive, NOFOLLOW)) {
            completed = true; return false;
         }
         if (!extractor.extract(stage.toString(), archive.toFile())) {
            completed = true; return false;
         }
         Files.deleteIfExists(archive);
         // Capture EXACT staged contents after extraction and before switching.
         // This also rejects symlinks, junction-like entries and devices.
         // A second comparison after moving the old root detects hostile or
         // accidental writes to staging during the rename window.
         validateTreeNoLinks(stage);
         Map<String, byte[]> stagedWitness = snapshotTreeNoLinks(stage);
         if (hadOriginal) {
            requireSameSnapshot(initial, snapshotTreeNoLinks(root),
               "Active cache changed during update; refusing stale replacement");
         } else if (Files.exists(root, NOFOLLOW)) {
            throw new IOException("A different writer created the previously missing cache root");
         }
         writeState(work, root, "STAGED");
         if (hadOriginal) {
            writeState(work, root, "MOVING_OLD");
            moveDirectory(root, old);
            writeState(work, root, "OLD_MOVED");
         }
         afterBackup.onSwitch();
         // A non-cooperating cache writer can alter an open file descriptor
         // after the final pre-move snapshot. Check the RENAMED original again
         // while it is still preserved under previous/, before promoting stage.
         // This narrows the last mutation window; it is NOT a filesystem lock
         // against writers that ignore our separate update lock.
         if (hadOriginal) {
            requireSameSnapshot(initial, snapshotTreeNoLinks(old),
               "Original cache changed after relocation; refusing stale replacement");
         }
         if (Files.exists(root, NOFOLLOW)) {
            throw new IOException("A different writer recreated the cache root after relocation");
         }
         // Stage has been writable to non-cooperating same-account processes
         // throughout the root relocation. Do not promote unseen files or a
         // changed staged snapshot, even if names, lengths and mtimes agree.
         requireSameSnapshot(stagedWitness, snapshotTreeNoLinks(stage),
            "Staged cache changed after validation; refusing untrusted promotion");
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
            boolean expectedScoped = workspaceName.startsWith(expectedPrefix);
            if (isScopedWorkspace(workspaceName) && !expectedScoped) {
               // A previous Windows build may have hashed the same physical
               // root using a differently capitalized path. Recognize that
               // owner's VALID journal without treating a foreign malformed
               // workspace as ours. Never delete or rewrite a foreign entry.
               if (File.separatorChar != '\\') continue;
               Path foreignMarker = work.resolve(MARKER);
               if (!Files.isRegularFile(foreignMarker, NOFOLLOW)) continue;
               String[] legacy;
               try { legacy = readState(work); }
               catch (IOException malformedForeign) { continue; }
               if (!sameRoot(legacy[1], root)) continue;
               // This is a journal claiming this root under an old casing.
               // Its directory and contents are subsequently validated.
            }
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
            if (!sameRoot(journal[1], root)) {
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
      if (!sameRoot(entry[1], root)) {
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
      boolean abandonedExists = Files.exists(abandoned, NOFOLLOW);
      // Rollback is a separate journalled transaction. Without these phases,
      // a crash AFTER old was restored but BEFORE work cleanup would leave a
      // PROMOTING marker and risk deleting the restored original on restart.
      if (phase.equals("ROLLBACK_RESTORED")) {
         if (oldExists || !activeExists) {
            throw new IOException("Inconsistent completed rollback state: " + work);
         }
         deleteTreeNoLinks(work);
         return;
      }
      if (phase.equals("ROLLBACK_PREPARED") && !oldExists) {
         // The ONLY code removing 'previous' in this phase promotes it back
         // to 'root'. Never quarantine or delete that restored live directory.
         if (!activeExists) {
            throw new IOException("Rollback has no restored cache or backup: " + work);
         }
         writeState(work, root, "ROLLBACK_RESTORED");
         deleteTreeNoLinks(work);
         return;
      }
      if (phase.equals("ROLLBACK_EMPTY")) {
         if (oldExists) {
            throw new IOException("No-original rollback unexpectedly has a backup: " + work);
         }
         if (activeExists && !abandonedExists) moveDirectory(root, abandoned);
         else if (activeExists) {
            throw new IOException("Conflicting cache and interrupted-new during rollback: " + work);
         }
         deleteTreeNoLinks(work);
         return;
      }
      if (abandonedExists && !phase.equals("ROLLBACK_PREPARED")) {
         throw new IOException("Recovery has an unresolved interrupted-new directory: " + work);
      }
      if (oldExists) {
         if (phase.equals("PROMOTED") && activeExists) {
            // The journal says installation completed; old is safe to release.
            deleteTreeNoLinks(work);
            return;
         }
         if (activeExists && (!(phase.equals("PROMOTING") ||
               phase.equals("ROLLBACK_PREPARED")) || stageExists || abandonedExists)) {
            throw new IOException("Ambiguous cache recovery; old and active present: " + work);
         }
         // MUST journal intent before touching the active root. If the next
         // process starts after we restore 'previous' to 'root', it can tell
         // restored-original from newly promoted cache by this phase.
         if (!phase.equals("ROLLBACK_PREPARED")) writeState(work, root, "ROLLBACK_PREPARED");
         if (activeExists) {
            // Quarantine an uncommitted freshly promoted cache.
            moveDirectory(root, abandoned);
         }
         try {
            moveDirectory(old, root);
         } catch (IOException restoreFailed) {
            throw new IOException("Rollback failed; original preserved at " + old, restoreFailed);
         }
         writeState(work, root, "ROLLBACK_RESTORED");
         deleteTreeNoLinks(work);
         return;
      }
      if (activeExists) {
         if (phase.equals("PROMOTED")) {
            deleteTreeNoLinks(work);
            return;
         }
         if (phase.equals("PROMOTING") && !stageExists) {
            // Previously missing cache: journal the no-original rollback
            // before quarantining the uncommitted newly installed root.
            writeState(work, root, "ROLLBACK_EMPTY");
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
               lines[2].equals("PROMOTING") || lines[2].equals("PROMOTED") ||
               lines[2].equals("ROLLBACK_PREPARED") ||
               lines[2].equals("ROLLBACK_RESTORED") || lines[2].equals("ROLLBACK_EMPTY"))) {
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

   /**
    * Snapshot file CONTENT, not just mtime/size. A background process can
    * rewrite a file in place without altering length or even timestamps.
    * Relative names include directory markers to detect added/removed paths.
    * This does NOT prevent a noncooperating process writing in the tiny gap
    * between the final comparison and root rename.
    */
   private static Map<String, byte[]> snapshotTreeNoLinks(Path root) throws IOException {
      Map<String, byte[]> witness = new TreeMap<>();
      Files.walkFileTree(root, new SimpleFileVisitor<Path>() {
         @Override public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs)
               throws IOException {
            requirePlainDirectory(dir);
            witness.put("D:" + root.relativize(dir).toString(), new byte[0]);
            return FileVisitResult.CONTINUE;
         }
         @Override public FileVisitResult visitFile(Path file, BasicFileAttributes attrs)
               throws IOException {
            if (!attrs.isRegularFile() || attrs.isSymbolicLink() || attrs.isOther()) {
               throw new IOException("Unsafe cache file while computing snapshot: " + file);
            }
            MessageDigest hasher;
            try { hasher = MessageDigest.getInstance("SHA-256"); }
            catch (NoSuchAlgorithmException e) { throw new IOException("SHA-256 unavailable", e); }
            byte[] buf = new byte[32768];
            try (InputStream input = Files.newInputStream(file, StandardOpenOption.READ, NOFOLLOW)) {
               int n;
               while ((n = input.read(buf)) >= 0) {
                  if (n > 0) hasher.update(buf, 0, n);
               }
            }
            witness.put("F:" + root.relativize(file).toString(), hasher.digest());
            return FileVisitResult.CONTINUE;
         }
      });
      return witness;
   }

   private static void requireSameSnapshot(Map<String, byte[]> expected,
         Map<String, byte[]> observed, String reason) throws IOException {
      if (!expected.keySet().equals(observed.keySet())) {
         throw new IOException(reason + " (file or directory set differs)");
      }
      for (Map.Entry<String, byte[]> entry : expected.entrySet()) {
         if (!Arrays.equals(entry.getValue(), observed.get(entry.getKey()))) {
            throw new IOException(reason + " (content mismatch at " + entry.getKey() + ")");
         }
      }
   }

   private static void validateTreeNoLinks(Path root) throws IOException {
      Files.walkFileTree(root, new SimpleFileVisitor<Path>() {
         @Override public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs)
               throws IOException {
            requirePlainDirectory(dir);
            return FileVisitResult.CONTINUE;
         }
         @Override public FileVisitResult visitFile(Path file, BasicFileAttributes attrs)
               throws IOException {
            if (!attrs.isRegularFile() || attrs.isSymbolicLink() || attrs.isOther()) {
               throw new IOException("Unsafe staged cache path: " + file);
            }
            return FileVisitResult.CONTINUE;
         }
      });
   }

   /** Soft preflight only; actual disk exhaustion still requires IOException handling. */
   private static void verifyStagingHeadroom(Path root) throws IOException {
      // Free-space is not reserved and can shrink while downloading. The
      // core invariant remains staging-and-rollback, not an ENOSPC guarantee.
      long originalSize = 0L;
      try (java.util.stream.Stream<Path> paths = Files.walk(root)) {
         for (Path file : (Iterable<Path>) paths::iterator) {
            if (Files.isRegularFile(file, NOFOLLOW)) {
               long bytes = Files.size(file);
               originalSize = bytes > Long.MAX_VALUE - originalSize
                  ? Long.MAX_VALUE : originalSize + bytes;
            }
         }
      }
      if (originalSize > Files.getFileStore(root.getParent()).getUsableSpace()) {
         throw new IOException("Insufficient usable space to stage existing cache bytes");
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
               StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.COPY_ATTRIBUTES, NOFOLLOW);
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

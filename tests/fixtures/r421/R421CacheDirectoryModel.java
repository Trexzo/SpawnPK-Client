import java.io.IOException;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.Locale;

/**
 * R421 independently invented TEMP-only Java 11 path-provenance model.
 * No recovered/game classes, no player data and no journal cleanup.
 *
 * File-path checks are not anchored openat; this is cooperative local
 * preflight, NOT a defense against hostile in-flight ancestor replacement.
 */
public final class R421CacheDirectoryModel {
    enum State { CREATED, EXISTING, REFUSED }

    static String resolveWithoutCreation(String home, String key, boolean test,
                                         boolean relativeCache) {
        if (key == null || !key.matches("[A-Za-z0-9_-]{1,80}"))
            throw new IllegalArgumentException("unsafe-cache-key");
        if (relativeCache)
            return "." + java.io.File.separator + "cache" +
                   java.io.File.separator;
        if (home == null || home.isEmpty())
            throw new IllegalArgumentException("missing-home");
        return home + java.io.File.separator + "." + key.toLowerCase() +
               (test ? "-test" : "") + java.io.File.separator;
    }

    static boolean sameDirectory(BasicFileAttributes before,
                                 BasicFileAttributes after) {
        return before.isDirectory() && after.isDirectory() &&
               !before.isSymbolicLink() && !after.isSymbolicLink() &&
               !before.isOther() && !after.isOther() &&
               (before.fileKey() == null ||
                 before.fileKey().equals(after.fileKey()));
    }

    static State prepare(Path raw) {
        if (raw == null) return State.REFUSED;
        Path directory = raw.toAbsolutePath().normalize();
        Path parent = directory.getParent();
        if (parent == null || directory.getFileName() == null)
            return State.REFUSED;
        try {
            Path ancestor = parent;
            while (ancestor != null) {
                BasicFileAttributes attrs = Files.readAttributes(
                    ancestor, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                if (!attrs.isDirectory() || attrs.isSymbolicLink() ||
                    attrs.isOther())
                    return State.REFUSED;
                ancestor = ancestor.getParent();
            }
            BasicFileAttributes parentBefore = Files.readAttributes(
                parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            if (!parentBefore.isDirectory() || parentBefore.isOther())
                return State.REFUSED;
            try {
                BasicFileAttributes leafBefore = Files.readAttributes(
                    directory, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                if (!leafBefore.isDirectory() || leafBefore.isSymbolicLink() ||
                    leafBefore.isOther())
                    return State.REFUSED;
                BasicFileAttributes leafAfter = Files.readAttributes(
                    directory, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                BasicFileAttributes parentAfter = Files.readAttributes(
                    parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                return sameDirectory(leafBefore, leafAfter) &&
                       sameDirectory(parentBefore, parentAfter)
                    ? State.EXISTING : State.REFUSED;
            } catch (NoSuchFileException missing) {
                try {
                    Files.createDirectory(directory);
                } catch (FileAlreadyExistsException raced) {
                    return State.REFUSED;
                }
                BasicFileAttributes created = Files.readAttributes(
                    directory, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                if (!created.isDirectory() || created.isSymbolicLink() ||
                    created.isOther())
                    return State.REFUSED;
                BasicFileAttributes parentAfter = Files.readAttributes(
                    parent, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
                return sameDirectory(parentBefore, parentAfter)
                    ? State.CREATED : State.REFUSED;
            }
        } catch (IOException | SecurityException invalid) {
            return State.REFUSED;
        }
    }

    public static void main(String[] argv) {
        if (argv.length == 2 && "prepare".equals(argv[0])) {
            System.out.println(prepare(Paths.get(argv[1])));
            return;
        }
        if (argv.length == 5 && "derive".equals(argv[0])) {
            try {
                System.out.println(resolveWithoutCreation(
                    argv[1], argv[2], Boolean.parseBoolean(argv[3]),
                    Boolean.parseBoolean(argv[4])));
            } catch (IllegalArgumentException refused) {
                System.out.println("REFUSED");
            }
            return;
        }
        throw new IllegalArgumentException(
            "prepare <invented TEMP dir> | derive <home> <key> <test> <relative>");
    }
}

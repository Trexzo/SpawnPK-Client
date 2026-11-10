import java.io.IOException;
import java.net.URI;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.util.Comparator;
import java.util.Map;

/** Public stand-alone provider capability probe: no game source or user data. */
public final class DirectoryForceProbe {
    private static String attempt(Path directory) {
        if (!Files.isDirectory(directory, LinkOption.NOFOLLOW_LINKS)) return "invalid-directory";
        try (FileChannel channel = FileChannel.open(directory, StandardOpenOption.READ)) {
            channel.force(true);
            return "supported";
        } catch (IOException | UnsupportedOperationException | SecurityException failure) {
            return "unsupported:" + failure.getClass().getSimpleName();
        }
    }

    public static void main(String[] args) throws Exception {
        Path scratch = Files.createTempDirectory("r376-provider-probe-");
        try {
            Path directory = scratch.resolve("ordinary");
            Files.createDirectory(directory);
            String nativeResult = attempt(directory);
            String repeat = attempt(directory);
            if (!nativeResult.equals(repeat))
                throw new AssertionError("Directory capability probe changed unexpectedly");
            System.out.println("R376_NATIVE_PROVIDER=" + nativeResult);
            Path file = scratch.resolve("regular-file");
            Files.writeString(file, "UNTOUCHED");
            if (!attempt(file).equals("invalid-directory"))
                throw new AssertionError("Regular file identified as directory");
            if (!Files.readString(file).equals("UNTOUCHED"))
                throw new AssertionError("Capability probe mutated test file");
            URI zipUri = URI.create("jar:" + scratch.resolve("probe.zip").toUri());
            try (FileSystem zip = FileSystems.newFileSystem(zipUri, Map.of("create", "true"))) {
                Path zipDirectory = zip.getPath("/inside");
                Files.createDirectory(zipDirectory);
                System.out.println("R376_ZIP_PROVIDER=" + attempt(zipDirectory));
            }
            System.out.println("R376_PROVIDER_PROBE_PASS");
        } finally {
            try (var walk = Files.walk(scratch)) {
                for (Path path : walk.sorted(Comparator.reverseOrder()).toArray(Path[]::new))
                    Files.deleteIfExists(path);
            }
        }
    }
}

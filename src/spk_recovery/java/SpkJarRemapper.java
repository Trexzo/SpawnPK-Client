import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.Manifest;
import java.util.zip.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.commons.ClassRemapper;
import jdk.internal.org.objectweb.asm.commons.Remapper;

/**
 * Whole-JAR class-name remapper used by the Python recovery orchestrator.
 *
 * Uses the ASM copy bundled inside the selected JDK so the repository does not
 * need to vendor a third-party ASM JAR. Only class identities are remapped in
 * R2B; member renaming belongs to a later stage.
 */
public final class SpkJarRemapper {
    private static final class MapRemapper extends Remapper {
        private final Map<String, String> names;
        private final boolean rewriteStrings;

        MapRemapper(Map<String, String> names, boolean rewriteStrings) {
            this.names = names;
            this.rewriteStrings = rewriteStrings;
        }

        @Override
        public String map(String internalName) {
            return names.getOrDefault(internalName, internalName);
        }

        @Override
        public Object mapValue(Object value) {
            if (rewriteStrings && value instanceof String) {
                String s = (String) value;
                String internal = names.get(s);
                if (internal != null) {
                    return internal;
                }
                for (Map.Entry<String, String> entry : names.entrySet()) {
                    if (s.equals(entry.getKey().replace('/', '.'))) {
                        return entry.getValue().replace('/', '.');
                    }
                }
            }
            return super.mapValue(value);
        }
    }

    private static Map<String, String> loadMap(Path path) throws IOException {
        Map<String, String> out = new LinkedHashMap<>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            if (line.isBlank() || line.startsWith("#")) {
                continue;
            }
            String[] parts = line.split("\\t", -1);
            if (parts.length != 2 || parts[0].isEmpty() || parts[1].isEmpty()) {
                throw new IllegalArgumentException("bad mapping row: " + line);
            }
            if (out.put(parts[0], parts[1]) != null) {
                throw new IllegalArgumentException("duplicate source: " + parts[0]);
            }
        }
        if (out.isEmpty()) {
            throw new IllegalArgumentException("empty mapping");
        }
        Set<String> targets = new HashSet<>();
        for (String target : out.values()) {
            if (!targets.add(target)) {
                throw new IllegalArgumentException("duplicate target: " + target);
            }
        }
        return out;
    }

    private static byte[] remapClass(
        byte[] input,
        Map<String, String> names,
        boolean rewriteStrings
    ) {
        ClassReader reader = new ClassReader(input);
        ClassWriter writer = new ClassWriter(0);
        reader.accept(
            new ClassRemapper(writer, new MapRemapper(names, rewriteStrings)),
            0
        );
        return writer.toByteArray();
    }

    private static byte[] remapManifest(
        byte[] input,
        Map<String, String> names
    ) throws IOException {
        Manifest manifest = new Manifest(new ByteArrayInputStream(input));
        String main = manifest.getMainAttributes().getValue("Main-Class");
        if (main != null) {
            String mapped = names.get(main.replace('.', '/'));
            if (mapped != null) {
                manifest.getMainAttributes().putValue(
                    "Main-Class",
                    mapped.replace('/', '.')
                );
            }
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        manifest.write(out);
        return out.toByteArray();
    }

    private static String mapDotted(
        String dotted,
        Map<String, String> names
    ) {
        String mapped = names.get(dotted.replace('.', '/'));
        return mapped == null ? dotted : mapped.replace('/', '.');
    }

    private static byte[] remapService(
        byte[] input,
        Map<String, String> names
    ) {
        String text = new String(input, StandardCharsets.UTF_8);
        StringBuilder out = new StringBuilder();
        String[] lines = text.split("(?<=\\n)", -1);
        for (String line : lines) {
            String newline = line.endsWith("\n") ? "\n" : "";
            String body = newline.isEmpty()
                ? line
                : line.substring(0, line.length() - 1);
            String trimmed = body.trim();
            if (!trimmed.isEmpty() && !trimmed.startsWith("#")) {
                int hash = body.indexOf('#');
                String provider = (
                    hash >= 0 ? body.substring(0, hash) : body
                ).trim();
                String mapped = mapDotted(provider, names);
                if (!mapped.equals(provider)) {
                    int start = body.indexOf(provider);
                    body = body.substring(0, start)
                        + mapped
                        + body.substring(start + provider.length());
                }
            }
            out.append(body).append(newline);
        }
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }

    private static String outputName(
        String inputName,
        Map<String, String> names
    ) {
        if (inputName.endsWith(".class")) {
            String internal = inputName.substring(
                0,
                inputName.length() - ".class".length()
            );
            String mapped = names.get(internal);
            if (mapped != null) {
                return mapped + ".class";
            }
        }
        if (inputName.startsWith("META-INF/services/")) {
            String service = inputName.substring("META-INF/services/".length());
            return "META-INF/services/" + mapDotted(service, names);
        }
        return inputName;
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "usage: <mapping.tsv> <input.jar> <output.jar> "
                + "[--rewrite-class-name-strings]"
            );
        }

        Path mappingPath = Paths.get(args[0]);
        Path inputPath = Paths.get(args[1]);
        Path outputPath = Paths.get(args[2]);
        boolean rewriteStrings =
            args.length >= 4
            && "--rewrite-class-name-strings".equals(args[3]);

        Map<String, String> names = loadMap(mappingPath);
        Map<String, byte[]> output = new TreeMap<>();

        try (ZipFile input = new ZipFile(inputPath.toFile())) {
            Enumeration<? extends ZipEntry> entries = input.entries();
            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                if (entry.isDirectory()) {
                    continue;
                }
                byte[] data;
                try (InputStream stream = input.getInputStream(entry)) {
                    data = stream.readAllBytes();
                }

                String name = entry.getName();
                if (name.endsWith(".class")) {
                    data = remapClass(data, names, rewriteStrings);
                } else if ("META-INF/MANIFEST.MF".equalsIgnoreCase(name)) {
                    data = remapManifest(data, names);
                } else if (name.startsWith("META-INF/services/")) {
                    data = remapService(data, names);
                }

                String target = outputName(name, names);
                if (output.put(target, data) != null) {
                    throw new IllegalStateException(
                        "output path collision: " + target
                    );
                }
            }
        }

        Path parent = outputPath.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }

        try (
            ZipOutputStream jar = new ZipOutputStream(
                Files.newOutputStream(outputPath)
            )
        ) {
            for (Map.Entry<String, byte[]> row : output.entrySet()) {
                byte[] bytes = row.getValue();
                CRC32 crc = new CRC32();
                crc.update(bytes);

                ZipEntry entry = new ZipEntry(row.getKey());
                entry.setTime(0L);
                entry.setMethod(ZipEntry.STORED);
                entry.setSize(bytes.length);
                entry.setCompressedSize(bytes.length);
                entry.setCrc(crc.getValue());

                jar.putNextEntry(entry);
                jar.write(bytes);
                jar.closeEntry();
            }
        }

        System.out.println("SPK_JAR_REMAP_PASS");
        System.out.println("mapped_classes=" + names.size());
        System.out.println("output_entries=" + output.size());
    }
}

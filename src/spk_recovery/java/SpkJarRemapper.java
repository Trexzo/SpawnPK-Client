import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.Manifest;
import java.util.zip.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.commons.ClassRemapper;
import jdk.internal.org.objectweb.asm.commons.Remapper;

/** Whole-JAR class/member remapper used by the Python recovery orchestrator. */
public final class SpkJarRemapper {
    private record MemberKey(String owner, String name, String descriptor) {}

    private static final class MappingSet {
        final Map<String, String> classes = new LinkedHashMap<>();
        final Map<MemberKey, String> fields = new LinkedHashMap<>();
        final Map<MemberKey, String> methods = new LinkedHashMap<>();
    }

    private static final class MapRemapper extends Remapper {
        private final MappingSet mappings;
        private final boolean rewriteStrings;

        MapRemapper(MappingSet mappings, boolean rewriteStrings) {
            this.mappings = mappings;
            this.rewriteStrings = rewriteStrings;
        }

        @Override
        public String map(String internalName) {
            return mappings.classes.getOrDefault(internalName, internalName);
        }

        @Override
        public String mapFieldName(String owner, String name, String descriptor) {
            return mappings.fields.getOrDefault(
                new MemberKey(owner, name, descriptor),
                name
            );
        }

        @Override
        public String mapMethodName(String owner, String name, String descriptor) {
            return mappings.methods.getOrDefault(
                new MemberKey(owner, name, descriptor),
                name
            );
        }

        @Override
        public Object mapValue(Object value) {
            if (rewriteStrings && value instanceof String) {
                String s = (String) value;
                String internal = mappings.classes.get(s);
                if (internal != null) {
                    return internal;
                }
                for (Map.Entry<String, String> entry : mappings.classes.entrySet()) {
                    if (s.equals(entry.getKey().replace('/', '.'))) {
                        return entry.getValue().replace('/', '.');
                    }
                }
            }
            return super.mapValue(value);
        }
    }

    private static MappingSet loadMap(Path path) throws IOException {
        MappingSet out = new MappingSet();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            if (line.isBlank() || line.startsWith("#")) {
                continue;
            }
            String[] parts = line.split("\\t", -1);
            switch (parts[0]) {
                case "C" -> {
                    if (parts.length != 3) {
                        throw new IllegalArgumentException("bad class mapping row: " + line);
                    }
                    if (out.classes.put(parts[1], parts[2]) != null) {
                        throw new IllegalArgumentException("duplicate class source: " + parts[1]);
                    }
                }
                case "F", "M" -> {
                    if (parts.length != 5) {
                        throw new IllegalArgumentException("bad member mapping row: " + line);
                    }
                    MemberKey key = new MemberKey(parts[1], parts[2], parts[3]);
                    Map<MemberKey, String> map =
                        "F".equals(parts[0]) ? out.fields : out.methods;
                    if (map.put(key, parts[4]) != null) {
                        throw new IllegalArgumentException("duplicate member source: " + key);
                    }
                }
                default -> throw new IllegalArgumentException(
                    "unknown mapping row kind: " + line
                );
            }
        }

        if (out.classes.isEmpty() && out.fields.isEmpty() && out.methods.isEmpty()) {
            throw new IllegalArgumentException("empty mapping");
        }

        Set<String> classTargets = new HashSet<>();
        for (String target : out.classes.values()) {
            if (!classTargets.add(target)) {
                throw new IllegalArgumentException("duplicate class target: " + target);
            }
        }
        return out;
    }

    private static byte[] remapClass(
        byte[] input,
        MappingSet mappings,
        boolean rewriteStrings
    ) {
        ClassReader reader = new ClassReader(input);
        ClassWriter writer = new ClassWriter(0);
        reader.accept(
            new ClassRemapper(writer, new MapRemapper(mappings, rewriteStrings)),
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

        MappingSet mappings = loadMap(mappingPath);
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
                    data = remapClass(data, mappings, rewriteStrings);
                } else if ("META-INF/MANIFEST.MF".equalsIgnoreCase(name)) {
                    data = remapManifest(data, mappings.classes);
                } else if (name.startsWith("META-INF/services/")) {
                    data = remapService(data, mappings.classes);
                }

                String target = outputName(name, mappings.classes);
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
        System.out.println("mapped_classes=" + mappings.classes.size());
        System.out.println("mapped_fields=" + mappings.fields.size());
        System.out.println("mapped_methods=" + mappings.methods.size());
        System.out.println("output_entries=" + output.size());
    }
}

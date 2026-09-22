import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.lang.model.element.Element;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

public final class SourceNameRewriter {
    private static final Base64.Decoder B64 = Base64.getUrlDecoder();

    private static String dec(String value) {
        int rem = value.length() % 4;
        if (rem != 0) {
            value += "=".repeat(4 - rem);
        }
        return new String(B64.decode(value), StandardCharsets.UTF_8);
    }

    private static final class Target {
        final String sourceFile;
        final long declarationStart;
        final String oldName;
        final String newName;
        final String symbolId;
        boolean declarationFound = false;

        Target(
            String sourceFile,
            long declarationStart,
            String oldName,
            String newName,
            String symbolId
        ) {
            this.sourceFile = sourceFile;
            this.declarationStart = declarationStart;
            this.oldName = oldName;
            this.newName = newName;
            this.symbolId = symbolId;
        }

        String key() {
            return sourceFile + ":" + declarationStart;
        }
    }

    private static final class Replacement {
        final int start;
        final int end;
        final String oldText;
        final String newText;
        final String symbolId;

        Replacement(
            int start,
            int end,
            String oldText,
            String newText,
            String symbolId
        ) {
            this.start = start;
            this.end = end;
            this.oldText = oldText;
            this.newText = newText;
            this.symbolId = symbolId;
        }
    }

    private static List<Path> sources(Path root) throws IOException {
        try (Stream<Path> stream = Files.walk(root)) {
            return stream
                .filter(Files::isRegularFile)
                .filter(path -> path.toString().endsWith(".java"))
                .sorted()
                .collect(Collectors.toList());
        }
    }

    private static Map<String, Target> loadTargets(Path path) throws IOException {
        Map<String, Target> out = new LinkedHashMap<>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            if (line.isBlank() || line.startsWith("#")) {
                continue;
            }
            String[] parts = line.split("\\t", -1);
            if (parts.length != 5) {
                throw new IllegalArgumentException("bad source rename mapping row");
            }
            Target target = new Target(
                dec(parts[0]),
                Long.parseLong(parts[1]),
                dec(parts[2]),
                dec(parts[3]),
                dec(parts[4])
            );
            if (out.put(target.key(), target) != null) {
                throw new IllegalArgumentException(
                    "duplicate source rename target: " + target.key()
                );
            }
        }
        if (out.isEmpty()) {
            throw new IllegalArgumentException("source rename plan is empty");
        }
        return out;
    }

    private static int findDeclarationName(
        String source,
        int from,
        int to,
        String name
    ) {
        int result = -1;
        int index = Math.max(0, from);
        int limit = Math.min(source.length(), to);
        while (index < limit) {
            int hit = source.indexOf(name, index);
            if (hit < 0 || hit + name.length() > limit) {
                break;
            }
            boolean leftOk = hit == 0
                || !Character.isJavaIdentifierPart(source.charAt(hit - 1));
            int after = hit + name.length();
            boolean rightOk = after >= source.length()
                || !Character.isJavaIdentifierPart(source.charAt(after));
            if (leftOk && rightOk) {
                result = hit;
            }
            index = hit + Math.max(1, name.length());
        }
        return result;
    }

    private static String relative(Path root, CompilationUnitTree unit) {
        Path source = Paths.get(unit.getSourceFile().toUri())
            .toAbsolutePath().normalize();
        return root.relativize(source).toString().replace('\\', '/');
    }

    private static JavacTask task(
        JavaCompiler compiler,
        StandardJavaFileManager manager,
        List<Path> files,
        DiagnosticCollector<JavaFileObject> diagnostics,
        String classpath
    ) {
        List<String> options = new ArrayList<>();
        options.add("-proc:none");
        options.add("-Xlint:none");
        if (classpath != null && !classpath.isBlank()) {
            options.add("-classpath");
            options.add(classpath);
        }
        Iterable<? extends JavaFileObject> units =
            manager.getJavaFileObjectsFromPaths(files);
        return (JavacTask) compiler.getTask(
            null,
            manager,
            diagnostics,
            options,
            null,
            units
        );
    }

    private static void assertNoErrors(
        DiagnosticCollector<JavaFileObject> diagnostics,
        String phase
    ) {
        List<String> errors = diagnostics.getDiagnostics().stream()
            .filter(d -> d.getKind() == Diagnostic.Kind.ERROR)
            .limit(40)
            .map(d -> phase + ": " + d.toString())
            .collect(Collectors.toList());
        if (!errors.isEmpty()) {
            throw new IllegalStateException(
                "javac semantic analysis failed:\n" + String.join("\n", errors)
            );
        }
    }

    private static int rewrite(
        Path root,
        Map<String, Target> targets,
        String classpath
    ) throws Exception {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("system Java compiler unavailable");
        }
        List<Path> files = sources(root);
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();

        Map<String, String> sourceText = new HashMap<>();
        Map<String, List<Replacement>> replacements = new HashMap<>();
        IdentityHashMap<Element, Target> elements = new IdentityHashMap<>();

        try (StandardJavaFileManager manager =
                 compiler.getStandardFileManager(
                     diagnostics,
                     Locale.ROOT,
                     StandardCharsets.UTF_8
                 )) {
            JavacTask task = task(
                compiler,
                manager,
                files,
                diagnostics,
                classpath
            );
            Iterable<? extends CompilationUnitTree> parsed = task.parse();
            task.analyze();
            assertNoErrors(diagnostics, "input");

            Trees trees = Trees.instance(task);
            List<CompilationUnitTree> units = new ArrayList<>();
            parsed.forEach(units::add);

            for (CompilationUnitTree unit : units) {
                String rel = relative(root, unit);
                Path file = root.resolve(rel);
                String text = Files.readString(file, StandardCharsets.UTF_8);
                sourceText.put(rel, text);

                new TreePathScanner<Void, Void>() {
                    @Override
                    public Void visitVariable(
                        VariableTree node,
                        Void unused
                    ) {
                        long start = trees.getSourcePositions()
                            .getStartPosition(unit, node);
                        Target target = targets.get(rel + ":" + start);
                        if (target == null) {
                            return super.visitVariable(node, unused);
                        }
                        if (!node.getName().toString().equals(target.oldName)) {
                            throw new IllegalStateException(
                                target.symbolId
                                + ": declaration name mismatch at "
                                + rel + ":" + start
                            );
                        }
                        Element element = trees.getElement(getCurrentPath());
                        if (element == null) {
                            throw new IllegalStateException(
                                target.symbolId
                                + ": javac could not resolve declaration element"
                            );
                        }

                        long end = trees.getSourcePositions()
                            .getEndPosition(unit, node);
                        long initializerStart = node.getInitializer() == null
                            ? end
                            : trees.getSourcePositions()
                                .getStartPosition(unit, node.getInitializer());
                        int nameStart = findDeclarationName(
                            text,
                            (int) start,
                            (int) initializerStart,
                            target.oldName
                        );
                        if (nameStart < 0) {
                            throw new IllegalStateException(
                                target.symbolId
                                + ": could not locate declaration identifier"
                            );
                        }
                        replacements
                            .computeIfAbsent(rel, key -> new ArrayList<>())
                            .add(
                                new Replacement(
                                    nameStart,
                                    nameStart + target.oldName.length(),
                                    target.oldName,
                                    target.newName,
                                    target.symbolId
                                )
                            );
                        elements.put(element, target);
                        target.declarationFound = true;
                        return super.visitVariable(node, unused);
                    }
                }.scan(unit, null);
            }

            for (CompilationUnitTree unit : units) {
                String rel = relative(root, unit);
                new TreePathScanner<Void, Void>() {
                    @Override
                    public Void visitIdentifier(
                        IdentifierTree node,
                        Void unused
                    ) {
                        Element element = trees.getElement(getCurrentPath());
                        Target target = elements.get(element);
                        if (target != null) {
                            long start = trees.getSourcePositions()
                                .getStartPosition(unit, node);
                            long end = trees.getSourcePositions()
                                .getEndPosition(unit, node);
                            if (start >= 0 && end >= start) {
                                replacements
                                    .computeIfAbsent(
                                        rel,
                                        key -> new ArrayList<>()
                                    )
                                    .add(
                                        new Replacement(
                                            (int) start,
                                            (int) end,
                                            target.oldName,
                                            target.newName,
                                            target.symbolId
                                        )
                                    );
                            }
                        }
                        return super.visitIdentifier(node, unused);
                    }
                }.scan(unit, null);
            }
        }

        for (Target target : targets.values()) {
            if (!target.declarationFound) {
                throw new IllegalStateException(
                    target.symbolId
                    + ": accepted source declaration was not found"
                );
            }
        }

        int replacementCount = 0;
        for (Map.Entry<String, List<Replacement>> row : replacements.entrySet()) {
            String rel = row.getKey();
            String text = sourceText.get(rel);
            List<Replacement> edits = row.getValue();
            edits.sort(
                Comparator.comparingInt((Replacement r) -> r.start)
                    .thenComparingInt(r -> r.end)
            );

            int priorEnd = -1;
            for (Replacement edit : edits) {
                if (edit.start < priorEnd) {
                    throw new IllegalStateException(
                        "overlapping source replacements in " + rel
                    );
                }
                priorEnd = edit.end;
            }

            StringBuilder builder = new StringBuilder(text);
            ListIterator<Replacement> iterator =
                edits.listIterator(edits.size());
            while (iterator.hasPrevious()) {
                Replacement edit = iterator.previous();
                String current = builder.substring(edit.start, edit.end);
                if (!current.equals(edit.oldText)) {
                    throw new IllegalStateException(
                        edit.symbolId
                        + ": expected " + edit.oldText
                        + " at " + rel + ":" + edit.start
                        + " but found " + current
                    );
                }
                builder.replace(
                    edit.start,
                    edit.end,
                    edit.newText
                );
                replacementCount++;
            }
            Files.writeString(
                root.resolve(rel),
                builder.toString(),
                StandardCharsets.UTF_8
            );
        }
        return replacementCount;
    }

    private static void verifyRewritten(
        Path root,
        String classpath
    ) throws Exception {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();
        List<Path> files = sources(root);
        try (StandardJavaFileManager manager =
                 compiler.getStandardFileManager(
                     diagnostics,
                     Locale.ROOT,
                     StandardCharsets.UTF_8
                 )) {
            JavacTask task = task(
                compiler,
                manager,
                files,
                diagnostics,
                classpath
            );
            task.parse();
            task.analyze();
            assertNoErrors(diagnostics, "rewritten");
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 2 || args.length > 3) {
            throw new IllegalArgumentException(
                "usage: <source-root> <mapping.tsv> [classpath]"
            );
        }
        Path root = Paths.get(args[0]).toAbsolutePath().normalize();
        Path mapping = Paths.get(args[1]).toAbsolutePath().normalize();
        String classpath = args.length == 3 ? args[2] : "";

        Map<String, Target> targets = loadTargets(mapping);
        int replacements = rewrite(root, targets, classpath);
        verifyRewritten(root, classpath);

        long filesChanged = targets.values().stream()
            .map(target -> target.sourceFile)
            .distinct()
            .count();

        System.out.println("SPK_SOURCE_REWRITE_PASS");
        System.out.println("accepted_symbols=" + targets.size());
        System.out.println("files_changed=" + filesChanged);
        System.out.println("replacements=" + replacements);
    }
}

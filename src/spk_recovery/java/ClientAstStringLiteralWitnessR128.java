import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;
import javax.tools.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;

/** R128: parse-only source literal witnesses; no client-code execution. */
public final class ClientAstStringLiteralWitnessR128 {
    private static String enc(String value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(
            value.getBytes(StandardCharsets.UTF_8));
    }
    private static final class Scanner extends TreePathScanner<Void, Void> {
        private final String pkg;
        private final List<String> output;
        private String topType;
        private final Set<String> strings = new HashSet<>();

        Scanner(String pkg, List<String> output) {
            this.pkg = pkg;
            this.output = output;
        }

        @Override public Void visitClass(ClassTree node, Void ignored) {
            if (topType != null) {
                // Separate nested/anonymous classes have separate JVM CPs.
                // They cannot be attributed to the outer class by guessing.
                return null;
            }
            String name = node.getSimpleName().toString();
            if (name.isEmpty()) return null;
            topType = (pkg.isEmpty() ? "" : pkg + "/") + name;
            super.visitClass(node, ignored);
            for (String value : strings) {
                output.add(enc(topType) + "\t" + enc(value));
            }
            topType = null;
            strings.clear();
            return null;
        }

        @Override public Void visitLiteral(LiteralTree node, Void ignored) {
            if (topType != null && node.getValue() instanceof String) {
                strings.add((String) node.getValue());
            }
            return null;
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("ONE_ROOT");
        Path root = Paths.get(args[0]).toRealPath();
        List<Path> sources;
        try (Stream<Path> stream = Files.walk(root)) {
            sources = stream.filter(Files::isRegularFile)
                .filter(x -> x.toString().endsWith(".java"))
                .sorted().collect(Collectors.toList());
        }
        if (sources.isEmpty() || sources.size() > 5000) {
            throw new IllegalArgumentException("SOURCE_COUNT_BOUND");
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("JDK_REQUIRED");
        DiagnosticCollector<JavaFileObject> diagnostics =
            new DiagnosticCollector<>();
        List<String> rows = new ArrayList<>();
        try (StandardJavaFileManager files = compiler.getStandardFileManager(
                diagnostics, Locale.ROOT, StandardCharsets.UTF_8)) {
            JavacTask task = (JavacTask) compiler.getTask(
                null, files, diagnostics,
                Arrays.asList("--release", "11", "-proc:none", "-implicit:none"),
                null, files.getJavaFileObjectsFromPaths(sources));
            for (CompilationUnitTree unit : task.parse()) {
                String pkg = unit.getPackageName() == null ? ""
                    : unit.getPackageName().toString().replace('.', '/');
                new Scanner(pkg, rows).scan(unit, null);
            }
        }
        long failures = diagnostics.getDiagnostics().stream()
            .filter(d -> d.getKind() == Diagnostic.Kind.ERROR).count();
        if (failures != 0) throw new IllegalStateException(
            "JAVA_SOURCE_PARSE_ERROR_" + failures);
        Collections.sort(rows);
        for (String row : rows) System.out.println(row);
    }
}
